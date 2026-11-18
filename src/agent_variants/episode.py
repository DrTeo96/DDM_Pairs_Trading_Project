"""Variants 14 (B) and 15 (C): FinBERT with the episode window, i.e. the news published while the spread was moving away from the mean,
up to the end of the signal bar. Rules in LOG.md.

1. For each signal: start of the episode = first bar in a row, going back from the signal, with z beyond EPISODE_Z with the same sign,
   minus EPISODE_BUFFER minutes; if the episode reaches the first bar of the day, from the close of the previous trading day.
   End = t_signal + 1 minute (the decision is at the close of the signal bar).
2. Decisions with the rules of variants 9 and 10 (only the window changes).
3. Backtest (A, B, C at cost 0 and 5) and evaluation as in point 4.

It writes to Results/agent_variants/finbert_episode/: decisions.csv, episode.csv.
Usage: uv run python -m src.agent_variants.episode
"""
import re
from math import comb

import numpy as np
import pandas as pd
from src.agent_variants.common import market_days
from src.backtest import _z_for, add_costs, apply_version, blocked_vs_random, entry_window, load_trades, summary, trading_days
from src.config import DEC_FINBERT_EPISODE, FINBERT_SCORES, NEWS, RESULTS, read_parquet

OUT = DEC_FINBERT_EPISODE.parent
EPISODE_Z = 1.0
EPISODE_BUFFER = pd.Timedelta(minutes=5)
DECISION_LAG = pd.Timedelta(minutes=1)
MAX_SYMBOLS, STRONG, FOLLOW_MIN = 3, 0.8, 0.5
EVENT_RE = re.compile(r"\b(acqui\w*|merg\w*|takeover|buyout|divest\w*|spin-?off|investigat\w*|probe|subpoena\w*|lawsuit|sues|sued|settle\w*|fraud\w*|recall\w*|bankrupt\w*|"
                      r"chapter 11|resign\w*|steps? down|ousted|fired|retire\w*|new (ceo|cfo)|appoint\w*|names? (a )?(new )?(ceo|cfo)|delist\w*|going private)\b", re.I)

pd.options.display.float_format = "{:,.2f}".format
pd.options.display.width = 250
pd.options.display.max_colwidth = 110
trades, days = load_trades(), trading_days()
A = apply_version(trades, "A")
A["window"] = entry_window(A)
tdays = market_days()

# ---------------------------------------------------------------- 1. start of the episode

cache, starts, kinds, lens = {}, [], [], []
for t in trades.itertuples():
    d, z = _z_for(t.pair, t.hl_min, t.ema, cache)
    i = d.ts.get_loc(t.t_signal)
    assert np.isclose(z[i], t.z_signal), f"signal {t.signal_id}: z differs from 03_signals"
    side, j, first = np.sign(z[i]), i, d.day_start[i]
    while j - 1 >= first and side * z[j - 1] > EPISODE_Z:
        j -= 1
    if j == first and side * z[j] > EPISODE_Z:
        start, kind = tdays[tdays < t.t_signal.normalize()].max() + pd.Timedelta(hours=16), "overnight"
    else:
        start, kind = d.ts[j] - EPISODE_BUFFER, "in session"
    starts.append(start)
    kinds.append(kind)
    lens.append((t.t_signal + DECISION_LAG - start).total_seconds() / 60)
ep = trades[["signal_id", "pair", "ticker_A", "ticker_B", "t_signal", "ret_A_30m", "ret_B_30m"]].assign(ep_start=starts, ep_kind=kinds, ep_minutes=lens)
print("episodes:", ep.ep_kind.value_counts().to_dict(), "| length in session (minutes): median", ep.loc[ep.ep_kind == "in session", "ep_minutes"].median())

# ---------------------------------------------------------------- 2. decisions with the rules of variants 9 and 10

news = read_parquet(NEWS).merge(pd.read_parquet(FINBERT_SCORES), on="id")
news["strong"] = news[["p_pos", "p_neg"]].max(axis=1) >= STRONG
news["event"] = (news.headline.fillna("") + " " + news.summary.fillna("")).map(lambda s: bool(EVENT_RE.search(s)))
rows = []
for s in ep.itertuples():
    w = news[(news.ts >= s.ep_start) & (news.ts < s.t_signal + DECISION_LAG) & (news.n_symbols <= MAX_SYMBOLS)]
    mA, mB = w[f"mentions_{s.ticker_A}"].astype(bool), w[f"mentions_{s.ticker_B}"].astype(bool)
    keep = mA ^ mB
    tg = w[keep].assign(side=np.where(mA[keep], "A", "B"))
    st = tg[tg.strong]
    block = bool(len(st)) and st.side.nunique() == 1 and bool(st.event.any())
    sA = tg.loc[tg.side == "A", "score"].mean() if (tg.side == "A").any() else 0.0
    sB = tg.loc[tg.side == "B", "score"].mean() if (tg.side == "B").any() else 0.0
    rel, move = sA - sB, s.ret_A_30m - s.ret_B_30m
    follow = abs(rel) >= FOLLOW_MIN and np.sign(rel) == np.sign(move)
    dec = "block" if block else "enter"
    rows.append(dict(signal_id=s.signal_id, pair=s.pair, t_signal=s.t_signal, ep_kind=s.ep_kind, ep_start=s.ep_start, n_targeted=len(tg), n_strong=len(st),
                     n_in_signal_bar=int(((tg.ts >= s.t_signal) & (tg.ts < s.t_signal + DECISION_LAG)).sum()),
                     rel_score=rel, decision=dec, decision_C="follow" if follow else dec,
                     follow_side=(f"long {s.ticker_A} / short {s.ticker_B}" if rel > 0 else f"short {s.ticker_A} / long {s.ticker_B}") if follow else "",
                     headlines=" | ".join(tg.headline.astype(str))))
dec = pd.DataFrame(rows)
OUT.mkdir(parents=True, exist_ok=True)
dec.to_csv(DEC_FINBERT_EPISODE, index=False)
print(f"signals with at least one targeted news item in the episode: {(dec.n_targeted > 0).sum()} (overnight {((dec.n_targeted > 0) & (dec.ep_kind == 'overnight')).sum()}, "
      f"in session {((dec.n_targeted > 0) & (dec.ep_kind == 'in session')).sum()}) | with a news item in the signal bar: {(dec.n_in_signal_bar > 0).sum()}")
print("B:", dec.decision.value_counts().to_dict(), "| C:", dec.decision_C.value_counts().to_dict())

# ---------------------------------------------------------------- 3. backtest and evaluation

B = apply_version(trades, "B", dec[["signal_id", "decision"]])
C = apply_version(trades, "C", dec[["signal_id", "decision_C", "follow_side"]])
res = []
for name, t in (("A, no agent", A), ("14 B FinBERT episode", B), ("15 C FinBERT episode", C)):
    for c in (0, 5):
        sm = summary(add_costs(t, c), days)
        res.append({"version": name, "cost_bps": c, "trade": sm["trade"], "net_bps": sm["net_bps"], "pnl_usd": sm["pnl_usd"], "sharpe": sm["sharpe"]})
res = pd.DataFrame(res)
print("\n" + res.to_string(index=False))

A["reversion"] = A.exit_reason.eq("reversion")
blk, kept = A[A.signal_id.isin(dec.query("decision == 'block'").signal_id)], A[~A.signal_id.isin(dec.query("decision == 'block'").signal_id)]


def fisher_two_sided(a, b, c, d):
    r1, c1, n = a + b, a + c, a + b + c + d
    p = lambda x: comb(c1, x) * comb(n - c1, r1 - x) / comb(n, r1)   # noqa: E731
    return min(1.0, sum(p(x) for x in range(max(0, r1 + c1 - n), min(r1, c1) + 1) if p(x) <= p(a) * (1 + 1e-9)))


if len(blk):
    print(f"\n14 B: blocked {len(blk)}, reversion {blk.reversion.mean():.0%} against {kept.reversion.mean():.0%} of the kept ones "
          f"(p Fisher {fisher_two_sided(int(blk.reversion.sum()), len(blk) - int(blk.reversion.sum()), int(kept.reversion.sum()), len(kept) - int(kept.reversion.sum())):.2f}); "
          f"mean gross {blk.gross_bps.mean():.1f}, median {blk.gross_bps.median():.1f}; p random block {blocked_vs_random(trades, dec[['signal_id', 'decision']])['p_value']:.2f}")
    print(blk.merge(dec[["signal_id", "ep_kind", "headlines"]], on="signal_id")[["signal_id", "pair", "t_signal", "ep_kind", "exit_reason", "gross_bps", "headlines"]].to_string(index=False))
f = C[C.c_kind == "follow"].merge(A[["signal_id", "gross_bps"]].rename(columns={"gross_bps": "gross_A"}), on="signal_id")
if len(f):
    print(f"\n15 C: {len(f)} inverted trades, news right {(f.gross_bps > 0).mean():.0%}, mean gross C {f.gross_bps.mean():.1f} (median {f.gross_bps.median():.1f}), A on the same signals {f.gross_A.mean():.1f}")
res.to_csv(OUT / "episode.csv", index=False)
print(f"\nsaved in {OUT.relative_to(RESULTS.parent)}: decisions.csv, episode.csv")
