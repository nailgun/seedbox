from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class FlannelPackage(BaseIgnitionPackage):
    def get_units(self):
        units = [
            self.get_unit_dropins('flanneld.service', dropins=[
                '40-etcd.conf',
                '40-network-config.conf',
                # workaround for a VirtualBox environment issue
                # https://github.com/coreos/flannel/issues/98
                '40-iface.conf',
            ]),
        ]

        return units
