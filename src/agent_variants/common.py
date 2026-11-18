"""Small functions shared by the agent variant scripts."""
import duckdb
import pandas as pd

from src.config import DAILY


def market_days() -> pd.DatetimeIndex:
    """All the trading days of the daily prices (from 2006): used to find the trading day before a signal.
    It also contains test days, but the scripts use it only to look back from the signal."""
    d = duckdb.sql(f"SELECT DISTINCT date FROM '{DAILY.as_posix()}' ORDER BY date").df()
    return pd.DatetimeIndex(pd.to_datetime(d.date))
