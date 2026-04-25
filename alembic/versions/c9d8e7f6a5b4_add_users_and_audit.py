"""Add User model, audit timestamps, source_url to startups

Revision ID: c9d8e7f6a5b4
Revises: a1b2c3d4e5f6
Create Date: 2026-04-25 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = 'c9d8e7f6a5b4'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Users table ───────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # ── Startups: add source_url and audit timestamps ─────────────────────────
    op.add_column('startups', sa.Column('source_url', sa.String(length=500), nullable=True))
    op.add_column('startups', sa.Column('created_at', sa.DateTime(timezone=True),
                                         nullable=False, server_default=func.now()))
    op.add_column('startups', sa.Column('updated_at', sa.DateTime(timezone=True),
                                         nullable=False, server_default=func.now()))

    # ── Investors: add audit timestamps ───────────────────────────────────────
    op.add_column('investors', sa.Column('created_at', sa.DateTime(timezone=True),
                                          nullable=False, server_default=func.now()))
    op.add_column('investors', sa.Column('updated_at', sa.DateTime(timezone=True),
                                          nullable=False, server_default=func.now()))


def downgrade() -> None:
    op.drop_column('investors', 'updated_at')
    op.drop_column('investors', 'created_at')
    op.drop_column('startups', 'updated_at')
    op.drop_column('startups', 'created_at')
    op.drop_column('startups', 'source_url')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_table('users')
