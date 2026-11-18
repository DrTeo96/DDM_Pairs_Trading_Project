"""FinBERT agent for versions B and C, window tied to the session (option B). Train only.

News window (New York times, like the prices):
- signal in the "overnight gap" (minutes 15-29 from the open, as backtest.entry_window): news from the last close (16:00 of the previous trading day) to the signal;
- all the other signals: news of today's session, from 9:30 to the signal.
In every case `ts <= t_signal` (publication time, never updated_at_ny).

"Targeted" news item: it tags only one of the two companies of the pair and has at most MAX_SYMBOLS tickers in total.
Sentiment: FinBERT, score = p_pos - p_neg. "Strong" news item: the winning class (positive or negative) has probability >= STRONG.

B (can only block): blocks if there is at least one strong targeted news item, all the strong news are about the same company and at least one has
an event word (acquisition, investigation, resignation...) in the headline or the summary. Otherwise it enters.
C (can also follow): `follow` if the difference of the mean scores (company A minus company B, 0 if it has no targeted news) has absolute value >= FOLLOW_MIN
and the same sign as the relative move of the 30 minutes before the signal (ret_A_30m - ret_B_30m). The trade goes in the direction of the news: positive
relative score = long A / short B. Otherwise the B rule decides.
The model sees neither prices, nor the direction of the signal, nor the trade results. Thresholds fixed before looking at the results.

Usage: uv run python -m src.agent_variants.agent_finbert   ->   Results/agent_variants/finbert_session/decisions.csv
"""
import re
import numpy as np
import pandas as pd

from src.agent_variants.common import market_days
from src.config import DEC_FINBERT_SESSION, FINBERT_SCORES, NEWS, SIGNALS, TRAIN_END

OUT = DEC_FINBERT_SESSION
LAST_TRAIN_DAY = pd.Timestamp(TRAIN_END)   # the test (from 17 September) is not read

MAX_SYMBOLS = 3      # targeted news item: at most 3 tickers
STRONG = 0.8         # minimum probability of the winning class for a "strong" news item
FOLLOW_MIN = 0.5     # minimum absolute value of the relative score to follow the news
OPEN_WINDOW = (15, 30)   # as backtest.OPEN_WINDOW: minutes from the open of the "overnight gap"

EVENT_RE = re.compile(r"\b(acqui\w*|merg\w*|takeover|buyout|divest\w*|spin-?off|investigat\w*|probe|subpoena\w*|lawsuit|sues|sued|settle\w*|fraud\w*|recall\w*|bankrupt\w*|"
                      r"chapter 11|resign\w*|steps? down|ousted|fired|retire\w*|new (ceo|cfo)|appoint\w*|names? (a )?(new )?(ceo|cfo)|delist\w*|going private)\b", re.I)

signals = pd.read_csv(SIGNALS, parse_dates=["t_signal"])
assert signals.t_signal.max().normalize() <= LAST_TRAIN_DAY, "a signal falls in the test"
news = pd.read_parquet(NEWS).merge(pd.read_parquet(FINBERT_SCORES), on="id", how="left")
assert news.score.notna().all() and news.ts.max() < LAST_TRAIN_DAY + pd.Timedelta(days=1)
days = market_days()
news["strong"] = news[["p_pos", "p_neg"]].max(axis=1) >= STRONG
news["event"] = (news.headline.fillna("") + " " + news.summary.fillna("")).map(lambda s: bool(EVENT_RE.search(s)))


def window_start(t: pd.Timestamp) -> tuple[pd.Timestamp, str]:
    minute = t.hour * 60 + t.minute - (9 * 60 + 30)
    if OPEN_WINDOW[0] <= minute < OPEN_WINDOW[1]:
        prev = days[days < t.normalize()].max()                       # last trading day before today
        return prev + pd.Timedelta(hours=16), "overnight gap (from the last close)"
    return t.normalize() + pd.Timedelta(hours=9, minutes=30), "today's session (from 9:30)"


rows = []
for s in signals.itertuples():
    start, kind = window_start(s.t_signal)
    w = news[(news.ts > start) & (news.ts <= s.t_signal)]
    mA, mB = w[f"mentions_{s.ticker_A}"].astype(bool), w[f"mentions_{s.ticker_B}"].astype(bool)
    targeted = w[(mA ^ mB) & (w.n_symbols <= MAX_SYMBOLS)].assign(side=np.where(mA[(mA ^ mB) & (w.n_symbols <= MAX_SYMBOLS)], "A", "B"))
    strong = targeted[targeted.strong]
    block = bool(len(strong)) and strong.side.nunique() == 1 and bool(strong.event.any())
    sA = targeted.loc[targeted.side == "A", "score"].mean() if (targeted.side == "A").any() else 0.0
    sB = targeted.loc[targeted.side == "B", "score"].mean() if (targeted.side == "B").any() else 0.0
    rel, move = sA - sB, s.ret_A_30m - s.ret_B_30m
    follow = abs(rel) >= FOLLOW_MIN and np.sign(rel) == np.sign(move)
    dec_B = "block" if block else "enter"
    follow_side = f"long {s.ticker_A} / short {s.ticker_B}" if rel > 0 else f"short {s.ticker_A} / long {s.ticker_B}"
    rows.append(dict(signal_id=s.signal_id, pair=s.pair, t_signal=s.t_signal, window=kind, window_start=start, n_news=len(w), n_targeted=len(targeted),
                     n_strong=len(strong), score_A=sA, score_B=sB, rel_score=rel, move30_rel=move, decision=dec_B,
                     decision_C="follow" if follow else dec_B, follow_side=follow_side if follow else "",
                     headline=(strong.sort_values("ts").iloc[-1].headline if len(strong) else "")))

out = pd.DataFrame(rows)
OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT, index=False)
print(f"{len(out)} signals | with news in the window: {(out.n_news > 0).sum()} | with targeted news: {(out.n_targeted > 0).sum()} | with strong news: {(out.n_strong > 0).sum()}")
print("B:", out.decision.value_counts().to_dict(), "| C:", out.decision_C.value_counts().to_dict())
print(out.groupby("window")[["n_news", "n_targeted"]].agg(lambda x: (x > 0).mean()).round(2).to_string())
