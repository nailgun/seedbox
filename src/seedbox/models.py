import enum

from flask_sqlalchemy import SQLAlchemy

from seedbox import pki

db = SQLAlchemy()
default_coreos_channel = 'stable'
default_coreos_version = '1235.9.0'
default_etcd_version = 2


class Runtime(enum.IntEnum):
    docker = 1
    rkt = 2


class Cluster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    ca_credentials_id = db.Column(db.Integer, db.ForeignKey('credentials_data.id'), nullable=False)
    ca_credentials = db.relationship('CredentialsData')

    coreos_channel = db.Column(db.String(80), default=default_coreos_channel, nullable=False)
    coreos_version = db.Column(db.String(80), default=default_coreos_version, nullable=False)
    etcd_version = db.Column(db.Integer, default=default_etcd_version, nullable=False)
    manage_etc_hosts = db.Column(db.Boolean, nullable=False)
    allow_unsafe_credentials_transfer = db.Column(db.Boolean, nullable=False)

    k8s_runtime = db.Column(db.Integer, default=Runtime.docker.value, nullable=False)
    k8s_pod_network = db.Column(db.String(80), default='10.2.0.0/16', nullable=False)
    k8s_service_network = db.Column(db.String(80), default='10.3.0.0/24', nullable=False)
    k8s_hyperkube_tag = db.Column(db.String(80), default='v1.5.2_coreos.0', nullable=False)

    def __repr__(self):
        return '<Cluster %r>' % self.name

    def __str__(self):
        return self.name

    @property
    def ca_credentials_error(self):
        try:
            pki.validate_certificate_subject_name(self.ca_credentials.cert, self.name)
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


class Node(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(80), unique=True, nullable=False)
    fqdn = db.Column(db.String(80), unique=True, nullable=False)

    cluster_id = db.Column(db.Integer, db.ForeignKey('cluster.id'), nullable=False)
    cluster = db.relationship('Cluster', backref=db.backref('nodes', lazy='dynamic'))

    credentials_id = db.Column(db.Integer, db.ForeignKey('credentials_data.id'), nullable=False)
    credentials = db.relationship('CredentialsData')

    target_config_version = db.Column(db.Integer, default=1, nullable=False)
    current_config_version = db.Column(db.Integer, nullable=True)
    current_ignition_config = db.Column(db.Text, nullable=False)

    _coreos_channel = db.Column(db.String(80), nullable=False)
    _coreos_version = db.Column(db.String(80), nullable=False)

    coreos_autologin = db.Column(db.Boolean, nullable=False)
    root_disk = db.Column(db.String(80), default='/dev/sda', nullable=False)
    linux_consoles = db.Column(db.String(80), default='tty0,ttyS0', nullable=False)

    is_etcd_server = db.Column(db.Boolean, nullable=False)
    is_k8s_schedulable = db.Column(db.Boolean, default=True, nullable=False)
    is_k8s_apiserver = db.Column(db.Boolean, nullable=False)
    is_k8s_apiserver_lb = db.Column(db.Boolean, nullable=False)

    def __repr__(self):
        return '<Node %r>' % self.fqdn

    def __str__(self):
        return self.fqdn

    @property
    def coreos_channel(self):
        return self._coreos_channel or self.cluster.coreos_channel

    @property
    def coreos_version(self):
        return self._coreos_version or self.cluster.coreos_version

    @property
    def is_ready(self):
        return self.target_config_version == self.current_config_version

    @property
    def credentials_error(self):
        try:
            pki.verify_certificate_chain(self.cluster.ca_credentials.cert, self.credentials.cert)
            pki.validate_certificate_host(self.credentials.cert, self.fqdn)
        except pki.InvalidCertificate as e:
            return str(e)

    @property
    def root_partition(self):
        return self.root_disk + '1'


# TODO: allow user to belong to more then one cluster (https://kubernetes.io/docs/user-guide/kubeconfig-file/)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey('cluster.id'), nullable=False)
    cluster = db.relationship('Cluster', backref=db.backref('users', lazy='dynamic'))
    name = db.Column(db.String(80), nullable=False)  # TODO: unique together with cluster_id
    credentials_id = db.Column(db.Integer, db.ForeignKey('credentials_data.id'), nullable=False)
    credentials = db.relationship('CredentialsData')
    ssh_key = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return '<User %r>' % self.name

    def __str__(self):
        return self.name

    @property
    def credentials_error(self):
        try:
            pki.validate_certificate_subject_name(self.credentials.cert, self.name)
        except pki.InvalidCertificate as e:
            return str(e)


class CredentialsData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cert = db.Column(db.Text, nullable=False)
    key = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return '<CredentialsData #%r>' % self.id
