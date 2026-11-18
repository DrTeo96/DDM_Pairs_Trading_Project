"""The test: signals, finbert_episode decisions and trades of A, B and C from 17 September to 30 October 2026.

    uv run python -m src.test_final                check on the train, then the test (done once on 14 November 2026: not to be redone)
    uv run python -m src.test_final --check-only   only the check on the train: reads nothing of the test

The rules are written in docs/Test.md and are those of the train, unchanged:
- signals as in 03_signals.ipynb (half-life 60 minutes, entry 2, exit 0, stop 3.5, 90 minutes), with the EMA running on from the train;
- decisions as in agent_variants/episode.py (episode with z beyond 1 and a 5-minute buffer, FinBERT, targeted news with at most
  3 tickers, strong from 0.8, follow from 0.5, same list of event words);
- trades as in backtest.apply_version.

Before the test, the same functions redo the train and must find exactly the signals of 03_signals.ipynb and the decisions and trades
of finbert_episode saved in Results/agent_variants/finbert_episode/. If they do not match, the test does not start. The script prints
no profits: the results are read in 06_test_backtest.ipynb and 07_test_robustness.ipynb.

It writes to Results/test/: signals_test.csv, decisions.csv, trades_A.csv, trades_B.csv and trades_C.csv.
The test signal_ids start again from 0: they must not be compared with the train ones.

Note: the test was run on 14 November 2026 with the Italian version of this script (same logic, Italian file names and values);
its output files were then renamed and their values translated to English, without recomputing anything.
"""
import argparse
import re

import numpy as np
import pandas as pd

from src.agent_variants.common import market_days
from src.backtest import _z_for, apply_version, load_trades
from src.config import DEC_FINBERT_EPISODE, FINBERT_SCORES, FINBERT_SCORES_TEST, NEWS, NEWS_TEST, RESULTS_TEST, ROOT, SIGNALS, TEST_END, TEST_START, read_parquet
from src.signals import STOP_EXTRA, list_pairs, load_pair, run_rules, zscore

# signal: as in 03_signals.ipynb
HL, ENTRY, EXIT = 60, 2.0, 0.0
SIGNAL_COLS = ["signal_id", "pair", "ticker_A", "ticker_B", "t_signal", "t_entry", "t_exit", "direction", "z_signal", "most_moved_leg", "ret_A_30m", "ret_B_30m",
               "price_A_in", "price_B_in", "price_A_out", "price_B_out", "exit_reason", "gross_bps", "minutes_in_trade", "exec_price_stale", "ema", "hl_min",
               "entry_z", "exit_z", "stop_z"]

# finbert_episode: as in agent_variants/episode.py (not imported from there because that script runs as soon as it is imported)
EPISODE_Z = 1.0
EPISODE_BUFFER = pd.Timedelta(minutes=5)
DECISION_LAG = pd.Timedelta(minutes=1)
MAX_SYMBOLS, STRONG, FOLLOW_MIN = 3, 0.8, 0.5
EVENT_RE = re.compile(r"\b(acqui\w*|merg\w*|takeover|buyout|divest\w*|spin-?off|investigat\w*|probe|subpoena\w*|lawsuit|sues|sued|settle\w*|fraud\w*|recall\w*|bankrupt\w*|"
                      r"chapter 11|resign\w*|steps? down|ousted|fired|retire\w*|new (ceo|cfo)|appoint\w*|names? (a )?(new )?(ceo|cfo)|delist\w*|going private)\b", re.I)


def signals(period: str) -> pd.DataFrame:
    """The A trades in a period ('train' or 'test'), with the rules of 03_signals.ipynb, in the SIGNALS format."""
    all_trades = []
    for p in list_pairs().pair:
        d = load_pair(p)
        day = d.ts.normalize()
        active = d.is_train if period == "train" else np.asarray((day >= pd.Timestamp(TEST_START)) & (day <= pd.Timestamp(TEST_END)))
        tr, _ = run_rules(d, zscore(d.S, HL), ENTRY, EXIT, active=active)
        all_trades.append(tr)
    out = pd.concat(all_trades, ignore_index=True).sort_values(["t_signal", "pair"]).reset_index(drop=True)
    out["signal_id"] = out.index
    out["ema"] = "continuous"
    out["hl_min"], out["entry_z"], out["exit_z"], out["stop_z"] = HL, ENTRY, EXIT, ENTRY + STOP_EXTRA
    return out[SIGNAL_COLS]


def news_with_scores(period: str) -> pd.DataFrame:
    """News with the FinBERT scores. For the test also the train ones, needed by the "overnight" episodes of 17 September
    (from 16:00 of the 16th): the windows take anyway only news published before the decision."""
    news = read_parquet(NEWS).merge(pd.read_parquet(FINBERT_SCORES), on="id")
    if period == "test":
        test = read_parquet(NEWS_TEST).merge(pd.read_parquet(FINBERT_SCORES_TEST), on="id")
        assert len(test) == len(read_parquet(NEWS_TEST)), "the FinBERT score of some test news is missing"
        news = pd.concat([news, test[news.columns]], ignore_index=True).drop_duplicates("id").sort_values(["ts", "id"]).reset_index(drop=True)
    news["strong"] = news[["p_pos", "p_neg"]].max(axis=1) >= STRONG
    news["event"] = (news.headline.fillna("") + " " + news.summary.fillna("")).map(lambda s: bool(EVENT_RE.search(s)))
    return news


def decisions(trades: pd.DataFrame, news: pd.DataFrame) -> pd.DataFrame:
    """B and C decisions of finbert_episode for each signal, as in agent_variants/episode.py (steps 1 and 2)."""
    tdays = market_days()
    cache, rows = {}, []
    for t in trades.itertuples():
        # 1. start of the episode
        d, z = _z_for(t.pair, t.hl_min, t.ema, cache)
        i = d.ts.get_loc(t.t_signal)
        assert np.isclose(z[i], t.z_signal), f"signal {t.signal_id}: z differs from the signals"
        side, j, first = np.sign(z[i]), i, d.day_start[i]
        while j - 1 >= first and side * z[j - 1] > EPISODE_Z:
            j -= 1
        if j == first and side * z[j] > EPISODE_Z:
            start, kind = tdays[tdays < t.t_signal.normalize()].max() + pd.Timedelta(hours=16), "overnight"
        else:
            start, kind = d.ts[j] - EPISODE_BUFFER, "in session"
        # 2. decisions
        w = news[(news.ts >= start) & (news.ts < t.t_signal + DECISION_LAG) & (news.n_symbols <= MAX_SYMBOLS)]
        mA, mB = w[f"mentions_{t.ticker_A}"].astype(bool), w[f"mentions_{t.ticker_B}"].astype(bool)
        keep = mA ^ mB
        tg = w[keep].assign(side=np.where(mA[keep], "A", "B"))
        st = tg[tg.strong]
        block = bool(len(st)) and st.side.nunique() == 1 and bool(st.event.any())
        sA = tg.loc[tg.side == "A", "score"].mean() if (tg.side == "A").any() else 0.0
        sB = tg.loc[tg.side == "B", "score"].mean() if (tg.side == "B").any() else 0.0
        rel, move = sA - sB, t.ret_A_30m - t.ret_B_30m
        follow = abs(rel) >= FOLLOW_MIN and np.sign(rel) == np.sign(move)
        dec = "block" if block else "enter"
        rows.append(dict(signal_id=t.signal_id, pair=t.pair, t_signal=t.t_signal, ep_kind=kind, ep_start=start, n_targeted=len(tg), n_strong=len(st),
                         n_in_signal_bar=int(((tg.ts >= t.t_signal) & (tg.ts < t.t_signal + DECISION_LAG)).sum()),
                         rel_score=rel, decision=dec, decision_C="follow" if follow else dec,
                         follow_side=(f"long {t.ticker_A} / short {t.ticker_B}" if rel > 0 else f"short {t.ticker_A} / long {t.ticker_B}") if follow else "",
                         headlines=" | ".join(tg.headline.astype(str))))
    return pd.DataFrame(rows)


def _same(a: pd.DataFrame, b: pd.DataFrame, cols, what: str) -> None:
    a, b = a.reset_index(drop=True), b.reset_index(drop=True)
    if len(a) != len(b):
        raise SystemExit(f"CHECK FAILED ({what}): {len(a)} rows instead of {len(b)}. The test does not start.")
    for c in cols:
        x, y = a[c], b[c]
        ok = np.allclose(x.astype(float), y.astype(float), equal_nan=True) if pd.api.types.is_numeric_dtype(y) and not pd.api.types.is_bool_dtype(y) \
            else (x.astype(str).fillna("") == y.astype(str).fillna("")).all()
        if not ok:
            raise SystemExit(f"CHECK FAILED ({what}): column {c} does not match. The test does not start.")


def check_train() -> None:
    """The functions of this script, applied to the train, must redo exactly the train files."""
    sig = signals("train")
    saved = pd.read_csv(SIGNALS, parse_dates=["t_signal", "t_entry", "t_exit"])
    _same(sig, saved, SIGNAL_COLS, "train signals")
    trades = load_trades()
    dec = decisions(trades, news_with_scores("train"))
    saved_dec = pd.read_csv(DEC_FINBERT_EPISODE).fillna({"follow_side": ""})
    _same(dec.assign(follow_side=dec.follow_side.fillna("")), saved_dec, ["signal_id", "decision", "decision_C", "follow_side", "n_targeted", "n_strong", "rel_score"],
          "finbert_episode decisions on the train")
    for letter, col in (("B", "decision"), ("C", "decision_C")):
        t = apply_version(trades, letter, dec)
        ref = pd.read_csv(DEC_FINBERT_EPISODE.parent / f"trades_{letter}.csv")
        _same(t.sort_values("signal_id"), ref.sort_values("signal_id"), ["signal_id", "gross_bps"], f"finbert_episode {letter} trades on the train")
    print(f"check on the train passed: {len(sig)} signals, finbert_episode decisions and B and C trades identical to the saved ones")


def test() -> None:
    news_test = read_parquet(NEWS_TEST)
    sig = signals("test")
    assert sig.t_signal.min() >= pd.Timestamp(TEST_START) and sig.t_exit.max() < pd.Timestamp(TEST_END) + pd.Timedelta(days=1), "signals outside the test"
    RESULTS_TEST.mkdir(parents=True, exist_ok=True)
    sig.to_csv(RESULTS_TEST / "signals_test.csv", index=False)
    trades = load_trades(RESULTS_TEST / "signals_test.csv", allow_test=True)
    dec = decisions(trades, news_with_scores("test"))
    out = {"signals_test": sig, "decisions": dec, "trades_A": apply_version(trades, "A"),
           "trades_B": apply_version(trades, "B", dec), "trades_C": apply_version(trades, "C", dec)}
    for name, df in out.items():
        if name != "signals_test":
            df.to_csv(RESULTS_TEST / f"{name}.csv", index=False)
    print(f"test done: {len(sig)} signals in {sig.t_signal.dt.normalize().nunique()} days, {(dec.decision == 'block').sum()} blocks in B, "
          f"{(dec.decision_C == 'follow').sum()} follows in C ({len(news_test)} test news)")
    print(f"saved in {RESULTS_TEST.relative_to(ROOT)}: {', '.join(out)}. The results are read in 06_test_backtest.ipynb and 07_test_robustness.ipynb.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check-only", action="store_true", help="only the check on the train, without reading the test")
    a = ap.parse_args()
    check_train()
    if not a.check_only:
        test()
