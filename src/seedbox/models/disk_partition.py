from sqlalchemy.schema import UniqueConstraint

from .db import db


class DiskPartition(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    disk_id = db.Column(db.Integer, db.ForeignKey('disk.id'), nullable=False)
    disk = db.relationship('Disk', backref=db.backref('partitions', lazy='dynamic'))

    number = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(80), nullable=False)
    size_mibs = db.Column(db.Integer, nullable=True)
    format = db.Column(db.String(10), nullable=False, default='ext4')

    __table_args__ = (
        UniqueConstraint('disk_id', 'number', name='_disk_partition_number_uc'),
        UniqueConstraint('disk_id', 'label', name='_disk_partition_label_uc'),
    )

    def __repr__(self):
        return '<DiskPartition %r>' % self.id

    def __str__(self):
        return self.label

    @property
    def is_root(self):
        return self.label == 'ROOT'

    @property
    def device(self):
        return '{}{}'.format(self.disk.device, self.number)
