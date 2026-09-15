"""v2_question_type_and_ai_scores

Revision ID: a1b2c3d4e5f6
Revises: dfda7c9ed50b
Create Date: 2026-09-14 22:52:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'a1b2c3d4e5f6'
down_revision = 'dfda7c9ed50b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- questions jadvaliga o'zgarishlar ---------------------
    # body_svg -> body_text
    op.add_column('questions', sa.Column('body_text', sa.Text(), nullable=True))
    # Eski body_svg ma'lumotlarini body_text ga ko'chirish
    op.execute("UPDATE questions SET body_text = body_svg WHERE body_text IS NULL")
    # body_text ni NOT NULL qilish
    op.alter_column('questions', 'body_text', nullable=False)
    # Eski body_svg ustunini o'chirish
    op.drop_column('questions', 'body_svg')

    # question_type qo'shish
    op.add_column('questions', sa.Column('question_type', sa.String(20), nullable=True))
    op.execute("UPDATE questions SET question_type = 'practical' WHERE question_type IS NULL")
    op.alter_column('questions', 'question_type', nullable=False, server_default='practical')

    # test_cases ni nullable qilish
    op.alter_column('questions', 'test_cases', nullable=True)

    # --- exam_sessions jadvaliga o'zgarishlar ----------------
    op.add_column('exam_sessions', sa.Column('note_content', sa.Text(), nullable=True))
    op.add_column('exam_sessions', sa.Column('time_spent_secs', sa.Integer(), nullable=True))

    # --- submissions jadvaliga o'zgarishlar ------------------
    op.add_column('submissions', sa.Column('submission_type', sa.String(20), nullable=True))
    op.execute("UPDATE submissions SET submission_type = 'practical' WHERE submission_type IS NULL")
    op.alter_column('submissions', 'submission_type', nullable=False, server_default='practical')

    op.add_column('submissions', sa.Column('note_content', sa.Text(), nullable=True))
    op.add_column('submissions', sa.Column('file_content', sa.Text(), nullable=True))

    # code ustuni nullable bolishi kerak
    op.alter_column('submissions', 'code', nullable=True)

    # --- participant_ai_scores yangi jadval -------------------
    op.create_table(
        'participant_ai_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('challenge_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('challenges.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('day_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('challenge_days.id', ondelete='CASCADE'), nullable=True),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('imported_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.UniqueConstraint('challenge_id', 'user_id', 'day_id', 'category',
                            name='uq_ai_score_per_category'),
    )


def downgrade() -> None:
    op.drop_table('participant_ai_scores')

    op.drop_column('submissions', 'file_content')
    op.drop_column('submissions', 'note_content')
    op.drop_column('submissions', 'submission_type')

    op.drop_column('exam_sessions', 'time_spent_secs')
    op.drop_column('exam_sessions', 'note_content')

    op.drop_column('questions', 'question_type')
    op.add_column('questions', sa.Column('body_svg', sa.Text(), nullable=True))
    op.execute("UPDATE questions SET body_svg = body_text WHERE body_svg IS NULL")
    op.alter_column('questions', 'body_svg', nullable=False)
    op.drop_column('questions', 'body_text')
