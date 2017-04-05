from .db import db


class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    node_id = db.Column(db.Integer, db.ForeignKey('node.id'), nullable=False)
    node = db.relationship('Node', backref=db.backref('addresses', lazy='dynamic'))

    interface = db.Column(db.String(80), nullable=False)
    ip = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return '<Address %r>' % self.id

    def __str__(self):
        return '{}: {}'.format(self.interface, self.ip)
