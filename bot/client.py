"""
bot/client.py
~~~~~~~~~~~~~
Thin Binance Futures Testnet REST API wrapper.

This module is the **only** place in the codebase that talks to Binance.
It handles authentication (HMAC-SHA256 signing), request construction,
error mapping, and raw response logging.  All higher-level logic lives in
:mod:`bot.orders`.

Testnet base URL is hard-coded to ensure the bot cannot accidentally hit
the live exchange.
"""

import hashlib
import hmac
import time
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from bot.logging_config import get_logger

logger = get_logger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

BASE_URL = "https://testnet.binancefuture.com"
ORDER_ENDPOINT = "/fapi/v1/order"
DEFAULT_RECV_WINDOW = 5000  # milliseconds


# ── Custom exceptions ─────────────────────────────────────────────────────────


class BinanceAPIError(Exception):
    """
    Raised when the Binance API returns a non-2xx status code.

    Attributes:
        status_code: HTTP status returned by the API.
        error_code: Binance error code from the JSON response body (if present).
        error_msg: Binance error message from the JSON response body (if present).
    """

    def __init__(self, status_code: int, error_code: int, error_msg: str) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.error_msg = error_msg
        super().__init__(
            f"Binance API error {error_code}: {error_msg} (HTTP {status_code})"
        )


class NetworkError(Exception):
    """Raised when a network-level failure prevents the request from completing."""


# ── Client ────────────────────────────────────────────────────────────────────


class BinanceClient:
    """
    Minimal Binance USDT-M Futures Testnet REST client.

    Args:
        api_key: Testnet API key (loaded from environment, never hardcoded).
        api_secret: Testnet API secret (loaded from environment, never hardcoded).
        recv_window: Maximum difference (ms) between request timestamp and
            server time.  Defaults to :data:`DEFAULT_RECV_WINDOW`.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        recv_window: int = DEFAULT_RECV_WINDOW,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError(
                "BINANCE_API_KEY and BINANCE_API_SECRET must both be set in the .env file."
            )
        self._api_key = api_key
        self._api_secret = api_secret
        self._recv_window = recv_window
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _timestamp(self) -> int:
        """Return the current UTC timestamp in milliseconds."""
        return int(time.time() * 1000)

    def _sign(self, query_string: str) -> str:
        """
        Generate an HMAC-SHA256 signature for the given query string.

        Args:
            query_string: URL-encoded parameter string to sign.

        Returns:
            Hex-digest signature string.
        """
        return hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    # ── Public API methods ────────────────────────────────────────────────────

    def new_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        time_in_force: str = "GTC",
    ) -> dict[str, Any]:
        """
        Place a new futures order on the Binance Testnet.

        Args:
            symbol: Trading pair (e.g. ``"BTCUSDT"``).
            side: ``"BUY"`` or ``"SELL"``.
            order_type: ``"MARKET"`` or ``"LIMIT"``.
            quantity: Order quantity in base asset units.
            price: Limit price; required for ``"LIMIT"`` orders, ignored for
                ``"MARKET"`` orders.
            time_in_force: Time-in-force policy for LIMIT orders.  Defaults to
                ``"GTC"`` (Good Till Cancelled).

        Returns:
            Parsed JSON response dictionary from the Binance API.

        Raises:
            :class:`BinanceAPIError`: On a non-2xx API response.
            :class:`NetworkError`: On connection or timeout failures.
        """
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "recvWindow": self._recv_window,
            "timestamp": self._timestamp(),
        }

        if order_type == "LIMIT":
            params["price"] = price
            params["timeInForce"] = time_in_force

        query_string = urlencode(params)
        params["signature"] = self._sign(query_string)

        # Log full request payload at DEBUG (never leaks to console)
        logger.debug("REQUEST  POST %s | payload: %s", ORDER_ENDPOINT, params)

        url = BASE_URL + ORDER_ENDPOINT

        try:
            response = self._session.post(url, data=params, timeout=10)
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network connection error: %s", exc)
            raise NetworkError(f"Failed to connect to Binance Testnet: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out: %s", exc)
            raise NetworkError(f"Request to Binance Testnet timed out: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Unexpected network error: %s", exc)
            raise NetworkError(f"Unexpected network error: {exc}") from exc

        # Log raw response at DEBUG
        logger.debug(
            "RESPONSE %s | status=%s | body=%s",
            ORDER_ENDPOINT,
            response.status_code,
            response.text,
        )

        if not response.ok:
            try:
                err = response.json()
                code = err.get("code", -1)
                msg = err.get("msg", response.text)
            except ValueError:
                code, msg = -1, response.text
            logger.error(
                "API error | HTTP %s | code=%s | msg=%s",
                response.status_code,
                code,
                msg,
            )
            raise BinanceAPIError(response.status_code, code, msg)

        return response.json()
