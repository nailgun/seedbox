"""empty message

Revision ID: 35099fc974d2
Revises: ae00e7974dca
Create Date: 2017-05-19 17:01:48.878196

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '35099fc974d2'
down_revision = 'ae00e7974dca'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('node', 'wipe_root_disk_next_boot')
    op.drop_column('node', 'root_partition_size_sectors')
    op.drop_column('node', 'root_disk')


def downgrade():
    op.add_column('node', sa.Column('root_disk', sa.VARCHAR(length=80), autoincrement=False, nullable=False))
    op.add_column('node', sa.Column('root_partition_size_sectors', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('node', sa.Column('wipe_root_disk_next_boot', sa.BOOLEAN(), autoincrement=False, nullable=False))
