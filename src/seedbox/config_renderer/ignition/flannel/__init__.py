from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class FlannelPackage(BaseIgnitionPackage):
    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': '/opt/configure-flannel-network.sh',
                'mode': 0o755,
                'contents': {
                    'source': self.to_data_url(self.render_template('configure-flannel-network.sh')),
                },
            },
        ]

    def get_units(self):
        units = [
            self.get_unit('flanneld.service', dropins=['40-etcd.conf']),
            self.get_unit('flanneld.service', dropins=['40-network-config.conf']),

            # workaround for a VirtualBox environment issue
            # https://github.com/coreos/flannel/issues/98
            self.get_unit('flanneld.service', dropins=['40-iface.conf']),
        ]

        return units
