"""empty message

Revision ID: 579f89f6b1a0
Revises: 283dc9256301
Create Date: 2017-05-07 04:48:43.309982

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '579f89f6b1a0'
down_revision = '283dc9256301'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TABLE cluster ALTER COLUMN k8s_admission_control TYPE varchar(255)')


def downgrade():
    pass
