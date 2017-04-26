import io
import os
import re
import tarfile

import requests
from jinja2 import Environment

from seedbox import config

NOT_SPECIFIED = object()
jinja_var_env = Environment(autoescape=False)
jinja_env = Environment(keep_trailing_newline=True, autoescape=False)


class Addon:
    base_url = 'https://github.com/kubernetes/kubernetes/raw/release-{version}/cluster/addons/{path}/'
    encoding = 'utf-8'

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

    def render_files(self, cluster):
        yield 'Chart.yaml', self.render_chart_yaml()
        yield 'values.yaml', self.render_values_yaml(cluster)

        for url in self.manifest_files:
            filename, content = self.render_manifest_file(cluster, url)
            yield os.path.join('templates', filename), content

    def render_chart_yaml(self):
        return 'name: {}\nversion: {}\n'.format(self.name, self.version).encode(self.encoding)

    def render_values_yaml(self, cluster):
        return ''.join('{}: {}\n'.format(var_name, jinja_var_env.from_string(var_tpl).render({
            'config': config,
            'cluster': cluster,
        })) for var_name, var_tpl in self.vars_map.items()).encode(self.encoding)

    def render_manifest_file(self, cluster, url):
        pillar = SaltPillarEmulator(cluster)

        resp = requests.get(url)
        resp.raise_for_status()

        content = resp.content
        if self.is_salt_template:
            t = jinja_env.from_string(content.decode(self.encoding))
            content = t.render({
                'pillar': pillar,
            }).encode(self.encoding)
        else:
            for var_name in self.vars_map.keys():
                var_name = var_name.encode(self.encoding)
                content = content.replace(b'$' + var_name, b'{{ .Values.%s }}' % var_name)

        filename = os.path.basename(url)
        m = re.match(r'(.*\.yaml).*', filename)
        if m:
            filename = m.group(1)

        return filename, content


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


def render_addon_tgz(cluster, addon):
    tgz_fp = io.BytesIO()
    with TarFile.open(fileobj=tgz_fp, mode='w:gz') as tgz:
        for path, content in addon.render_files(cluster):
            tgz.adddata(os.path.join(addon.name, path), content)
    return tgz_fp.getvalue()
