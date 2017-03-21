from seedbox import config
from seedbox.config_renderer.ignition.base import BaseIgnitionPackage


class KubeletPackage(BaseIgnitionPackage):
    def __init__(self, hyperkube_tag, hostname, is_schedulable, is_apiserver, runtime, apiserver_nodes, dns_service_ip, manage_etc_hosts):
        self.template_context = {
            'hyperkube_tag': hyperkube_tag,
            'hostname': hostname,
            'is_schedulable': is_schedulable,
            'is_apiserver': is_apiserver,
            'runtime': runtime,
            'apiserver_endpoints': ['https://{}:{}'.format(n.fqdn, config.k8s_apiserver_secure_port) for n in apiserver_nodes],
            'dns_service_ip': dns_service_ip,
            'manage_etc_hosts': manage_etc_hosts,
        }

    def get_units(self):
        return [
            self.get_unit('kubelet.service', enable=True),
        ]
