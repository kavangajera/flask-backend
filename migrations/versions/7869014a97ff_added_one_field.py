"""Added one field

Revision ID: 7869014a97ff
Revises: 6e5e676a2e8b
Create Date: 2025-05-16 15:52:29.933656

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7869014a97ff'
down_revision = '6e5e676a2e8b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('gst', sa.Numeric(precision=10, scale=2), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('gst')

    # ### end Alembic commands ###
