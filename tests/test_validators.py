"""
tests/test_validators.py
~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for the pure validation helpers in :mod:`bot.validators`.

Run with:  python -m pytest tests/ -v
"""

import pytest
from bot.validators import (
    validate_price,
    validate_quantity,
    validate_side,
    validate_order_type,
    validate_symbol,
)


# ── validate_symbol ───────────────────────────────────────────────────────────

class TestValidateSymbol:
    def test_valid_lowercase_normalised(self):
        assert validate_symbol("btcusdt") == "BTCUSDT"

    def test_valid_uppercase_unchanged(self):
        assert validate_symbol("ETHUSDT") == "ETHUSDT"

    def test_raises_on_empty_string(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_symbol("")

    def test_raises_on_whitespace_only(self):
        with pytest.raises(ValueError, match="blank"):
            validate_symbol("   ")

    def test_raises_on_none(self):
        with pytest.raises((ValueError, AttributeError)):
            validate_symbol(None)


# ── validate_side ─────────────────────────────────────────────────────────────

class TestValidateSide:
    def test_buy_uppercase(self):
        assert validate_side("BUY") == "BUY"

    def test_sell_lowercase_normalised(self):
        assert validate_side("sell") == "SELL"

    def test_raises_on_invalid(self):
        with pytest.raises(ValueError, match="BUY or SELL"):
            validate_side("HOLD")

    def test_raises_on_empty(self):
        with pytest.raises(ValueError):
            validate_side("")


# ── validate_order_type ───────────────────────────────────────────────────────

class TestValidateOrderType:
    def test_market_uppercase(self):
        assert validate_order_type("MARKET") == "MARKET"

    def test_limit_lowercase_normalised(self):
        assert validate_order_type("limit") == "LIMIT"

    def test_raises_on_invalid(self):
        with pytest.raises(ValueError, match="MARKET or LIMIT"):
            validate_order_type("STOP")


# ── validate_quantity ─────────────────────────────────────────────────────────

class TestValidateQuantity:
    def test_valid_float_string(self):
        assert validate_quantity("0.01") == pytest.approx(0.01)

    def test_valid_int(self):
        assert validate_quantity(1) == 1.0

    def test_raises_on_zero(self):
        with pytest.raises(ValueError, match="greater than 0"):
            validate_quantity(0)

    def test_raises_on_negative(self):
        with pytest.raises(ValueError, match="greater than 0"):
            validate_quantity(-5)

    def test_raises_on_non_numeric(self):
        with pytest.raises(ValueError, match="positive number"):
            validate_quantity("abc")


# ── validate_price ────────────────────────────────────────────────────────────

class TestValidatePrice:
    def test_market_ignores_price(self):
        """MARKET orders should always return None regardless of price input."""
        assert validate_price(99999, "MARKET") is None
        assert validate_price(None, "MARKET") is None

    def test_limit_valid_price(self):
        assert validate_price("85000", "LIMIT") == pytest.approx(85000.0)

    def test_limit_raises_on_missing_price(self):
        with pytest.raises(ValueError, match="required for LIMIT"):
            validate_price(None, "LIMIT")

    def test_limit_raises_on_zero_price(self):
        with pytest.raises(ValueError, match="greater than 0"):
            validate_price(0, "LIMIT")

    def test_limit_raises_on_negative_price(self):
        with pytest.raises(ValueError, match="greater than 0"):
            validate_price(-1, "LIMIT")

    def test_limit_raises_on_non_numeric(self):
        with pytest.raises(ValueError, match="positive number"):
            validate_price("abc", "LIMIT")
