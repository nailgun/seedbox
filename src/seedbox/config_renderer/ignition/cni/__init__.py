from seedbox import config
from seedbox.config_renderer.ignition.base import BaseIgnitionPackage
from seedbox.config_renderer.ignition.mixins import EtcdEndpointsMixin


class CNIPackage(EtcdEndpointsMixin, BaseIgnitionPackage):
    def __init__(self, etcd_nodes):
        self.etcd_nodes = etcd_nodes

    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': config.k8s_cni_conf_path + '/10-flannel.conf',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('cni.conf')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/etc/flannel/options.env',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('options.env')),
                },
            },
            {
                'filesystem': 'root',
                'path': config.k8s_cni_path + '/docker_opts_cni.env',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('docker-opts.env')),
                },
            },
        ]

    def get_units(self):
        return [
            self.get_unit('flanneld.service', dropins=['40-add-options.conf']),
            self.get_unit('docker.service', dropins=['40-flannel.conf']),
        ]
