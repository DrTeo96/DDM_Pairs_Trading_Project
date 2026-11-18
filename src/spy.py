"""SPY daily prices from Alpaca, for beta and alpha against the market in Step 7 (07_robustness.ipynb).

It uses the same Alpaca keys as the news (.env file, see .env.example). From the terminal, in the project folder:
    uv run python -m src.spy        downloads the SPY daily bars from NEWS_START to TRAIN_END and saves them in SPY_DAILY

Prices adjusted for splits and dividends (adjustment=all), so the daily return includes dividends, like the total return
of the Bloomberg stocks. The bars are the consolidated ones of all exchanges (sip feed). As for the news, the test (after
TRAIN_END) is not downloaded.
"""
import json
import urllib.parse
import urllib.request

import pandas as pd

from src.config import NEWS_START, SPY_DAILY, TRAIN_END
from src.news import load_keys

URL = "https://data.alpaca.markets/v2/stocks/SPY/bars"


def download(start: str = NEWS_START, end: str = TRAIN_END) -> pd.DataFrame:
    """SPY daily bars between two dates (included), one page at a time."""
    if pd.Timestamp(end) > pd.Timestamp(TRAIN_END):
        raise ValueError(f"{end} is after the end of the train ({TRAIN_END}): the test prices are not downloaded")
    keys = load_keys()
    params = {"timeframe": "1Day", "start": start, "end": end, "adjustment": "all", "feed": "sip", "limit": 10000}
    rows = []
    while True:
        req = urllib.request.Request(f"{URL}?{urllib.parse.urlencode(params)}", headers={
            "APCA-API-KEY-ID": keys["ALPACA_API_KEY_ID"], "APCA-API-SECRET-KEY": keys["ALPACA_API_SECRET_KEY"], "accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        rows += data.get("bars") or []
        if not data.get("next_page_token"):
            break
        params["page_token"] = data["next_page_token"]
    if not rows:
        raise RuntimeError("Alpaca returned no SPY bars: check that the keys have access to market data")
    d = pd.DataFrame(rows)
    # t is the start of the New York day expressed in UTC: the right date is the New York one
    d["date"] = pd.to_datetime(d.t).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    return d.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})[["date", "open", "high", "low", "close", "volume"]]


if __name__ == "__main__":
    spy = download()
    SPY_DAILY.parent.mkdir(parents=True, exist_ok=True)
    spy.to_parquet(SPY_DAILY, index=False)
    print(f"SPY: {len(spy)} days, from {spy.date.min():%d/%m/%Y} to {spy.date.max():%d/%m/%Y}, saved in {SPY_DAILY.name}")
