"""Tests for the Money value object."""
from decimal import Decimal
import pytest
from domain.value_objects.money import Money
from domain.exceptions import InvalidMoneyError


class TestMoneyCreation:
    def test_valid_creation(self):
        m = Money(amount=Decimal("10.00"), currency="USD")
        assert m.amount == Decimal("10.00")
        assert m.currency == "USD"

    def test_negative_amount_raises(self):
        with pytest.raises(InvalidMoneyError):
            Money(amount=Decimal("-1.00"), currency="USD")

    def test_zero_is_valid(self):
        m = Money(amount=Decimal("0.00"), currency="USD")
        assert m.amount == Decimal("0.00")

    def test_is_immutable(self):
        m = Money(amount=Decimal("5.00"), currency="USD")
        with pytest.raises((AttributeError, TypeError)):
            m.amount = Decimal("99.00")


class TestMoneyEquality:
    def test_same_amount_and_currency_equal(self):
        a = Money(amount=Decimal("10.00"), currency="USD")
        b = Money(amount=Decimal("10.00"), currency="USD")
        assert a == b

    def test_different_currency_not_equal(self):
        a = Money(amount=Decimal("10.00"), currency="USD")
        b = Money(amount=Decimal("10.00"), currency="EUR")
        assert a != b

    def test_different_amount_not_equal(self):
        a = Money(amount=Decimal("10.00"), currency="USD")
        b = Money(amount=Decimal("20.00"), currency="USD")
        assert a != b
