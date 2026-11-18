"""runner_scoring_ranking_audit

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-18 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. challenges.prize_amounts
    op.add_column('challenges', sa.Column('prize_amounts', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    # 2. questions: sample_tests, hidden_tests, options, correct_option, reference_solution
    op.add_column('questions', sa.Column('sample_tests', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('questions', sa.Column('hidden_tests', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('questions', sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('questions', sa.Column('correct_option', sa.Integer(), nullable=True))
    op.add_column('questions', sa.Column('reference_solution', sa.Text(), nullable=True))

    # 3. exam_sessions: ip_address, user_agent
    op.add_column('exam_sessions', sa.Column('ip_address', sa.String(length=64), nullable=True))
    op.add_column('exam_sessions', sa.Column('user_agent', sa.String(length=500), nullable=True))

    # 4. submissions: selected_option, graded_by, graded_at, grade_reason
    op.add_column('submissions', sa.Column('selected_option', sa.Integer(), nullable=True))
    op.add_column('submissions', sa.Column('graded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('submissions', sa.Column('graded_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('submissions', sa.Column('grade_reason', sa.Text(), nullable=True))

    # 5. challenge_results: is_tie, prize_amount, final_note, prize_paid_at
    op.add_column('challenge_results', sa.Column('is_tie', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('challenge_results', sa.Column('prize_amount', sa.Integer(), nullable=True))
    op.add_column('challenge_results', sa.Column('final_note', sa.Text(), nullable=True))
    op.add_column('challenge_results', sa.Column('prize_paid_at', sa.DateTime(timezone=True), nullable=True))

    # 6. score_audit_log
    op.create_table(
        'score_audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('submission_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('submissions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('admin_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('old_score', sa.Integer(), nullable=False),
        sa.Column('new_score', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # 7. login_attempts
    op.create_table(
        'login_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('login', sa.String(length=100), nullable=False),
        sa.Column('ip', sa.String(length=64), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_login_attempts_login', 'login_attempts', ['login'])
    op.create_index('ix_login_attempts_ip', 'login_attempts', ['ip'])
    op.create_index('ix_login_attempts_created_at', 'login_attempts', ['created_at'])

    # 8. login_events
    op.create_table(
        'login_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ip', sa.String(length=64), nullable=False),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_login_events_user_id', 'login_events', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_login_events_user_id', table_name='login_events')
    op.drop_table('login_events')

    op.drop_index('ix_login_attempts_created_at', table_name='login_attempts')
    op.drop_index('ix_login_attempts_ip', table_name='login_attempts')
    op.drop_index('ix_login_attempts_login', table_name='login_attempts')
    op.drop_table('login_attempts')

    op.drop_table('score_audit_log')

    op.drop_column('challenge_results', 'prize_paid_at')
    op.drop_column('challenge_results', 'final_note')
    op.drop_column('challenge_results', 'prize_amount')
    op.drop_column('challenge_results', 'is_tie')

    op.drop_column('submissions', 'grade_reason')
    op.drop_column('submissions', 'graded_at')
    op.drop_column('submissions', 'graded_by')
    op.drop_column('submissions', 'selected_option')

    op.drop_column('exam_sessions', 'user_agent')
    op.drop_column('exam_sessions', 'ip_address')

    op.drop_column('questions', 'reference_solution')
    op.drop_column('questions', 'correct_option')
    op.drop_column('questions', 'options')
    op.drop_column('questions', 'hidden_tests')
    op.drop_column('questions', 'sample_tests')

    op.drop_column('challenges', 'prize_amounts')
