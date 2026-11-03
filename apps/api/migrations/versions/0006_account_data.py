"""Let users delete their own account, and remove old records on a schedule."""

from alembic import op

from costpilot.shared.config import get_settings

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    app_user = get_settings().postgres_app_user
    # Row-Level Security still limits workspace deletes to the signed-in workspace.
    op.execute(f'GRANT DELETE ON users TO "{app_user}"')
    op.execute(f'GRANT DELETE ON workspaces TO "{app_user}"')

    # Old records live in every workspace, so the clean-up runs with the owner's rights.
    # The app may call this one function, and cannot delete across workspaces any other way.
    op.execute("""
        CREATE FUNCTION apply_retention(
            audit_days integer, conversation_days integer, failed_job_days integer
        )
        RETURNS TABLE (
            deleted_audit_events bigint,
            deleted_conversations bigint,
            deleted_failed_jobs bigint,
            deleted_sessions bigint
        )
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
        BEGIN
            IF least(audit_days, conversation_days, failed_job_days) < 1 THEN
                RAISE EXCEPTION 'Retention days must be at least 1';
            END IF;

            DELETE FROM audit_events
            WHERE created_at < now() - make_interval(days => audit_days);
            GET DIAGNOSTICS deleted_audit_events = ROW_COUNT;

            -- A conversation goes only when nothing in it is newer than the limit.
            DELETE FROM conversations c
            WHERE c.created_at < now() - make_interval(days => conversation_days)
              AND NOT EXISTS (
                  SELECT 1 FROM messages m
                  WHERE m.conversation_id = c.id
                    AND m.created_at >= now() - make_interval(days => conversation_days)
              );
            GET DIAGNOSTICS deleted_conversations = ROW_COUNT;

            DELETE FROM jobs
            WHERE status = 'failed'
              AND created_at < now() - make_interval(days => failed_job_days);
            GET DIAGNOSTICS deleted_failed_jobs = ROW_COUNT;

            DELETE FROM sessions WHERE expires_at <= now();
            GET DIAGNOSTICS deleted_sessions = ROW_COUNT;

            RETURN NEXT;
        END
        $$
    """)
    op.execute("REVOKE ALL ON FUNCTION apply_retention(integer, integer, integer) FROM PUBLIC")
    op.execute(
        f'GRANT EXECUTE ON FUNCTION apply_retention(integer, integer, integer) TO "{app_user}"'
    )


def downgrade() -> None:
    app_user = get_settings().postgres_app_user
    op.execute("DROP FUNCTION apply_retention(integer, integer, integer)")
    op.execute(f'REVOKE DELETE ON workspaces FROM "{app_user}"')
    op.execute(f'REVOKE DELETE ON users FROM "{app_user}"')
