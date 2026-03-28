"""
bot/validators.py
~~~~~~~~~~~~~~~~~
Pure input-validation helpers for the trading bot CLI.

All functions are side-effect-free and raise :class:`ValueError` with a clear
human-readable message on invalid input. This makes them easy to unit-test and
to reuse from any entry point (CLI, REST hook, tests, etc.).
"""

from typing import Optional


VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}


def validate_symbol(symbol: str) -> str:
    """
    Validate and normalise a trading symbol.

    Args:
        symbol: Raw symbol string from user input (e.g. ``"btcusdt"``).

    Returns:
        Upper-cased symbol string (e.g. ``"BTCUSDT"``).

    Raises:
        ValueError: If the symbol is empty or not a string.
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string (example: BTCUSDT).")
    normalised = symbol.strip().upper()
    if not normalised:
        raise ValueError("Symbol cannot be blank (example: BTCUSDT).")
    return normalised


def validate_side(side: str) -> str:
    """
    Validate the order side.

    Args:
        side: Raw side string (e.g. ``"buy"``).

    Returns:
        Upper-cased side string – either ``"BUY"`` or ``"SELL"``.

    Raises:
        ValueError: If the value is not BUY or SELL.
    """
    normalised = side.strip().upper()
    if normalised not in VALID_SIDES:
        raise ValueError(
            f"Side must be BUY or SELL, got '{side}'."
        )
    return normalised


def validate_order_type(order_type: str) -> str:
    """
    Validate the order type.

    Args:
        order_type: Raw order type string (e.g. ``"market"``).

    Returns:
        Upper-cased order type – either ``"MARKET"`` or ``"LIMIT"``.

    Raises:
        ValueError: If the value is not MARKET or LIMIT.
    """
    normalised = order_type.strip().upper()
    if normalised not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Order type must be MARKET or LIMIT, got '{order_type}'."
        )
    return normalised


def validate_quantity(quantity: str | float) -> float:
    """
    Validate and parse the order quantity.

    Args:
        quantity: Quantity as a string or float.

    Returns:
        A positive float quantity.

    Raises:
        ValueError: If the value cannot be parsed or is not positive.
    """
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise ValueError(
            f"Quantity must be a positive number, got '{quantity}'."
        )
    if qty <= 0:
        raise ValueError(
            f"Quantity must be greater than 0, got {qty}."
        )
    return qty


def validate_price(price: Optional[str | float], order_type: str) -> Optional[float]:
    """
    Validate the order price.

    For LIMIT orders the price is **required** and must be positive.
    For MARKET orders the price is **ignored** (returns ``None``).

    Args:
        price: Price as a string, float, or ``None``.
        order_type: An already-validated order type string (``"MARKET"`` or ``"LIMIT"``).

    Returns:
        A positive float price for LIMIT orders; ``None`` for MARKET orders.

    Raises:
        ValueError: If price is missing or invalid for a LIMIT order.
    """
    if order_type == "MARKET":
        # Price is irrelevant for MARKET orders; silently ignore it.
        return None

    # LIMIT order: price is mandatory
    if price is None:
        raise ValueError(
            "Price is required for LIMIT orders. Use --price <value>."
        )
    try:
        p = float(price)
    except (TypeError, ValueError):
        raise ValueError(
            f"Price must be a positive number, got '{price}'."
        )
    if p <= 0:
        raise ValueError(
            f"Price must be greater than 0, got {p}."
        )
    return p
