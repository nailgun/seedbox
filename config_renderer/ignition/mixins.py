import config


class EtcdEndpointsMixin(object):
    etcd_nodes = None

    def get_template_context(self):
        context = super(EtcdEndpointsMixin, self).get_template_context()
        context.setdefault('etcd_endpoints', [
            'http://{}:{}'.format(n.fqdn, config.etcd_client_port) for n in self.etcd_nodes
        ])
        return context
