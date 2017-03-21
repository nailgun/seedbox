from seedbox import config
from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class KubeProxyPackage(BaseIgnitionPackage):
    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': config.k8s_manifests_path + '/kube-proxy.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-proxy.yaml')),
                },
            },
        ]
