"""What each cloud supplies. A new cloud adds a profile here, and no new agents are needed."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SteadyServiceRule:
    """Suggests a commitment when a service costs about the same each month."""

    id: str
    title: str
    reason: str
    services: tuple[str, ...]
    source_title: str
    source_path: str


@dataclass(frozen=True)
class ServiceReviewRule:
    """Suggests a review when a service costs enough to be worth one."""

    id: str
    title: str
    reason: str
    services: tuple[str, ...]
    source_title: str
    source_path: str


@dataclass(frozen=True)
class UsageReviewRule:
    """Suggests a review when a usage type appears on the bill."""

    id: str
    title: str
    reason: str
    usage_marker: str
    source_title: str
    source_path: str


@dataclass(frozen=True)
class PriceDifferenceRule:
    """Works out a saving, because the provider publishes the exact price difference."""

    id: str
    title: str
    reason: str
    usage_marker: str
    saving_rate: Decimal
    source_title: str
    source_path: str


@dataclass(frozen=True)
class ProviderProfile:
    provider: str
    steady_rules: tuple[SteadyServiceRule, ...] = ()
    review_rules: tuple[ServiceReviewRule, ...] = ()
    usage_rules: tuple[UsageReviewRule, ...] = ()
    price_rules: tuple[PriceDifferenceRule, ...] = ()


AWS = ProviderProfile(
    provider="aws",
    price_rules=(
        PriceDifferenceRule(
            id="aws-gp2-to-gp3",
            title="Move EBS gp2 volumes to gp3",
            reason="AWS lists gp3 at a 20 percent lower price per GiB than gp2.",
            usage_marker="gp2",
            saving_rate=Decimal("0.20"),
            source_title="EBS General Purpose SSD volumes",
            source_path="/ebs/latest/userguide/general-purpose.html",
        ),
    ),
    steady_rules=(
        SteadyServiceRule(
            id="aws-ec2-savings-plans",
            title="Consider Savings Plans for steady EC2 use",
            reason="Your EC2 cost has been steady, which suits a usage commitment.",
            services=("EC2-Instances", "AmazonEC2", "EC2"),
            source_title="What are Savings Plans",
            source_path="/savingsplans/latest/userguide/what-is-savings-plans.html",
        ),
        SteadyServiceRule(
            id="aws-rds-reserved",
            title="Consider RDS Reserved Instances",
            reason="Your RDS cost has been steady, which suits a reservation.",
            services=("RDS", "AmazonRDS"),
            source_title="RDS Reserved DB instances",
            source_path="/AmazonRDS/latest/UserGuide/USER_WorkingWithReservedDBInstances.html",
        ),
    ),
    review_rules=(
        ServiceReviewRule(
            id="aws-s3-lifecycle",
            title="Review S3 storage lifecycle rules",
            reason="Lifecycle rules can move objects you rarely read to cheaper storage.",
            services=("S3", "AmazonS3"),
            source_title="S3 object lifecycle management",
            source_path="/AmazonS3/latest/userguide/object-lifecycle-mgmt.html",
        ),
    ),
    usage_rules=(
        UsageReviewRule(
            id="aws-nat-gateway",
            title="Review NAT gateway traffic",
            reason="NAT gateways charge per hour and for each gigabyte they process.",
            usage_marker="NatGateway",
            source_title="NAT gateway pricing",
            source_path="/vpc/latest/userguide/nat-gateway-pricing.html",
        ),
    ),
)

PROFILES = {AWS.provider: AWS}
