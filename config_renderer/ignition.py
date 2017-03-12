import json
import base64
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
        storage = self.get_storage_config()
        storage['files'] = self.get_files_config()

        return {
            'ignition': {
                'version': '2.0.0',
                'config': {},
            },
            'storage': storage,
            'networkd': {},
            'passwd': {
                'users': [{
                    'name': 'core',
                    'sshAuthorizedKeys': self.get_ssh_keys(),
                }],
            },
            'systemd': {
                'units': self.get_units_config(),
            },
        }

    def get_storage_config(self):
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
            }]
        }

    def get_files_config(self):
        files = self.get_common_files()

        if config.install_etc_hosts:
            files += [{
                'filesystem': 'root',
                'path': '/etc/hosts',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self._render_template('hosts')),
                },
            }]

        if self.node.is_k8s_apiserver or self.node.is_k8s_schedulable:
            files += self.get_k8s_files()

        if self.node.is_k8s_apiserver:
            files += self.get_k8s_apiserver_files()
            files += self.get_k8s_addons_files()

        return files

    def get_common_files(self):
        return [
            {
                'filesystem': 'root',
                'path': '/etc/sysctl.d/max-user-watches.conf',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self._render_template('sysctl-max-user-watches.conf')),
                },
            },
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

    def get_k8s_files(self):
        files = [
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/kubeconfig.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self._render_template('kubeconfig.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/cni/net.d/10-flannel.conf',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self._render_template('cni-flannel.conf')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/cni/docker_opts_cni.env',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self._render_template('cni-docker-opts.env')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/etc/flannel/options.env',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self._render_template('flannel-options.env')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-proxy.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self._render_template('manifests/kube-proxy.yaml')),
                },
            },
        ]

        if config.k8s_runtime == 'rkt':
            files += [{
                'filesystem': 'root',
                'path': '/opt/bin/host-rkt',
                'mode': 0o755,
                'contents': {
                    'source': to_data_url(self._render_template('host-rkt')),
                },
            }]

        return files

    def get_k8s_apiserver_files(self):
        return [
            {
                'filesystem': 'root',
                'path': '/opt/init-flannel',
                'mode': 0o755,
                'contents': {
                    'source': to_data_url(self._render_template('init-flannel')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-apiserver.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self._render_template('manifests/kube-apiserver.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-controller-manager.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self._render_template('manifests/kube-controller-manager.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-scheduler.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self._render_template('manifests/kube-scheduler.yaml')),
                },
            },
        ]

    def get_k8s_addons_files(self):
        return [
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/kube-dns-autoscaler-deployment.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self._render_template('manifests/kube-dns-autoscaler-deployment.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/kube-dns-deployment.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self._render_template('manifests/kube-dns-deployment.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/kube-dns-svc.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self._render_template('manifests/kube-dns-svc.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/heapster-deployment.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self._render_template('manifests/heapster-deployment.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/heapster-svc.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self._render_template('manifests/heapster-svc.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/kube-dashboard-deployment.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self._render_template('manifests/kube-dashboard-deployment.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/kube-dashboard-svc.yaml',
                'mode': 0o644,
                'contents': {
                    'source': to_data_url(self._render_template('manifests/kube-dashboard-svc.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/opt/k8s-addons',
                'mode': 0o755,
                'contents': {
                    'source': to_data_url(self._render_template('k8s-addons')),
                },
            },
        ]

    def get_ssh_keys(self):
        return [user.ssh_key for user in self.cluster.users.filter(models.User.ssh_key != '')]

    def get_units_config(self):
        units = self.get_common_units()

        if self.node.is_etcd_server:
            units += self.get_etcd_server_units()

        if self.node.is_k8s_apiserver or self.node.is_k8s_schedulable:
            units += self.get_k8s_units()

        if self.node.is_k8s_apiserver:
            units += self.get_k8s_addons_units()

        return units

    def get_etcd_server_units(self):
        etcd_version = self.cluster.etcd_version
        if etcd_version == 2:
            unit_name = 'etcd2.service'
        elif etcd_version == 3:
            unit_name = 'etcd-member.service'
        else:
            raise Exception('Unknown etcd version', etcd_version)

        return [
            self.get_unit(unit_name, enable=True, dropins=['40-etcd-cluster.conf']),
            # TODO: add support for etcd proxies
            self.get_unit('locksmithd.service', dropins=['40-etcd-lock.conf']),
        ]

    def get_common_units(self):
        flanneld_service_dropins = ['40-add-options.conf']
        if self.node.is_k8s_apiserver:
            flanneld_service_dropins += ['40-init-flannel.conf']

        return [
            self.get_unit('provision-report.service', enable=True),
            self.get_unit('docker.service', dropins=['40-flannel.conf']),
            self.get_unit('flanneld.service', dropins=flanneld_service_dropins),
        ]

    def get_k8s_units(self):
        units = [
            self.get_unit('kubelet.service', enable=True),
        ]

        if config.k8s_runtime == 'rkt':
            units += [
                self.get_unit('rkt-api.service', enable=True),
                self.get_unit('load-rkt-stage1.service', enable=True),
            ]

        return units

    def get_k8s_addons_units(self):
        return [
            self.get_unit('k8s-addons.service', enable=True),
        ]

    def get_unit(self, name, enable=False, dropins=None):
        if dropins:
            return {
                'name': name,
                'enable': enable,
                'dropins': [{
                    'name': dropin,
                    'contents': self._render_template('dropins/' + name + '/' + dropin),
                } for dropin in dropins],
            }
        else:
            return {
                'name': name,
                'enable': enable,
                'contents': self._render_template('units/' + name),
            }

    def _render_template(self, name):
        from . import render_template
        return render_template(name, self.node)


def to_data_url(data, mediatype='', b64=False):
    if b64:
        if not isinstance(data, bytes):
            data = data.encode('utf-8')
        return 'data:{};base64,{}'.format(mediatype, base64.b64encode(data).decode('ascii'))
    else:
        return 'data:{},{}'.format(mediatype, urllib.parse.quote(data))
