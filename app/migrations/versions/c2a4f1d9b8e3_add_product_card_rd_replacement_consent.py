"""add product card rd replacement consent

Revision ID: c2a4f1d9b8e3
Revises: b9d7f8c2a6e1
Create Date: 2026-09-23 23:25:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = 'c2a4f1d9b8e3'
down_revision = 'b9d7f8c2a6e1'
branch_labels = None
depends_on = None


def upgrade():
    columns = {column['name'] for column in inspect(op.get_bind()).get_columns('product_cards')}
    if 'rd_replacement_consent' in columns:
        return

    with op.batch_alter_table('product_cards', schema=None) as batch_op:
        batch_op.add_column(sa.Column('rd_replacement_consent', sa.Boolean(), nullable=True))


def downgrade():
    columns = {column['name'] for column in inspect(op.get_bind()).get_columns('product_cards')}
    if 'rd_replacement_consent' not in columns:
        return

    with op.batch_alter_table('product_cards', schema=None) as batch_op:
        batch_op.drop_column('rd_replacement_consent')
