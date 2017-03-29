from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class IptablesPackage(BaseIgnitionPackage):
    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': '/var/lib/iptables/rules-save',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('rules')),
                },
            },
        ]

    def get_units(self):
        return [
            self.enable_unit('iptables-restore.service'),
        ]
