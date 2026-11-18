"""telegram_bot_and_otp

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-18 18:10:00.000000

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _sanitize_login(raw: str) -> str:
    cleaned = re.sub(r'[^a-z0-9_]', '', (raw or '').lower())
    return cleaned[:40] if cleaned else 'user'


def upgrade() -> None:
    # 1. Add new columns to users (nullable initially where needed)
    op.add_column('users', sa.Column('login', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('telegram_id', sa.BigInteger(), nullable=True))
    op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('full_name', sa.String(length=200), nullable=True))
    op.add_column('users', sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.add_column('users', sa.Column('status', sa.String(length=20), nullable=False, server_default='registered'))
    op.add_column('users', sa.Column('consent_version', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('consent_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('self_level', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('age_group', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('region', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('source', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('interest', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('waitlisted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('promoted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('disqualified_reason', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('notifications_muted', sa.Boolean(), nullable=False, server_default=sa.text('false')))

    # 2. Populate login & defaults for existing users (e.g. existing admin)
    if not op.get_context().as_sql:
        conn = op.get_bind()
        rows = conn.execute(sa.text("SELECT id, username, email FROM users ORDER BY created_at ASC")).fetchall()
        used_logins: set[str] = set()
        for row in rows:
            base = _sanitize_login(row.username or (row.email.split('@')[0] if row.email else 'user'))
            candidate = base
            counter = 1
            while candidate in used_logins:
                candidate = f"{base[:44]}_{counter}"
                counter += 1
            used_logins.add(candidate)
            conn.execute(
                sa.text(
                    "UPDATE users SET login = :login, must_change_password = false, status = 'confirmed' WHERE id = :id"
                ),
                {"login": candidate, "id": row.id},
            )

    # 3. Enforce NOT NULL on login, nullable on email/password_hash, unique indexes
    op.alter_column('users', 'login', nullable=False)
    op.alter_column('users', 'email', existing_type=sa.String(length=255), nullable=True)
    op.alter_column('users', 'password_hash', existing_type=sa.String(length=255), nullable=True)

    op.create_index(op.f('ix_users_login'), 'users', ['login'], unique=True)
    op.create_index(op.f('ix_users_telegram_id'), 'users', ['telegram_id'], unique=True)
    op.create_index(op.f('ix_users_phone'), 'users', ['phone'], unique=True)

    # 4. Create new tables
    op.create_table(
        'one_time_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_one_time_codes_user_created', 'one_time_codes', ['user_id', 'created_at'])

    op.create_table(
        'support_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('answered', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )

    op.create_table(
        'broadcast_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('admin_telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('sent_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    op.create_table(
        'consent_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rules_version', sa.Integer(), nullable=False),
        sa.Column('agreed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('consent_log')
    op.drop_table('broadcast_log')
    op.drop_table('support_messages')
    op.drop_index('ix_one_time_codes_user_created', table_name='one_time_codes')
    op.drop_table('one_time_codes')

    op.drop_index(op.f('ix_users_phone'), table_name='users')
    op.drop_index(op.f('ix_users_telegram_id'), table_name='users')
    op.drop_index(op.f('ix_users_login'), table_name='users')

    # Restore non-null email & password_hash safely for existing rows
    op.execute("UPDATE users SET email = login || '@legacy.local' WHERE email IS NULL")
    op.execute("UPDATE users SET password_hash = '' WHERE password_hash IS NULL")
    op.alter_column('users', 'password_hash', existing_type=sa.String(length=255), nullable=False)
    op.alter_column('users', 'email', existing_type=sa.String(length=255), nullable=False)

    op.drop_column('users', 'notifications_muted')
    op.drop_column('users', 'disqualified_reason')
    op.drop_column('users', 'promoted_at')
    op.drop_column('users', 'waitlisted_at')
    op.drop_column('users', 'confirmed_at')
    op.drop_column('users', 'interest')
    op.drop_column('users', 'source')
    op.drop_column('users', 'region')
    op.drop_column('users', 'age_group')
    op.drop_column('users', 'self_level')
    op.drop_column('users', 'consent_at')
    op.drop_column('users', 'consent_version')
    op.drop_column('users', 'status')
    op.drop_column('users', 'must_change_password')
    op.drop_column('users', 'full_name')
    op.drop_column('users', 'phone')
    op.drop_column('users', 'telegram_id')
    op.drop_column('users', 'login')
