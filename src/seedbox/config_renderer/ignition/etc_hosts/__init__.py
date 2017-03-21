from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class EtcHostsPackage(BaseIgnitionPackage):
    def get_files(self):
        return [{
            'filesystem': 'root',
            'path': '/etc/hosts',
            'mode': 0o644,
            'contents': {
                'source': self.to_data_url(self.render_template('hosts')),
            },
        }]
