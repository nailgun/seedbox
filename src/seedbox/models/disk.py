from sqlalchemy.schema import UniqueConstraint

from .db import db


class Disk(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    node_id = db.Column(db.Integer, db.ForeignKey('node.id'), nullable=False)
    node = db.relationship('Node', backref=db.backref('disks', lazy='dynamic'))

    device = db.Column(db.String(80), nullable=False)
    wipe_next_boot = db.Column(db.Boolean, nullable=False, default=True)
    sector_size_bytes = db.Column(db.Integer, nullable=False, default=512)

    __table_args__ = (
        UniqueConstraint('node_id', 'device', name='_node_disk_device_uc'),
    )

    def __repr__(self):
        return '<Disk %r>' % self.id

    def __str__(self):
        return self.device
