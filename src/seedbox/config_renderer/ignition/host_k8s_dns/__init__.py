from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class HostK8sDnsPackage(BaseIgnitionPackage):
    def get_files(self):
        return [{
            'filesystem': 'root',
            'path': '/etc/systemd/resolved.conf.d/40-k8s-dns.conf',
            'mode': 0o644,
            'contents': {
                'source': self.to_data_url(self.render_template('resolved.conf')),
            },
        }]
