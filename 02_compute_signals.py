"""Compute the weekly signals (1 long, 0 flat, -1 short) of the strategies in config.yaml.

The row of a week holds the signal computed after its close.

Input:  data/prices/close.csv
Output: data/signals/<strategy>.csv
        data/signals/config.yaml, the settings used
"""

import numpy as np
import pandas as pd

from src.config import DATA_KEYS, ROOT, check_used, load_config, save_used
from src.data import read_weekly


def sma(close: pd.DataFrame, window: int) -> pd.DataFrame:
    """Long if the close is above its moving average, flat otherwise."""
    average = close.rolling(window).mean()
    return (close > average).astype(int).where(average.notna())


def random(close: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Random signal in {-1, 0, +1}, independent of the prices."""
    rng = np.random.default_rng(seed)
    signals = pd.DataFrame(rng.integers(-1, 2, size=close.shape), index=close.index, columns=close.columns)
    return signals.where(close.notna())


STRATEGIES = {"sma": sma, "random": random}


def main() -> None:
    cfg = load_config()
    data_dir = ROOT / cfg["data"]["data_dir"]
    tickers = cfg["data"]["tickers"]

    data_used = {key: cfg["data"][key] for key in DATA_KEYS}
    check_used(data_used, data_dir / "prices" / "config.yaml", "01_download_data.py")
    close = read_weekly(data_dir / "prices" / "close.csv")[tickers]

    computed = {}  # saved only when every strategy is valid
    for name, params in cfg["strategies"].items():
        if name not in STRATEGIES:
            raise ValueError(f"strategy {name} in config.yaml has no function in STRATEGIES of 02_compute_signals.py")
        signals = STRATEGIES[name](close, **(params or {}))
        if not (signals.index.equals(close.index) and list(signals.columns) == tickers):
            raise ValueError(f"signals of {name} must have the same weeks and tickers as the closes")
        if signals.isna().all().all():
            raise ValueError(f"strategy {name} has no signal: check its parameters")
        if not signals.isin([-1, 0, 1]).where(signals.notna(), True).all().all():
            raise ValueError(f"signals of {name} must be -1, 0, +1 or missing")
        first = signals.notna().any(axis=1).to_numpy().argmax()
        computed[name] = signals.iloc[first:].astype("Int64")  # from the first week with a signal

    for name, signals in computed.items():
        path = data_dir / "signals" / f"{name}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        signals.to_csv(path)
        print(f"Saved {path.relative_to(ROOT)}: {signals.shape[0]} weeks, {signals.shape[1]} tickers")
        print(f"Share of weeks long: {(signals == 1).mean().round(2).to_dict()}")

    save_used({"data": data_used, "strategies": cfg["strategies"]}, data_dir / "signals" / "config.yaml")


if __name__ == "__main__":
    main()
