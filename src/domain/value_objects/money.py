"""Money value object — immutable, Decimal-based currency representation."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from domain.exceptions import InvalidMoneyError


@dataclass(frozen=True)
class Money:
    """Immutable money with Decimal precision and currency code."""

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        if self.amount < Decimal("0"):
            raise InvalidMoneyError(
                f"Money amount cannot be negative (got {self.amount})."
            )
        # Normalize to 2 decimal places
        quantized = self.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        object.__setattr__(self, "amount", quantized)
