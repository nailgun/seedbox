from seedbox import config
from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class KubeconfigPackage(BaseIgnitionPackage):
    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': config.kubeconfig_path,
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kubeconfig.yaml')),
                },
            },
        ]
