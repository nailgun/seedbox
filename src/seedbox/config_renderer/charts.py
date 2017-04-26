import io
import os
import re
import tarfile

import requests
from jinja2 import Environment

from seedbox import config

NOT_SPECIFIED = object()


class Addon:
    base_url = 'https://github.com/kubernetes/kubernetes/raw/release-{version}/cluster/addons/{path}/'

    def __init__(self, name, version, manifest_files, vars_map=None, is_salt_template=False, path=None, base_url=None):
        if vars_map is None:
            vars_map = {}

        if path is None:
            path = name

        if base_url is None:
            base_url = self.base_url

        self.name = name
        self.version = version

        self.manifest_files = []
        for fname in manifest_files:
            fname = base_url.format(path=path, version=self.version) + fname
            self.manifest_files.append(fname)

        self.vars_map = vars_map
        self.is_salt_template = is_salt_template


class SaltPillarEmulator:
    def __init__(self, cluster):
        self.cluster = cluster

    def get(self, var_name, default=NOT_SPECIFIED):
        try:
            return getattr(self, '_' + var_name)
        except AttributeError:
            if default is NOT_SPECIFIED:
                raise
            else:
                return default

    @property
    def _num_nodes(self):
        return self.cluster.nodes.count()


# TODO: add notes
addons = {
    'dns': {
        '1.5': Addon('dns', '1.5', [
            'skydns-rc.yaml.sed',
            'skydns-svc.yaml.sed',
        ], {
            'DNS_DOMAIN': '{{ config.k8s_cluster_domain }}',
            'DNS_SERVER_IP': '{{ cluster.k8s_dns_service_ip }}',
        }),
        '1.6': Addon('dns', '1.6', [
            'kubedns-cm.yaml',
            'kubedns-sa.yaml',
            'kubedns-controller.yaml.sed',
            'kubedns-svc.yaml.sed',
        ], {
            'DNS_DOMAIN': '{{ config.k8s_cluster_domain }}',
            'DNS_SERVER_IP': '{{ cluster.k8s_dns_service_ip }}',
        }),
    },
    'dns-horizontal-autoscaler': {
        '1.5': Addon('dns-horizontal-autoscaler', '1.5', ['dns-horizontal-autoscaler.yaml']),
        '1.6': Addon('dns-horizontal-autoscaler', '1.6', ['dns-horizontal-autoscaler.yaml']),
    },
    'dashboard': {
        '1.5': Addon('dashboard', '1.5', [
            'dashboard-controller.yaml',
            'dashboard-service.yaml',
        ]),
        '1.6': Addon('dashboard', '1.6', [
            'dashboard-controller.yaml',
            'dashboard-service.yaml',
        ]),
    },
    'heapster': {
        '1.5': Addon('heapster', '1.5', [
            'heapster-controller.yaml',
            'heapster-service.yaml',
        ], is_salt_template=True, path='cluster-monitoring/standalone'),
        '1.6': Addon('heapster', '1.6', [
            'heapster-controller.yaml',
            'heapster-service.yaml',
        ], is_salt_template=True, path='cluster-monitoring/standalone'),
    },
}


class TarFile(tarfile.TarFile):
    def adddata(self, path, data):
        info = tarfile.TarInfo(path)
        info.size = len(data)
        self.addfile(info, io.BytesIO(data))


# TODO: refactor
def render_addon_tgz(cluster, addon):
    pillar = SaltPillarEmulator(cluster)

    tgz_fp = io.BytesIO()

    with TarFile.open(fileobj=tgz_fp, mode='w:gz') as tgz:
        chart = 'name: {}\nversion: {}\n'.format(addon.name, addon.version).encode('ascii')
        tgz.adddata(os.path.join(addon.name, 'Chart.yaml'), chart)
        for manifest_url in addon.manifest_files:
            manifest_file_name = os.path.basename(manifest_url)
            m = re.match(r'(.*\.yaml).*', manifest_file_name)
            if m:
                manifest_file_name = m.group(1)
            resp = requests.get(manifest_url)
            resp.raise_for_status()

            manifest_content = resp.content
            if addon.is_salt_template:
                jinja_env = Environment(keep_trailing_newline=True, autoescape=False)
                t = jinja_env.from_string(manifest_content.decode('ascii'))
                manifest_content = t.render({
                    'pillar': pillar,
                }).encode('ascii')
            else:
                for var_name in addon.vars_map.keys():
                    var_name = var_name.encode('ascii')
                    manifest_content = manifest_content.replace(b'$' + var_name, b'{{ .Values.%s }}' % var_name)

            tgz.adddata(os.path.join(addon.name, 'templates', manifest_file_name), manifest_content)

        jinja_env = Environment(autoescape=False)
        values = ''
        for var_name, var_value in addon.vars_map.items():
            values += var_name
            values += ': '
            t = jinja_env.from_string(var_value)
            values += t.render({
                'config': config,
                'cluster': cluster,
            })
            values += '\n'
        tgz.adddata(os.path.join(addon.name, 'values.yaml'), values.encode('ascii'))

    return tgz_fp.getvalue()
