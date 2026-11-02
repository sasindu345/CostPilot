"""Add documents and the background job queue."""

from alembic import op

from costpilot.shared.config import get_settings

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

CURRENT_WORKSPACE = "NULLIF(current_setting('app.workspace_id', true), '')::uuid"


def upgrade() -> None:
    app_user = get_settings().postgres_app_user
    op.execute("""
        CREATE TABLE documents (
            id uuid PRIMARY KEY,
            workspace_id uuid NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
            uploaded_by uuid NOT NULL REFERENCES users (id),
            file_name text NOT NULL,
            storage_key text NOT NULL,
            size_bytes bigint NOT NULL,
            sha256 text NOT NULL,
            status text NOT NULL
                CHECK (status IN ('queued', 'processing', 'processed', 'failed')),
            error_message text,
            row_count bigint,
            created_at timestamptz NOT NULL DEFAULT now(),
            processed_at timestamptz,
            UNIQUE (workspace_id, sha256)
        )
    """)
    op.execute("CREATE INDEX documents_recent ON documents (workspace_id, created_at DESC)")
    op.execute("ALTER TABLE documents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE documents FORCE ROW LEVEL SECURITY")
    op.execute(f"""
        CREATE POLICY document_access ON documents
        USING (workspace_id = {CURRENT_WORKSPACE})
        WITH CHECK (workspace_id = {CURRENT_WORKSPACE})
    """)

    # The worker must see jobs from every workspace, so this table has no Row-Level Security.
    # It only holds IDs and error class names, never user data.
    op.execute("""
        CREATE TABLE jobs (
            id uuid PRIMARY KEY,
            document_id uuid NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
            workspace_id uuid NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
            status text NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued', 'running', 'failed')),
            attempts integer NOT NULL DEFAULT 0,
            run_after timestamptz NOT NULL DEFAULT now(),
            locked_at timestamptz,
            last_error text,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX jobs_ready ON jobs (run_after, created_at) WHERE status = 'queued'")

    op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON documents TO "{app_user}"')
    op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON jobs TO "{app_user}"')


def downgrade() -> None:
    op.execute("DROP TABLE jobs")
    op.execute("DROP TABLE documents")
