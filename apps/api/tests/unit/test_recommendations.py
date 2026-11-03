"""The rules must be repeatable, and a saving may only appear if it can be proven."""

from datetime import date
from decimal import Decimal

import pytest

from costpilot.modules.analytics.contracts import ServiceMonthCost, UsageChange
from costpilot.modules.recommendations.domain.profiles import (
    AWS,
    AZURE,
    GCP,
    PROFILES,
    ProviderProfile,
)
from costpilot.modules.recommendations.domain.rules import RuleInput, find_recommendations

OCT = date(2026, 10, 1)
DOCS = "https://docs.aws.amazon.com"
MONTHS = (date(2026, 8, 1), date(2026, 9, 1), OCT)


def costs(service, *amounts):
    return [
        ServiceMonthCost(month, service, "USD", Decimal(amount))
        for month, amount in zip(MONTHS, amounts, strict=True)
    ]


def usage(usage_type, cost):
    return UsageChange("EC2-Other", usage_type, "us-east-1", Decimal(cost), Decimal(cost), 2)


def run(costs_list=(), usage_list=()):
    data = RuleInput(costs_list, usage_list, OCT, "USD", Decimal(5), Decimal("1.25"), DOCS)
    return find_recommendations(AWS, data)


def ids(found):
    return [item.id for item in found]


def test_gp2_saving_is_worked_out_from_the_published_price_difference():
    found = run(usage_list=[usage("EBS:VolumeUsage.gp2", "50.00")])

    assert ids(found) == ["aws-gp2-to-gp3"]
    assert found[0].monthly_saving == Decimal("10.00")
    assert found[0].source_url.startswith("https://docs.aws.amazon.com")


def test_every_other_rule_claims_no_saving():
    found = run(
        costs("EC2-Instances", "100", "105", "110") + costs("S3", "20", "20", "20"),
        [usage("NatGateway-Hours", "30.00")],
    )

    assert set(ids(found)) == {"aws-nat-gateway", "aws-ec2-savings-plans", "aws-s3-lifecycle"}
    assert all(item.monthly_saving is None for item in found)


def test_an_unsteady_service_gets_no_commitment_advice():
    assert "aws-ec2-savings-plans" not in ids(run(costs("EC2-Instances", "100", "40", "200")))


def test_a_service_missing_from_one_month_is_not_steady():
    assert run(costs("RDS", "0", "70", "70")) == []


def test_small_costs_are_ignored():
    assert run(costs("S3", "1", "1", "1"), [usage("EBS:VolumeUsage.gp2", "1.00")]) == []


def test_the_same_bill_always_gives_the_same_result():
    bill = costs("S3", "20", "20", "20")

    assert run(bill) == run(bill)


def test_a_cloud_with_no_rules_gets_no_advice():
    data = RuleInput(
        costs("S3", "20", "20", "20"), [], OCT, "USD", Decimal(5), Decimal("1.25"), DOCS
    )

    assert find_recommendations(ProviderProfile("azure"), data) == []


@pytest.mark.parametrize(
    ("profile", "service", "rule"),
    [
        (AZURE, "Virtual Machines", "azure-vm-reservations"),
        (GCP, "Compute Engine", "gcp-committed-use"),
    ],
)
def test_other_clouds_suggest_their_own_commitments(profile, service, rule):
    data = RuleInput(
        costs(service, "50", "50", "50"), [], OCT, "USD", Decimal(5), Decimal("1.25"), DOCS
    )

    found = find_recommendations(profile, data)

    assert rule in ids(found)
    assert all(item.monthly_saving is None for item in found)
    assert found[0].provider == profile.provider


def test_every_cloud_has_a_profile():
    assert set(PROFILES) == {"aws", "azure", "gcp", "oci", "digitalocean"}
