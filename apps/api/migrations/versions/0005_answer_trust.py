"""Save each answer's evidence grade and how it was made."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE messages
            ADD COLUMN grade text CHECK (grade IN ('A', 'B', 'C', 'D')),
            ADD COLUMN trace jsonb NOT NULL DEFAULT '{}'
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE messages DROP COLUMN grade, DROP COLUMN trace")
