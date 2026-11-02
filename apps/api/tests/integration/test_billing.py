"""Tests saved records, overlap rules and summaries on real PostgreSQL. Needs `make up`."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from costpilot.modules.billing.application.import_service import BillImportService
from costpilot.modules.billing.contracts import BillRejectedError
from costpilot.modules.billing.infrastructure.postgres_store import PostgresBillingStore
from costpilot.modules.documents.domain.models import Document, DocumentStatus
from costpilot.modules.documents.infrastructure.postgres_repository import (
    PostgresDocumentRepository,
)
from costpilot.modules.identity.domain.models import VerifiedIdentity
from costpilot.modules.identity.infrastructure.postgres_repository import (
    PostgresIdentityRepository,
)
from costpilot.shared.config import get_settings
from costpilot.shared.database import Database

COUNT_QUERIES = (
    "SELECT count(*) FROM cost_records",
    "SELECT count(*) FROM document_periods",
    "SELECT count(*) FROM monthly_summaries",
)
CE_COLUMNS = ["Service", "EC2-Instances($)", "S3($)"]
CUR_COLUMNS = [
    "bill_payer_account_id",
    "line_item_line_item_type",
    "line_item_usage_start_date",
    "line_item_usage_end_date",
    "line_item_product_code",
    "line_item_unblended_cost",
    "line_item_currency_code",
]


@pytest.fixture
async def database():
    db = Database(get_settings().app_database_url)
    yield db
    await db.close()


@pytest.fixture
def documents(database):
    return PostgresDocumentRepository(database)


@pytest.fixture
def importer(database):
    return BillImportService(store=PostgresBillingStore(database), batch_size=2)


async def new_workspace(database):
    subject = str(uuid4())
    user, _ = await PostgresIdentityRepository(database).save_identity(
        VerifiedIdentity(subject, f"{subject}@example.test", "Test user", "token")
    )
    return user


async def add_document(documents, user, age_days=0):
    document = Document(
        id=uuid4(),
        workspace_id=user.workspace_id,
        uploaded_by=user.user_id,
        file_name="bill.csv",
        storage_key="key",
        size_bytes=1,
        sha256=str(uuid4()),
        status=DocumentStatus.PROCESSED,
        created_at=datetime.now(UTC) - timedelta(days=age_days),
    )
    await documents.create_with_job(document)
    return document


async def import_rows(importer, user, document, columns, rows):
    result = await importer.import_bill(user.workspace_id, document.id, columns, iter(rows))
    await importer.refresh(user.workspace_id)
    return result


def cur_row(month, cost, account="111", currency="USD", product="AmazonEC2"):
    return [
        account,
        "Usage",
        f"{month}-01T00:00:00Z",
        f"{month}-02T00:00:00Z",
        product,
        cost,
        currency,
    ]


async def monthly_totals(database, user):
    async with database.transaction(workspace_id=user.workspace_id) as db:
        rows = await db.execute(
            text(
                "SELECT billing_month, billing_currency, sum(billed_cost) AS total "
                "FROM monthly_summaries GROUP BY 1, 2 ORDER BY 1, 2"
            )
        )
        return {(str(r.billing_month)[:7], r.billing_currency): r.total for r in rows}


async def status_of(documents, user, document):
    return (await documents.get(user.workspace_id, document.id)).status


async def test_exact_totals_reach_the_summaries(database, documents, importer):
    user = await new_workspace(database)
    document = await add_document(documents, user)

    result = await import_rows(
        importer,
        user,
        document,
        CUR_COLUMNS,
        [cur_row("2026-10", "0.1"), cur_row("2026-10", "0.2"), cur_row("2026-09", "1.0000000001")],
    )

    assert result.record_count == 3
    assert result.provider_name == "aws"
    assert str(result.first_month) == "2026-09-01"
    assert str(result.last_month) == "2026-10-01"
    assert await monthly_totals(database, user) == {
        ("2026-09", "USD"): Decimal("1.0000000001"),
        ("2026-10", "USD"): Decimal("0.3"),
    }


async def test_currencies_are_never_added_together(database, documents, importer):
    user = await new_workspace(database)
    document = await add_document(documents, user)

    await import_rows(
        importer,
        user,
        document,
        CUR_COLUMNS,
        [cur_row("2026-10", "1.00"), cur_row("2026-10", "2.00", currency="EUR")],
    )

    assert await monthly_totals(database, user) == {
        ("2026-10", "EUR"): Decimal("2.00"),
        ("2026-10", "USD"): Decimal("1.00"),
    }


async def test_newer_bill_for_the_same_month_replaces_the_older_one(database, documents, importer):
    user = await new_workspace(database)
    older = await add_document(documents, user, age_days=1)
    newer = await add_document(documents, user)

    await import_rows(importer, user, older, CUR_COLUMNS, [cur_row("2026-10", "10.00")])
    await import_rows(importer, user, newer, CUR_COLUMNS, [cur_row("2026-10", "12.00")])

    assert await monthly_totals(database, user) == {("2026-10", "USD"): Decimal("12.00")}
    assert await status_of(documents, user, older) is DocumentStatus.REPLACED
    assert await status_of(documents, user, newer) is DocumentStatus.PROCESSED


async def test_detailed_file_beats_a_newer_summary_file(database, documents, importer):
    user = await new_workspace(database)
    detailed = await add_document(documents, user, age_days=1)
    summary = await add_document(documents, user)

    await import_rows(importer, user, detailed, CUR_COLUMNS, [cur_row("2026-10", "10.00")])
    await import_rows(importer, user, summary, CE_COLUMNS, [["2026-10-01", "99.00", "1.00"]])

    assert await monthly_totals(database, user) == {("2026-10", "USD"): Decimal("10.00")}
    assert await status_of(documents, user, summary) is DocumentStatus.REPLACED


async def test_files_keep_their_months_that_do_not_overlap(database, documents, importer):
    user = await new_workspace(database)
    summary = await add_document(documents, user, age_days=1)
    detailed = await add_document(documents, user)

    await import_rows(
        importer,
        user,
        summary,
        CE_COLUMNS,
        [["2026-09-01", "5.00", "1.00"], ["2026-10-01", "99.00", "1.00"]],
    )
    await import_rows(importer, user, detailed, CUR_COLUMNS, [cur_row("2026-10", "10.00")])

    assert await monthly_totals(database, user) == {
        ("2026-09", "USD"): Decimal("6.00"),
        ("2026-10", "USD"): Decimal("10.00"),
    }
    assert await status_of(documents, user, summary) is DocumentStatus.PROCESSED


async def test_two_accounts_in_the_same_month_both_count(database, documents, importer):
    user = await new_workspace(database)
    first = await add_document(documents, user)
    second = await add_document(documents, user)

    await import_rows(importer, user, first, CUR_COLUMNS, [cur_row("2026-10", "10.00")])
    await import_rows(
        importer, user, second, CUR_COLUMNS, [cur_row("2026-10", "5.00", account="222")]
    )

    assert await monthly_totals(database, user) == {("2026-10", "USD"): Decimal("15.00")}


async def test_deleting_the_winner_brings_the_older_file_back(database, documents, importer):
    user = await new_workspace(database)
    older = await add_document(documents, user, age_days=1)
    newer = await add_document(documents, user)
    await import_rows(importer, user, older, CUR_COLUMNS, [cur_row("2026-10", "10.00")])
    await import_rows(importer, user, newer, CUR_COLUMNS, [cur_row("2026-10", "12.00")])

    await documents.delete(user.workspace_id, newer.id)
    await importer.refresh(user.workspace_id)

    assert await monthly_totals(database, user) == {("2026-10", "USD"): Decimal("10.00")}
    assert await status_of(documents, user, older) is DocumentStatus.PROCESSED


async def test_deleting_the_only_file_empties_the_summaries(database, documents, importer):
    user = await new_workspace(database)
    document = await add_document(documents, user)
    await import_rows(importer, user, document, CUR_COLUMNS, [cur_row("2026-10", "10.00")])

    await documents.delete(user.workspace_id, document.id)
    await importer.refresh(user.workspace_id)

    assert await monthly_totals(database, user) == {}


async def test_importing_again_does_not_double_count(database, documents, importer):
    user = await new_workspace(database)
    document = await add_document(documents, user)

    await import_rows(importer, user, document, CUR_COLUMNS, [cur_row("2026-10", "10.00")])
    await import_rows(importer, user, document, CUR_COLUMNS, [cur_row("2026-10", "10.00")])

    assert await monthly_totals(database, user) == {("2026-10", "USD"): Decimal("10.00")}


async def test_a_bad_row_saves_nothing(database, documents, importer):
    user = await new_workspace(database)
    document = await add_document(documents, user)
    rows = [cur_row("2026-10", "1.00") for _ in range(5)] + [cur_row("2026-10", "bad")]

    with pytest.raises(BillRejectedError, match="Row 7"):
        await import_rows(importer, user, document, CUR_COLUMNS, rows)

    async with database.transaction(workspace_id=user.workspace_id) as db:
        saved = await db.execute(text("SELECT count(*) FROM cost_records"))
        assert saved.scalar_one() == 0


async def test_one_workspace_cannot_read_anothers_costs(database, documents, importer):
    owner, stranger = await new_workspace(database), await new_workspace(database)
    document = await add_document(documents, owner)
    await import_rows(importer, owner, document, CUR_COLUMNS, [cur_row("2026-10", "10.00")])

    assert await monthly_totals(database, stranger) == {}
    async with database.transaction(workspace_id=stranger.workspace_id) as db:
        for query in COUNT_QUERIES:
            assert (await db.execute(text(query))).scalar_one() == 0
