import datetime

from .db import db


class Provision(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    node_id = db.Column(db.Integer, db.ForeignKey('node.id'), nullable=False)
    node = db.relationship('Node', backref=db.backref('provisions', lazy='dynamic'))
    applied_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    config_version = db.Column(db.Integer, nullable=False)
    ignition_config = db.Column(db.Binary, nullable=True)
    ipxe_config = db.Column(db.Text, nullable=True)
