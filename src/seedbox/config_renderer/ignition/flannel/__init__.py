from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class FlannelPackage(BaseIgnitionPackage):
    def get_units(self):
        dropins = [
            '40-etcd-cluster.conf',
            '40-network-config.conf',
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
