from sqlalchemy.schema import UniqueConstraint

from .db import db


class Mountpoint(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    node_id = db.Column(db.Integer, db.ForeignKey('node.id'), nullable=False)
    node = db.relationship('Node', backref=db.backref('mountpoints', lazy='dynamic'))

    what = db.Column(db.String(80), nullable=False)
    where = db.Column(db.String(80), nullable=False)
    wanted_by = db.Column(db.String(80), default='local-fs.target', nullable=False)
    is_persistent = db.Column(db.Boolean, nullable=False)

    __table_args__ = (
        UniqueConstraint('node_id', 'what', name='_node_mountpoint_what_uc'),
        UniqueConstraint('node_id', 'where', name='_node_mountpoint_where_uc'),
    )

    def __repr__(self):
        return '<Mountpoint %r>' % self.id

    def __str__(self):
        return '{} -> {}'.format(self.what, self.where)
