"""empty message

Revision ID: ae00e7974dca
Revises: 519c11fc090d
Create Date: 2017-05-19 17:00:48.920776

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ae00e7974dca'
down_revision = '519c11fc090d'
branch_labels = None
depends_on = None


def upgrade():
    from seedbox import models
    session = models.db.session

    models.Node.root_disk = sa.Column(sa.String(80), nullable=False)
    models.Node.wipe_root_disk_next_boot = sa.Column(sa.Boolean, nullable=False)
    models.Node.root_partition_size_sectors = sa.Column(sa.Integer, nullable=True)

    for node in models.Node.query.all():
        disk = models.Disk()
        disk.node = node
        disk.device = node.root_disk
        disk.wipe_next_boot = node.wipe_root_disk_next_boot
        session.add(disk)

        partition = models.DiskPartition()
        partition.disk = disk
        partition.number = 1
        partition.label = 'ROOT'
        partition.format = 'ext4'

        if node.root_partition_size_sectors:
            partition.size_mibs = node.root_partition_size_sectors * 512 // 1024 // 1024

        session.add(partition)

        if partition.size_mibs:
            partition = models.DiskPartition()
            partition.disk = disk
            partition.number = 2
            partition.label = 'Persistent'
            partition.format = 'ext4'
            session.add(partition)

            mountpoint = models.Mountpoint()
            mountpoint.node = node
            mountpoint.what = disk.device + '2'
            mountpoint.where = '/mnt/persistent'
            mountpoint.is_persistent = True
            session.add(mountpoint)

    session.commit()


def downgrade():
    pass
