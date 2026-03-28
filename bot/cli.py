"""
bot/cli.py
~~~~~~~~~~
CLI for the Binance Futures Testnet trading bot.

Normal usage (all flags upfront):
    python -m bot.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

Interactive mode (bot prompts for anything missing):
    python -m bot.cli --interactive
    python -m bot.cli --symbol BTCUSDT --interactive   # pre-fill what you know

Credentials come from a .env file – see .env.example.
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from bot.client import BinanceAPIError, BinanceClient, NetworkError
from bot.logging_config import get_logger
from bot.orders import OrderService

logger = get_logger(__name__)


# ── Small UX helpers ──────────────────────────────────────────────────────────


def _banner() -> None:
    print()
    print("  Binance Futures Testnet  –  trading bot")
    print("  ----------------------------------------")
    print()


def _prompt(label: str, hint: str = "") -> str:
    """Ask the user for a value, showing an optional hint."""
    suffix = f"  ({hint})" if hint else ""
    try:
        return input(f"  {label}{suffix}: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n\nAborted.")
        sys.exit(0)


def _confirm(symbol: str, side: str, order_type: str, quantity: str, price: str | None) -> bool:
    """Show a quick summary and ask the user to confirm before sending."""
    print()
    print("  About to place:")
    print(f"    {side} {order_type}  {quantity} {symbol}", end="")
    if order_type == "LIMIT" and price:
        print(f"  @  {price}")
    else:
        print("  (market price)")
    print()
    try:
        ans = input("  Send order? [Y/n]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\n\nAborted.")
        sys.exit(0)
    return ans in ("", "y", "yes")


# ── argparse type converters ──────────────────────────────────────────────────


def _side(value: str) -> str:
    v = value.strip().upper()
    if v not in ("BUY", "SELL"):
        raise argparse.ArgumentTypeError(f"got '{value}' – must be BUY or SELL")
    return v


def _order_type(value: str) -> str:
    v = value.strip().upper()
    if v not in ("MARKET", "LIMIT"):
        raise argparse.ArgumentTypeError(f"got '{value}' – must be MARKET or LIMIT")
    return v


def _positive_float(value: str) -> str:
    try:
        f = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' is not a number")
    if f <= 0:
        raise argparse.ArgumentTypeError(f"must be > 0, got {f}")
    return value


# ── Interactive fill-in ───────────────────────────────────────────────────────


def _fill_interactive(args: argparse.Namespace) -> argparse.Namespace:
    """
    Prompt the user for any argument that wasn't provided on the command line.
    Already-supplied values are left untouched, so partial pre-fill works fine.
    """
    print("  Fill in the order details (press Enter to confirm each field).\n")

    if not args.symbol:
        args.symbol = _prompt("Symbol", "e.g. BTCUSDT") or None

    if not args.side:
        raw = _prompt("Side", "BUY or SELL")
        args.side = raw.strip().upper() or None

    if not args.order_type:
        raw = _prompt("Type", "MARKET or LIMIT")
        args.order_type = raw.strip().upper() or None

    if not args.quantity:
        args.quantity = _prompt("Quantity", "e.g. 0.01") or None

    # Only ask for price when we already know it's a LIMIT order
    if args.order_type == "LIMIT" and not args.price:
        args.price = _prompt("Price", "limit price per unit") or None

    return args


# ── Parser ────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    """Return the configured argument parser."""
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Place MARKET or LIMIT futures orders on the Binance Testnet.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  market buy   python -m bot.cli --symbol BTCUSDT --side BUY  --type MARKET --quantity 0.01
  market sell  python -m bot.cli --symbol BTCUSDT --side SELL --type MARKET --quantity 0.01
  limit buy    python -m bot.cli --symbol BTCUSDT --side BUY  --type LIMIT  --quantity 0.01 --price 85000
  limit sell   python -m bot.cli --symbol BTCUSDT --side SELL --type LIMIT  --quantity 0.01 --price 90000
  interactive  python -m bot.cli --interactive
        """,
    )

    parser.add_argument("--symbol",   default=None, metavar="SYMBOL", help="e.g. BTCUSDT")
    parser.add_argument("--side",     default=None, metavar="BUY|SELL",     type=_side,          help="BUY or SELL (case-insensitive)")
    parser.add_argument("--type",     default=None, metavar="MARKET|LIMIT", type=_order_type,    dest="order_type", help="MARKET or LIMIT (case-insensitive)")
    parser.add_argument("--quantity", default=None, metavar="QTY",          type=_positive_float, help="base asset amount, e.g. 0.01")
    parser.add_argument("--price",    default=None, metavar="PRICE",        type=_positive_float, help="limit price – required for LIMIT, ignored for MARKET")
    parser.add_argument("--interactive", "-i", action="store_true", help="prompt for any missing fields instead of failing")
    parser.add_argument("--yes", "-y", action="store_true", help="skip the confirmation prompt")

    return parser


# ── Validation (post-parse) ───────────────────────────────────────────────────


def _validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Check that all required fields are present and consistent."""
    missing = [f for f, v in [("--symbol", args.symbol), ("--side", args.side),
                               ("--type", args.order_type), ("--quantity", args.quantity)] if not v]
    if missing:
        parser.error(f"missing required arguments: {', '.join(missing)}")

    if args.order_type == "LIMIT" and not args.price:
        parser.error("--price is required for LIMIT orders  (example: --price 85000)")

    if args.order_type == "MARKET" and args.price:
        print("  note: --price is ignored for MARKET orders\n")


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    """Main entry point – load creds, parse args, place order."""
    load_dotenv()
    api_key    = os.getenv("BINANCE_API_KEY",    "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    parser = build_parser()
    args   = parser.parse_args()

    _banner()

    # ── Credentials check ─────────────────────────────────────────────────────
    if not api_key or not api_secret:
        print("  No API credentials found.\n")
        print("  Quick fix:")
        print("    cp .env.example .env")
        print("    # then add your keys from https://testnet.binancefuture.com\n")
        logger.error("Missing API credentials – aborting.")
        sys.exit(1)

    # ── Interactive fill-in ───────────────────────────────────────────────────
    if args.interactive:
        args = _fill_interactive(args)

    # ── Validate ──────────────────────────────────────────────────────────────
    _validate_args(args, parser)

    # ── Confirmation prompt ───────────────────────────────────────────────────
    if not args.yes and sys.stdin.isatty():
        if not _confirm(args.symbol, args.side, args.order_type, args.quantity, args.price):
            print("  Cancelled.\n")
            sys.exit(0)

    # ── Place order ───────────────────────────────────────────────────────────
    try:
        client  = BinanceClient(api_key=api_key, api_secret=api_secret)
        service = OrderService(client)
        service.place_order(
            symbol     = args.symbol,
            side       = args.side,
            order_type = args.order_type,
            quantity   = args.quantity,
            price      = args.price,
        )

    except ValueError as exc:
        print(f"\n  Error: {exc}\n")
        logger.error("Validation error: %s", exc)
        sys.exit(1)

    except BinanceAPIError as exc:
        print(
            f"\n  Binance error {exc.error_code}: {exc.error_msg}"
            f"  (HTTP {exc.status_code})\n"
        )
        logger.error("Binance API error: %s", exc)
        sys.exit(1)

    except NetworkError as exc:
        print(f"\n  Network error: {exc}\n")
        logger.error("Network error: %s", exc)
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n  Interrupted.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
