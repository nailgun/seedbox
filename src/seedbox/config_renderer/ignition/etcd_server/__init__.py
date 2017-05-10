from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class EtcdServerPackage(BaseIgnitionPackage):
    def get_units(self):
        dropins = [
            '40-etcd-cluster.conf',
            '40-ssl.conf',
            '40-oom.conf',
            '30-image.conf',
        ]

        if self.node.persistent_partition:
            dropins += ['40-persistent.conf']

        return [
            self.get_unit_dropins('etcd-member.service', dropins=dropins, enableunit=True),
        ]
