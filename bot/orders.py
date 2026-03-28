"""
bot/orders.py
~~~~~~~~~~~~~
Order placement orchestrator.

This module owns the business logic for placing MARKET and LIMIT orders.
It calls validators, prints a pre-flight summary, delegates to the Binance
client, and prints the formatted order response.
"""

from typing import Optional

from bot.client import BinanceClient
from bot.logging_config import get_logger
from bot import validators

logger = get_logger(__name__)


class OrderService:
    """
    High-level order service that wraps :class:`~bot.client.BinanceClient`.

    Args:
        client: An initialised :class:`~bot.client.BinanceClient` instance.
    """

    def __init__(self, client: BinanceClient) -> None:
        self._client = client

    # ── Public methods ────────────────────────────────────────────────────────

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str | float,
        price: Optional[str | float] = None,
    ) -> dict:
        """
        Validate inputs, print a pre-flight summary, place the order, and
        print the formatted response.

        Args:
            symbol: Trading pair (e.g. ``"BTCUSDT"``).
            side: ``"BUY"`` or ``"SELL"`` (case-insensitive).
            order_type: ``"MARKET"`` or ``"LIMIT"`` (case-insensitive).
            quantity: Order quantity in base asset units.
            price: Limit price; required for ``"LIMIT"`` orders, ignored for
                ``"MARKET"`` orders.

        Returns:
            Raw response dictionary from the Binance API.

        Raises:
            :class:`ValueError`: On invalid input.
            :class:`~bot.client.BinanceAPIError`: On an API-level error.
            :class:`~bot.client.NetworkError`: On a network failure.
        """
        # ── Validate ──────────────────────────────────────────────────────────
        symbol = validators.validate_symbol(symbol)
        side = validators.validate_side(side)
        order_type = validators.validate_order_type(order_type)
        qty = validators.validate_quantity(quantity)
        validated_price = validators.validate_price(price, order_type)

        # ── Pre-flight summary ────────────────────────────────────────────────
        self._print_order_summary(symbol, side, order_type, qty, validated_price)
        logger.info(
            "Placing %s %s order | symbol=%s | qty=%s | price=%s",
            side,
            order_type,
            symbol,
            qty,
            validated_price if validated_price is not None else "N/A (MARKET)",
        )

        # ── Place order ───────────────────────────────────────────────────────
        response = self._client.new_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=qty,
            price=validated_price,
        )

        # ── Print response ────────────────────────────────────────────────────
        self._print_order_response(response)
        logger.info(
            "Order accepted | orderId=%s | status=%s | executedQty=%s | avgPrice=%s",
            response.get("orderId"),
            response.get("status"),
            response.get("executedQty"),
            response.get("avgPrice", "N/A"),
        )

        return response

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _print_order_summary(
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float],
    ) -> None:
        """Print a clean pre-flight order summary to the console."""
        sep = "─" * 45
        print(f"\n{sep}")
        print("  ORDER SUMMARY")
        print(sep)
        print(f"  Symbol     : {symbol}")
        print(f"  Side       : {side}")
        print(f"  Type       : {order_type}")
        print(f"  Quantity   : {quantity}")
        if order_type == "LIMIT" and price is not None:
            print(f"  Price      : {price}")
            print(f"  TimeInForce: GTC")
        else:
            print(f"  Price      : N/A (MARKET order)")
        print(f"{sep}\n")

    @staticmethod
    def _print_order_response(response: dict) -> None:
        """Print a clean formatted order response to the console."""
        order_id = response.get("orderId", "N/A")
        status = response.get("status", "N/A")
        executed_qty = response.get("executedQty", "N/A")
        avg_price = response.get("avgPrice")

        # avgPrice is "0" or "0.00000" for unfilled LIMIT orders
        if avg_price in (None, "0", "0.00000", "0.00", 0, 0.0):
            avg_price_display = "N/A"
        else:
            avg_price_display = avg_price

        sep = "─" * 45
        print(f"{sep}")
        print("  ORDER RESPONSE")
        print(sep)
        print(f"  Order ID    : {order_id}")
        print(f"  Status      : {status}")
        print(f"  Executed Qty: {executed_qty}")
        print(f"  Avg Price   : {avg_price_display}")
        print(f"{sep}")
        print("  ✅ Order placed successfully!")
        print(f"{sep}\n")
