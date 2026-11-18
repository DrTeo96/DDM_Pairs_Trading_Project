"""Bloomberg data of the project: from the raw files to clean datasets in pandas, with the quality checks.

From the terminal, in the project folder:
    uv run python -m src.data      rebuilds data/processed/ from the files in data/raw/ and prints the checks
In a notebook:
    from src.data import load
    daily = load("daily")          # or "intraday_1m", "sentiment"

To know before using the data (found by the checks):
- the universe is today's index members: whoever joined after 2006 does not have the full history (survivorship bias)
- daily: PX_LAST is already adjusted for splits and dividends; some series have holes of years (e.g. FITB),
  so returns must use the ret column, computed only between consecutive trading days
- intraday_1m: New York times, prices NOT adjusted (splits show up as gaps: APH, CRWD, DD, MNST);
  the volume is only a part of PX_VOLUME, in a different share per exchange
- sentiment: growing coverage, from about 10% of the days in 2007 to about 60% from 2022
"""
import datetime

import duckdb
import numpy as np
import pandas as pd

from src.config import PROCESSED, RAW

# Memory cap for duckdb: beyond it, sorting spills to disk (inside data/) instead of taking more RAM.
# With 2 GB the heaviest step stays around 4 GB at peak instead of going over 5.
MEMORY_LIMIT = "2GB"
TEMP_DIR = PROCESSED / ".duckdb_tmp"


def _connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{MEMORY_LIMIT}'")
    con.execute(f"SET temp_directory='{TEMP_DIR.as_posix()}'")
    return con

# the raw file name is the Bloomberg ticker: AAPL_UW_Equity.parquet -> "AAPL UW Equity"
TICKER_FROM_FILENAME = r"replace(regexp_extract(filename, '([^/\\]+)\.parquet$', 1), '_', ' ')"

# for each folder of data/raw: SQL expressions for ticker and timestamp, columns to keep, whether to drop duplicates
DATASETS = {
    # raw minutes are in UTC: converted to New York time (09:30 open, daylight saving handled)
    "intraday_1m": dict(
        ticker=TICKER_FROM_FILENAME,
        ts="timezone('America/New_York', timezone('UTC', time))",
        cols="open, high, low, close, volume, n_events",
        dedup=False,
    ),
    "daily": dict(
        ticker=TICKER_FROM_FILENAME,
        ts="date",
        cols="PX_LAST, PX_VOLUME, TOT_RETURN_INDEX_GROSS_DVDS",
        dedup=False,
    ),
    # the ticker is already a column; the *_2023_2023 files repeat rows already in *_2006_2026
    "sentiment": dict(
        ticker="ticker",
        ts="date",
        cols="* EXCLUDE (ticker, date, filename)",
        dedup=True,
    ),
}

# value Bloomberg writes in the sentiment in place of a missing data point
SENTINEL = -134217.7


def build_processed() -> None:
    """Merges the raw files of each folder into data/processed/<name>_all.parquet.

    The timestamp becomes two columns, date and time (always 00:00:00 for daily and sentiment).
    """
    PROCESSED.mkdir(parents=True, exist_ok=True)
    con = _connect()
    # parallel write with less memory: the file blocks come out in scattered order, load() sorts again
    con.execute("SET preserve_insertion_order=false")
    for name, cfg in DATASETS.items():
        out = PROCESSED / f"{name}_all.parquet"
        distinct = "DISTINCT ON (ticker, date, time)" if cfg["dedup"] else ""
        # the subquery avoids clashes between the new names date/time and the raw columns with the same name
        rows = con.execute(f"""
            COPY (
                SELECT {distinct} ticker, CAST(ts AS DATE) AS date, CAST(ts AS TIME) AS time, * EXCLUDE (ticker, ts)
                FROM (
                    SELECT {cfg['ticker']} AS ticker, {cfg['ts']} AS ts, {cfg['cols']}
                    FROM read_parquet('{(RAW / name).as_posix()}/*.parquet', filename=true)
                )
                ORDER BY ticker, date, time
            ) TO '{out.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 500000)
        """).fetchall()[0][0]
        print(f"{out.name}: {rows:,} rows")
    con.close()


def load(name: str) -> pd.DataFrame:
    """A dataset of data/processed ("intraday_1m", "daily" or "sentiment") in pandas, sorted by ticker, date, time.

    ticker and time are categories: few values repeated millions of times, much less memory.
    sentiment: the -134217.7 placeholders become NaN.
    daily: also the columns step (trading days since the previous record of the same ticker:
    1 = next day, > 1 = hole in the series) and ret (return of PX_LAST, only where step is 1).
    """
    path = (PROCESSED / f"{name}_all.parquet").as_posix()
    con = _connect()
    # ticker and time become categories already inside duckdb (ENUM type). Converting them in pandas, .df() would first create one
    # Python object per row: with the 13 million intraday rows that is about 6 GB at peak for a table that takes 0.8.
    con.execute(f"CREATE TYPE ticker_t AS ENUM (SELECT DISTINCT ticker FROM '{path}' ORDER BY ticker)")
    con.execute(f"CREATE TYPE time_t AS ENUM (SELECT DISTINCT CAST(time AS VARCHAR) FROM '{path}' ORDER BY 1)")
    df = con.execute(f"""
        SELECT * REPLACE (CAST(ticker AS ticker_t) AS ticker, CAST(CAST(time AS VARCHAR) AS time_t) AS time)
        FROM '{path}' ORDER BY ticker, date, time
    """).df()
    con.close()   # frees at once the copy of the data that duckdb keeps for itself
    df["ticker"] = df["ticker"].cat.as_unordered().cat.rename_categories(pd.Index(df["ticker"].cat.categories.astype(object)).astype("str"))
    df["time"] = df["time"].cat.as_unordered().cat.rename_categories([datetime.time.fromisoformat(t) for t in df["time"].cat.categories])
    if name == "sentiment":
        num = df.select_dtypes("number").columns
        sentinel = df[num] == SENTINEL
        print(f"sentiment: {sentinel.sum().sum()} placeholders {SENTINEL} converted to NaN")
        df[num] = df[num].mask(sentinel)
    if name == "daily":
        calendar = pd.DatetimeIndex(df["date"].unique()).sort_values()  # days on which at least one ticker trades
        df["step"] = pd.Series(calendar.get_indexer(df["date"]), index=df.index).groupby(df["ticker"], observed=True).diff()
        # across a hole the "return" would be false: FITB would make +367% after 9 years without data
        df["ret"] = df.groupby("ticker", observed=True)["PX_LAST"].pct_change().where(df["step"] == 1)
    return df


def intraday_sessions(intraday: pd.DataFrame) -> pd.DataFrame:
    """One row per ticker and day: first open, last close, volume, number of bars and overnight gap."""
    sessions = intraday.groupby(["ticker", "date"], observed=True).agg(
        open=("open", "first"), close=("close", "last"), volume=("volume", "sum"), bars=("close", "size"))
    # overnight gap: open of the day against the close of the previous session of the same ticker
    sessions["gap"] = sessions["open"] / sessions.groupby(level="ticker", observed=True)["close"].shift() - 1
    return sessions


def show(table: pd.DataFrame) -> None:
    """Prints a whole table: print(table) would cut rows and columns."""
    print(table.to_string())


def check_standard(name: str, df: pd.DataFrame) -> None:
    """Basic checks: size, period, types, missing and distinct values, duplicates, statistics."""
    rows_per_ticker = df.groupby("ticker", observed=True).size()
    print(f"\n=== {name} ===")
    print(f"rows: {len(df):,} | columns: {df.shape[1]} | memory: {df.memory_usage(deep=True).sum() / 1e6:,.0f} MB")
    print(f"period: {df['date'].min().date()} → {df['date'].max().date()} | tickers: {df['ticker'].nunique()} "
          f"| rows per ticker: min {rows_per_ticker.min():,}, median {rows_per_ticker.median():,.0f}, max {rows_per_ticker.max():,}")
    show(df.head(3))
    show(pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "non_null": df.notna().sum(),
        "null_%": (df.isna().mean() * 100).round(2),
        "unique": df.nunique(),
    }))
    dup_keys = df.duplicated(["ticker", "date", "time"]).sum()
    # a duplicated row necessarily has a duplicated key: without duplicated keys the comparison on all columns
    # (the step that uses the most memory, on the intraday) is not needed
    dup_rows = df.duplicated().sum() if dup_keys else 0
    print(f"duplicated rows: {dup_rows} | duplicated keys (ticker, date, time): {dup_keys}")
    show(df.describe().T)


def check_intraday(intraday: pd.DataFrame, sessions: pd.DataFrame) -> None:
    """1-minute bars: inconsistent prices, completeness, missing tickers, extreme jumps."""
    print("\n=== intraday_1m: price checks ===")
    show(pd.Series({
        "prices <= 0": (intraday[["open", "high", "low", "close"]] <= 0).any(axis=1).sum(),
        "volume <= 0": (intraday["volume"] <= 0).sum(),
        # high and low must contain open and close
        "high < max(open, close)": (intraday["high"] < np.maximum(intraday["open"], intraday["close"])).sum(),
        "low > min(open, close)": (intraday["low"] > np.minimum(intraday["open"], intraday["close"])).sum(),
        "high < low": (intraday["high"] < intraday["low"]).sum(),
        "bars outside 09:30-15:59": (~intraday["time"].isin(pd.date_range("09:30", "15:59", freq="min").time)).sum(),
    }, name="cases").to_frame())

    # the full session has 390 bars: a minute without trades produces no bar
    bars = sessions["bars"]
    print(f"bars per ticker-day: median {bars.median():.0f} of 390, complete days {(bars == 390).mean():.1%}")

    # a sudden drop in the tickers present means a hole in the download, not a market event
    n_ticker = sessions.groupby(level="date").size()
    print(f"tickers per day: median {n_ticker.median():.0f}; days with many missing tickers:")
    show(n_ticker[n_ticker < 0.95 * n_ticker.median()].to_frame("ticker"))

    # 1-minute returns within the same session, without the overnight jump
    r1m = intraday.groupby(["ticker", "date"], observed=True)["close"].pct_change()
    extreme = r1m.abs() > 0.05
    print(f"1-minute returns beyond ±5%: {extreme.sum()}")
    show(intraday.loc[extreme, ["ticker", "date", "time", "open", "close", "volume"]].assign(ret=r1m[extreme]))

    print(f"overnight gaps beyond ±15%: {(sessions['gap'].abs() > 0.15).sum()} | beyond ±40%: {(sessions['gap'].abs() > 0.4).sum()}")


def check_daily(daily: pd.DataFrame) -> None:
    """Daily prices: missing values, holes in the series, history per ticker, extreme returns, dividends."""
    print("\n=== daily: price checks ===")
    show(pd.Series({
        "PX_LAST missing": daily["PX_LAST"].isna().sum(),
        "PX_LAST <= 0": (daily["PX_LAST"] <= 0).sum(),
        "PX_VOLUME <= 0": (daily["PX_VOLUME"] <= 0).sum(),
    }, name="cases").to_frame())
    print("PX_LAST missing, most affected tickers:", daily.loc[daily["PX_LAST"].isna(), "ticker"].value_counts().head(5).to_dict())

    holes = daily[daily["step"] > 1].groupby("ticker", observed=True)["step"].agg(
        holes="size", missing_days=lambda s: (s - 1).sum(), max_hole="max").astype(int)
    print(f"\ntickers with holes in the series: {len(holes)}")
    show(holes.sort_values("missing_days", ascending=False))

    span = daily.groupby("ticker", observed=True)["date"].agg(["min", "max", "size"])
    first_day = daily["date"].min()
    print(f"tickers present from the first day ({first_day.date()}): {(span['min'] == first_day).sum()} | joined later: {(span['min'] > first_day).sum()}")
    print("last available day:", span["max"].dt.strftime("%Y-%m-%d").value_counts().to_dict())
    print("tickers with less than one year of history (< 252 days):")
    show(span[span["size"] < 252])

    print(f"daily returns beyond ±40%: {(daily['ret'].abs() > 0.4).sum()}; the 10 most extreme:")
    show(daily.loc[daily["ret"].abs().nlargest(10).index, ["ticker", "date", "PX_LAST", "ret"]])

    # if PX_LAST did not include dividends, on ex-dividend days the total return would beat the price
    r_tr = daily.groupby("ticker", observed=True)["TOT_RETURN_INDEX_GROSS_DVDS"].pct_change().where(daily["step"] == 1)
    both = daily["ret"].notna() & r_tr.notna()
    print(f"days with TOT_RETURN_INDEX return = PX_LAST return (±0.1%): {((r_tr - daily['ret']).abs() <= 0.001)[both].mean():.2%}")


def check_intraday_vs_daily(sessions: pd.DataFrame, daily: pd.DataFrame) -> None:
    """Comparison between the two price sources: splits, dividend adjustment, volumes."""
    print("\n=== intraday vs daily ===")
    s = sessions.join(daily.set_index(["ticker", "date"])[["PX_LAST", "PX_VOLUME", "ret"]])

    # a huge intraday gap with an almost zero daily return is a split: the daily is adjusted, the intraday is not
    print("overnight gaps beyond ±40% and daily return of the same day:")
    show(s.loc[s["gap"].abs() > 0.4, ["gap", "ret"]])

    # if the difference between the last intraday close and PX_LAST grows going back, PX_LAST is adjusted for dividends
    diff = (s["close"] / s["PX_LAST"] - 1).abs() * 100
    month = s.index.get_level_values("date").to_period("M").rename("month")
    show(diff.groupby(month).median().round(3).to_frame("median diff. close vs PX_LAST (%)"))

    # share of the daily volume captured by the intraday bars, per exchange (UN = NYSE, UW = Nasdaq, UF = Cboe)
    share = s["volume"] / s["PX_VOLUME"]
    exchange = s.index.get_level_values("ticker").astype(str).str.split().str[1].rename("exchange")
    show(share.groupby(exchange).median().round(2).to_frame("intraday volume / PX_VOLUME (median)"))


if __name__ == "__main__":
    build_processed()
    # one dataset at a time: keeping all three in memory together is not needed by any check
    intraday = load("intraday_1m")
    check_standard("intraday_1m", intraday)
    sessions = intraday_sessions(intraday)
    check_intraday(intraday, sessions)
    del intraday
    daily = load("daily")
    check_standard("daily", daily)
    check_daily(daily)
    check_standard("sentiment", load("sentiment"))
    check_intraday_vs_daily(sessions, daily)
