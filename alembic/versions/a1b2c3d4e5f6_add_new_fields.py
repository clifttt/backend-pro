"""add new fields to models

Revision ID: a1b2c3d4e5f6
Revises: be668d3b47b0
Create Date: 2026-03-05 15:52:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'be668d3b47b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new fields: description, founded_year, status to startups;
       fund_name, focus_area to investors;
       rename announced_date→date and add status to investments."""

    # --- startups ---
    op.add_column('startups', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('startups', sa.Column('founded_year', sa.Integer(), nullable=True))
    op.add_column('startups', sa.Column('status', sa.String(length=50), nullable=True))

    # --- investors ---
    op.add_column('investors', sa.Column('fund_name', sa.String(length=255), nullable=True))
    op.add_column('investors', sa.Column('focus_area', sa.String(length=255), nullable=True))

    # --- investments: rename announced_date -> date, add status ---
    op.add_column('investments', sa.Column('date', sa.Date(), nullable=True))
    op.add_column('investments', sa.Column('status', sa.String(length=50), nullable=True))

    # Copy data from announced_date to date (if any rows exist)
    op.execute("UPDATE investments SET date = announced_date WHERE announced_date IS NOT NULL")

    # Drop old column
    op.drop_column('investments', 'announced_date')


def downgrade() -> None:
    """Reverse the upgrade."""

    # investments: restore announced_date, drop date & status
    op.add_column('investments', sa.Column('announced_date', sa.Date(), nullable=True))
    op.execute("UPDATE investments SET announced_date = date WHERE date IS NOT NULL")
    op.drop_column('investments', 'date')
    op.drop_column('investments', 'status')

    # investors
    op.drop_column('investors', 'focus_area')
    op.drop_column('investors', 'fund_name')

    # startups
    op.drop_column('startups', 'status')
    op.drop_column('startups', 'founded_year')
    op.drop_column('startups', 'description')
