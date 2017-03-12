from config_renderer.ignition.base import BaseIgnitionPackage
from config_renderer.ignition.mixins import EtcdEndpointsMixin


class FlannelInitPackage(EtcdEndpointsMixin, BaseIgnitionPackage):
    def __init__(self, etcd_nodes):
        self.etcd_nodes = etcd_nodes

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
