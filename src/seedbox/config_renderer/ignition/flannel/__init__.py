from seedbox import config
from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class FlannelPackage(BaseIgnitionPackage):
    def get_files(self):
        files = []
        if self.cluster.k8s_cni:
            files += [{
                'filesystem': 'root',
                'path': config.k8s_cni_conf_path + '/10-flannel.conf',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('cni-conf.json')),
                },
            }]
        return files

    def get_units(self):
        dropins = [
            '40-etcd-cluster.conf',
            '40-network-config.conf',
            '40-oom.conf',
        ]

        if self.cluster.explicitly_advertise_addresses:
            dropins += [
                '40-iface.conf',
            ]

        if self.cluster.aci_proxy_url:
            dropins += [
                '30-proxy.conf',
            ]

        return [
            self.get_unit_dropins('flanneld.service', dropins=dropins),
        ]
