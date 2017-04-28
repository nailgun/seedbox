from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class EtcdServerPackage(BaseIgnitionPackage):
    def get_units(self):
        return [
            self.get_unit_dropins('etcd-member.service', [
                '40-etcd-cluster.conf',
                '40-ssl.conf',
                '30-version.conf',
            ], enableunit=True),
        ]
