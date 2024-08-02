"""Criar tabelas 5

Revision ID: 95cd830368dc
Revises: 5ffdbca20806
Create Date: 2024-07-29 19:49:36.065599

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '95cd830368dc'
down_revision = '5ffdbca20806'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('rateio_mensal', schema=None) as batch_op:
        batch_op.add_column(sa.Column('energia_rateada', sa.Float(), nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('rateio_mensal', schema=None) as batch_op:
        batch_op.drop_column('energia_rateada')

    # ### end Alembic commands ###
