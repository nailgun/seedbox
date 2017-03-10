from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Cluster(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    ca_credentials_id = db.Column(db.Integer, db.ForeignKey('credentials_data.id'), nullable=False)
    ca_credentials = db.relationship('CredentialsData')
    coreos_channel = db.Column(db.String(80), default='stable', nullable=False)
    coreos_version = db.Column(db.String(80), default='1235.9.0', nullable=False)
    #
    # def __init__(self, name):
    #     self.name = name

    def __repr__(self):
        return '<Cluster %r>' % self.name

    def __str__(self):
        return self.name

    @property
    def coreos_base_url(self):
        # TODO: not secure, download to manager first
        return 'http://{}.release.core-os.net/amd64-usr/{}/'.format(self.coreos_channel, self.coreos_version)


# TODO: add SMBIOS UUID, serial, mac, etc? (http://ipxe.org/cfg/uuid)
class Node(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey('cluster.id'), nullable=False)
    cluster = db.relationship('Cluster', backref=db.backref('nodes', lazy='dynamic'))
    ip = db.Column(db.String(80), unique=True, nullable=False)
    fqdn = db.Column(db.String(80), unique=True, nullable=False)
    is_master = db.Column(db.Boolean, nullable=False)
    credentials_id = db.Column(db.Integer, db.ForeignKey('credentials_data.id'), nullable=False)
    credentials = db.relationship('CredentialsData')
    #
    # def __init__(self, cluster_id, ip):
    #     self.cluster_id = cluster_id
    #     self.ip = ip

    def __repr__(self):
        return '<Node %r>' % self.ip

    def __str__(self):
        return self.ip


# TODO: allow user to belong to more then one cluster (https://kubernetes.io/docs/user-guide/kubeconfig-file/)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey('cluster.id'), nullable=False)
    cluster = db.relationship('Cluster', backref=db.backref('users', lazy='dynamic'))
    name = db.Column(db.String(80), nullable=False)  # TODO: unique together with cluster_id
    credentials_id = db.Column(db.Integer, db.ForeignKey('credentials_data.id'), nullable=False)
    credentials = db.relationship('CredentialsData')
    #
    # def __init__(self, cluster_id, name):
    #     self.cluster_id = cluster_id
    #     self.name = name

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
