from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Recommendation:
    """A cost finding made by plain rules. `monthly_saving` is None unless it can be proven."""

    id: str
    provider: str
    title: str
    reason: str
    currency: str
    monthly_saving: Decimal | None = None
    source_title: str | None = None
    source_url: str | None = None
