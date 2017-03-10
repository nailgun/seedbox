import json
import base64
import urllib.parse
from flask import request

import config
import models


def render(node, indent=False):
    from . import render_template

    def render_tpl(template_name):
        return render_template(template_name, node)

    def get_unit(name, enable=False, dropins=None):
        if dropins:
            return {
                'name': name,
                'enable': enable,
                'dropins': [{
                    'name': dropin,
                    'contents': render_tpl('dropins/' + name + '/' + dropin),
                } for dropin in dropins],
            }
        else:
            return {
                'name': name,
                'enable': enable,
                'contents': render_tpl('units/' + name),
            }

    ssh_keys = [user.ssh_key for user in node.cluster.users.filter(models.User.ssh_key != '')]

    files = [
        {
            'filesystem': 'root',
            'path': '/etc/sysctl.d/max-user-watches.conf',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(render_tpl('sysctl-max-user-watches.conf')),
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
        {
            'filesystem': 'root',
            'path': '/etc/kubernetes/cni/net.d/10-flannel.conf',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(render_tpl('cni-flannel.conf')),
            },
        },
        {
            'filesystem': 'root',
            'path': '/etc/kubernetes/cni/docker_opts_cni.env',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(render_tpl('cni-docker-opts.env')),
            },
        },
        {
            'filesystem': 'root',
            'path': '/etc/flannel/options.env',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(render_tpl('flannel-options.env')),
            },
        },
        {
            'filesystem': 'root',
            'path': '/opt/init-flannel',
            'mode': 0o755,
            'contents': {
                'source': to_data_url(render_tpl('init-flannel')),
            },
        },
        {
            'filesystem': 'root',
            'path': '/etc/kubernetes/manifests/kube-proxy.yaml',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(render_tpl('manifests/kube-proxy.yaml')),
            },
        },
        {
            'filesystem': 'root',
            'path': '/etc/kubernetes/manifests/kube-apiserver.yaml',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(render_tpl('manifests/kube-apiserver.yaml')),
            },
        },
        {
            'filesystem': 'root',
            'path': '/etc/kubernetes/manifests/kube-controller-manager.yaml',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(render_tpl('manifests/kube-controller-manager.yaml')),
            },
        },
        {
            'filesystem': 'root',
            'path': '/etc/kubernetes/manifests/kube-scheduler.yaml',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(render_tpl('manifests/kube-scheduler.yaml')),
            },
        },
        {
            'filesystem': 'root',
            'path': '/srv/kubernetes/manifests/kube-dns-autoscaler-deployment.yaml',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(render_tpl('manifests/kube-dns-autoscaler-deployment.yaml')),
            },
        },
        {
            'filesystem': 'root',
            'path': '/srv/kubernetes/manifests/kube-dns-deployment.yaml',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(render_tpl('manifests/kube-dns-deployment.yaml')),
            },
        },
        {
            'filesystem': 'root',
            'path': '/srv/kubernetes/manifests/kube-dns-svc.yaml',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(render_tpl('manifests/kube-dns-svc.yaml')),
            },
        },
        {
            'filesystem': 'root',
            'path': '/srv/kubernetes/manifests/heapster-deployment.yaml',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(render_tpl('manifests/heapster-deployment.yaml')),
            },
        },
        {
            'filesystem': 'root',
            'path': '/srv/kubernetes/manifests/heapster-svc.yaml',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(render_tpl('manifests/heapster-svc.yaml')),
            },
        },
        {
            'filesystem': 'root',
            'path': '/srv/kubernetes/manifests/kube-dashboard-deployment.yaml',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(render_tpl('manifests/kube-dashboard-deployment.yaml')),
            },
        },
        {
            'filesystem': 'root',
            'path': '/srv/kubernetes/manifests/kube-dashboard-svc.yaml',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(render_tpl('manifests/kube-dashboard-svc.yaml')),
            },
        },
        {
            'filesystem': 'root',
            'path': '/opt/k8s-addons',
            'mode': 0o755,
            'contents': {
                'source': to_data_url(render_tpl('k8s-addons')),
            },
        },
    ]

    if config.install_etc_hosts:
        files.append({
            'filesystem': 'root',
            'path': '/etc/hosts',
            'mode': 0o644,
            'contents': {
                'source': to_data_url(render_tpl('hosts')),
            },
        })

    if config.k8s_runtime == 'rkt':
        files.append({
            'filesystem': 'root',
            'path': '/opt/bin/host-rkt',
            'mode': 0o755,
            'contents': {
                'source': to_data_url(render_tpl('host-rkt')),
            },
        })

    units = [
        get_unit('provision-report.service', enable=True),
        get_unit('flanneld.service', dropins=['40-ExecStartPre-symlink.conf']),
        get_unit('docker.service', dropins=['40-flannel.conf']),
        get_unit('kubelet.service', enable=True),
        get_unit('k8s-addons.service', enable=True),
    ]

    if config.k8s_runtime == 'rkt':
        units += [
            get_unit('rkt-api.service', enable=True),
            get_unit('load-rkt-stage1.service', enable=True),
        ]

    if node.is_etcd_server:
        etcd_version = node.cluster.etcd_version
        if etcd_version == 2:
            unit_name = 'etcd2.service'
        elif etcd_version == 3:
            unit_name = 'etcd-member.service'
        else:
            raise Exception('Unknown etcd version', etcd_version)
        units.append(get_unit(unit_name, enable=True, dropins=['40-etcd-cluster.conf']))
        units.append(get_unit('locksmithd.service', dropins=['40-etcd-lock.conf']))

    cfg = {
        'ignition': {
            'version': '2.0.0',
            'config': {},
        },
        'storage': {
            'files': files,
        },
        'networkd': {},
        'passwd': {
            'users': [{
                'name': 'core',
                'sshAuthorizedKeys': ssh_keys,
            }],
        },
        'systemd': {
            'units': units,
        },
    }

    if indent:
        return json.dumps(cfg, indent=2)
    else:
        return json.dumps(cfg, separators=(',', ':'))


def to_data_url(data, mediatype='', b64=False):
    if b64:
        if not isinstance(data, bytes):
            data = data.encode('utf-8')
        return 'data:{};base64,{}'.format(mediatype, base64.b64encode(data).decode('ascii'))
    else:
        return 'data:{},{}'.format(mediatype, urllib.parse.quote(data))
