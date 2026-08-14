# Cross-platform Ralph Loop migration (Windows → macOS / Linux)

Most Ralph Loop PROMPT.md files in the wild were authored on Windows for quant/trading or Windows-native tooling. When the user wants to run the same loop on macOS or Linux, you must rewrite specific parts of the prompt — don't just `sed` the paths.

## What to change

### 1. Working directory and paths

| Windows | macOS / Linux |
|---|---|
| `A:\scalp-master\` | `/Users/<user>/scalp-master/` or `~/projects/scalp-master/` |
| `C:\Users\<user>\...` | `/Users/<user>/...` (macOS) or `/home/<user>/...` (Linux) |
| Backslash separators | Forward slash everywhere |

Add an explicit constraint clause like:
> **C11 (cross-platform):** All paths use `/`. Python code uses `pathlib.Path` exclusively — no raw string paths. Shell commands target bash/zsh.

### 2. Platform-locked Python packages

Document which packages have **no native macOS/Linux build** and what the replacement is:

| Windows-only package | Replacement on Mac/Linux |
|---|---|
| `MetaTrader5` (Python) | Direct HTTPS to broker (Dukascopy bi5, Oanda v20, IBKR `ib_insync`, ccxt for crypto) |
| `pywin32`, `pythoncom` | N/A — refactor or drop |
| Windows-only MQL5 EA build | Build on a Windows VPS during deploy phase; develop+backtest on Mac |

Update the stack constraint (`C3` typically) to remove the banned package and add the replacement.

### 3. Data source replacement (most common pain point)

The biggest migration item for trading bots is the historical-data feed. MT5's `copy_rates_range` is Windows-only. Options:

**Dukascopy (free, recommended for FX/metals/indices/crypto):**
- Endpoint: `https://datafeed.dukascopy.com/datafeed/{SYMBOL}/{YYYY}/{MM-1:02d}/{DD:02d}/{HH:02d}h_ticks.bi5`
- LZMA-compressed binary; decode with stdlib `lzma`, then `struct.unpack` 5 fields per tick:
  - `time_offset_ms` (uint32, big-endian) — ms since hour start
  - `ask_int` (uint32) — ask × price_scale
  - `bid_int` (uint32) — bid × price_scale
  - `ask_vol` (float32) — million units
  - `bid_vol` (float32) — million units
- Price scale: 5-decimal FX pairs ×100000; JPY pairs ×1000; metals/indices ×1000 (verify per symbol).
- MM is zero-indexed (January = 00).
- Aggregate ticks → M1 OHLCV; cache as parquet per symbol per year-month.
- Rate limit: max 2 parallel HTTP, ~100ms delay, exponential backoff. No auth required but be polite.
- History: ~2003-01-01 → today for major pairs.

**Other free/cheap options:**
- `ccxt` — exchange-native crypto (Binance, Bybit, etc.); already cross-platform.
- Oanda v20 — free demo API, REST, all platforms.
- IBKR `ib_insync` — requires TWS/IB Gateway running, cross-platform.
- Polygon.io — paid, broad asset coverage, clean REST.

### 4. Live-deploy phase

If the original PROMPT.md says "deploy as MQL5 EA on broker terminal", note that the EA still needs a Windows VPS — but:
- Development / backtest / research → Mac/Linux
- Compile MQL5 source on Mac via `mql5-cross` not viable; ship `.mq5` source to a Windows VPS or have user compile there
- Add a `code/deploy/mq5/` directory but mark it "produced on Mac, compiled & run on Windows VPS"

Alternatively suggest replacing MT5 live execution with a broker that has a cross-platform API (Oanda, IBKR, ccxt for crypto) so the entire stack stays on the loop's host.

### 5. Symbol list adjustment

Broker-specific symbol names differ. Examples:
- MT5: `US100`, `US30`, `GER40`, `SPX500`, `XAUUSD`
- Dukascopy: `USATECH.IDX`, `USA30.IDX`, `DEU.IDX`, `USA500.IDX`, `XAUUSD`
- ccxt: `BTC/USDT` (slash + quote currency)

Verify symbol availability before locking the default set; iter 5+ adaptive narrowing handles the rest.

### 6. Backtest realism layer parameters

Spread, commission, swap, and trading hours are broker-specific. When migrating:
- Re-fetch typical spread from the new data source's documentation
- Update commission table (Dukascopy ≠ IC Markets ≠ Pepperstone)
- Verify session hours per symbol (US indices close at 22:00 broker time, varies)

Keep these parametric in `code/backtest_engine.py`, not hardcoded — easier to re-tune than to re-port.

## Migration checklist

- [ ] Replace all `A:\` / `C:\` paths with `/Users/...` or `~/...`
- [ ] Remove `MetaTrader5` from `requirements.txt`; add replacement data-source library
- [ ] Rewrite `data_loader.py` skeleton for the new data source
- [ ] Update constraint C6 (data source endpoint, history depth, rate limits)
- [ ] Update default symbol set to match new broker's nomenclature
- [ ] Bump PROMPT.md version (e.g. `v1.0` → `v1.1-mac`) and note migration in changelog block
- [ ] Add `C11` cross-platform clause (pathlib, forward slashes, bash/zsh)
- [ ] If live-deploy mentioned: separate "develop here, deploy on Windows VPS" or pivot to cross-platform broker API
- [ ] Verify `python3.11 -m venv` works on target system; install requirements clean before first iter
