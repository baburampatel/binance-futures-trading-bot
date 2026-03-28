# Binance Futures Testnet – Trading Bot

A Python script for placing MARKET and LIMIT futures orders on the [Binance Testnet](https://testnet.binancefuture.com). Written as a hiring assignment — it hits the real Testnet API, logs everything to a file, and validates inputs before touching the network.

Hardcoded to the Testnet. Not usable on live Binance without changing the base URL.

---

## Project layout

```
trading_bot/
├── bot/
│   ├── client.py          # raw REST calls, HMAC signing
│   ├── orders.py          # order logic + console output
│   ├── validators.py      # input checks, no side effects
│   ├── logging_config.py  # file + console logging
│   └── cli.py             # argparse CLI, interactive mode
├── tests/
│   └── test_validators.py
├── logs/
│   └── trading_bot.log    # sample log included
├── .env.example
└── requirements.txt
```

---

## Setup

**Python 3.10+ required.**

```bash
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and paste your Testnet keys:

```
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
```

Get keys at https://testnet.binancefuture.com → API Management.

---

## Running orders

All commands run from inside `trading_bot/`.

```bash
# market buy
python -m bot.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

# market sell
python -m bot.cli --symbol BTCUSDT --side SELL --type MARKET --quantity 0.01

# limit buy
python -m bot.cli --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.01 --price 85000

# limit sell
python -m bot.cli --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 90000
```

### Interactive mode

If you'd rather be prompted for each field:

```bash
python -m bot.cli --interactive
# or pre-fill part of it:
python -m bot.cli --symbol BTCUSDT --interactive
```

You'll also get a quick confirmation before each order is sent. Skip it with `--yes` / `-y` if you're scripting.

```bash
python -m bot.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --yes
```

---

## What the output looks like

```
  Binance Futures Testnet  –  trading bot
  ----------------------------------------

  About to place:
    BUY MARKET  0.01 BTCUSDT  (market price)

  Send order? [Y/n]: y

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

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

23 tests covering all input validation paths. No live API needed.

---

## Logs

Everything gets written to `logs/trading_bot.log`:
- **DEBUG**: full request payload + raw API response
- **INFO**: order placed / error summary (also on console)

The `logs/` folder includes a sample log with one MARKET and one LIMIT entry.

---

## Common errors

| What happened | What you'll see |
|---|---|
| `--price` missing on a LIMIT order | `--price is required for LIMIT orders` |
| Bad symbol or quantity | validation error before any API call |
| Binance rejects the request | error code + message from Binance |
| No network / timeout | `Network error: ...` |
| `.env` not set up | short message with the fix |

---

## Assumptions

- **Testnet only** — base URL is hardcoded, can't be overridden from CLI
- **LIMIT orders use GTC** — Good-Till-Cancelled; most common default
- **No position tracking** — this only places orders; no P&L, no balance checks
- **Lot-size is your job** — Binance will reject quantities that violate the symbol's precision rules; the error message from the API will tell you what's wrong
- **One order per run** — if you need bulk orders or a loop, wrap the CLI call in a shell script
