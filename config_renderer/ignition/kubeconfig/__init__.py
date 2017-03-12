from config_renderer.ignition.base import BaseIgnitionPackage

import config


class KubeconfigPackage(BaseIgnitionPackage):
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
                    'source': self.to_data_url(self.render_template('kubeconfig.yaml')),
                },
            },
        ]
