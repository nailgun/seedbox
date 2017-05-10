from collections import defaultdict

from seedbox import config, models
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

        files += [
            {
                'filesystem': 'root',
                'path': '/opt/bin/cluster-etcdctl',
                'mode': 0o755,
                'contents': {
                    'source': self.to_data_url(self.render_template('cluster-etcdctl')),
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
            self.get_unit_dropins('sshd.service', ['40-oom.conf']),
            self.get_unit_dropins('sshd@.service', ['40-oom.conf']),
            self.get_unit_dropins('containerd.service', ['40-oom.conf']),
        ]

        if self.cluster.aci_proxy_url:
            units += [
                self.get_unit_dropins('docker.service', ['30-proxy.conf']),
            ]

        if self.cluster.aci_proxy_ca_cert:
            units += [
                self.get_unit('add-http-proxy-ca-certificate.service', enable=True)
            ]

        mountpoints = list(self.node.mountpoints.all())
        if self.node.persistent_partition:
            mountpoint = models.Mountpoint()
            mountpoint.what = self.node.persistent_partition
            mountpoint.where = '/mnt/persistent'
            mountpoint.wanted_by = models.Mountpoint.wanted_by.default.arg
            mountpoints.append(mountpoint)

        for mountpoint in mountpoints:
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
