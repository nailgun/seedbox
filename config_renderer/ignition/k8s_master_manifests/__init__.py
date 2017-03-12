from config_renderer.ignition.base import BaseIgnitionPackage

import config


class K8sMasterManifestsPackage(BaseIgnitionPackage):
    def __init__(self, hyperkube_tag, etcd_nodes):
        self.template_context = {
            'hyperkube_tag': hyperkube_tag,
            # TODO: move this to mixin
            'etcd_endpoints': ['http://{}:{}'.format(n.fqdn, config.etcd_client_port) for n in etcd_nodes],
            'config': config,
        }

    def get_files(self):
        return [
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-apiserver.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-apiserver.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-controller-manager.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-controller-manager.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': '/etc/kubernetes/manifests/kube-scheduler.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-scheduler.yaml')),
                },
            },
        ]
