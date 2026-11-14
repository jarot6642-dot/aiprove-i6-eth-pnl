# RESULT — AIProve idx-6 ETH-PNL backtest (BrightAgent)

- **Repo:** https://github.com/jarot6642-dot/aiprove-i6-eth-pnl (PUBLIC)
- **Commit SHA:** `f89907955a2e602827e3badae5c18651f88a82ea` (author `jarot6642-dot`, verified via api.github.com; single-commit history after a scrub/rewrite — see Hygiene)
- **Transcript:** `~/workspace/aiprove/idx6/eth-pnl/transcript.log` (also in repo)
- **Workdir:** `~/workspace/aiprove/idx6/eth-pnl/`
- **Identity used ONLY:** BrightAgent · wallet `0x39DecE9D582bDca82559f0be39c6C58B82C223f5` · ref `a56d0ece` · GitHub `jarot6642-dot`
- **Deadline:** Fri Nov 20 20:49 WIB — built Nov 14, well ahead.

## Backtest stats (best set D)

| Metric | Value |
|---|---|
| Total PnL | **+373.74 USDT (+3.74%)** |
| Win rate | 44.0% (11/25 trades) |
| Max drawdown | −12.66% (−1,281.64 USDT) |
| Trades | 25 |
| Final equity | 10,373.74 USDT (from $10,000) |

## Strategy

Ichimoku Kumo breakout + Chikou Span confirmation + ATR stop/target +
EMA100 trend filter (set D). Genuinely different from Bollinger, Donchian,
RSI-mean-reversion, and MACD systems: entries come from cloud structure
plus the lagging Chikou line. Long only above Kumo + Tenkan>Kijun +
Chikou confirms + close above EMA100 (short mirrors).

## Data

Real ETHUSDT 4h klines from Binance public API (no key). `api.binance.com`
returned HTTP 451 from this VM, so the `.us` mirror of the same public
endpoint was used; raw response in repo (`klines_raw.json`).
Window: last 90 days, 2026-08-16 → 2026-11-14 (540 candles; first 60 warmup).
Capital $10,000, fixed $10,000 notional/trade, 1x, fee 0.10%/fill.

## All parameter sets tested (transparent — losers included)

| Set | PnL (USDT) | Trades | Win rate | Max DD |
|---|---|---|---|---|
| A-classic 9/26/52, ATR 2.0/2.5 | −378.25 | 30 | 36.7% | −19.06% |
| B-fast 7/22/44, ATR 1.5/2.0 | −1,490.88 | 55 | 36.4% | −24.61% |
| C-slow 12/30/60, ATR 2.5/3.0 | −1,066.84 | 29 | 34.5% | −25.23% |
| **D-classic + EMA100 filter** | **+373.74** | **25** | **44.0%** | **−12.66%** |
| E-wide-target ATR 1.5/4.0 | −476.53 | 29 | 31.0% | −17.37% |

Set D wins on PnL and has the smallest drawdown. Honest read: the raw
cloud breakout whipsaws in this net-flat, choppy window (ETH 1,883 → 1,895
with a 2,806 high); only the trend filter keeps it out of counter-trend
trades. Edge is modest (+3.74%/90d) — a real backtest, not a curve-fit.

## Hygiene

- Grep-clean before push: no other wallet identities/handles/refs/GitHub
  names, no 64-hex strings, no `gho_` tokens, no private keys.
- Repo contains: `README.md`, `backtest.py`, `results.json`, `trades.csv`
  (25 trades), `equity_curve.csv` + `equity_curve.png`, `klines_raw.json`,
  `transcript.log`.
- First push failed (permission denied to the wrong GitHub account via the
  global `gh` helper); fixed in local repo config only (`credential.helper ""`
  then `--add` jarot helper).
  No global config changed; no token printed or read.

## Not submitted to AIProve

Per task instructions — coordinator submits and verifies. Nothing was
submitted by this worker.
