from datetime import date
from decimal import Decimal

import numpy as np

from costpilot.modules.analytics.domain.calculations import month_window, percent_change
from costpilot.modules.analytics.domain.models import ServiceMonthCost, UnusualCost

# Makes the median absolute deviation comparable to a standard deviation.
MAD_SCALE = 1.4826


class NumpyUnusualCostDetector:
    """Flags a service whose month is far above its own usual level.

    It uses the median, so one earlier spike does not hide a new one. NumPy decimals are only
    used to decide what looks unusual. Every amount shown to users stays exact.
    """

    def __init__(
        self,
        history_months: int,
        min_history_months: int,
        threshold: float,
        min_increase_percent: float,
        min_increase_amount: float,
    ) -> None:
        self._history_months = history_months
        self._min_history_months = min_history_months
        self._threshold = threshold
        self._min_increase_percent = min_increase_percent
        self._min_increase_amount = min_increase_amount

    def find(self, costs: list[ServiceMonthCost], latest_month: date) -> list[UnusualCost]:
        history_window = month_window(latest_month, self._history_months + 1)[:-1]
        by_service: dict[str, dict[date, Decimal]] = {}
        for item in costs:
            service = by_service.setdefault(item.service, {})
            service[item.month] = service.get(item.month, Decimal(0)) + item.cost

        found = []
        for service, months in by_service.items():
            current = months.get(latest_month)
            history = [months[month] for month in history_window if month in months]
            if current is None or len(history) < self._min_history_months:
                continue
            usual = self._usual_level(history)
            if self._is_unusual(float(current), [float(value) for value in history]):
                found.append(
                    UnusualCost(
                        service=service,
                        month=latest_month,
                        cost=current,
                        usual_cost=usual,
                        increase=current - usual,
                        percent=percent_change(usual, current),
                    )
                )
        return sorted(found, key=lambda item: -item.increase)

    def _usual_level(self, history: list[Decimal]) -> Decimal:
        ordered = sorted(history)
        middle = len(ordered) // 2
        if len(ordered) % 2:
            return ordered[middle]
        return (ordered[middle - 1] + ordered[middle]) / 2

    def _is_unusual(self, current: float, history: list[float]) -> bool:
        values = np.array(history)
        median = float(np.median(values))
        spread = MAD_SCALE * float(np.median(np.abs(values - median)))
        increase = current - median
        if increase < self._min_increase_amount:
            return False
        if median > 0 and increase / median * 100 < self._min_increase_percent:
            return False
        return spread == 0 or increase / spread >= self._threshold
