from seedbox import pki
from .db import db


# TODO: allow user to belong to more then one cluster (https://kubernetes.io/docs/user-guide/kubeconfig-file/)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey('cluster.id'), nullable=False)
    cluster = db.relationship('Cluster', backref=db.backref('users', lazy='dynamic'))
    name = db.Column(db.String(80), nullable=False)  # TODO: unique together with cluster_id
    credentials_id = db.Column(db.Integer, db.ForeignKey('credentials_data.id'), nullable=False)
    credentials = db.relationship('CredentialsData')
    groups = db.Column(db.String(255), nullable=False)      # TODO: rename to k8s_groups
    ssh_key = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return '<User %r>' % self.name

    def __str__(self):
        return self.name

    @property
    def credentials_error(self):
        try:
            pki.verify_certificate_chain(self.cluster.ca_credentials.cert, self.credentials.cert)
            pki.validate_certificate_subject_name(self.credentials.cert, self.name)
            if self.groups:
                pki.validate_certificate_organizations(self.credentials.cert, self.groups.split(','))
            pki.validate_certificate_key_usage(self.credentials.cert, is_web_server=False, is_web_client=True)
        except pki.InvalidCertificate as e:
            return str(e)
