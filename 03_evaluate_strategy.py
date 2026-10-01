"""Evaluate the strategies and benchmarks, In-Sample and Out-of-Sample, without costs: returns, metrics, charts (see docs/metrics.md).

metrics.type: close_to_close (execution at the close) or open_to_open (execution at the next open).

Inputs:  data/prices/{open,close}.csv, data/signals/<strategy>.csv
Outputs: data/metrics/{returns,performance,return_stats,behaviour,market}.csv
         data/plots/{equity,drawdown,exposure}.html
"""

import pandas as pd

from src import metrics, plots
from src.config import DATA_KEYS, ROOT, check_used, load_config
from src.data import read_weekly

EQUAL_WEIGHT = "Equal weight"

PERIODS = ["IS", "OOS"]

TYPES = ["close_to_close", "open_to_open"]


def forward_returns(opens: pd.DataFrame, close: pd.DataFrame, kind: str) -> pd.DataFrame:
    """Return earned by the signal of each week."""
    if kind == "close_to_close":
        return close.shift(-1) / close - 1  # C(t+1) / C(t) - 1
    return opens.shift(-2) / opens.shift(-1) - 1  # O(t+2) / O(t+1) - 1


def execution_dates(weeks: pd.MultiIndex, kind: str) -> tuple[pd.Series, pd.Series]:
    """Days when the position of each week is taken and when its return is realized."""
    date_open = pd.Series(weeks.get_level_values("date_open"), index=weeks)
    date_close = pd.Series(weeks.get_level_values("date_close"), index=weeks)
    if kind == "close_to_close":
        return date_close, date_close.shift(-1)  # close of week t, close of week t+1
    return date_open.shift(-1), date_open.shift(-2)  # open of week t+1, open of week t+2


def evaluated_weeks(signals: dict[str, pd.DataFrame], forward: pd.DataFrame) -> pd.MultiIndex:
    """Weeks with every signal and return available."""
    weeks = forward.index
    complete = forward.notna().all(axis=1)
    for s in signals.values():
        complete &= s.reindex(weeks).notna().all(axis=1)
    if not complete.any():
        raise ValueError("no week has a signal of every strategy and a return for every ticker: check the tickers and the dates")
    first, last = complete[complete].index[[0, -1]]
    weeks = weeks[weeks.get_loc(first) : weeks.get_loc(last) + 1]
    missing = ~complete.loc[weeks]
    if missing.any():
        week = missing[missing].index[0][1].date()
        raise ValueError(f"missing signals or prices inside the evaluated period, e.g. in the week of {week}")
    return weeks


def returns_table(signals: dict[str, pd.DataFrame], forward: pd.DataFrame, tickers: list[str], market: str) -> pd.DataFrame:
    returns = pd.DataFrame({name: (s * forward[tickers]).mean(axis=1) for name, s in signals.items()})
    returns[EQUAL_WEIGHT] = forward[tickers].mean(axis=1)
    returns[market] = forward[market]
    return returns


def save(table: pd.DataFrame, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path)
    print(f"Saved {path.relative_to(ROOT)}: {table.shape[0]} rows, {table.shape[1]} columns")


def main() -> None:
    cfg = load_config()
    data_dir = ROOT / cfg["data"]["data_dir"]
    tickers, market = cfg["data"]["tickers"], cfg["data"]["benchmark"]
    kind, risk_free = cfg["metrics"]["type"], cfg["metrics"]["risk_free"]
    is_end = pd.Timestamp(cfg["metrics"]["is_end"])
    if kind not in TYPES:
        raise ValueError(f"metrics.type ({kind}) must be one of {TYPES}")
    if is_end.day_name() != "Friday":
        raise ValueError(f"metrics.is_end ({is_end.date()}) must be a Friday: the In-Sample period ends with a whole week")

    data_used = {key: cfg["data"][key] for key in DATA_KEYS}
    check_used(data_used, data_dir / "prices" / "config.yaml", "01_download_data.py")
    check_used(
        {"data": data_used, "strategies": cfg["strategies"]}, data_dir / "signals" / "config.yaml", "02_compute_signals.py"
    )

    opens = read_weekly(data_dir / "prices" / "open.csv")
    close = read_weekly(data_dir / "prices" / "close.csv")
    signals = {name: read_weekly(data_dir / "signals" / f"{name}.csv") for name in cfg["strategies"]}
    for name, s in signals.items():
        if list(s.columns) != tickers or not s.index.equals(close.index[-len(s) :]):
            raise ValueError(f"signals of {name} do not match the prices: run 02_compute_signals.py again")
        if not s.isin([-1, 0, 1]).where(s.notna(), True).all().all():
            raise ValueError(f"signals of {name} must be -1, 0, +1 or missing")

    forward = forward_returns(opens, close, kind)
    weeks = evaluated_weeks(signals, forward)
    signals = {name: s.loc[weeks].astype(int) for name, s in signals.items()}
    returns = returns_table(signals, forward.loc[weeks], tickers, market)
    first, last = weeks[0][1].date(), weeks[-1][1].date()
    print(f"Returns: {kind}. Evaluated period: signals from the week of {first} to the week of {last} ({len(weeks)} weeks)")

    entered, realized = (dates.loc[weeks] for dates in execution_dates(close.index, kind))
    period = pd.Series("OOS", index=weeks).where(realized > is_end, "IS")
    if not set(PERIODS) <= set(period):
        days = f"{realized.iloc[0].date()} to {realized.iloc[-1].date()}"
        raise ValueError(f"metrics.is_end ({is_end.date()}) must split the days when the returns are realized ({days})")

    tables = {"performance": {}, "return_stats": {}, "behaviour": {}, "market": {}}
    for p in PERIODS:
        in_p = period == p
        r_p = returns[in_p]
        print(
            f"{p}: {in_p.sum()} weeks, returns realized from {realized[in_p].iloc[0].date()} to {realized[in_p].iloc[-1].date()}"
        )
        for name, r in r_p.items():
            tables["performance"][p, name] = metrics.performance(r, risk_free)
            tables["return_stats"][p, name] = metrics.return_stats(r)
            if name != market:
                tables["market"][p, name] = metrics.market(r, r_p[market], risk_free)
        for name, s in signals.items():
            tables["behaviour"][p, name] = metrics.behaviour(s[in_p])

    out_dir = data_dir / "metrics"
    save(pd.concat([period.rename("period"), returns], axis=1), out_dir / "returns.csv")
    for file, rows in tables.items():
        save(pd.DataFrame(rows).T.rename_axis(["period", "series"]), out_dir / f"{file}.csv")

    colors = plots.colors(list(signals), [EQUAL_WEIGHT, market])
    plots.save_plots(returns, signals, period, entered, realized, colors, data_dir / "plots")

    summary = pd.DataFrame(tables["performance"]).T[
        ["annualized_return", "annualized_volatility", "sharpe_ratio", "max_drawdown"]
    ]
    print(summary.round(3).to_string())


if __name__ == "__main__":
    main()
