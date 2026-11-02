"""Add users, sessions, workspaces, memberships and audit events."""

from alembic import op

from costpilot.shared.config import get_settings

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

CURRENT_USER = "NULLIF(current_setting('app.user_id', true), '')::uuid"
CURRENT_WORKSPACE = "NULLIF(current_setting('app.workspace_id', true), '')::uuid"


def upgrade() -> None:
    app_user = get_settings().postgres_app_user
    op.execute("""
        CREATE TABLE users (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            keycloak_subject text NOT NULL UNIQUE,
            email text NOT NULL,
            display_name text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE sessions (
            token_hash bytea PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            sealed_id_token text NOT NULL,
            expires_at timestamptz NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE workspaces (
            id uuid PRIMARY KEY,
            name text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE TABLE memberships (
            workspace_id uuid NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
            user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            role text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (workspace_id, user_id)
        )
    """)
    op.execute("CREATE INDEX memberships_user_id ON memberships (user_id)")
    op.execute("""
        CREATE TABLE audit_events (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id uuid NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
            user_id uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            action text NOT NULL,
            details jsonb NOT NULL DEFAULT '{}',
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX audit_events_workspace ON audit_events (workspace_id, created_at)")

    for table in ("workspaces", "memberships", "audit_events"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    op.execute(f"""
        CREATE POLICY workspace_access ON workspaces
        USING (id = {CURRENT_WORKSPACE})
    """)
    op.execute(f"""
        CREATE POLICY membership_read ON memberships FOR SELECT
        USING (workspace_id = {CURRENT_WORKSPACE} OR user_id = {CURRENT_USER})
    """)
    op.execute(f"""
        CREATE POLICY membership_write ON memberships FOR INSERT
        WITH CHECK (workspace_id = {CURRENT_WORKSPACE} AND user_id = {CURRENT_USER})
    """)
    op.execute(f"""
        CREATE POLICY audit_access ON audit_events
        USING (workspace_id = {CURRENT_WORKSPACE})
        WITH CHECK (workspace_id = {CURRENT_WORKSPACE})
    """)

    op.execute(f'GRANT SELECT, INSERT, UPDATE ON users TO "{app_user}"')
    op.execute(f'GRANT SELECT, INSERT, DELETE ON sessions TO "{app_user}"')
    op.execute(f'GRANT SELECT, INSERT, UPDATE ON workspaces TO "{app_user}"')
    op.execute(f'GRANT SELECT, INSERT ON memberships TO "{app_user}"')
    op.execute(f'GRANT SELECT, INSERT ON audit_events TO "{app_user}"')


def downgrade() -> None:
    for table in ("audit_events", "memberships", "workspaces", "sessions", "users"):
        op.execute(f"DROP TABLE {table}")
