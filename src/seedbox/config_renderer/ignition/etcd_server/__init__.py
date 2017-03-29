from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class EtcdServerPackage(BaseIgnitionPackage):
    def get_units(self):
        if self.cluster.etcd_version == 2:
            unit_name = 'etcd2.service'
        elif self.cluster.etcd_version == 3:
            unit_name = 'etcd-member.service'
        else:
            raise Exception('Unknown etcd version', self.cluster.etcd_version)

        return [
            self.get_unit_dropins(unit_name, ['40-etcd-cluster.conf'], enableunit=True),
        ]
