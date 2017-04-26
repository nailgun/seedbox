import io
import os
import re
import tarfile

import requests
from jinja2 import Environment

from seedbox import config

basedir = os.path.dirname(__file__)


class Addon:
    def __init__(self, manifest_files, vars_map=None, is_salt_template=False):
        if vars_map is None:
            vars_map = {}
        self.manifest_files = manifest_files
        self.vars_map = vars_map
        self.is_salt_template = is_salt_template


# TODO: replace with something better
class Ref:
    def __init__(self, path):
        self.path = path

    @property
    def value(self):
        obj = addons
        for path_part in self.path.split('|'):
            try:
                obj = obj[path_part]
            except TypeError:
                obj = getattr(obj, path_part)
        return obj


class SaltPillarEmulator:
    NO_DEFAULT = object()

    def __init__(self, cluster):
        self.cluster = cluster

    def get(self, var_name, default=NO_DEFAULT):
        try:
            return getattr(self, '_' + var_name)
        except AttributeError:
            if default is self.NO_DEFAULT:
                raise
            else:
                return default

    @property
    def _num_nodes(self):
        return self.cluster.nodes.count()


# TODO: add notes
addons = {
    'dns': {
        '1.5': Addon(['https://github.com/kubernetes/kubernetes/raw/release-1.5/cluster/addons/dns/' + name for name in [
            'skydns-rc.yaml.sed',
            'skydns-svc.yaml.sed',
        ]], {
            'DNS_DOMAIN': 'config.k8s_cluster_domain',
            'DNS_SERVER_IP': 'cluster.k8s_dns_service_ip',
        }),
        '1.6': Addon(['https://github.com/kubernetes/kubernetes/raw/release-1.6/cluster/addons/dns/' + name for name in [
            'kubedns-cm.yaml',
            'kubedns-sa.yaml',
            'kubedns-controller.yaml.sed',
            'kubedns-svc.yaml.sed',
        ]], Ref('dns|1.5|vars_map')),
    },
    'dns-horizontal-autoscaler': {
        '1.5': Addon(['https://github.com/kubernetes/kubernetes/raw/release-1.5/cluster/addons/dns-horizontal-autoscaler/dns-horizontal-autoscaler.yaml']),
        '1.6': Addon(['https://github.com/kubernetes/kubernetes/raw/release-1.6/cluster/addons/dns-horizontal-autoscaler/dns-horizontal-autoscaler.yaml']),
    },
    'dashboard': {
        '1.5': Addon(['https://github.com/kubernetes/kubernetes/raw/release-1.5/cluster/addons/dashboard/' + name for name in [
            'dashboard-controller.yaml',
            'dashboard-service.yaml',
        ]]),
        '1.6': Ref('dashboard|1.5'),
    },
    'heapster': {
        '1.5': Addon(['https://github.com/kubernetes/kubernetes/raw/release-1.5/cluster/addons/cluster-monitoring/standalone/' + name for name in [
            'heapster-controller.yaml',
            'heapster-service.yaml',
        ]], is_salt_template=True),
        '1.6': Addon(['https://github.com/kubernetes/kubernetes/raw/release-1.6/cluster/addons/cluster-monitoring/standalone/' + name for name in [
            'heapster-controller.yaml',
            'heapster-service.yaml',
        ]], is_salt_template=True),
    },
}


class TarFile(tarfile.TarFile):
    def adddata(self, path, data):
        info = tarfile.TarInfo(path)
        info.size = len(data)
        self.addfile(info, io.BytesIO(data))


# TODO: refactor
def render_addon_tgz(cluster, addon, name, version):
    pillar = SaltPillarEmulator(cluster)
    if isinstance(addon, Ref):
        addon = addon.value

    manifest_files = addon.manifest_files
    if isinstance(manifest_files, Ref):
        manifest_files = manifest_files.value

    vars_map = addon.vars_map
    if isinstance(vars_map, Ref):
        vars_map = vars_map.value

    tgz_fp = io.BytesIO()

    with TarFile.open(fileobj=tgz_fp, mode='w:gz') as tgz:
        chart = 'name: {}\nversion: {}\n'.format(name, version).encode('ascii')
        tgz.adddata(os.path.join(name, 'Chart.yaml'), chart)
        for manifest_url in manifest_files:
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
                for var_name in vars_map.keys():
                    var_name = var_name.encode('ascii')
                    manifest_content = manifest_content.replace(b'$' + var_name, b'{{ .Values.%s }}' % var_name)

            tgz.adddata(os.path.join(name, 'templates', manifest_file_name), manifest_content)

        jinja_env = Environment(autoescape=False)
        values = ''
        for var_name, var_path in vars_map.items():
            values += var_name
            values += ': '
            t = jinja_env.from_string("'{{ " + var_path + " }}'")
            values += t.render({
                'config': config,
                'cluster': cluster,
            })
            values += '\n'
        tgz.adddata(os.path.join(name, 'values.yaml'), values.encode('ascii'))

    return tgz_fp.getvalue()
