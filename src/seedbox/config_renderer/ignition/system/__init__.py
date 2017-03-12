from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class SystemPackage(BaseIgnitionPackage):
    def __init__(self, url_root, target_config_version, fqdn):
        self.fqdn = fqdn
        self.template_context = {
            'url_root': url_root,
            'target_config_version': target_config_version,
        }

    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': '/etc/sysctl.d/max-user-watches.conf',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('sysctl-max-user-watches.conf')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/etc/hostname',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.fqdn + '\n'),
                },
            },
        ]

    def get_units(self):
        return [
            self.get_unit('provision-report.service', enable=True),
        ]
