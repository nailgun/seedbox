from seedbox import config
from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class RktRuntimePackage(BaseIgnitionPackage):
    def get_files(self):
        return [{
            'filesystem': 'root',
            'path': config.node_host_rkt_path,
            'mode': 0o755,
            'contents': {
                'source': self.to_data_url(self.render_template('host-rkt')),
            },
        }]

    def get_units(self):
        units = [
            self.get_unit('rkt-api.service', enable=True),
            self.get_unit('load-rkt-stage1.service', enable=True),
        ]

        if self.cluster.aci_proxy_url:
            units += [
                self.get_unit_dropins('rkt-api.service', ['30-proxy.conf']),
            ]

        return units
