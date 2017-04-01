from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class K8sAddonsPackage(BaseIgnitionPackage):
    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': '/opt/kubernetes/addons/kube-system-default-sa.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-system-default-sa.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/opt/kubernetes/addons/kube-dns-autoscaler-deployment.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-dns-autoscaler-deployment.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/opt/kubernetes/addons/kube-dns-deployment.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-dns-deployment.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/opt/kubernetes/addons/kube-dns-svc.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-dns-svc.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/opt/kubernetes/addons/heapster-deployment.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('heapster-deployment.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/opt/kubernetes/addons/heapster-svc.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('heapster-svc.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/opt/kubernetes/addons/kube-dashboard-deployment.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-dashboard-deployment.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/opt/kubernetes/addons/kube-dashboard-svc.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-dashboard-svc.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/opt/kubernetes/addons/install.sh',
                'mode': 0o755,
                'contents': {
                    'source': self.to_data_url(self.render_template('install.sh')),
                },
            },
        ]

    def get_units(self):
        return [
            self.get_unit('k8s-addons.service', enable=True),
        ]
