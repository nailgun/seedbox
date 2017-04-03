from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class DnsmasqPackage(BaseIgnitionPackage):
    def get_files(self):
        return [{
            'filesystem': 'root',
            'path': '/etc/systemd/resolved.conf.d/30-dnsmasq.conf',
            'mode': 0o644,
            'contents': {
                'source': self.to_data_url(self.render_template('resolved.conf')),
            },
        }]

    def get_units(self):
        return [
            self.get_unit('dnsmasq.service', enable=True)
        ]
