from .base import BaseIgnitionPackage


class EtcHostsPackage(BaseIgnitionPackage):
    name = 'etc-hosts'

    def __init__(self, nodes):
        self.template_context = {
            'nodes': nodes,
        }

    def get_files(self):
        return [{
            'filesystem': 'root',
            'path': '/etc/hosts',
            'mode': 0o644,
            'contents': {
                'source': self.to_data_url(self.render_template('hosts')),
            },
        }]
