"""Add conversations, messages and the daily question count."""

from alembic import op

from costpilot.shared.config import get_settings

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

CURRENT_WORKSPACE = "NULLIF(current_setting('app.workspace_id', true), '')::uuid"


def upgrade() -> None:
    app_user = get_settings().postgres_app_user
    op.execute("""
        CREATE TABLE conversations (
            id uuid PRIMARY KEY,
            workspace_id uuid NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
            user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            title text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX conversations_recent ON conversations (user_id, created_at DESC)")
    op.execute("""
        CREATE TABLE messages (
            id uuid PRIMARY KEY,
            conversation_id uuid NOT NULL REFERENCES conversations (id) ON DELETE CASCADE,
            workspace_id uuid NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
            role text NOT NULL CHECK (role IN ('user', 'assistant')),
            content text NOT NULL,
            sources jsonb NOT NULL DEFAULT '[]',
            created_at timestamptz NOT NULL DEFAULT clock_timestamp()
        )
    """)
    op.execute("CREATE INDEX messages_conversation ON messages (conversation_id, created_at)")
    op.execute("""
        CREATE TABLE assistant_usage (
            workspace_id uuid NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
            day date NOT NULL,
            questions integer NOT NULL,
            PRIMARY KEY (workspace_id, day)
        )
    """)
    for table in ("conversations", "messages", "assistant_usage"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_access ON {table}
            USING (workspace_id = {CURRENT_WORKSPACE})
            WITH CHECK (workspace_id = {CURRENT_WORKSPACE})
        """)
    op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON conversations TO "{app_user}"')
    op.execute(f'GRANT SELECT, INSERT, DELETE ON messages TO "{app_user}"')
    op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON assistant_usage TO "{app_user}"')


def downgrade() -> None:
    op.execute("DROP TABLE assistant_usage")
    op.execute("DROP TABLE messages")
    op.execute("DROP TABLE conversations")
