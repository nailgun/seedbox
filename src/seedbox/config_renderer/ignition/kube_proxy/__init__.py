import logging

from seedbox import config, config_renderer
from seedbox.config_renderer.ignition.base import BaseIgnitionPackage

log = logging.getLogger(__name__)


class KubeProxyPackage(BaseIgnitionPackage):
    def get_files(self):
        user = self.cluster.k8s_kube_proxy_user
        if not user:
            log.warning('No user "%s" for kube-proxy in cluster %s', config.k8s_kube_proxy_user_name, self.cluster)
            return []

        return [
            {
                'filesystem': 'root',
                'path': config.k8s_manifests_path + '/kube-proxy.yaml',
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(self.render_template('kube-proxy.yaml')),
                },
            },
            {
                'filesystem': 'root',
                'path': config.k8s_kube_proxy_config_path,
                'mode': 0o644,
                'contents': {
                    'source': self.to_data_url(config_renderer.kubeconfig.render([user], default_user=user)),
                },
            },
        ]
