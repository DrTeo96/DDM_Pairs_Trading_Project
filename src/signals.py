"""Pairs-trading signals: spread, z-score with an EMA, entry and exit rules.

In a notebook:
    from src.signals import list_pairs, load_pair, zscore, run_rules
    d = load_pair("KO-PEP")
    z = zscore(d.S, hl=120)
    trades, blocked = run_rules(d, z, entry=2.0, exit_=0.0)

The rules:
- log spread with beta = 1: S = ln(price A) - ln(price B), because the amounts on the two legs are equal
- z-score = (S - EMA(S)) / exponential standard deviation; the EMA runs continuously over the whole series (the night counts as one bar)
- entry at the close of bar t if |z| >= threshold, execution at the open of bar t+1 (no lookahead)
- no entry if one of the two legs has a filled bar t (no trade in that minute: stale price)
- exit at the first of: reversion (|z| <= exit threshold), stop (|z| >= entry + STOP_EXTRA), time (MAX_HOLD minutes), end of the day
- gross profit in basis points of the amount of one leg: without costs (costs are in backtest.py)
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.config import PAIRS_DIR, SELECTED, TRAIN_END, read_parquet

N_MINUTES = 390            # 1-minute bars in the session: 09:30-15:59
EMA_MIN_PERIODS = 60       # bars of history needed before trusting the EMA mean and standard deviation
OPEN_SKIP = 15             # no new entries in the first 15 minutes
CLOSE_SKIP = 30            # no new entries in the last 30 minutes
MAX_HOLD = 90              # maximum holding time, in minutes
STOP_EXTRA = 1.5           # stop-loss: entry + 1.5 in units of z
LOOKBACK = 30              # minutes used only for the descriptive column "most moved leg"


def list_pairs() -> pd.DataFrame:
    """The pairs with the Bloomberg tickers (columns pair, A, B) and the short tickers (sym_A, sym_B)."""
    sel = pd.read_csv(SELECTED)[["pair", "A", "B"]]
    sel["sym_A"] = sel["A"].str.split().str[0]
    sel["sym_B"] = sel["B"].str.split().str[0]
    return sel


@dataclass
class PairData:
    pair: str
    sym_A: str
    sym_B: str
    ts: pd.DatetimeIndex
    S: pd.Series              # log spread, indexed by time
    day_id: np.ndarray        # number of the trading day, 0, 1, 2...
    minute: np.ndarray        # minutes from the open: 0 = the 09:30 bar, 389 = the 15:59 bar
    last_of_day: np.ndarray   # True on the last bar of each day
    day_start: np.ndarray     # index of the first bar of the day, for each bar
    oA: np.ndarray            # open and close prices of the two stocks
    oB: np.ndarray
    cA: np.ndarray
    cB: np.ndarray
    stale: np.ndarray         # True if at least one of the two legs has a filled bar
    filled_A: np.ndarray
    filled_B: np.ndarray
    is_train: np.ndarray      # True for the bars of the days up to TRAIN_END


def load_pair(pair: str) -> PairData:
    """Reads the clean 1-minute file of a pair (02_intraday.ipynb) and prepares the arrays used by the engine."""
    row = list_pairs().set_index("pair").loc[pair]
    raw = read_parquet(PAIRS_DIR / f"{pair}_1min.parquet")
    wide = lambda col: raw.pivot(index="ts", columns="ticker", values=col).sort_index()
    close, open_, filled = wide("close"), wide("open"), wide("filled")
    assert close.isna().sum().sum() == 0, f"{pair}: there are missing prices"
    ts = close.index
    day = ts.normalize()
    n = len(ts)
    day_id = pd.factorize(day)[0]
    first_of_day = np.r_[True, day_id[1:] != day_id[:-1]]
    return PairData(
        pair=pair, sym_A=row["sym_A"], sym_B=row["sym_B"], ts=ts,
        S=np.log(close[row["A"]]) - np.log(close[row["B"]]),
        day_id=day_id, minute=(ts.hour * 60 + ts.minute - (9 * 60 + 30)).to_numpy(),
        last_of_day=np.r_[day_id[1:] != day_id[:-1], True],
        day_start=np.maximum.accumulate(np.where(first_of_day, np.arange(n), 0)),
        oA=open_[row["A"]].to_numpy(), oB=open_[row["B"]].to_numpy(), cA=close[row["A"]].to_numpy(), cB=close[row["B"]].to_numpy(),
        stale=(filled[row["A"]] | filled[row["B"]]).to_numpy(), filled_A=filled[row["A"]].to_numpy(), filled_B=filled[row["B"]].to_numpy(),
        is_train=np.asarray(day <= pd.Timestamp(TRAIN_END)),
    )


def zscore(S: pd.Series, hl: float, reset_daily: bool = False) -> np.ndarray:
    """Z-score of S with exponential mean and standard deviation. hl = half-life in 1-minute bars.
    reset_daily=False: continuous EMA over the whole series (the group's choice). reset_daily=True: the EMA restarts every morning (comparison).
    Causal: the value of a bar uses only past bars and the bar itself."""
    if reset_daily:
        g = S.groupby(S.index.normalize())
        mean = g.transform(lambda x: x.ewm(halflife=hl, min_periods=30).mean())
        std = g.transform(lambda x: x.ewm(halflife=hl, min_periods=30).std())
    else:
        mean = S.ewm(halflife=hl, min_periods=EMA_MIN_PERIODS).mean()
        std = S.ewm(halflife=hl, min_periods=EMA_MIN_PERIODS).std()
    return ((S - mean) / std).to_numpy()


def run_rules(d: PairData, z: np.ndarray, entry: float, exit_: float, stop: float | None = None, active: np.ndarray | None = None):
    """Applies the rules to the z-score series, bar by bar, in chronological order, only on the `active` bars (the train by default).
    Returns (trade table, number of candidate bars discarded because one leg was filled)."""
    stop = entry + STOP_EXTRA if stop is None else stop
    active = d.is_train if active is None else active
    n, ts = len(d.ts), d.ts
    trades, blocked, i = [], 0, 0
    while i < n - 1:
        if not active[i]:
            i += 1
            continue
        candidate = (not np.isnan(z[i])) and abs(z[i]) >= entry and OPEN_SKIP <= d.minute[i] <= N_MINUTES - 1 - CLOSE_SKIP
        if not candidate:
            i += 1
            continue
        if d.stale[i]:                     # one leg has a stale price: no entry
            blocked += 1
            i += 1
            continue
        side = np.sign(z[i])               # +1: high spread (short A, long B); -1: low spread (long A, short B)
        e = i + 1                          # execution at the next bar
        s_in = np.log(d.oA[e] / d.oB[e])
        k = e
        while True:
            reason = None
            if d.last_of_day[k]:
                reason, a_out, b_out = "end_of_day", d.cA[k], d.cB[k]
                break
            zk = side * z[k]
            if zk <= exit_: reason = "reversion"
            elif zk >= stop: reason = "stop"
            elif k - e + 1 >= MAX_HOLD: reason = "time"
            if reason:
                k += 1                     # the exit is executed at the open of the next bar
                a_out, b_out = d.oA[k], d.oB[k]
                break
            k += 1
        s_out = np.log(a_out / b_out)
        start = max(i - LOOKBACK + 1, d.day_start[i])
        trades.append(dict(
            pair=d.pair, t_signal=ts[i], t_entry=ts[e], t_exit=ts[k], side=-int(side), z_signal=z[i], exit_reason=reason,
            price_A_in=d.oA[e], price_B_in=d.oB[e], price_A_out=a_out, price_B_out=b_out, exec_price_stale=bool(d.stale[e]),
            ret_A_30m=np.log(d.cA[i] / d.oA[start]), ret_B_30m=np.log(d.cB[i] / d.oB[start]),
            gross_bps=-side * (s_out - s_in) * 1e4,
        ))
        i = k + 1                          # one bar of pause after every exit
    out = pd.DataFrame(trades)
    if len(out):
        out["ticker_A"], out["ticker_B"] = d.sym_A, d.sym_B
        out["most_moved_leg"] = np.where(out.ret_A_30m.abs() >= out.ret_B_30m.abs(), d.sym_A, d.sym_B)
        out["direction"] = np.where(out.side > 0, f"long {d.sym_A} / short {d.sym_B}", f"short {d.sym_A} / long {d.sym_B}")
        out["minutes_in_trade"] = (out.t_exit - out.t_entry).dt.total_seconds() / 60
        out["minute_of_day"] = (out.t_entry.dt.hour * 60 + out.t_entry.dt.minute) - (9 * 60 + 30)
    return out, blocked
