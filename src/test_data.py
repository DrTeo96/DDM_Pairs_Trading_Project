"""Test data from Alpaca: news of the 30 stocks and SPY daily prices. Rules in docs/Test.md.

    uv run python -m src.test_data           downloads news (TEST_START - TEST_END) and SPY (from the trading day before TEST_START to TEST_END)
    uv run python -m src.test_data --probe   a single test call on the news, saves nothing

It uses the Alpaca keys in .env, like src/news.py and src/spy.py. Those two scripts refuse the test dates to protect the train;
this script downloads them to separate files (NEWS_TEST, SPY_TEST) and does not touch the train files.
The news are saved in the same format as the train (news.build_table): ts is the publication time in New York time.
Downloading the data reads neither intraday prices nor results: the test itself is in src/test_final.py.
"""
import argparse
import json
import shutil
import time
import urllib.parse
import urllib.request

import pandas as pd

from src.config import NEWS_SET, NEWS_TEST, SPY_TEST, TEST_END, TEST_START
from src.news import NY, PAGE_LIMIT, PAUSE, RAW_NEWS, URL, _get, build_table, load_keys, save_table, tickers_of
from src.spy import URL as SPY_URL

SPY_START = "2026-09-16"   # the last trading day before the test: its close is needed for the return of 17 September


def _bounds(start: str, end: str) -> tuple[str, str]:
    """Like news._bounds, but for the test: from New York midnight of `start` to the midnight after `end`, in UTC."""
    if pd.Timestamp(start) < pd.Timestamp(TEST_START) or pd.Timestamp(end) > pd.Timestamp(TEST_END):
        raise ValueError(f"the test news go from {TEST_START} to {TEST_END}")
    s = pd.Timestamp(start).tz_localize(NY).tz_convert("UTC")
    e = (pd.Timestamp(end) + pd.Timedelta(days=1)).tz_localize(NY).tz_convert("UTC")
    return s.strftime("%Y-%m-%dT%H:%M:%SZ"), e.strftime("%Y-%m-%dT%H:%M:%SZ")


def probe() -> None:
    """One call with 5 news items, to check keys and access to the period."""
    s, e = _bounds(TEST_START, TEST_END)
    data = _get({"symbols": ",".join(tickers_of(NEWS_SET)), "start": s, "end": e, "limit": 5, "sort": "asc"}, load_keys())
    items = data.get("news", [])
    print(f"Keys accepted. Period {TEST_START} - {TEST_END}: {len(items)} news items in the test page.")
    for n in items:
        print(f"  {n['created_at']}  [{','.join(n.get('symbols', []))}]  {n['headline'][:90]}")


def download_news() -> pd.DataFrame:
    """Downloads all the test news (like news.download) and returns the clean table (news.build_table).
    The raw pages go to RAW_NEWS/<NEWS_SET>_<TEST_START>_<TEST_END>/; if the download stops, the folder stays incomplete."""
    keys = load_keys()
    s, e = _bounds(TEST_START, TEST_END)
    out = RAW_NEWS / f"{NEWS_SET}_{TEST_START}_{TEST_END}"
    tmp = out.with_name(out.name + ".incomplete")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    token, page = None, 0
    while True:
        params = {"symbols": ",".join(tickers_of(NEWS_SET)), "start": s, "end": e, "limit": PAGE_LIMIT, "sort": "asc", "include_content": "false"}
        if token:
            params["page_token"] = token
        data = _get(params, keys)
        page += 1
        (tmp / f"page_{page:04d}.json").write_text(json.dumps(data, ensure_ascii=False))
        n = len(data.get("news", []))
        print(f"page {page}: {n} news items, up to {data['news'][-1]['created_at'] if n else '-'}")
        token = data.get("next_page_token")
        if not token:
            break
        time.sleep(PAUSE)
    if out.exists():
        shutil.rmtree(out)
    tmp.rename(out)
    table = build_table(NEWS_SET, TEST_START, TEST_END)
    assert table.ts.min() >= pd.Timestamp(TEST_START) and table.ts.max() < pd.Timestamp(TEST_END) + pd.Timedelta(days=1), "news outside the test"
    return table


def download_spy() -> pd.DataFrame:
    """SPY daily bars, adjusted for splits and dividends, as in spy.download."""
    keys = load_keys()
    params = {"timeframe": "1Day", "start": SPY_START, "end": TEST_END, "adjustment": "all", "feed": "sip", "limit": 10000}
    rows = []
    while True:
        req = urllib.request.Request(f"{SPY_URL}?{urllib.parse.urlencode(params)}", headers={
            "APCA-API-KEY-ID": keys["ALPACA_API_KEY_ID"], "APCA-API-SECRET-KEY": keys["ALPACA_API_SECRET_KEY"], "accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        rows += data.get("bars") or []
        if not data.get("next_page_token"):
            break
        params["page_token"] = data["next_page_token"]
    if not rows:
        raise RuntimeError("Alpaca returned no SPY bars")
    d = pd.DataFrame(rows)
    d["date"] = pd.to_datetime(d.t).dt.tz_convert(NY).dt.tz_localize(None).dt.normalize()
    return d.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})[["date", "open", "high", "low", "close", "volume"]]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--probe", action="store_true", help="a single test call, saving nothing")
    if ap.parse_args().probe:
        probe()
    else:
        news = download_news()
        save_table(news, NEWS_TEST)
        print(f"news: {len(news)} from {news.ts.min()} to {news.ts.max()} (New York time), saved in {NEWS_TEST.name}")
        spy = download_spy()
        SPY_TEST.parent.mkdir(parents=True, exist_ok=True)
        spy.to_parquet(SPY_TEST, index=False)
        print(f"SPY: {len(spy)} days, from {spy.date.min():%d/%m/%Y} to {spy.date.max():%d/%m/%Y}, saved in {SPY_TEST.name}")
