from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class RktRuntimePackage(BaseIgnitionPackage):
    def get_files(self):
        return [{
            'filesystem': 'root',
            'path': '/opt/bin/host-rkt',
            'mode': 0o755,
            'contents': {
                'source': self.to_data_url(self.render_template('host-rkt')),
            },
        }]

    def get_units(self):
        return [
            self.get_unit('rkt-api.service', enable=True),
            self.get_unit('load-rkt-stage1.service', enable=True),
        ]
