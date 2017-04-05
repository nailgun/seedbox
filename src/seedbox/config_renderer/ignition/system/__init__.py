from collections import defaultdict

from seedbox import config
from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class SystemPackage(BaseIgnitionPackage):
    def get_files(self):
        files = [
            {
                'filesystem': 'root',
                'path': '/etc/sysctl.d/max-user-watches.conf',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('sysctl-max-user-watches.conf')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/etc/hostname',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.node.fqdn + '\n'),
                },
            },
        ]

        if self.cluster.etcd_version == 3:
            etcdctl_template = 'cluster-etcdctl3'
        else:
            etcdctl_template = 'cluster-etcdctl'

        files += [
            {
                'filesystem': 'root',
                'path': '/opt/bin/cluster-etcdctl',
                'mode': 0o755,
                'contents': {
                    'source': self.to_data_url(self.render_template(etcdctl_template)),
                },
            },
        ]

        if self.cluster.aci_proxy_ca_cert:
            files += [
                {
                    'filesystem': 'root',
                    'path': config.aci_proxy_ca_cert_path,
                    'mode': 0o644,
                    'contents': {
                        'source': self.to_data_url(self.cluster.aci_proxy_ca_cert + '\n'),
                    },
                },
            ]

        return files

    def get_units(self):
        units = [
            self.get_unit('provision-report.service', enable=True),
            self.get_unit_dropins('fleet.service', ['40-etcd-cluster.conf']),
            self.get_unit_dropins('locksmithd.service', [
                '40-etcd-cluster.conf',
                '40-etcd-lock.conf',
            ]),
        ]

        if self.cluster.aci_proxy_url:
            units += [
                self.get_unit_dropins('docker.service', ['30-proxy.conf']),
            ]

        if self.cluster.aci_proxy_ca_cert:
            units += [
                self.get_unit('add-http-proxy-ca-certificate.service', enable=True)
            ]

        for mountpoint in self.node.mountpoints.all():
            enable = bool(mountpoint.wanted_by)

            unit_name = mountpoint.where.replace('/', '-')
            while unit_name[0] == '-':
                unit_name = unit_name[1:]
            unit_name += '.mount'

            units += [
                self.get_unit(unit_name, enable=enable, template_name='volume.mount', additional_context={
                    'mountpoint': mountpoint,
                })
            ]

        return units

    def get_networkd_units(self):
        interfaces = defaultdict(list)
        for address in self.node.addresses.all():
            interfaces[address.interface].append(address)

        return [
            self.get_unit('aa-{}-addresses.network'.format(interface),
                          template_name='addresses.network',
                          additional_context={
                              'interface': interface,
                              'addresses': addresses,
                          })
            for interface, addresses in interfaces.items()
        ]
