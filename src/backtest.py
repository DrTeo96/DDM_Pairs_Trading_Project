"""Simulation: costs, three versions (A, B, C), comparison between result versions and metrics on the signal trades.

The engine does not redo the signal: it starts from the trade table of 03_signals.ipynb (times, prices, direction, gross profit)
and applies to it, in this order, the decision of the version (A, B or C), the costs and the capital.
In a notebook:
    from src.backtest import load_trades, load_version, apply_version, add_costs, summary
    trades = load_trades()                                  # train trades
    a = add_costs(apply_version(trades, "A"), cost_bps=5)   # version A, 5 bps per operation
    b = apply_version(trades, "B", load_version("spark_24h"))
    print(summary(a))

The rules:
- fixed and equal amount on the two legs (NOTIONAL_LEG dollars per leg), no leverage, everything closed at the end of the day
- a trade has 4 operations (opening and closing of two legs): cost of the trade = 4 x cost_bps, in basis points of the amount of one leg,
  the same base as the gross profit (`gross_bps`)
- net profit = gross - cost; in dollars = net / 10,000 x NOTIONAL_LEG
- portfolio capital = CAPITAL_PER_PAIR per pair (two legs of NOTIONAL_LEG): each pair can have one open trade at a time
- daily returns are the dollar profit of the trades closed that day divided by the capital; days without trades count as 0
- no risk-free rate in the Sharpe ratio (3 months of data, trades closed every evening): stated in the report
- the test period is not read: `load_trades` refuses any trade after TRAIN_END, unless it is asked `allow_test=True`

The versions:
- A: every signal enters, no agent.
- B: the agent can only block (column `decision`).
- C: the agent can also follow the news (column `decision_C` = 'follow', direction in `follow_side`). A 'follow' trade opens at the
  same bar as A but in the direction of the news, i.e. it bets that the spread keeps widening, and exits at the first of:
  reversion of the spread (|z| <= exit threshold: the news was wrong), MAX_HOLD minutes, end of the day. No stop besides the reversion.

The result versions (VERSIONS) are the sets of decisions to compare: the agent runs, the lexicon baseline, the group's hand
classification and the agent variants in src/agent_variants/. `load_version` brings them all to the same format
(signal_id, decision, decision_C, follow_side). If the original file is missing (for example the raw answers of the agent, which
are only on the computer of whoever ran it), the copy on git in Results/agent_variants/<name>/ (`copy`) is read, already in
this format.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import (AGENT_DECISIONS_COPY, BASELINE_LEXICON, DEC_3B_6H, DEC_C_FRESH, DEC_FINBERT_EPISODE, DEC_FINBERT_SESSION,
                        MANUAL_DECISIONS, RESULTS, RUN_6H, RUN_24H, RUN_24H_REASONING, SIGNALS, TRAIN_END, VARIANTS)
from src.signals import MAX_HOLD, list_pairs, load_pair, zscore

NOTIONAL_LEG = 10_000         # dollars per leg: the same amount on both legs, no leverage
CAPITAL_PER_PAIR = 2 * NOTIONAL_LEG
OPERATIONS_PER_TRADE = 4      # opening and closing of two legs
COST_SCENARIOS = [0, 2, 5, 10]  # basis points per operation
MAIN_COST = 5                 # realistic scenario, decided before looking at the results
DAYS_PER_YEAR = 252
OPEN_WINDOW = (15, 30)        # minutes from the open: "overnight gap" if the signal falls here

DECISIONS = {"enter", "block", "follow"}  # possible decisions of the agent (agent_variants/agent.py)

# The decision sets compared in the backtest. complete=True: one decision for each of the 973 train signals;
# complete=False: only the 40 signals of the hand-classified sample, so they are compared only on those signals.
# path: original file; copy: copy on git in the load_version format (None if not needed); who: who made the variant;
# letters: the versions the set provides, if not B and C (3b_6h decides only B, c_fresh only C).
# The variants that change the backtest itself (reduced size, delayed entry, B_exaggeration) are not decision sets:
# their trades are in Results/agent_variants/ and notebook 06 reads them from there.
VERSIONS = {
    "spark_24h": dict(path=RUN_24H, copy=AGENT_DECISIONS_COPY, kind="agent", complete=True, who="Giulio",
                      label="Spark X2.6 4B agent, news of the previous 24 hours, reasoning off (main version)"),
    "spark_6h": dict(path=RUN_6H, copy=VARIANTS / "spark_6h/decisions.csv", kind="agent", complete=True, who="Giulio",
                     label="Spark X2.6 4B agent, news of the previous 6 hours, reasoning off"),
    "lexicon": dict(path=BASELINE_LEXICON, copy=VARIANTS / "lexicon/decisions.csv", kind="lexicon", complete=True, who="Giulio",
                    label="Baseline without a model: positive and negative words of the Loughran-McDonald lexicon"),
    "3b_6h": dict(path=DEC_3B_6H, copy=None, kind="agent", complete=True, who="Beatrice", letters=("B",),
                  label="Llama 3.2 3B agent, news of the previous 6 hours, full prompt, keyword filter on the block (B only)"),
    "finbert_session": dict(path=DEC_FINBERT_SESSION, copy=None, kind="agent", complete=True, who="Beatrice",
                            label="FinBERT on targeted news, window tied to the session (overnight gap: from the last close)"),
    "c_fresh": dict(path=DEC_C_FRESH, copy=None, kind="agent", complete=True, who="Beatrice", letters=("C",),
                    label="C only: follows fresh news (60 minutes, in session), strong, with an event and the same direction as the move"),
    "finbert_episode": dict(path=DEC_FINBERT_EPISODE, copy=None, kind="agent", complete=True, who="Beatrice",
                            label="FinBERT, rules of finbert_session with the news published while the spread was moving away"),
    "spark_24h_reasoning": dict(path=RUN_24H_REASONING, copy=None, kind="agent", complete=False, who="Giulio",
                                label="Spark X2.6 4B agent, 24 hours, reasoning on (sample only)"),
    "manual": dict(path=MANUAL_DECISIONS, copy=None, kind="manual", complete=False, who="Giulio",
                   label="The group's hand classification, with the same rule as the agent (sample only)"),
}


def version_file(name: str) -> tuple[Path | None, bool]:
    """The file to read a decision set from: the original if it exists, otherwise the copy on git. The second value says whether it is the copy."""
    v = VERSIONS[name]
    if v["path"].exists():
        return v["path"], False
    if v["copy"] is not None and v["copy"].exists():
        return v["copy"], True
    return None, False


def available_versions(complete: bool | None = None) -> list[str]:
    """The decision sets that can be read on this computer (original or copy)."""
    return [n for n, v in VERSIONS.items() if version_file(n)[0] is not None and (complete is None or v["complete"] == complete)]


def load_trades(path: Path = SIGNALS, allow_test: bool = False) -> pd.DataFrame:
    """Trades of 03_signals.ipynb. Times as datetime; signal minute counted from the 9:30 open."""
    t = pd.read_csv(path, parse_dates=["t_signal", "t_entry", "t_exit"])
    if not allow_test and (t.t_exit.dt.normalize() > pd.Timestamp(TRAIN_END)).any():
        raise ValueError("the table contains trades after the end of the train: the test is used only once, with allow_test=True")
    t["signal_minute"] = t.t_signal.dt.hour * 60 + t.t_signal.dt.minute - (9 * 60 + 30)
    t["day"] = t.t_exit.dt.normalize()
    return t


def trading_days() -> pd.DatetimeIndex:
    """Trading days of the train, from the clean price files (needed to count the days without trades too)."""
    d = load_pair(list_pairs().pair.iloc[0])
    return pd.DatetimeIndex(d.ts[d.is_train].normalize().unique())


def load_version(name: str) -> pd.DataFrame:
    """A decision set of VERSIONS, in the format read by `apply_version`: signal_id, decision, decision_C, follow_side.

    agent: the columns are already there (decisions.csv of a run, or the agent columns in signal_agreement.csv).
    lexicon: `decision` as it is; `action` = 'flat' means block; 'only_A' or 'only_B' with `side` (long/short) means following the
             news on that stock. To compare it with the agent, the lexicon C is simulated with the hedged pair: long the indicated
             stock and short the other (or the opposite), not with a single leg.
    manual: the columns manual_decision and manual_decision_C; no direction to follow, so version B only."""
    if name not in VERSIONS:
        raise ValueError(f"unknown version: {name}. Possible: {', '.join(VERSIONS)}")
    v = VERSIONS[name]
    path, is_copy = version_file(name)
    if path is None:
        raise FileNotFoundError(f"{v['path']} is missing: it is the file of version {name}")
    d = pd.read_csv(path)
    if v["kind"] == "agent" or is_copy:
        # a B-only set (no decision_C column) decides in C as in B; a C-only set (no decision column) always enters in B
        d = d.assign(decision=d.decision if "decision" in d else "enter")
        d = d.assign(decision_C=d.decision_C if "decision_C" in d else d.decision, follow_side=d.follow_side if "follow_side" in d else "")
        out = d[["signal_id", "decision", "decision_C", "follow_side"]].copy()
    elif v["kind"] == "manual":
        out = d[["signal_id", "manual_decision", "manual_decision_C"]].rename(columns={"manual_decision": "decision", "manual_decision_C": "decision_C"})
        out["follow_side"] = ""
    else:
        trades = load_trades()[["signal_id", "ticker_A", "ticker_B"]]
        d = d.merge(trades, on="signal_id", how="left")
        follow = d.action.isin(["only_A", "only_B"])
        a_long = ((d.action == "only_A") & (d.side == "long")) | ((d.action == "only_B") & (d.side == "short"))
        side_txt = np.where(a_long, "long " + d.ticker_A + " / short " + d.ticker_B, "short " + d.ticker_A + " / long " + d.ticker_B)
        out = pd.DataFrame({
            "signal_id": d.signal_id,
            "decision": d.decision,
            "decision_C": np.where(follow, "follow", np.where(d.decision == "enter", "enter", "block")),
            "follow_side": np.where(follow, side_txt, ""),
        })
    out["follow_side"] = out.follow_side.fillna("")
    return out.reset_index(drop=True)


def _z_for(pair: str, hl: float, ema: str, cache: dict):
    """Prices and z-score of a pair, read only once per call of simulate_follow."""
    key = (pair, hl, ema)
    if key not in cache:
        d = load_pair(pair)
        cache[key] = (d, zscore(d.S, hl=hl, reset_daily=ema != "continuous"))
    return cache[key]


def simulate_follow(trades: pd.DataFrame, follow_side: pd.Series) -> pd.DataFrame:
    """Version C: redoes, bar by bar, the trades in which the agent follows the news.

    trades: rows of load_trades to follow; follow_side: for each row 'long X / short Y' (same index as trades).
    If the direction to follow is the same as the A trade, the trade stays the A one. Otherwise it opens at the same bar
    as A (t_entry) in the opposite direction and exits at the first of spread reversion (|z| <= exit_z), MAX_HOLD minutes and
    end of the day, at the open of the next bar as in signals.run_rules (at the end of the day, at the close)."""
    cache, rows = {}, []
    for idx, t in trades.iterrows():
        a_long_A = t.direction.startswith("long")
        a_long_F = str(follow_side.loc[idx]).startswith("long")
        r = t.to_dict()
        if a_long_A == a_long_F:
            rows.append(r | dict(c_kind="follow, same as A"))
            continue
        d, z = _z_for(t.pair, t.hl_min, t.ema, cache)
        i = d.ts.get_loc(t.t_signal)
        e = d.ts.get_loc(t.t_entry)
        assert np.isclose(z[i], t.z_signal), f"signal {t.signal_id}: the z-score does not match the one of 03_signals"
        side = np.sign(z[i])               # as in run_rules: +1 high spread
        k = e
        while True:
            if d.last_of_day[k]:
                reason, a_out, b_out = "end_of_day", d.cA[k], d.cB[k]
                break
            if side * z[k] <= t.exit_z:
                reason = "reversion"
            elif k - e + 1 >= MAX_HOLD:
                reason = "time"
            else:
                k += 1
                continue
            k += 1
            a_out, b_out = d.oA[k], d.oB[k]
            break
        s_in, s_out = np.log(d.oA[e] / d.oB[e]), np.log(a_out / b_out)
        sign = 1 if a_long_F else -1        # +1: long A / short B
        t_exit = d.ts[k]
        rows.append(r | dict(
            direction=follow_side.loc[idx], t_exit=t_exit, price_A_out=a_out, price_B_out=b_out, exit_reason=reason,
            gross_bps=sign * (s_out - s_in) * 1e4, minutes_in_trade=(t_exit - t.t_entry).total_seconds() / 60,
            day=t_exit.normalize(), c_kind="follow",
        ))
    return pd.DataFrame(rows, columns=[*trades.columns, "c_kind"])


def apply_version(trades: pd.DataFrame, version: str, decisions: pd.DataFrame | None = None) -> pd.DataFrame:
    """Selects (and for C redoes) the trades of version A, B or C.

    A: every signal enters, no agent.
    B: `decisions` has the columns signal_id and decision ('enter' or 'block'): the blocked trades are dropped.
    C: `decisions` also has decision_C ('enter', 'block', 'follow') and follow_side: 'enter' keeps the A trade, 'block' drops it,
       'follow' is redone by simulate_follow in the direction of the news.
    If a signal has no decision, versions B and C block it (the agent's safety rule)."""
    if version == "A":
        return trades.copy()
    if decisions is None:
        raise ValueError(f"version {version} needs the agent's decisions")
    if version == "B":
        bad = set(decisions.decision) - (DECISIONS - {"follow"})
        if bad:
            raise ValueError(f"invalid decisions for version B: {bad}")
        ok = trades.merge(decisions[["signal_id", "decision"]], on="signal_id", how="left")
        return ok[ok.decision == "enter"].drop(columns="decision").reset_index(drop=True)
    if version != "C":
        raise ValueError("version must be A, B or C")
    if "decision_C" not in decisions:
        raise ValueError("version C needs the decision_C column")
    bad = set(decisions.decision_C) - DECISIONS
    if bad:
        raise ValueError(f"unknown decisions: {bad}")
    ok = trades.merge(decisions[["signal_id", "decision_C", "follow_side"]], on="signal_id", how="left")
    follow = ok[ok.decision_C == "follow"]
    if (follow.follow_side.fillna("") == "").any():
        raise ValueError("there are 'follow' decisions without the direction to follow (follow_side)")
    keep = ok[ok.decision_C == "enter"].assign(c_kind="enter")
    out = pd.concat([keep, simulate_follow(follow.drop(columns=["decision_C", "follow_side"]), follow.follow_side)], ignore_index=True)
    return out.drop(columns=["decision_C", "follow_side"], errors="ignore").sort_values("t_signal").reset_index(drop=True)


def random_decisions(trades: pd.DataFrame, p_block: float = 0.2, seed: int = 0) -> pd.DataFrame:
    """Fake decisions (random block), only to check that the engine works: not to be interpreted."""
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"signal_id": trades.signal_id, "decision": np.where(rng.random(len(trades)) < p_block, "block", "enter")})


def add_costs(trades: pd.DataFrame, cost_bps: float) -> pd.DataFrame:
    """Adds the cost, the net profit in basis points and the net profit in dollars.
    If there is a `size` column (size of the trade: 1 full, 0.5 half), dollar profit and costs are multiplied by the size."""
    t = trades.copy()
    t["cost_bps"] = OPERATIONS_PER_TRADE * cost_bps
    t["net_bps"] = t.gross_bps - t.cost_bps
    t["pnl_usd"] = t.net_bps / 1e4 * NOTIONAL_LEG * (t["size"] if "size" in t else 1)
    return t


def daily_pnl(trades: pd.DataFrame, days: pd.DatetimeIndex, n_pairs: int | None = None) -> pd.DataFrame:
    """Dollar profit, return on capital and equity curve per day (days without trades count as 0).
    n_pairs: pairs the capital is allocated to; by default all those in the list, even if one has no trades."""
    pnl = trades.groupby("day").pnl_usd.sum().reindex(days, fill_value=0.0)
    capital = (len(list_pairs()) if n_pairs is None else n_pairs) * CAPITAL_PER_PAIR
    out = pd.DataFrame({"pnl_usd": pnl, "ret": pnl / capital})
    out["equity"] = out.ret.cumsum()          # fixed capital, so returns are summed (no reinvestment)
    out["drawdown"] = out.equity - out.equity.cummax().clip(lower=0)
    return out


def summary(trades: pd.DataFrame, days: pd.DatetimeIndex | None = None, n_pairs: int | None = None) -> dict:
    """Trade metrics (in basis points) and, if the days are given, metrics of the daily portfolio.
    With the `size` column, mean gross and net profit are weighted by the size (profit per dollar invested)."""
    net = trades.net_bps if "net_bps" in trades else trades.gross_bps
    n = len(net)
    wins, losses = net[net > 0], net[net < 0]
    w = trades["size"] if "size" in trades else None
    out = {
        "trade": n,
        "gross_bps": np.average(trades.gross_bps, weights=w) if n else np.nan,
        "net_bps": np.average(net, weights=w) if n else np.nan,
        "se_bps": net.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan,
        "win_rate": (net > 0).mean(),
        "profit_factor": wins.sum() / abs(losses.sum()) if len(losses) else np.nan,
        "avg_win_bps": wins.mean(),
        "avg_loss_bps": losses.mean(),
        "avg_minutes": trades.minutes_in_trade.mean(),
    }
    if days is not None and "pnl_usd" in trades:
        d = daily_pnl(trades, days, n_pairs)
        out.update(
            pnl_usd=d.pnl_usd.sum(),
            total_return=d.equity.iloc[-1],
            sharpe=d.ret.mean() / d.ret.std(ddof=1) * np.sqrt(DAYS_PER_YEAR) if d.ret.std() > 0 else np.nan,
            max_drawdown=d.drawdown.min(),
        )
    return out


def breakeven_cost(trades: pd.DataFrame) -> float:
    """Cost per operation (in basis points) at which the mean net profit goes to zero."""
    return trades.gross_bps.mean() / OPERATIONS_PER_TRADE


def by_cost(trades: pd.DataFrame, days: pd.DatetimeIndex, costs=COST_SCENARIOS) -> pd.DataFrame:
    """One row per cost scenario."""
    return pd.DataFrame({c: summary(add_costs(trades, c), days) for c in costs}).T.rename_axis("cost_bps_per_operation")


def by_group(trades: pd.DataFrame, key, cost_bps: float = MAIN_COST) -> pd.DataFrame:
    """Gross and net profit per group (pair, entry window, exit reason...)."""
    t = add_costs(trades, cost_bps)
    g = t.groupby(key)
    return pd.DataFrame({
        "trade": g.size(),
        "gross_bps": g.gross_bps.mean(),
        "net_bps": g.net_bps.mean(),
        "se_bps": g.net_bps.std(ddof=1) / np.sqrt(g.size()),
        "win_rate": g.net_bps.apply(lambda x: (x > 0).mean()),
    })


def entry_window(trades: pd.DataFrame) -> pd.Series:
    """'open' if the signal falls between minutes 15 and 30 from the open (overnight gap), 'after' otherwise."""
    lo, hi = OPEN_WINDOW
    return pd.Series(np.where(trades.signal_minute.between(lo, hi - 1), "open (15-30 min)", "after 30 min"), index=trades.index, name="window")


# ---------------------------------------------------------------- comparison between result versions

def version_trades(trades: pd.DataFrame, name: str, letters=("A", "B", "C")) -> dict[str, pd.DataFrame]:
    """The trades of a result version, per letter. For partial versions, all letters (A included) are
    restricted to the signals that have a decision, so the comparison is on the same signals."""
    dec = load_version(name)
    if not VERSIONS[name]["complete"]:
        trades = trades[trades.signal_id.isin(dec.signal_id)]
    if "letters" in VERSIONS[name]:
        letters = [x for x in letters if x == "A" or x in VERSIONS[name]["letters"]]
    elif (dec.follow_side == "").all():
        letters = [x for x in letters if x != "C"]   # without a direction to follow, C cannot be simulated
    return {x: apply_version(trades, x, None if x == "A" else dec) for x in letters}


def compare_versions(trades: pd.DataFrame, days: pd.DatetimeIndex | None, names, costs=(0, MAIN_COST),
                     letters=("A", "B", "C")) -> pd.DataFrame:
    """One row per result version, letter (A, B, C) and cost per operation, with the metrics of `summary`.
    days=None: trade metrics only (for the partial versions, where the daily portfolio makes no sense).
    A appears only once per subset of signals: it is the same for all complete versions."""
    rows, seen_A = [], set()
    for name in names:
        by_letter = version_trades(trades, name, letters)
        ids = frozenset(by_letter["A"].signal_id)
        n_all = len(ids)
        for letter, t in by_letter.items():
            label = "no agent" if letter == "A" else name
            if letter == "A":
                if ids in seen_A:
                    continue
                seen_A.add(ids)
            for c in costs:
                s = summary(add_costs(t, c), days if VERSIONS[name]["complete"] else None)
                rows.append(dict(decisions=label, version=letter, signals=n_all, cost_bps=c, trades_excluded=n_all - len(t)) | s)
    return pd.DataFrame(rows).set_index(["decisions", "version", "signals", "cost_bps"])


def blocked_vs_random(trades: pd.DataFrame, decisions: pd.DataFrame, n_draws: int = 5000, seed: int = 0) -> dict:
    """Does the agent block the right trades or random ones? Mean gross profit of the blocked trades, against random blocks of the same number.

    p_value: share of random blocks that remove trades with a mean profit equal to or lower than those blocked by the agent.
    Small (below 0.05) means that the agent removes worse trades than chance would. The cost is the same for every
    trade, so the comparison on the gross profit holds for any cost scenario."""
    m = trades.merge(decisions[["signal_id", "decision"]], on="signal_id", how="left")
    blocked = m.decision != "enter"
    g = m.gross_bps.to_numpy()
    k = int(blocked.sum())
    rng = np.random.default_rng(seed)
    draws = np.array([g[rng.choice(len(g), k, replace=False)].mean() for _ in range(n_draws)]) if k else np.array([np.nan])
    obs = g[blocked].mean() if k else np.nan
    return dict(signals=len(g), blocked=k, gross_blocked_bps=obs, gross_kept_bps=g[~blocked].mean(), gross_all_bps=g.mean(),
                gross_random_blocked_bps=np.nanmean(draws), p_value=(draws <= obs).mean() if k else np.nan)


def save_results(tables: dict[str, pd.DataFrame]) -> list[Path]:
    """Writes every table to Results/<name>.csv (the name can contain a subfolder, for example 'spark_24h/trades_B')."""
    written = []
    for key, df in tables.items():
        path = RESULTS / f"{key}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=not isinstance(df.index, pd.RangeIndex))
        written.append(path)
    return written
