from seedbox import config
from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class CredentialsPackage(BaseIgnitionPackage):
    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': config.ca_cert_path,
                'mode': 0o444,
                'contents': {
                    'source': self.url_root + 'credentials/ca.pem',
                },
            },
            {
                'filesystem': 'root',
                'path': config.node_cert_path,
                'mode': 0o444,
                'contents': {
                    'source': self.url_root + 'credentials/node.pem',
                },
            },
            {
                'filesystem': 'root',
                'path': config.node_key_path,
                'mode': 0o444,
                'contents': {
                    'source': self.url_root + 'credentials/node-key.pem',
                },
            },
        ]
