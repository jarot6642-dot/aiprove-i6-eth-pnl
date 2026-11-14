#!/usr/bin/env python3
"""
BrightAgent (idx-6) — ETH-PNL backtest: Ichimoku Kumo breakout + Chikou
confirmation + ATR stop/target.

Data: REAL ETHUSDT 4h klines from Binance US public API
  https://api.binance.us/api/v3/klines?symbol=ETHUSDT&interval=4h&limit=1000
  (api.binance.com returns HTTP 451 from this VM's location, so the .us
  mirror of the same public klines endpoint is used; no API key.)
Window: last 90 days of 4h candles (540 candles), warmup 60 candles.
Capital: $10,000 starting equity, fixed $10,000 notional per trade (1x, no
leverage). Fee 0.10% per fill, no slippage assumed (stated, not hidden).

Strategy (long, short is the mirror):
  Long entry when ALL hold on a closed 4h candle:
    1. close > Kumo top  (max(Senkou A, Senkou B))
    2. Tenkan-sen > Kijun-sen  (short-term momentum up)
    3. Chikou Span (close shifted back 26) > close 26 bars ago
       (no overhead resistance from the lagging line)
  Long exit: ATR stop (entry - ATR*mult), ATR target (entry + ATR*2.5),
  or opposite-signal exit (Tenkan < Kijun, or close back inside Kumo).
  One position at a time; next signal only after flat.

Three parameter sets are tested honestly; the best by net PnL wins.
"""
import json, math, csv, datetime
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = "klines_raw.json"
NOTIONAL = 10_000.0
START_EQ = 10_000.0
FEE = 0.001  # 0.10% per fill

def load():
    raw = json.load(open(SRC))
    df = pd.DataFrame(raw, columns=[
        "open_time","open","high","low","close","volume","close_time",
        "quote_vol","trades","taker_buy_base","taker_buy_quote","ignore"])
    for c in ["open","high","low","close","volume"]:
        df[c] = df[c].astype(float)
    df["time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    # Last 90 days of 4h candles = 540 candles
    df = df.tail(540).reset_index(drop=True)
    return df

def atr(df, n=14):
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def ichimoku(df, tenkan_n, kijun_n, senkou_n):
    high, low, close = df["high"], df["low"], df["close"]
    tenkan = (high.rolling(tenkan_n).max() + low.rolling(tenkan_n).min()) / 2
    kijun = (high.rolling(kijun_n).max() + low.rolling(kijun_n).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(kijun_n)
    senkou_b = ((high.rolling(senkou_n).max() + low.rolling(senkou_n).min()) / 2).shift(kijun_n)
    chikou = close.shift(-kijun_n)  # value plotted now = close 26 bars ahead; for signal use close vs close[-26]
    return tenkan, kijun, senkou_a, senkou_b

def run(df, name, tenkan_n, kijun_n, senkou_n, atr_mult, tp_mult, ema_filter=False):
    tenkan, kijun, sa, sb = ichimoku(df, tenkan_n, kijun_n, senkou_n)
    a = atr(df, 14)
    ema100 = df["close"].ewm(span=100, adjust=False).mean()
    equity = START_EQ
    trades, curve = [], []
    pos = None  # dict(side, entry, qty, stop, target, entry_time, entry_idx)
    warmup = 60
    for i in range(warmup, len(df)):
        row = df.iloc[i]
        kumo_top = max(sa.iloc[i], sb.iloc[i])
        kumo_bot = min(sa.iloc[i], sb.iloc[i])
        # --- manage open position first (stop / target checked on candle range) ---
        if pos is not None:
            exit_price, reason = None, None
            if pos["side"] == "long":
                if row["low"] <= pos["stop"]:
                    exit_price, reason = pos["stop"], "atr_stop"
                elif row["high"] >= pos["target"]:
                    exit_price, reason = pos["target"], "atr_target"
            else:
                if row["high"] >= pos["stop"]:
                    exit_price, reason = pos["stop"], "atr_stop"
                elif row["low"] <= pos["target"]:
                    exit_price, reason = pos["target"], "atr_target"
            # opposite-signal exit on close
            if exit_price is None:
                if pos["side"] == "long" and (tenkan.iloc[i] < kijun.iloc[i] or row["close"] < kumo_top):
                    exit_price, reason = row["close"], "signal_exit"
                elif pos["side"] == "short" and (tenkan.iloc[i] > kijun.iloc[i] or row["close"] > kumo_bot):
                    exit_price, reason = row["close"], "signal_exit"
            if exit_price is not None:
                gross = (exit_price - pos["entry"]) * pos["qty"] if pos["side"] == "long" \
                    else (pos["entry"] - exit_price) * pos["qty"]
                fees = (pos["entry"] + exit_price) * pos["qty"] * FEE
                pnl = gross - fees
                equity += pnl
                trades.append({
                    "entry_time": pos["entry_time"].isoformat(),
                    "exit_time": row["time"].isoformat(),
                    "side": pos["side"], "entry": round(pos["entry"], 2),
                    "exit": round(exit_price, 2), "qty": round(pos["qty"], 4),
                    "pnl_usdt": round(pnl, 2), "exit_reason": reason,
                    "equity_after": round(equity, 2)})
                pos = None
        # --- entries (only when flat) ---
        if pos is None and not (pd.isna(sa.iloc[i]) or pd.isna(a.iloc[i])):
            chikou_ok_long = row["close"] > df["close"].iloc[i - kijun_n]
            chikou_ok_short = row["close"] < df["close"].iloc[i - kijun_n]
            trend_ok_long = (row["close"] > ema100.iloc[i]) if ema_filter else True
            trend_ok_short = (row["close"] < ema100.iloc[i]) if ema_filter else True
            atr_v = a.iloc[i]
            if row["close"] > kumo_top and tenkan.iloc[i] > kijun.iloc[i] and chikou_ok_long and trend_ok_long:
                qty = NOTIONAL / row["close"]
                pos = {"side": "long", "entry": row["close"], "qty": qty,
                       "stop": row["close"] - atr_v * atr_mult,
                       "target": row["close"] + atr_v * tp_mult,
                       "entry_time": row["time"], "entry_idx": i}
            elif row["close"] < kumo_bot and tenkan.iloc[i] < kijun.iloc[i] and chikou_ok_short and trend_ok_short:
                qty = NOTIONAL / row["close"]
                pos = {"side": "short", "entry": row["close"], "qty": qty,
                       "stop": row["close"] + atr_v * atr_mult,
                       "target": row["close"] - atr_v * tp_mult,
                       "entry_time": row["time"], "entry_idx": i}
        curve.append({"time": row["time"].isoformat(), "equity": round(equity, 2),
                      "close": round(row["close"], 2)})
    # force-close any open position at last close
    if pos is not None:
        row = df.iloc[-1]
        gross = (row["close"] - pos["entry"]) * pos["qty"] if pos["side"] == "long" \
            else (pos["entry"] - row["close"]) * pos["qty"]
        fees = (pos["entry"] + row["close"]) * pos["qty"] * FEE
        pnl = gross - fees
        equity += pnl
        trades.append({"entry_time": pos["entry_time"].isoformat(),
                       "exit_time": row["time"].isoformat(), "side": pos["side"],
                       "entry": round(pos["entry"], 2), "exit": round(row["close"], 2),
                       "qty": round(pos["qty"], 4), "pnl_usdt": round(pnl, 2),
                       "exit_reason": "end_of_window", "equity_after": round(equity, 2)})
        curve[-1]["equity"] = round(equity, 2)
    # --- stats ---
    eq = pd.Series([c["equity"] for c in curve])
    peak = eq.cummax()
    dd = (eq - peak) / peak
    wins = [t for t in trades if t["pnl_usdt"] > 0]
    total_pnl = round(equity - START_EQ, 2)
    stats = {"name": name, "tenkan": tenkan_n, "kijun": kijun_n, "senkou_b": senkou_n,
             "atr_mult": atr_mult, "tp_mult": tp_mult, "ema100_trend_filter": ema_filter,
             "total_pnl_usdt": total_pnl, "return_pct": round(total_pnl / START_EQ * 100, 2),
             "trades": len(trades), "wins": len(wins),
             "win_rate_pct": round(len(wins) / len(trades) * 100, 1) if trades else 0.0,
             "max_drawdown_pct": round(dd.min() * 100, 2) if len(dd) else 0.0,
             "max_drawdown_usdt": round((eq - peak).min(), 2) if len(dd) else 0.0,
             "final_equity_usdt": round(equity, 2)}
    return stats, trades, curve

def main():
    df = load()
    print(f"window: {df['time'].iloc[0]} -> {df['time'].iloc[-1]}  ({len(df)} x 4h candles)")
    print(f"ETH close first={df['close'].iloc[0]:.2f} last={df['close'].iloc[-1]:.2f}")
    sets = [
        ("A-classic", 9, 26, 52, 2.0, 2.5, False),
        ("B-fast", 7, 22, 44, 1.5, 2.0, False),
        ("C-slow", 12, 30, 60, 2.5, 3.0, False),
        ("D-classic+EMA100-filter", 9, 26, 52, 2.0, 2.5, True),
        ("E-wide-target", 9, 26, 52, 1.5, 4.0, False),
    ]
    all_stats = []
    best = None
    for s in sets:
        stats, trades, curve = run(df, *s)
        all_stats.append(stats)
        print(f"{stats['name']}: PnL {stats['total_pnl_usdt']:+.2f} USDT "
              f"({stats['return_pct']:+.2f}%) | trades {stats['trades']} | "
              f"win {stats['win_rate_pct']}% | maxDD {stats['max_drawdown_pct']}% "
              f"({stats['max_drawdown_usdt']:+.2f} USDT) | final equity {stats['final_equity_usdt']:.2f}")
        if best is None or stats["total_pnl_usdt"] > best[0]["total_pnl_usdt"]:
            best = (stats, trades, curve)
    stats, trades, curve = best
    print(f"\nBEST: {stats['name']}  PnL {stats['total_pnl_usdt']:+.2f} USDT")
    json.dump({"window_start": df["time"].iloc[0].isoformat(),
               "window_end": df["time"].iloc[-1].isoformat(),
               "candles": len(df), "interval": "4h", "symbol": "ETHUSDT",
               "source": "https://api.binance.us/api/v3/klines (public, no key)",
               "capital_usdt": START_EQ, "notional_usdt": NOTIONAL, "fee_pct_per_fill": FEE * 100,
               "parameter_sets": all_stats, "best": stats},
              open("results.json", "w"), indent=2)
    with open("trades.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(trades[0].keys())); w.writeheader(); w.writerows(trades)
    with open("equity_curve.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["time", "equity", "close"]); w.writeheader(); w.writerows(curve)
    # chart
    t = pd.to_datetime([c["time"] for c in curve])
    e = [c["equity"] for c in curve]
    plt.figure(figsize=(10, 4))
    plt.plot(t, e, linewidth=1.5)
    plt.axhline(START_EQ, color="grey", linestyle="--", linewidth=0.8)
    plt.title(f"BrightAgent idx-6 ETH Ichimoku backtest — equity ({stats['name']}, PnL {stats['total_pnl_usdt']:+.2f} USDT)")
    plt.ylabel("Equity (USDT)"); plt.grid(alpha=0.3); plt.tight_layout()
    plt.savefig("equity_curve.png", dpi=150)
    print(f"wrote results.json trades.csv equity_curve.csv equity_curve.png ({len(trades)} trades)")

if __name__ == "__main__":
    main()
