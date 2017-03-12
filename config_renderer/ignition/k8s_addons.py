from .base import BaseIgnitionPackage

import config


class K8sAddonsPackage(BaseIgnitionPackage):
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
                    'source': self.to_data_url(self.render_template('kube-dns-autoscaler-deployment.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/kube-dns-deployment.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-dns-deployment.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/kube-dns-svc.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-dns-svc.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/heapster-deployment.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('heapster-deployment.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/heapster-svc.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('heapster-svc.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/kube-dashboard-deployment.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-dashboard-deployment.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/srv/kubernetes/manifests/kube-dashboard-svc.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-dashboard-svc.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/opt/k8s-addons',
                'mode': 0o755,
                'contents': {
                    'source': self.to_data_url(self.render_template('install')),
                },
            },
        ]

    def get_units(self):
        return [
            self.get_unit('k8s-addons.service', enable=True),
        ]
