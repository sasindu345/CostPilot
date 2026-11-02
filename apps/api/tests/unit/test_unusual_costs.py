from datetime import date
from decimal import Decimal

from costpilot.modules.analytics.domain.calculations import month_window
from costpilot.modules.analytics.domain.models import ServiceMonthCost
from costpilot.modules.analytics.infrastructure.numpy_unusual_cost_detector import (
    NumpyUnusualCostDetector,
)

LATEST = date(2026, 10, 1)


def detector():
    return NumpyUnusualCostDetector(
        history_months=6,
        min_history_months=3,
        threshold=3.0,
        min_increase_percent=20,
        min_increase_amount=1,
    )


def history(service, *amounts):
    months = month_window(LATEST, len(amounts))
    return [
        ServiceMonthCost(month, service, "USD", Decimal(amount))
        for month, amount in zip(months, amounts, strict=True)
    ]


def test_a_sudden_spike_is_found_with_exact_amounts():
    found = detector().find(history("EC2", "100", "102", "98", "101", "99", "300"), LATEST)

    assert len(found) == 1
    assert found[0].service == "EC2"
    assert found[0].usual_cost == Decimal("100")
    assert found[0].increase == Decimal("200")
    assert found[0].percent == Decimal("200.0")


def test_normal_ups_and_downs_are_ignored():
    assert detector().find(history("EC2", "100", "130", "90", "120", "95", "125"), LATEST) == []


def test_an_earlier_spike_does_not_hide_a_new_one():
    found = detector().find(history("EC2", "100", "1000", "100", "100", "100", "400"), LATEST)

    assert [item.service for item in found] == ["EC2"]


def test_a_tiny_amount_is_not_worth_flagging():
    assert detector().find(history("S3", "0.01", "0.01", "0.01", "0.50"), LATEST) == []


def test_a_small_percent_rise_on_a_steady_service_is_ignored():
    assert detector().find(history("EC2", "100", "100", "100", "110"), LATEST) == []


def test_not_enough_history_means_no_opinion():
    assert detector().find(history("EC2", "1", "1", "500"), LATEST) == []


def test_a_cost_going_down_is_not_flagged():
    assert detector().find(history("EC2", "100", "100", "100", "10"), LATEST) == []


def test_biggest_increase_comes_first():
    costs = history("Small", "10", "10", "10", "50") + history("Big", "100", "100", "100", "500")

    assert [item.service for item in detector().find(costs, LATEST)] == ["Big", "Small"]
