from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
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

    def __repr__(self):
        return '<Cluster %r>' % self.name

    def __str__(self):
        return self.name


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

    _coreos_channel = db.Column(db.String(80), nullable=True)
    _coreos_version = db.Column(db.String(80), nullable=True)

    coreos_autologin = db.Column(db.Boolean, nullable=False)
    linux_consoles = db.Column(db.String(80), default='tty0,ttyS0', nullable=False)

    is_etcd_server = db.Column(db.Boolean, nullable=False)
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


class NodeConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    def __repr__(self):
        return '<NodeConfig %r>' % self.id


# TODO: allow user to belong to more then one cluster (https://kubernetes.io/docs/user-guide/kubeconfig-file/)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey('cluster.id'), nullable=False)
    cluster = db.relationship('Cluster', backref=db.backref('users', lazy='dynamic'))
    name = db.Column(db.String(80), nullable=False)  # TODO: unique together with cluster_id
    credentials_id = db.Column(db.Integer, db.ForeignKey('credentials_data.id'), nullable=False)
    credentials = db.relationship('CredentialsData')
    ssh_key = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return '<User %r>' % self.name

    def __str__(self):
        return self.name


class CredentialsData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cert = db.Column(db.Text, nullable=False)
    key = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return '<CredentialsData #%r>' % self.id
