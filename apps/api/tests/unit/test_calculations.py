"""Worked out by hand. The first test uses the figures from the design image."""

from datetime import date
from decimal import Decimal

from costpilot.modules.analytics.domain.calculations import (
    build_trend,
    compare_services,
    month_window,
    monthly_totals,
    percent_change,
    previous_month,
    top_services,
)
from costpilot.modules.analytics.domain.models import ServiceMonthCost

OCT = date(2026, 10, 1)
SEP = date(2026, 9, 1)


def cost(month, service, amount):
    return ServiceMonthCost(month, service, "USD", Decimal(amount))


DESIGN_MONTH = [
    cost(OCT, "EC2", "120.00"),
    cost(OCT, "RDS", "65.00"),
    cost(OCT, "S3", "18.60"),
    cost(OCT, "CloudWatch", "25.00"),
    cost(OCT, "Lambda", "20.00"),
]


def test_the_change_in_the_design_image_is_minus_8_1_percent():
    assert percent_change(Decimal("270.40"), Decimal("248.60")) == Decimal("-8.1")


def test_a_rise_is_positive():
    assert percent_change(Decimal("100"), Decimal("150")) == Decimal("50.0")


def test_percent_rounds_half_up():
    assert percent_change(Decimal("1000"), Decimal("1000.5")) == Decimal("0.1")


def test_no_percent_from_zero():
    assert percent_change(Decimal("0"), Decimal("10")) is None


def test_no_percent_from_a_net_credit():
    assert percent_change(Decimal("-5"), Decimal("10")) is None


def test_six_month_window_ends_at_the_latest_month():
    window = month_window(OCT, 6)

    assert window[0] == date(2026, 5, 1)
    assert window[-1] == OCT
    assert len(window) == 6


def test_window_crosses_the_new_year():
    assert month_window(date(2027, 1, 1), 2) == [date(2026, 12, 1), date(2027, 1, 1)]


def test_previous_month_of_january():
    assert previous_month(date(2027, 1, 1)) == date(2026, 12, 1)


def test_top_services_add_up_to_the_total_with_an_other_row():
    rows = top_services(DESIGN_MONTH, OCT, limit=3)

    assert [row.name for row in rows] == ["EC2", "RDS", "CloudWatch", "Other"]
    assert sum(row.cost for row in rows) == Decimal("248.60")
    assert rows[0].share_percent == Decimal("48.3")
    assert rows[-1].cost == Decimal("38.60")


def test_a_service_named_other_joins_the_other_row_instead_of_repeating_it():
    costs = [
        cost(OCT, "EC2", "120.00"),
        cost(OCT, "RDS", "65.00"),
        cost(OCT, "S3", "18.60"),
        cost(OCT, "Other", "45.00"),
    ]

    rows = top_services(costs, OCT, limit=3)

    assert [row.name for row in rows] == ["EC2", "RDS", "S3", "Other"]
    assert rows[-1].cost == Decimal("45.00")


def test_a_service_named_other_is_added_to_the_smaller_services():
    costs = [*DESIGN_MONTH, cost(OCT, "Other", "1.00")]

    rows = top_services(costs, OCT, limit=3)

    assert [row.name for row in rows].count("Other") == 1
    assert rows[-1].cost == Decimal("39.60")


def test_no_other_row_when_everything_fits():
    rows = top_services(DESIGN_MONTH, OCT, limit=5)

    assert "Other" not in [row.name for row in rows]


def test_top_services_ignore_other_months():
    assert top_services([cost(SEP, "EC2", "1")], OCT, limit=3) == []


def test_a_month_of_only_credits_has_no_shares():
    assert top_services([cost(OCT, "Credit", "-5")], OCT, limit=3) == []


def test_a_missing_month_stays_empty_but_a_zero_month_stays_zero():
    totals = {OCT: Decimal(0)}

    trend = build_trend(totals, [SEP, OCT])

    assert trend[0].cost is None
    assert trend[1].cost == Decimal(0)


def test_monthly_totals_are_exact():
    totals = monthly_totals([cost(OCT, "A", "0.1"), cost(OCT, "B", "0.2")])

    assert totals[OCT] == Decimal("0.3")


def test_comparison_shows_the_biggest_change_first_and_new_services():
    rows = compare_services(
        [
            cost(SEP, "EC2", "100"),
            cost(OCT, "EC2", "90"),
            cost(OCT, "New", "30"),
            cost(SEP, "Gone", "5"),
        ],
        SEP,
        OCT,
    )

    assert [row.service for row in rows] == ["New", "EC2", "Gone"]
    assert rows[0].percent is None
    assert rows[1].difference == Decimal("-10")
    assert rows[1].percent == Decimal("-10.0")
    assert rows[2].second_cost == Decimal(0)
