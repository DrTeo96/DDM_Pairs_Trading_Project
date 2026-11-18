"""Variant 13 (point 5): C follows the news only if it is fresh, strong and with a clear direction. Rule in LOG.md.

Outside the overnight gap, news item of today's session published within FRESH_MIN minutes before the signal, targeted on a single company,
with an event word or a guidance change, strong FinBERT sentiment and the same direction as the relative move of the 30 minutes before.
In the other cases `enter`, as A.

Output: Results/agent_variants/c_fresh/decisions.csv (columns for backtest.apply_version "C": signal_id, decision_C, follow_side) with the details.
Usage: uv run python -m src.agent_variants.c_fresh
"""
import re
import numpy as np
import pandas as pd

from src.config import DEC_C_FRESH, FINBERT_SCORES, NEWS, SIGNALS

OUT = DEC_C_FRESH
FRESH_MIN = 60
MAX_SYMBOLS = 3
STRONG = 0.8
OPEN_WINDOW = (15, 30)

EVENT_RE = re.compile(r"\b(acqui\w*|merg\w*|takeover|buyout|divest\w*|spin-?off|investigat\w*|probe|subpoena\w*|lawsuit|sues|sued|settle\w*|fraud\w*|recall\w*|bankrupt\w*|"
                      r"chapter 11|resign\w*|steps? down|ousted|fired|retire\w*|new (ceo|cfo)|appoint\w*|names? (a )?(new )?(ceo|cfo)|delist\w*|going private)\b", re.I)
_UP_DOWN = r"(cut|cuts|lower\w*|slash\w*|rais\w*|boost\w*|hike\w*|increas\w*|reduc\w*|withdr\w*|suspend\w*)"
GUIDANCE_RE = re.compile(rf"\b(guidance|outlook|forecast)\b.*\b{_UP_DOWN}\b|\b{_UP_DOWN}\b.*\b(guidance|outlook|forecast)\b", re.I | re.S)

signals = pd.read_csv(SIGNALS, parse_dates=["t_signal"])
news = pd.read_parquet(NEWS).merge(pd.read_parquet(FINBERT_SCORES), on="id")
text = news.headline.fillna("") + ". " + news.summary.fillna("")
news["event"] = text.map(lambda s: bool(EVENT_RE.search(s) or GUIDANCE_RE.search(s)))
news["strong"] = news[["p_pos", "p_neg"]].max(axis=1) >= STRONG
cand = news[news.event & news.strong & (news.n_symbols <= MAX_SYMBOLS)]      # the only news that can make C follow

rows = []
for s in signals.itertuples():
    minute = s.t_signal.hour * 60 + s.t_signal.minute - (9 * 60 + 30)
    gap = OPEN_WINDOW[0] <= minute < OPEN_WINDOW[1]
    start = max(s.t_signal - pd.Timedelta(minutes=FRESH_MIN), s.t_signal.normalize() + pd.Timedelta(hours=9, minutes=30))
    w = cand[(cand.ts >= start) & (cand.ts <= s.t_signal)]
    mA, mB = w[f"mentions_{s.ticker_A}"].astype(bool), w[f"mentions_{s.ticker_B}"].astype(bool)
    w = w[mA ^ mB].assign(pair_dir=np.where(mA[mA ^ mB], 1, -1) * w[mA ^ mB].score)   # > 0: the news pushes A above B
    move = s.ret_A_30m - s.ret_B_30m
    rel = w.pair_dir.mean() if len(w) else 0.0
    follow = (not gap) and len(w) > 0 and np.sign(rel) == np.sign(move) and rel != 0
    rows.append(dict(signal_id=s.signal_id, pair=s.pair, t_signal=s.t_signal, gap=gap, n_news=len(w), rel=rel, move30_rel=move,
                     decision_C="follow" if follow else "enter",
                     follow_side=(f"long {s.ticker_A} / short {s.ticker_B}" if rel > 0 else f"short {s.ticker_A} / long {s.ticker_B}") if follow else "",
                     a_direction=s.direction, headline=" | ".join(w.headline.astype(str)), minutes_before=" | ".join(((s.t_signal - w.ts).dt.total_seconds() // 60).astype(int).astype(str))))

out = pd.DataFrame(rows)
OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT, index=False)
print(f"candidate news (event, strong sentiment, at most {MAX_SYMBOLS} tickers): {len(cand)} of {len(news)}")
print(f"signals outside the gap with a fresh candidate news item: {((~out.gap) & (out.n_news > 0)).sum()} | follow: {(out.decision_C == 'follow').sum()}")
pd.options.display.width = 250
pd.options.display.max_colwidth = 120
print(out[out.n_news > 0][["signal_id", "pair", "t_signal", "gap", "rel", "move30_rel", "decision_C", "follow_side", "a_direction", "minutes_before", "headline"]].to_string(index=False))
