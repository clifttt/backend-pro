"""init models

Revision ID: be668d3b47b0
Revises: 
Create Date: 2026-02-07 13:03:00.059774

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be668d3b47b0'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create initial tables for Investment Intelligence Hub."""
    
    # Create startups table
    op.create_table(
        'startups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_startups_name', 'startups', ['name'])
    
    # Create investors table
    op.create_table(
        'investors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_investors_name', 'investors', ['name'])
    
    # Create investments table
    op.create_table(
        'investments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('startup_id', sa.Integer(), nullable=False),
        sa.Column('investor_id', sa.Integer(), nullable=False),
        sa.Column('round', sa.String(length=50), nullable=True),
        sa.Column('amount_usd', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('announced_date', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['investor_id'], ['investors.id'], ),
        sa.ForeignKeyConstraint(['startup_id'], ['startups.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_investments_startup_id', 'investments', ['startup_id'])
    op.create_index('ix_investments_investor_id', 'investments', ['investor_id'])


def downgrade() -> None:
    """Downgrade schema - Drop all tables."""
    op.drop_index('ix_investments_investor_id', table_name='investments')
    op.drop_index('ix_investments_startup_id', table_name='investments')
    op.drop_table('investments')
    op.drop_index('ix_investors_name', table_name='investors')
    op.drop_table('investors')
    op.drop_index('ix_startups_name', table_name='startups')
    op.drop_table('startups')
