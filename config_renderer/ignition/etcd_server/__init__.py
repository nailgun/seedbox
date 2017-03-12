from config_renderer.ignition.base import BaseIgnitionPackage

import config


class EtcdServerPackage(BaseIgnitionPackage):
    def __init__(self, version, hostname, etcd_nodes):
        self.version = version
        self.template_context = {
            'version': version,
            'hostname': hostname,
            'etcd_nodes': etcd_nodes,
            'config': config,
        }

    def get_units(self):
        if self.version == 2:
            unit_name = 'etcd2.service'
        elif self.version == 3:
            unit_name = 'etcd-member.service'
        else:
            raise Exception('Unknown etcd version', self.version)

        return [
            self.get_unit(unit_name, enable=True, dropins=['40-etcd-cluster.conf']),
            # TODO: add support for etcd proxies
            self.get_unit('locksmithd.service', dropins=['40-etcd-lock.conf']),
        ]
