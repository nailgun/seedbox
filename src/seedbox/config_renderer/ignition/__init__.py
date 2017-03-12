import json
import itertools

from flask import request

from seedbox import config, models


# TODO: deploy addons separately via admin button
def render(node, indent=False):
    return IgnitionConfig(node).render(indent)


class IgnitionConfig(object):
    def __init__(self, node):
        self.node = node
        self.cluster = node.cluster

    def render(self, indent=False):
        content = self.get_content()
        if indent:
            return json.dumps(content, indent=2)
        else:
            return json.dumps(content, separators=(',', ':'))

    def get_content(self):
        packages = self.get_packages()
        files = list(itertools.chain.from_iterable(p.get_files() for p in packages))
        units = list(itertools.chain.from_iterable(p.get_units() for p in packages))

        return {
            'ignition': {
                'version': '2.0.0',
                'config': {},
            },
            'storage': self.get_storage_config(files),
            'networkd': {},
            'passwd': {
                'users': [{
                    'name': 'core',
                    'sshAuthorizedKeys': self.get_ssh_keys(),
                }],
            },
            'systemd': {
                'units': units
            },
        }

    def get_packages(self):
        etcd_nodes = self.cluster.nodes.filter_by(is_etcd_server=True)
        k8s_apiserver_nodes = self.cluster.nodes.filter_by(is_k8s_apiserver=True)

        from .system import SystemPackage
        from .credentials import CredentialsPackage

        packages = [
            SystemPackage(request.url_root, self.node.target_config_version, self.node.fqdn),
            CredentialsPackage(request.url_root),
        ]

        if self.cluster.manage_etc_hosts:
            from .etc_hosts import EtcHostsPackage
            packages += [
                EtcHostsPackage(self.cluster.nodes.all()),
            ]

        if self.node.is_etcd_server:
            from .etcd_server import EtcdServerPackage
            packages += [
                EtcdServerPackage(self.cluster.etcd_version, self.node.fqdn, etcd_nodes),
            ]

        if self.node.is_k8s_apiserver or self.node.is_k8s_schedulable:
            from .kubeconfig import KubeconfigPackage
            from .cni import CNIPackage
            from .kubelet import KubeletPackage
            from .kube_proxy import KubeProxyPackage
            runtime = models.Runtime(self.cluster.k8s_runtime)
            packages += [
                KubeconfigPackage(self.cluster.name),
                CNIPackage(etcd_nodes),
                KubeletPackage(self.cluster.k8s_hyperkube_tag, self.node.fqdn, self.node.is_k8s_schedulable, self.node.is_k8s_apiserver, runtime.name, k8s_apiserver_nodes, self.cluster.k8s_dns_service_ip),
                KubeProxyPackage(self.cluster.k8s_hyperkube_tag, self.get_single_k8s_apiserver_endpoint(), set_kubeconfig=not self.node.is_k8s_apiserver),
            ]

            if runtime == models.Runtime.rkt:
                from .rkt_runtime import RktRuntimePackage
                packages += [
                    RktRuntimePackage(),
                ]

        if self.node.is_k8s_apiserver:
            from .flannel_init import FlannelInitPackage
            from .k8s_master_manifests import K8sMasterManifestsPackage
            from .k8s_addons import K8sAddonsPackage
            packages += [
                FlannelInitPackage(etcd_nodes, self.cluster.k8s_pod_network),
                K8sMasterManifestsPackage(self.cluster.k8s_hyperkube_tag, etcd_nodes, self.cluster.k8s_service_network),
                K8sAddonsPackage(self.cluster.k8s_dns_service_ip),
            ]

        return packages

    def get_storage_config(self, files):
        return {
            'disks': [{
                'device': self.node.root_disk,
                'wipeTable': True,
                'partitions': [{
                    'label': 'ROOT',
                    'number': 0,
                    'start': 0,
                    'size': 0,
                }],
            }],
            'filesystems': [{
                'name': 'root',
                'mount': {
                    'device': self.node.root_partition,
                    'format': 'ext4',
                    'create': {
                        'force': True,
                        'options': ['-LROOT'],
                    },
                },
            }],
            'files': files,
        }

    def get_ssh_keys(self):
        return [user.ssh_key for user in self.cluster.users.filter(models.User.ssh_key != '')]

    def get_single_k8s_apiserver_endpoint(self):
        if self.node.is_k8s_apiserver:
            return 'http://127.0.0.1:{}'.format(config.k8s_apiserver_insecure_port)
        else:
            node = self.cluster.nodes.filter_by(is_k8s_apiserver_lb=True).first()
            if node:
                return 'https://{}:{}'.format(node.fqdn, config.k8s_apiserver_lb_port)
            else:
                node = self.cluster.nodes.filter_by(is_k8s_apiserver=True).first()

            if not node:
                raise Exception('no k8s apiserver node')

            return 'https://{}:{}'.format(node.fqdn, config.k8s_apiserver_secure_port)
