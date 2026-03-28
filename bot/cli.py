"""
bot/cli.py
~~~~~~~~~~
Command-line interface for the Binance Futures Testnet trading bot.

Usage examples::

    # MARKET BUY
    python -m bot.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

    # LIMIT SELL
    python -m bot.cli --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 90000

Credentials are loaded from a ``.env`` file in the project root.
Run ``python -m bot.cli --help`` for full usage.
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from bot.client import BinanceAPIError, BinanceClient, NetworkError
from bot.logging_config import get_logger
from bot.orders import OrderService

logger = get_logger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _print_banner() -> None:
    """Print a compact startup banner so the user knows which environment is active."""
    print()
    print("  ┌─────────────────────────────────────────────┐")
    print("  │   Binance Futures Testnet  –  Trading Bot   │")
    print("  └─────────────────────────────────────────────┘")
    print()


def _side_type(value: str) -> str:
    """
    argparse type converter for ``--side``.

    Accepts any case (buy / BUY) and normalises to uppercase.
    Provides a clear, user-friendly error message on invalid input.
    """
    normalised = value.strip().upper()
    if normalised not in ("BUY", "SELL"):
        raise argparse.ArgumentTypeError(
            f"'{value}' is not valid. Choose from: BUY or SELL."
        )
    return normalised


def _order_type_type(value: str) -> str:
    """
    argparse type converter for ``--type``.

    Accepts any case (market / MARKET) and normalises to uppercase.
    Provides a clear, user-friendly error message on invalid input.
    """
    normalised = value.strip().upper()
    if normalised not in ("MARKET", "LIMIT"):
        raise argparse.ArgumentTypeError(
            f"'{value}' is not valid. Choose from: MARKET or LIMIT."
        )
    return normalised


def _positive_float(value: str) -> str:
    """
    argparse type checker for ``--quantity`` and ``--price``.

    Validates that the value is a positive number without converting it
    (conversion happens properly inside :mod:`bot.validators`).
    """
    try:
        f = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"'{value}' is not a valid number. Example: 0.01"
        )
    if f <= 0:
        raise argparse.ArgumentTypeError(
            f"Value must be greater than 0, got {f}."
        )
    return value


# ── Parser ────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    """
    Build and return the argument parser for the trading bot CLI.

    Returns:
        A configured :class:`argparse.ArgumentParser` instance.
    """
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description=(
            "Binance Futures Testnet – place MARKET or LIMIT futures orders.\n"
            "Credentials are loaded from a .env file (see .env.example)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  MARKET BUY   python -m bot.cli --symbol BTCUSDT --side BUY  --type MARKET --quantity 0.01
  MARKET SELL  python -m bot.cli --symbol BTCUSDT --side SELL --type MARKET --quantity 0.01
  LIMIT  BUY   python -m bot.cli --symbol BTCUSDT --side BUY  --type LIMIT  --quantity 0.01 --price 85000
  LIMIT  SELL  python -m bot.cli --symbol BTCUSDT --side SELL --type LIMIT  --quantity 0.01 --price 90000

notes:
  • --price is REQUIRED for LIMIT orders and ignored for MARKET orders.
  • Symbols are case-insensitive (btcusdt == BTCUSDT).
  • Sides and types are case-insensitive (buy == BUY, limit == LIMIT).
        """,
    )

    parser.add_argument(
        "--symbol",
        required=True,
        metavar="SYMBOL",
        help="Trading pair symbol, e.g. BTCUSDT or ETHUSDT.",
    )
    parser.add_argument(
        "--side",
        required=True,
        metavar="BUY|SELL",
        type=_side_type,
        help="Order side: BUY to go long, SELL to go short. (case-insensitive)",
    )
    parser.add_argument(
        "--type",
        dest="order_type",
        required=True,
        metavar="MARKET|LIMIT",
        type=_order_type_type,
        help=(
            "Order type: MARKET executes immediately at market price; "
            "LIMIT rests in the book at your specified price. (case-insensitive)"
        ),
    )
    parser.add_argument(
        "--quantity",
        required=True,
        metavar="QTY",
        type=_positive_float,
        help="Order quantity in base asset units, e.g. 0.01 for 0.01 BTC.",
    )
    parser.add_argument(
        "--price",
        default=None,
        metavar="PRICE",
        type=_positive_float,
        help=(
            "Limit price per unit (required for LIMIT orders, ignored for MARKET). "
            "Example: 85000 for a BTC limit order at $85,000."
        ),
    )

    return parser


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    """
    Main entry point for the trading bot CLI.

    Loads credentials from ``.env``, parses CLI arguments, and places the
    requested order through :class:`~bot.orders.OrderService`.

    Exits with a non-zero status code on any error.
    """
    # ── Load environment variables ────────────────────────────────────────────
    load_dotenv()
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    # ── Parse arguments ───────────────────────────────────────────────────────
    parser = build_parser()
    args = parser.parse_args()

    _print_banner()

    # ── Validate credentials ──────────────────────────────────────────────────
    if not api_key or not api_secret:
        print(
            "  ❌  Missing API credentials.\n"
            "\n"
            "  Steps to fix:\n"
            "    1. Copy  .env.example  →  .env\n"
            "    2. Add your Testnet keys from https://testnet.binancefuture.com\n"
            "    3. Re-run this command.\n"
        )
        logger.error("Aborted – BINANCE_API_KEY / BINANCE_API_SECRET not set.")
        sys.exit(1)

    # ── LIMIT-order price guard (friendly message before any API call) ─────────
    if args.order_type == "LIMIT" and args.price is None:
        print(
            "  ❌  LIMIT orders require a price.\n"
            "      Add: --price <value>   (example: --price 85000)\n"
        )
        logger.error("Aborted – LIMIT order submitted without --price.")
        sys.exit(1)

    if args.order_type == "MARKET" and args.price is not None:
        print(
            "  ⚠️   Note: --price is ignored for MARKET orders.\n"
        )

    # ── Run ───────────────────────────────────────────────────────────────────
    try:
        client = BinanceClient(api_key=api_key, api_secret=api_secret)
        service = OrderService(client)
        service.place_order(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
        )

    except ValueError as exc:
        print(f"\n  ❌  Validation Error: {exc}\n")
        logger.error("Validation error: %s", exc)
        sys.exit(1)

    except BinanceAPIError as exc:
        print(
            f"\n  ❌  Binance API Error\n"
            f"      Code    : {exc.error_code}\n"
            f"      Message : {exc.error_msg}\n"
            f"      HTTP    : {exc.status_code}\n"
        )
        logger.error("Binance API error: %s", exc)
        sys.exit(1)

    except NetworkError as exc:
        print(
            f"\n  ❌  Network Error: {exc}\n"
            "      Check your internet connection and try again.\n"
        )
        logger.error("Network error: %s", exc)
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n  ⚠️   Interrupted by user.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
