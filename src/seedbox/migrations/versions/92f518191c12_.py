"""empty message

Revision ID: 92f518191c12
Revises: 91248bf831b8
Create Date: 2017-04-27 17:44:57.672006

"""
from alembic import op
import sqlalchemy as sa

from seedbox import config


# revision identifiers, used by Alembic.
revision = '92f518191c12'
down_revision = '91248bf831b8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('cluster', sa.Column('k8s_admission_control', sa.String(length=80), nullable=False,
                                       server_default=config.default_k8s_admission_control))
    op.alter_column('cluster', 'k8s_admission_control', server_default=None)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('cluster', 'k8s_admission_control')
    # ### end Alembic commands ###
