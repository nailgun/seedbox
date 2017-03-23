from seedbox import pki, config
from .db import db


class Node(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(80), unique=True, nullable=False)
    fqdn = db.Column(db.String(80), unique=True, nullable=False)

    cluster_id = db.Column(db.Integer, db.ForeignKey('cluster.id'), nullable=False)
    cluster = db.relationship('Cluster', backref=db.backref('nodes', lazy='dynamic'))

    credentials_id = db.Column(db.Integer, db.ForeignKey('credentials_data.id'), nullable=False)
    credentials = db.relationship('CredentialsData')

    target_config_version = db.Column(db.Integer, default=1, nullable=False)
    active_config_version = db.Column(db.Integer, nullable=True)
    active_ignition_config = db.Column(db.Text, nullable=False)

    coreos_autologin = db.Column(db.Boolean, nullable=False)
    root_disk = db.Column(db.String(80), default=config.default_root_disk, nullable=False)
    linux_consoles = db.Column(db.String(80), default=config.default_linux_consoles, nullable=False)
    disable_ipv6 = db.Column(db.Boolean, nullable=False)

    is_etcd_server = db.Column(db.Boolean, nullable=False)
    is_k8s_schedulable = db.Column(db.Boolean, default=True, nullable=False)
    is_k8s_apiserver = db.Column(db.Boolean, nullable=False)
    is_k8s_apiserver_lb = db.Column(db.Boolean, nullable=False)

    def __repr__(self):
        return '<Node %r>' % self.fqdn

    def __str__(self):
        return self.fqdn

    @property
    def is_config_match(self):
        return self.target_config_version == self.active_config_version

    @property
    def credentials_error(self):
        try:
            pki.verify_certificate_chain(self.cluster.ca_credentials.cert, self.credentials.cert)
            hosts = [self.fqdn]
            if self.is_k8s_apiserver:
                hosts += [
                    'kubernetes',
                    'kubernetes.default',
                    'kubernetes.default.svc',
                    'kubernetes.default.svc.' + config.k8s_cluster_domain,
                ]
            pki.validate_certificate_hosts(self.credentials.cert, hosts)
            pki.validate_certificate_key_usage(self.credentials.cert)
        except pki.InvalidCertificate as e:
            return str(e)

    @property
    def credentials_warning(self):
        try:
            ips = [self.ip]
            if self.is_k8s_apiserver:
                ips += [self.cluster.k8s_apiserver_service_ip]
            pki.validate_certificate_host_ips(self.credentials.cert, ips)
        except pki.InvalidCertificate as e:
            return str(e)

    @property
    def root_partition(self):
        return self.root_disk + '1'
