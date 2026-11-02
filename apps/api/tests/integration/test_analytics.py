"""Tests analytics on real PostgreSQL. Needs `make up`."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from costpilot.composition import build_analytics_service
from costpilot.modules.analytics.application.analytics_service import AnalyticsService
from costpilot.modules.analytics.domain.models import CostType, Filters
from costpilot.modules.analytics.infrastructure.numpy_unusual_cost_detector import (
    NumpyUnusualCostDetector,
)
from costpilot.modules.analytics.infrastructure.postgres_store import PostgresAnalyticsStore
from costpilot.modules.billing.application.import_service import BillImportService
from costpilot.modules.billing.infrastructure.postgres_store import PostgresBillingStore
from costpilot.modules.documents.infrastructure.postgres_repository import (
    PostgresDocumentRepository,
)
from costpilot.modules.identity.domain.models import VerifiedIdentity
from costpilot.modules.identity.infrastructure.postgres_repository import (
    PostgresIdentityRepository,
)
from costpilot.shared.config import get_settings
from costpilot.shared.database import Database
from tests.integration.test_billing import CE_COLUMNS, CUR_COLUMNS, add_document, cur_row

SIX_MONTHS = Filters(months=6)


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
    return BillImportService(store=PostgresBillingStore(database), batch_size=100)


@pytest.fixture
def analytics(database):
    return build_analytics_service(get_settings(), database)


async def new_user(database):
    subject = str(uuid4())
    user, _ = await PostgresIdentityRepository(database).save_identity(
        VerifiedIdentity(subject, f"{subject}@example.test", "Test user", "token")
    )
    return user


async def load(importer, documents, user, columns, rows):
    document = await add_document(documents, user)
    await importer.import_bill(user.workspace_id, document.id, columns, iter(rows))
    await importer.refresh(user.workspace_id)


def day_row(day, cost):
    return [
        "111",
        "Usage",
        f"{day}T00:00:00Z",
        f"{day}T23:59:59Z",
        "AmazonEC2",
        cost,
        "USD",
    ]


async def test_a_new_workspace_has_no_overview(database, analytics):
    user = await new_user(database)

    assert await analytics.overview(user.workspace_id, SIX_MONTHS) is None


async def test_design_image_figures_are_correct(database, documents, importer, analytics):
    user = await new_user(database)
    await load(
        importer,
        documents,
        user,
        CE_COLUMNS,
        [["2026-09-01", "250.40", "20.00"], ["2026-10-01", "230.00", "18.60"]],
    )

    overview = await analytics.overview(user.workspace_id, SIX_MONTHS)

    assert overview.total == Decimal("519.00")
    assert overview.latest_cost == Decimal("248.60")
    assert overview.previous_cost == Decimal("270.40")
    assert overview.change.percent == Decimal("-8.1")
    assert overview.latest_is_partial is False
    assert [point.cost for point in overview.trend][:4] == [None, None, None, None]
    assert sum(service.cost for service in overview.top_services) == Decimal("248.60")


async def test_a_half_finished_month_is_compared_with_the_same_days(
    database, documents, importer, analytics
):
    user = await new_user(database)
    september = [day_row(f"2026-09-{day:02d}", "10.00") for day in range(1, 31)]
    october = [day_row(f"2026-10-{day:02d}", "12.00") for day in range(1, 11)]
    await load(importer, documents, user, CUR_COLUMNS, september + october)

    overview = await analytics.overview(user.workspace_id, SIX_MONTHS)

    assert overview.latest_cost == Decimal("120.00")
    assert overview.latest_is_partial is True
    assert overview.days_covered == 10
    assert overview.change.compared_days == 10
    assert overview.change.previous_cost == Decimal("100.00")
    assert overview.change.percent == Decimal("20.0")


async def test_a_current_month_summary_file_gives_no_false_percentage(
    database, documents, importer
):
    user = await new_user(database)
    service = AnalyticsService(
        store=PostgresAnalyticsStore(database),
        detector=NumpyUnusualCostDetector(6, 3, 3.0, 20, 1),
        top_service_limit=3,
        today=lambda: date(2026, 10, 15),
    )
    await load(
        importer,
        documents,
        user,
        CE_COLUMNS,
        [["2026-09-01", "100.00", "0"], ["2026-10-01", "40.00", "0"]],
    )

    overview = await service.overview(user.workspace_id, SIX_MONTHS)

    assert overview.latest_is_partial is True
    assert overview.change.percent is None


async def test_each_currency_is_shown_on_its_own(database, documents, importer, analytics):
    user = await new_user(database)
    await load(
        importer,
        documents,
        user,
        CUR_COLUMNS,
        [
            cur_row("2026-10", "1.00"),
            cur_row("2026-10", "2.00", product="AmazonS3"),
            cur_row("2026-10", "50.00", currency="EUR"),
        ],
    )

    default = await analytics.overview(user.workspace_id, SIX_MONTHS)
    euros = await analytics.overview(user.workspace_id, Filters(months=6, currency="EUR"))

    assert default.currency == "USD"
    assert default.latest_cost == Decimal("3.00")
    assert euros.latest_cost == Decimal("50.00")
    assert set(default.currencies) == {"USD", "EUR"}


async def test_provider_filter(database, documents, importer, analytics):
    user = await new_user(database)
    await load(importer, documents, user, CUR_COLUMNS, [cur_row("2026-10", "1.00")])

    assert await analytics.overview(user.workspace_id, Filters(months=6, provider="azure")) is None


async def test_billed_and_effective_costs_are_separate(database, documents, importer, analytics):
    user = await new_user(database)
    columns = [*CUR_COLUMNS, "savings_plan_savings_plan_effective_cost"]
    row = cur_row("2026-10", "10.00")
    row[1] = "SavingsPlanCoveredUsage"
    await load(importer, documents, user, columns, [[*row, "7.00"]])

    billed = await analytics.overview(user.workspace_id, SIX_MONTHS)
    effective = await analytics.overview(
        user.workspace_id, Filters(months=6, cost_type=CostType.EFFECTIVE)
    )

    assert billed.latest_cost == Decimal("10.00")
    assert effective.latest_cost == Decimal("7.00")


async def test_unusual_spending_is_found(database, documents, importer, analytics):
    user = await new_user(database)
    rows = [
        ["2026-06-01", "100.00", "10.00"],
        ["2026-07-01", "101.00", "10.00"],
        ["2026-08-01", "99.00", "10.00"],
        ["2026-09-01", "100.00", "10.00"],
        ["2026-10-01", "300.00", "10.00"],
    ]
    await load(importer, documents, user, CE_COLUMNS, rows)

    unusual = await analytics.unusual_costs(user.workspace_id, SIX_MONTHS)

    assert [item.service for item in unusual] == ["EC2-Instances"]
    assert unusual[0].usual_cost == Decimal("100.00")


async def test_comparison_of_two_months(database, documents, importer, analytics):
    user = await new_user(database)
    await load(
        importer,
        documents,
        user,
        CE_COLUMNS,
        [["2026-09-01", "100.00", "10.00"], ["2026-10-01", "150.00", "10.00"]],
    )

    rows = await analytics.compare(
        user.workspace_id, SIX_MONTHS, date(2026, 9, 1), date(2026, 10, 1)
    )

    assert rows[0].service == "EC2-Instances"
    assert rows[0].difference == Decimal("50.00")


async def test_one_workspace_cannot_read_anothers_analytics(
    database, documents, importer, analytics
):
    owner, stranger = await new_user(database), await new_user(database)
    await load(importer, documents, owner, CUR_COLUMNS, [cur_row("2026-10", "10.00")])

    assert await analytics.overview(stranger.workspace_id, SIX_MONTHS) is None
