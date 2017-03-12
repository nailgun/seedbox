import json
import base64
import itertools
import urllib.parse
from flask import request

import config
import models


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

        packages = [
            SystemPackage(request.url_root, self.node.target_config_version),
            CredentialsPackage(),
        ]

        if config.install_etc_hosts:
            packages += [
                EtcHostsPackage(self.cluster.nodes.all()),
            ]

        if self.node.is_etcd_server:
            packages += [
                EtcdServerPackage(self.cluster.etcd_version, self.node.fqdn, etcd_nodes),
            ]

        if self.node.is_k8s_apiserver or self.node.is_k8s_schedulable:
            packages += [
                KubeconfigPackage(self.cluster.name),
                CNIPackage(etcd_nodes),
                KubeletPackage(config.k8s_hyperkube_tag, self.node.fqdn, self.node.is_k8s_schedulable, self.node.is_k8s_apiserver, config.k8s_runtime, k8s_apiserver_nodes),
                KubeProxyPackage(config.k8s_hyperkube_tag, self.get_single_k8s_apiserver_endpoint(), set_kubeconfig=not self.node.is_k8s_apiserver),
            ]

            if config.k8s_runtime == 'rkt':
                packages += [
                    RktRuntimePackage(),
                ]

        if self.node.is_k8s_apiserver:
            packages += [
                FlannelInitPackage(etcd_nodes),
                K8sMasterManifestsPackage(config.k8s_hyperkube_tag, etcd_nodes),
                K8sAddonsManifestsPackage(),
            ]

        return packages

    def get_storage_config(self, files):
        return {
            'disks': [{
                'device': config.root_disk,
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
                    'device': config.root_partition,
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
                return 'https://{}:{}'.format(node.fqdn, config.k8s_apiserver_secure_port)


class IgnitionPackage(object):
    name = None
    template_context = {}

    def get_files(self):
        return ()

    def get_units(self):
        return ()

    def get_unit(self, name, enable=False, dropins=None):
        if dropins:
            return {
                'name': name,
                'enable': enable,
                'dropins': [{
                    'name': dropin,
                    'contents': self.render_template(dropin),
                } for dropin in dropins],
            }
        else:
            return {
                'name': name,
                'enable': enable,
                'contents': self.render_template(name),
            }

    def get_template_context(self):
        return self.template_context

    def render_template(self, name):
        from . import jinja
        return jinja.get_template(self.name + '/' + name).render(self.get_template_context())


class SystemPackage(IgnitionPackage):
    name = 'system'

    def __init__(self, url_root, target_config_version):
        self.template_context = {
            'url_root': url_root,
            'target_config_version': target_config_version
        }

    def get_files(self):
        return [{
            'filesystem': 'root',
            'path': '/etc/sysctl.d/max-user-watches.conf',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(self.render_template('sysctl-max-user-watches.conf')),
            },
        }]

    def get_units(self):
        return [
            self.get_unit('provision-report.service', enable=True),
        ]


class CredentialsPackage(IgnitionPackage):
    name = 'credentials'

    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': config.ca_cert_path,
                'mode': 0o444,
                'contents': {
                    'source': request.url_root + 'credentials/ca.pem',
                },
            },
            {
                'filesystem': 'root',
                'path': config.node_cert_path,
                'mode': 0o444,
                'contents': {
                    'source': request.url_root + 'credentials/node.pem',
                },
            },
            {
                'filesystem': 'root',
                'path': config.node_key_path,
                'mode': 0o400,
                'contents': {
                    'source': request.url_root + 'credentials/node-key.pem',
                },
            },
        ]


class EtcHostsPackage(IgnitionPackage):
    name = 'etc-hosts'

    def __init__(self, nodes):
        self.template_context = {
            'nodes': nodes,
        }

    def get_files(self):
        return [{
            'filesystem': 'root',
            'path': '/etc/hosts',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(self.render_template('hosts')),
            },
        }]


class EtcdServerPackage(IgnitionPackage):
    name = 'etcd-server'

    def __init__(self, version, hostname, etcd_nodes):
        self.version = version
        self.template_context = {
            'version': version,
            'hostname': hostname,
            'etcd_nodes': etcd_nodes,
            'config': config,
        }

    def get_units(self):
        if self.version == 2:
            unit_name = 'etcd2.service'
        elif self.version == 3:
            unit_name = 'etcd-member.service'
        else:
            raise Exception('Unknown etcd version', self.version)

        return [
            self.get_unit(unit_name, enable=True, dropins=['40-etcd-cluster.conf']),
            # TODO: add support for etcd proxies
            self.get_unit('locksmithd.service', dropins=['40-etcd-lock.conf']),
        ]


class KubeconfigPackage(IgnitionPackage):
    name = 'kubeconfig'

    def __init__(self, cluster_name):
        self.template_context = {
            'cluster_name': cluster_name,
            'config': config,
        }

    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/kubeconfig.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self.render_template('kubeconfig.yaml')),
                },
            },
        ]


class CNIPackage(IgnitionPackage):
    name = 'cni'

    def __init__(self, etcd_nodes):
        self.template_context = {
            # TODO: move this to mixin
            'etcd_endpoints': ['http://{}:{}'.format(n.fqdn, config.etcd_client_port) for n in etcd_nodes],
        }

    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/cni/net.d/10-flannel.conf',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self.render_template('cni.conf')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/etc/flannel/options.env',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self.render_template('options.env')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/cni/docker_opts_cni.env',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self.render_template('docker-opts.env')),
                },
            },
        ]

    def get_units(self):
        return [
            self.get_unit('flanneld.service', dropins=['40-add-options.conf']),
            self.get_unit('docker.service', dropins=['40-flannel.conf']),
        ]


class KubeletPackage(IgnitionPackage):
    name = 'kubelet'

    def __init__(self, hyperkube_tag, hostname, is_schedulable, is_apiserver, runtime, apiserver_nodes):
        self.template_context = {
            'hyperkube_tag': hyperkube_tag,
            'hostname': hostname,
            'is_schedulable': is_schedulable,
            'is_apiserver': is_apiserver,
            'runtime': runtime,
            'config': config,
            'apiserver_endpoints': ['https://{}:{}'.format(n.fqdn, config.k8s_apiserver_secure_port) for n in apiserver_nodes],
        }

    def get_units(self):
        return [
            self.get_unit('kubelet.service', enable=True),
        ]


class KubeProxyPackage(IgnitionPackage):
    name = 'kube-proxy'

    def __init__(self, hyperkube_tag, apiserver_endpoint, set_kubeconfig):
        self.template_context = {
            'hyperkube_tag': hyperkube_tag,
            'apiserver_endpoint': apiserver_endpoint,
            'set_kubeconfig': set_kubeconfig,
        }

    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-proxy.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self.render_template('manifest.yaml')),
                },
            },
        ]


class RktRuntimePackage(IgnitionPackage):
    name = 'rkt-runtime'

    def get_files(self):
        return [{
            'filesystem': 'root',
            'path': '/opt/bin/host-rkt',
            'mode': 0o755,
            'contents': {
                'source': to_data_url(self.render_template('host-rkt')),
            },
        }]

    def get_units(self):
        return [
            self.get_unit('rkt-api.service', enable=True),
            self.get_unit('load-rkt-stage1.service', enable=True),
        ]


class FlannelInitPackage(IgnitionPackage):
    name = 'flannel-init'

    def __init__(self, etcd_nodes):
        self.template_context = {
            # TODO: move this to mixin
            'etcd_endpoints': ['http://{}:{}'.format(n.fqdn, config.etcd_client_port) for n in etcd_nodes],
            'config': config,
        }

    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': '/opt/init-flannel',
                'mode': 0o755,
                'contents': {
                    'source': to_data_url(self.render_template('init')),
                },
            },
        ]

    def get_units(self):
        return [
            self.get_unit('flanneld.service', dropins=['40-init-flannel.conf']),
        ]


class K8sMasterManifestsPackage(IgnitionPackage):
    name = 'k8s-master-manifests'

    def __init__(self, hyperkube_tag, etcd_nodes):
        self.template_context = {
            'hyperkube_tag': hyperkube_tag,
            # TODO: move this to mixin
            'etcd_endpoints': ['http://{}:{}'.format(n.fqdn, config.etcd_client_port) for n in etcd_nodes],
            'config': config,
        }

    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-apiserver.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self.render_template('kube-apiserver.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-controller-manager.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self.render_template('kube-controller-manager.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-scheduler.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self.render_template('kube-scheduler.yaml')),
                },
            },
        ]


class K8sAddonsManifestsPackage(IgnitionPackage):
    name = 'k8s-addons'

    def __init__(self):
        self.template_context = {
            'config': config,
        }

    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/kube-dns-autoscaler-deployment.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self.render_template('kube-dns-autoscaler-deployment.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/kube-dns-deployment.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self.render_template('kube-dns-deployment.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/kube-dns-svc.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self.render_template('kube-dns-svc.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/heapster-deployment.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self.render_template('heapster-deployment.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/heapster-svc.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self.render_template('heapster-svc.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/kube-dashboard-deployment.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self.render_template('kube-dashboard-deployment.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/kube-dashboard-svc.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self.render_template('kube-dashboard-svc.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/opt/k8s-addons',
                'mode': 0o755,
                'contents': {
                    'source': to_data_url(self.render_template('install')),
                },
            },
        ]

    def get_units(self):
        return [
            self.get_unit('k8s-addons.service', enable=True),
        ]


def to_data_url(data, mediatype='', b64=False):
    if b64:
        if not isinstance(data, bytes):
            data = data.encode('utf-8')
        return 'data:{};base64,{}'.format(mediatype, base64.b64encode(data).decode('ascii'))
    else:
        return 'data:{},{}'.format(mediatype, urllib.parse.quote(data))
