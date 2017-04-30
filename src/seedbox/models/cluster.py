from seedbox import pki, config, exceptions
from .db import db


class Cluster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    ca_credentials_id = db.Column(db.Integer, db.ForeignKey('credentials_data.id'), nullable=False)
    ca_credentials = db.relationship('CredentialsData', foreign_keys=[ca_credentials_id])
    install_dnsmasq = db.Column(db.Boolean, nullable=False, default=True)

    etcd_image_tag = db.Column(db.String(80), default=config.default_etcd_image_tag, nullable=False)
    assert_etcd_cluster_exists = db.Column(db.Boolean, nullable=False)
    etcd_nodes_dns_name = db.Column(db.String(80), default='', nullable=False)

    k8s_apiservers_audit_log = db.Column(db.Boolean, nullable=False)
    k8s_apiservers_swagger_ui = db.Column(db.Boolean, nullable=False)
    dnsmasq_static_records = db.Column(db.Boolean, nullable=False)

    # workaround for a VirtualBox environment issue
    # https://github.com/coreos/flannel/issues/98
    explicitly_advertise_addresses = db.Column(db.Boolean, nullable=False)

    k8s_pod_network = db.Column(db.String(80), default=config.default_k8s_pod_network, nullable=False)
    k8s_service_network = db.Column(db.String(80), default=config.default_k8s_service_network, nullable=False)
    k8s_hyperkube_tag = db.Column(db.String(80), default=config.default_k8s_hyperkube_tag, nullable=False)
    k8s_cni = db.Column(db.Boolean, nullable=False)
    k8s_apiservers_dns_name = db.Column(db.String(80), default='', nullable=False)
    k8s_is_rbac_enabled = db.Column(db.Boolean, nullable=False, default=True)
    k8s_admission_control = db.Column(db.String(80), default=config.default_k8s_admission_control, nullable=False)

    coreos_channel = db.Column(db.String(80), default=config.default_coreos_channel, nullable=False)
    coreos_version = db.Column(db.String(80), default=config.default_coreos_version, nullable=False)
    custom_coreos_images_base_url = db.Column(db.String(80), default='', nullable=False)

    aci_proxy_url = db.Column(db.String(80), default='', nullable=False)
    aci_proxy_ca_cert = db.Column(db.Text, default='', nullable=False)

    # TODO: split into two fields: service_account_private/public_key
    service_account_keypair_id = db.Column(db.Integer, db.ForeignKey('credentials_data.id'), nullable=False)
    service_account_keypair = db.relationship('CredentialsData', foreign_keys=[service_account_keypair_id])

    def __repr__(self):
        return '<Cluster %r>' % self.name

    def __str__(self):
        return self.name

    @property
    def ca_credentials_error(self):
        try:
            pki.validate_certificate_common_name(self.ca_credentials.cert, self.name)
            pki.validate_ca_certificate_constraints(self.ca_credentials.cert)
        except pki.InvalidCertificate as e:
            return str(e)

    @property
    def k8s_apiserver_service_ip(self):
        ip = self.k8s_service_network.split('/')[0]
        return ip.rsplit('.', maxsplit=1)[0] + '.1'

    @property
    def k8s_dns_service_ip(self):
        ip = self.k8s_service_network.split('/')[0]
        return ip.rsplit('.', maxsplit=1)[0] + '.10'

    # TODO: improve after https://github.com/kubernetes/kubernetes/issues/18174
    @property
    def k8s_apiserver_node(self):
        return self.nodes.filter_by(is_k8s_master=True).first()

    @property
    def k8s_apiserver_nodes(self):
        return self.nodes.filter_by(is_k8s_master=True)

    @property
    def k8s_apiserver_endpoint(self):
        if self.k8s_apiservers_dns_name:
            host = self.k8s_apiservers_dns_name
        else:
            apiserver = self.k8s_apiserver_node
            if apiserver is None:
                raise exceptions.K8sNoClusterApiserver()
            host = apiserver.fqdn
        return 'https://{}:{}'.format(host, config.k8s_apiserver_secure_port)

    @property
    def etcd_nodes(self):
        return self.nodes.filter_by(is_etcd_server=True)

    @property
    def etcd_client_endpoints(self):
        if self.etcd_nodes_dns_name:
            hosts = [self.etcd_nodes_dns_name]
        else:
            hosts = [n.fqdn for n in self.etcd_nodes]
        return ['https://{}:{}'.format(host, config.etcd_client_port) for host in hosts]

    @property
    def is_configured(self):
        from .node import Node
        return not self.nodes.filter(Node.target_config_version != Node.active_config_version).count()

    @property
    def are_etcd_nodes_configured(self):
        from .node import Node
        return not self.nodes.filter(Node.is_etcd_server,
                                     Node.target_config_version != Node.active_config_version).count()

    @property
    def coreos_images_base_url(self):
        if self.custom_coreos_images_base_url:
            return self.custom_coreos_images_base_url
        else:
            return config.default_coreos_images_base_url.format(channel=self.coreos_channel,
                                                                version=self.coreos_version)