from .base import BaseIgnitionPackage

import config


class FlannelInitPackage(BaseIgnitionPackage):
    name = 'flannel-init'

    def __init__(self, etcd_nodes):
        self.template_context = {
            # TODO: move this to mixin
            'etcd_endpoints': ['http://{}:{}'.format(n.fqdn, config.etcd_client_port) for n in etcd_nodes],
            'config': config,
        }

    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': '/opt/init-flannel',
                'mode': 0o755,
                'contents': {
                    'source': self.to_data_url(self.render_template('init')),
                },
            },
        ]

    def get_units(self):
        return [
            self.get_unit('flanneld.service', dropins=['40-init-flannel.conf']),
        ]
