from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class EtcdServerPackage(BaseIgnitionPackage):
    def get_units(self):
        if self.cluster.etcd_version == 2:
            unit_name = 'etcd2.service'
        elif self.cluster.etcd_version == 3:
            unit_name = 'etcd-member.service'
        else:
            raise Exception('Unknown etcd version', self.cluster.etcd_version)

        dropins = [
            '40-etcd-cluster.conf',
            '40-ssl.conf',
        ]

        if self.cluster.etcd_version == 3:
            dropins += [
                '30-version.conf',
            ]

        return [
            self.get_unit_dropins(unit_name, dropins, enableunit=True),
        ]
