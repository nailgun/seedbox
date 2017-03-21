from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class KubeletPackage(BaseIgnitionPackage):
    def get_units(self):
        return [
            self.get_unit('kubelet.service', enable=True),
        ]
