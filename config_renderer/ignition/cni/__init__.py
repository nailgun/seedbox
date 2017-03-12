from config_renderer.ignition.base import BaseIgnitionPackage

import config


class CNIPackage(BaseIgnitionPackage):
    def __init__(self, etcd_nodes):
        self.template_context = {
            # TODO: move this to mixin
            'etcd_endpoints': ['http://{}:{}'.format(n.fqdn, config.etcd_client_port) for n in etcd_nodes],
        }

    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/cni/net.d/10-flannel.conf',
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
                'path': '/etc/kubernetes/cni/docker_opts_cni.env',
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
