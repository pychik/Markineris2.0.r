"""add order rd replacement consent

Revision ID: b9d7f8c2a6e1
Revises: a30abca98d3e
Create Date: 2026-09-23 23:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b9d7f8c2a6e1'
down_revision = 'a30abca98d3e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('rd_replacement_consent', sa.Boolean(), nullable=True))


def downgrade():
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('rd_replacement_consent')
