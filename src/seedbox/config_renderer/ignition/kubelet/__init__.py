from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class KubeletPackage(BaseIgnitionPackage):
    def get_units(self):
        units = [
            self.get_unit('kubelet.service', enable=True),
        ]

        if self.cluster.aci_proxy_url:
            units += [
                self.get_unit_dropins('kubelet.service', ['30-proxy.conf']),
            ]

        return units
