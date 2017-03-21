from seedbox import config
from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class K8sMasterManifestsPackage(BaseIgnitionPackage):
    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': config.k8s_manifests_path + '/kube-apiserver.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-apiserver.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': config.k8s_manifests_path + '/kube-controller-manager.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-controller-manager.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': config.k8s_manifests_path + '/kube-scheduler.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-scheduler.yaml')),
                },
            },
        ]
