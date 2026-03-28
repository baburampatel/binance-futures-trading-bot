# Binance Futures Testnet – Trading Bot

A clean, minimal Python trading bot for the **Binance USDT-M Futures Testnet** that supports MARKET and LIMIT orders via a simple command-line interface.

---

## Features

- Place **MARKET** and **LIMIT** futures orders on the Binance Testnet
- Supports **BUY** and **SELL** on any valid symbol (e.g. `BTCUSDT`)
- Validates all CLI inputs before sending any request
- Prints a clean pre-flight order summary and a formatted order response
- Writes structured logs (requests, responses, errors) to `logs/trading_bot.log`
- Secrets loaded from `.env` — never hardcoded

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package marker
│   ├── client.py            # Binance REST API wrapper (Testnet only)
│   ├── orders.py            # Order placement orchestrator
│   ├── validators.py        # Pure input validation helpers
│   ├── logging_config.py    # File + console logging setup
│   └── cli.py               # argparse CLI entry point
├── tests/
│   ├── __init__.py
│   └── test_validators.py   # Unit tests for validators
├── logs/
│   └── trading_bot.log      # Auto-created at runtime
├── .env.example             # Credential template
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Prerequisites

- Python 3.10 or higher
- A [Binance Futures Testnet](https://testnet.binancefuture.com) account and API keys

### 2. Install Dependencies

```bash
cd trading_bot
pip install -r requirements.txt
```

### 3. Configure API Credentials

Copy the example env file and fill in your Testnet keys:

```bash
cp .env.example .env
```

Edit `.env`:

```env
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```

> ⚠️ **Never commit your `.env` file.** It is excluded from version control.

---

## Usage

All commands are run from inside the `trading_bot/` directory.

### MARKET BUY

```bash
python -m bot.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### MARKET SELL

```bash
python -m bot.cli --symbol BTCUSDT --side SELL --type MARKET --quantity 0.01
```

### LIMIT BUY

```bash
python -m bot.cli --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.01 --price 85000
```

### LIMIT SELL

```bash
python -m bot.cli --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 90000
```

### Help

```bash
python -m bot.cli --help
```

---

## Example Output

```
─────────────────────────────────────────────
  ORDER SUMMARY
─────────────────────────────────────────────
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.01
  Price      : N/A (MARKET order)
─────────────────────────────────────────────

─────────────────────────────────────────────
  ORDER RESPONSE
─────────────────────────────────────────────
  Order ID    : 3951409538
  Status      : FILLED
  Executed Qty: 0.01
  Avg Price   : 84123.50
─────────────────────────────────────────────
  ✅ Order placed successfully!
─────────────────────────────────────────────
```

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## Logs

Logs are automatically written to `logs/trading_bot.log`.

- **File handler** (DEBUG level): full API request payloads, response bodies, and errors
- **Console handler** (INFO level): human-readable summary messages only

Sample log entries are included in the `logs/` directory with examples of a MARKET order and a LIMIT order.

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing `--price` for LIMIT order | Clear validation error, no request sent |
| Invalid side / type / quantity | Validation error with descriptive message |
| Binance API error (e.g. bad symbol) | Prints API error code and message |
| Network timeout / connection failure | Prints network error, exits cleanly |
| Missing `.env` credentials | Clear message with setup instructions |

---

## Assumptions

1. **Testnet only** – the base URL `https://testnet.binancefuture.com` is hardcoded; the bot cannot be redirected to the live exchange unintentionally.
2. **USDT-M Futures** – only the `/fapi/v1/order` endpoint is used, scoped to Futures.
3. **timeInForce = GTC** – LIMIT orders use Good-Till-Cancelled by default, as this is the most common and least surprising default.
4. **No position management** – this bot places orders only; it does not track open positions, PnL, or account balance.
5. **Quantity precision** – the caller is responsible for providing a quantity that meets the symbol's lot-size filter on the Testnet. Binance returns a clear API error if precision is violated.
6. **Single-symbol CLI** – the CLI places one order per invocation; orchestration across multiple symbols is out of scope for this assignment.
7. **Python 3.10+** – the `str | float` union type hint syntax requires Python 3.10 or later.
