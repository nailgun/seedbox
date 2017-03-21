from seedbox import pki, config
from .db import db
from .runtime import Runtime

default_coreos_channel = 'stable'
default_coreos_version = '1235.9.0'
default_etcd_version = 2


class Cluster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    ca_credentials_id = db.Column(db.Integer, db.ForeignKey('credentials_data.id'), nullable=False)
    ca_credentials = db.relationship('CredentialsData')

    coreos_channel = db.Column(db.String(80), default=default_coreos_channel, nullable=False)
    coreos_version = db.Column(db.String(80), default=default_coreos_version, nullable=False)
    etcd_version = db.Column(db.Integer, default=default_etcd_version, nullable=False)
    manage_etc_hosts = db.Column(db.Boolean, nullable=False)
    allow_insecure_provision = db.Column(db.Boolean, nullable=False)

    k8s_runtime = db.Column(db.Integer, default=Runtime.docker.value, nullable=False)
    k8s_pod_network = db.Column(db.String(80), default='10.2.0.0/16', nullable=False)
    k8s_service_network = db.Column(db.String(80), default='10.3.0.0/24', nullable=False)
    k8s_hyperkube_tag = db.Column(db.String(80), default='v1.5.4_coreos.0', nullable=False)
    k8s_cni = db.Column(db.Boolean, nullable=False)

    def __repr__(self):
        return '<Cluster %r>' % self.name

    def __str__(self):
        return self.name

    @property
    def ca_credentials_error(self):
        try:
            pki.validate_certificate_subject_name(self.ca_credentials.cert, self.name)
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
    def k8s_apiserver(self):
        node = self.nodes.filter_by(is_k8s_apiserver_lb=True).first()
        if not node:
            node = self.nodes.filter_by(is_k8s_apiserver=True).first()
        return node

    @property
    def k8s_apiserver_endpoint(self):
        node = self.k8s_apiserver
        if node.is_k8s_apiserver_lb:
            port = config.k8s_apiserver_lb_port
        else:
            port = config.k8s_apiserver_secure_port
        return 'https://{}:{}'.format(node.fqdn, port)

    @property
    def k8s_runtime_name(self):
        return Runtime(self.k8s_runtime).name

    @property
    def k8s_apiserver_nodes(self):
        return self.nodes.filter_by(is_k8s_apiserver=True)

    @property
    def k8s_apiserver_endpoints(self):
        return ['https://{}:{}'.format(n.fqdn, config.k8s_apiserver_secure_port) for n in self.k8s_apiserver_nodes]

    @property
    def etcd_nodes(self):
        return self.nodes.filter_by(is_etcd_server=True)

    @property
    def etcd_endpoints(self):
        return ['http://{}:{}'.format(n.fqdn, config.etcd_client_port) for n in self.etcd_nodes]
