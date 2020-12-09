"""add started column for spoiler races

Revision ID: b56f29ae30c3
Revises: f09140697acb
Create Date: 2020-11-21 17:45:09.245305

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b56f29ae30c3'
down_revision = 'f09140697acb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('spoiler_races', sa.Column('started', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('spoiler_races', 'started')
    # ### end Alembic commands ###