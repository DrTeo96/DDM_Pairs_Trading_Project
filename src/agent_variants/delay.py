"""Variants 16 (B_k) and 17 (C_k): decision and entry k minutes after the signal, against an A delayed by the same k. Rules in LOG.md.

For each A signal (bar i): decision at the close of bar i + k, entry at the open of the next bar, exit with the rules
of signals.run_rules (reversion, stop, MAX_HOLD, end of the day). With k = 0 it must reproduce the 973 A trades (check).
The FinBERT agent reads the news from the start of the episode (variant 14) to the close of the decision bar.

It reads the decisions of episode.py (start of the episode). It writes to Results/agent_variants/delay/: delay.csv and the trades of A_k, B_k, C_k.
Usage: uv run python -m src.agent_variants.delay
"""
import re
from math import comb

import numpy as np
import pandas as pd
from src.backtest import _z_for, add_costs, load_trades, summary, trading_days
from src.config import DEC_FINBERT_EPISODE, FINBERT_SCORES, NEWS, RESULTS, VARIANTS, read_parquet
from src.signals import LOOKBACK, MAX_HOLD

OUT = VARIANTS / "delay"
DELAYS = (5, 15)
MAX_SYMBOLS, STRONG, FOLLOW_MIN = 3, 0.8, 0.5
EVENT_RE = re.compile(r"\b(acqui\w*|merg\w*|takeover|buyout|divest\w*|spin-?off|investigat\w*|probe|subpoena\w*|lawsuit|sues|sued|settle\w*|fraud\w*|recall\w*|bankrupt\w*|"
                      r"chapter 11|resign\w*|steps? down|ousted|fired|retire\w*|new (ceo|cfo)|appoint\w*|names? (a )?(new )?(ceo|cfo)|delist\w*|going private)\b", re.I)
pd.options.display.float_format = "{:,.2f}".format
pd.options.display.width = 220

trades, days = load_trades(), trading_days()
ep = pd.read_csv(DEC_FINBERT_EPISODE, parse_dates=["ep_start"]).set_index("signal_id").ep_start
news = read_parquet(NEWS).merge(pd.read_parquet(FINBERT_SCORES), on="id")
news = news[news.n_symbols <= MAX_SYMBOLS]
news["strong"] = news[["p_pos", "p_neg"]].max(axis=1) >= STRONG
news["event"] = (news.headline.fillna("") + " " + news.summary.fillna("")).map(lambda s: bool(EVENT_RE.search(s)))
cache = {}


def simulate(t, d, z, i: int, k: int, long_A: bool, with_stop: bool):
    """One trade with the decision at bar i + k. long_A: direction of the trade. with_stop: A uses the stop, the following C does not. None if there is no entry."""
    dec = i + k
    if dec + 1 >= len(d.ts) or d.day_id[dec] != d.day_id[i] or d.last_of_day[dec]:
        return None, "day over while waiting"
    side = np.sign(z[i])
    if k > 0 and side * z[dec] <= t.exit_z:
        return None, "reverted while waiting"
    e = dec + 1
    s_in, j = np.log(d.oA[e] / d.oB[e]), e
    while True:
        if d.last_of_day[j]:
            reason, a_out, b_out = "end_of_day", d.cA[j], d.cB[j]
            break
        zj = side * z[j]
        reason = "reversion" if zj <= t.exit_z else "stop" if (with_stop and zj >= t.stop_z) else "time" if j - e + 1 >= MAX_HOLD else None
        if reason:
            j += 1
            a_out, b_out = d.oA[j], d.oB[j]
            break
        j += 1
    sign = 1 if long_A else -1
    t_exit = d.ts[j]
    return dict(signal_id=t.signal_id, pair=t.pair, t_entry=d.ts[e], t_exit=t_exit, exit_reason=reason,
                gross_bps=sign * (np.log(a_out / b_out) - s_in) * 1e4, minutes_in_trade=(t_exit - d.ts[e]).total_seconds() / 60, day=t_exit.normalize()), None


def agent(t, d, i: int, k: int) -> tuple[str, bool | None, int]:
    """FinBERT decision (rules of variants 14 and 15) with the news up to the close of the decision bar."""
    dec = i + k
    w = news[(news.ts >= ep.loc[t.signal_id]) & (news.ts < d.ts[dec] + pd.Timedelta(minutes=1))]
    mA, mB = w[f"mentions_{t.ticker_A}"].astype(bool), w[f"mentions_{t.ticker_B}"].astype(bool)
    keep = mA ^ mB
    tg = w[keep].assign(side=np.where(mA[keep], "A", "B"))
    st = tg[tg.strong]
    block = bool(len(st)) and st.side.nunique() == 1 and bool(st.event.any())
    sA = tg.loc[tg.side == "A", "score"].mean() if (tg.side == "A").any() else 0.0
    sB = tg.loc[tg.side == "B", "score"].mean() if (tg.side == "B").any() else 0.0
    rel = sA - sB
    start = max(dec - LOOKBACK + 1, d.day_start[dec])
    move = np.log(d.cA[dec] / d.oA[start]) - np.log(d.cB[dec] / d.oB[start])
    if abs(rel) >= FOLLOW_MIN and np.sign(rel) == np.sign(move):
        return "follow", rel > 0, len(tg)
    return ("block" if block else "enter"), None, len(tg)


def fisher(a, b, c, dd):
    r1, c1, n = a + b, a + c, a + b + c + dd
    p = lambda x: comb(c1, x) * comb(n - c1, r1 - x) / comb(n, r1)   # noqa: E731
    return min(1.0, sum(p(x) for x in range(max(0, r1 + c1 - n), min(r1, c1) + 1) if p(x) <= p(a) * (1 + 1e-9)))


# ---------------------------------------------------------------- check: with k = 0 A is reproduced
check = []
for t in trades.itertuples():
    d, z = _z_for(t.pair, t.hl_min, t.ema, cache)
    i = d.ts.get_loc(t.t_signal)
    r, _ = simulate(t, d, z, i, 0, t.direction.startswith("long"), True)
    check.append(r["gross_bps"])
assert np.allclose(check, trades.gross_bps.values), "with k = 0 the simulation does not reproduce A"
print(f"check ok: with k = 0 the {len(trades)} trades match A (mean gross {np.mean(check):.2f} bps)\n")

rows, detail = [], []
for k in DELAYS:
    A_k, B_k, C_k, skipped, blocked_ids, follow_rows = [], [], [], {}, [], []
    for t in trades.itertuples():
        d, z = _z_for(t.pair, t.hl_min, t.ema, cache)
        i = d.ts.get_loc(t.t_signal)
        a_long = t.direction.startswith("long")
        ra, why = simulate(t, d, z, i, k, a_long, True)
        if ra is None:
            skipped[why] = skipped.get(why, 0) + 1
            continue
        A_k.append(ra)
        dec, f_long, n_news = agent(t, d, i, k)
        if dec == "block":
            blocked_ids.append(t.signal_id)
            continue
        B_k.append(ra)
        if dec == "follow" and f_long != a_long:
            rc, _ = simulate(t, d, z, i, k, f_long, False)
            if rc is not None:
                C_k.append(rc | {"c_kind": "follow"})
                follow_rows.append({"signal_id": t.signal_id, "gross_C": rc["gross_bps"], "gross_A_k": ra["gross_bps"]})
        else:
            C_k.append(ra | {"c_kind": "enter"})
    A_k, B_k, C_k = pd.DataFrame(A_k), pd.DataFrame(B_k), pd.DataFrame(C_k)
    OUT.mkdir(parents=True, exist_ok=True)
    for letter, tt in (("A", A_k), ("B", B_k), ("C", C_k)):
        add_costs(tt, 0).to_csv(OUT / f"trades_{letter}_{k}min.csv", index=False)
    # in the trades of the following C there is no block: the blocked ones stay out of C too (as in variant 15)
    print(f"k = {k} minutes: signals without a trade {skipped} | A_k {len(A_k)} trades | B_k blocks {len(blocked_ids)} | C_k follows (inverted direction) {len(follow_rows)}")
    for name, tt in ((f"A delayed {k} min", A_k), (f"16 B FinBERT {k} min", B_k), (f"17 C FinBERT {k} min", C_k)):
        for c in (0, 5):
            sm = summary(add_costs(tt, c), days)
            rows.append({"version": name, "cost_bps": c, "trade": sm["trade"], "net_bps": sm["net_bps"], "pnl_usd": sm["pnl_usd"], "sharpe": sm["sharpe"]})
    Ak = A_k.assign(reversion=A_k.exit_reason.eq("reversion"))
    blk, kept = Ak[Ak.signal_id.isin(blocked_ids)], Ak[~Ak.signal_id.isin(blocked_ids)]
    if len(blk):
        p = fisher(int(blk.reversion.sum()), len(blk) - int(blk.reversion.sum()), int(kept.reversion.sum()), len(kept) - int(kept.reversion.sum()))
        print(f"   blocked: reversion {blk.reversion.mean():.0%} against {kept.reversion.mean():.0%} (p Fisher {p:.2f}), mean gross {blk.gross_bps.mean():.1f}, median {blk.gross_bps.median():.1f}")
    if follow_rows:
        f = pd.DataFrame(follow_rows)
        print(f"   followed: news right {(f.gross_C > 0).mean():.0%}, mean gross C {f.gross_C.mean():.1f} (median {f.gross_C.median():.1f}), A_k on the same signals {f.gross_A_k.mean():.1f}")

res = pd.DataFrame(rows)
A0 = summary(add_costs(trades, 0), days)
print(f"\nA without delay, cost 0: {len(trades)} trades, {A0['net_bps']:.2f} bps, {A0['pnl_usd']:,.0f} $, Sharpe {A0['sharpe']:.2f}")
print(res.to_string(index=False))
res.to_csv(OUT / "delay.csv", index=False)
print(f"\nsaved in {OUT.relative_to(RESULTS.parent)}: delay.csv and trades_<A|B|C>_<k>min.csv")
