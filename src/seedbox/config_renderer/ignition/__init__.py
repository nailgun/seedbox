import itertools
import json

from flask import request

from seedbox import models


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
        packages = [P(self.node, request.url_root) for P in self.get_package_classes()]
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

    def get_package_classes(self):
        from .system import SystemPackage
        from .credentials import CredentialsPackage
        from .flannel import FlannelPackage

        packages = [
            SystemPackage,
            CredentialsPackage,
            FlannelPackage,
        ]

        if self.cluster.manage_etc_hosts:
            from .etc_hosts import EtcHostsPackage
            packages += [
                EtcHostsPackage,
            ]

        if self.node.is_etcd_server:
            from .etcd_server import EtcdServerPackage
            packages += [
                EtcdServerPackage,
            ]

        if self.node.is_k8s_schedulable or self.node.is_k8s_apiserver:
            from .kubeconfig import KubeconfigPackage
            from .kubelet import KubeletPackage
            from .kube_proxy import KubeProxyPackage
            packages += [
                KubeconfigPackage,
                KubeletPackage,
                KubeProxyPackage,
            ]

            if self.cluster.k8s_cni:
                from .cni import CNIPackage
                packages += [
                    CNIPackage,
                ]

        if self.node.is_k8s_apiserver:
            from .k8s_master_manifests import K8sMasterManifestsPackage
            packages += [
                K8sMasterManifestsPackage,
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
