"""Add FOCUS cost records, billing periods per document, and monthly summaries."""

from alembic import op

from costpilot.shared.config import get_settings

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

CURRENT_WORKSPACE = "NULLIF(current_setting('app.workspace_id', true), '')::uuid"


def upgrade() -> None:
    app_user = get_settings().postgres_app_user
    op.execute("""
        ALTER TABLE documents
            DROP CONSTRAINT documents_status_check,
            ADD CONSTRAINT documents_status_check
                CHECK (status IN ('queued', 'processing', 'processed', 'failed', 'replaced')),
            ADD COLUMN provider_name text,
            ADD COLUMN first_month date,
            ADD COLUMN last_month date
    """)
    op.execute("""
        CREATE TABLE cost_records (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            workspace_id uuid NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
            document_id uuid NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
            billing_month date NOT NULL,
            provider_name text NOT NULL,
            billing_account_id text NOT NULL DEFAULT '',
            sub_account_id text NOT NULL DEFAULT '',
            charge_period_start timestamptz NOT NULL,
            charge_period_end timestamptz NOT NULL,
            service_name text NOT NULL,
            service_category text NOT NULL,
            charge_category text NOT NULL,
            billed_cost numeric NOT NULL,
            effective_cost numeric NOT NULL,
            list_cost numeric,
            billing_currency text NOT NULL,
            region_id text NOT NULL DEFAULT '',
            resource_id text NOT NULL DEFAULT '',
            sku_id text NOT NULL DEFAULT '',
            consumed_quantity numeric,
            consumed_unit text NOT NULL DEFAULT '',
            tags jsonb NOT NULL DEFAULT '{}',
            detail_level text NOT NULL
        )
    """)
    op.execute("CREATE INDEX cost_records_document ON cost_records (document_id)")
    op.execute("CREATE INDEX cost_records_month ON cost_records (workspace_id, billing_month)")
    op.execute("""
        CREATE TABLE document_periods (
            workspace_id uuid NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
            document_id uuid NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
            provider_name text NOT NULL,
            billing_account_id text NOT NULL,
            billing_month date NOT NULL,
            detail_level text NOT NULL,
            is_active boolean NOT NULL DEFAULT false,
            PRIMARY KEY (document_id, provider_name, billing_account_id, billing_month)
        )
    """)
    op.execute("""
        CREATE TABLE monthly_summaries (
            workspace_id uuid NOT NULL REFERENCES workspaces (id) ON DELETE CASCADE,
            billing_month date NOT NULL,
            provider_name text NOT NULL,
            billing_currency text NOT NULL,
            service_name text NOT NULL,
            service_category text NOT NULL,
            charge_category text NOT NULL,
            billed_cost numeric NOT NULL,
            effective_cost numeric NOT NULL,
            PRIMARY KEY (
                workspace_id, billing_month, provider_name, billing_currency,
                service_name, service_category, charge_category
            )
        )
    """)
    for table in ("cost_records", "document_periods", "monthly_summaries"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_access ON {table}
            USING (workspace_id = {CURRENT_WORKSPACE})
            WITH CHECK (workspace_id = {CURRENT_WORKSPACE})
        """)
        op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO "{app_user}"')


def downgrade() -> None:
    op.execute("DROP TABLE monthly_summaries")
    op.execute("DROP TABLE document_periods")
    op.execute("DROP TABLE cost_records")
    op.execute("""
        ALTER TABLE documents
            DROP CONSTRAINT documents_status_check,
            ADD CONSTRAINT documents_status_check
                CHECK (status IN ('queued', 'processing', 'processed', 'failed')),
            DROP COLUMN provider_name,
            DROP COLUMN first_month,
            DROP COLUMN last_month
    """)
