from .base import BaseIgnitionPackage

import config


class CredentialsPackage(BaseIgnitionPackage):
    name = 'credentials'

    def __init__(self, url_root):
        self.url_root = url_root

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
                'mode': 0o400,
                'contents': {
                    'source': self.url_root + 'credentials/node-key.pem',
                },
            },
        ]
