"""Alpaca news (Benzinga source): download, local archive, clean table and news before each signal.

It needs the Alpaca keys in the .env file in the project folder (see .env.example) and the list of pairs
(src/01_pairs.ipynb), which gives the list of stocks. From the terminal, in the project folder:
    uv run python -m src.news --probe    a single test call: says whether the keys work, saves nothing
    uv run python -m src.news            downloads the news of the 30 stocks up to TRAIN_END and builds the clean table
In a notebook:
    from src.news import load_news
    news = load_news()

The table has one row per news item:
- ts: publication time (created_at) in New York time, without time zone, like the prices
- updated_at_ny: last update. Not to be used to decide whether a news item was known: it can be much later (lookahead)
- headline, summary, source, url, author
- symbols (all the tickers linked to the news item), n_symbols, mentions_<ticker> for each stock of the pairs
"""
import argparse
import json
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import duckdb
import pandas as pd

from src.config import NEWS_SET, NEWS_START, PROCESSED, RAW, SELECTED, TRAIN_END, env, read_parquet

RAW_NEWS = RAW / "news/alpaca"   # raw answers, one page per file: the archive from which the table can always be rebuilt

URL = "https://data.alpaca.markets/v1beta1/news"
PAGE_LIMIT = 50                  # maximum allowed by Alpaca per page
PAUSE = 0.4                      # seconds between two calls: the free plan allows 200 per minute, this way they are at most 150
MAX_RETRIES = 5
NY = "America/New_York"
MAX_SYMBOLS_FOCUSED = 3          # a news item is "targeted" if it tags at most 3 tickers; the others are generic lists


def tickers_of(name: str = NEWS_SET) -> list[str]:
    """The Alpaca tickers of NEWS_SET (the stocks of all the pairs) or of a single pair, for example "KO-PEP".
    The Alpaca ticker is the first word of the Bloomberg ticker (MA UN Equity -> MA)."""
    if not SELECTED.exists():
        raise FileNotFoundError(f"{SELECTED.name} is missing: the list of stocks comes from the list of pairs, run src/01_pairs.ipynb first")
    pairs = {r.pair: [r.A.split()[0], r.B.split()[0]] for r in pd.read_csv(SELECTED).itertuples()}
    if name == NEWS_SET:
        return sorted({t for ts in pairs.values() for t in ts})
    if name not in pairs:
        raise ValueError(f"{name} is neither {NEWS_SET} nor one of the pairs: {', '.join(pairs)}")
    return pairs[name]


def load_keys() -> dict:
    """The Alpaca keys, from .env or from the environment variables."""
    keys = {k: env(k) for k in ("ALPACA_API_KEY_ID", "ALPACA_API_SECRET_KEY")}
    missing = [k for k, v in keys.items() if not v]
    if missing:
        raise RuntimeError(f"{', '.join(missing)} missing: copy .env.example to .env and fill in the Alpaca keys")
    return keys


def _get(params: dict, keys: dict) -> dict:
    """One API call, with new attempts if the call limit is exceeded (429) or the server is in error (5xx)."""
    req = urllib.request.Request(f"{URL}?{urllib.parse.urlencode(params)}", headers={
        "APCA-API-KEY-ID": keys["ALPACA_API_KEY_ID"], "APCA-API-SECRET-KEY": keys["ALPACA_API_SECRET_KEY"], "accept": "application/json"})
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES - 1:
                time.sleep(5 * (attempt + 1))
                continue
            body = e.read().decode(errors="replace")[:300]
            hint = {401: " (invalid keys)", 403: " (the plan does not allow this request)", 422: " (invalid parameters)"}.get(e.code, "")
            raise RuntimeError(f"Alpaca answered {e.code}{hint}: {body}") from None
    raise RuntimeError("too many attempts")


def _bounds(start: str, end: str) -> tuple[str, str]:
    """From two dates to two UTC instants: from New York midnight of `start` to New York midnight after `end`."""
    if pd.Timestamp(end) > pd.Timestamp(TRAIN_END):
        raise ValueError(f"{end} is after the end of the train ({TRAIN_END}): the test news are not downloaded")
    s = pd.Timestamp(start).tz_localize(NY).tz_convert("UTC")
    e = (pd.Timestamp(end) + pd.Timedelta(days=1)).tz_localize(NY).tz_convert("UTC")
    return s.strftime("%Y-%m-%dT%H:%M:%SZ"), e.strftime("%Y-%m-%dT%H:%M:%SZ")


def probe(pair: str = NEWS_SET, start: str = NEWS_START, end: str = TRAIN_END) -> None:
    """A single call with 5 news items, to check keys and access to the history before downloading everything."""
    keys = load_keys()
    s, e = _bounds(start, end)
    data = _get({"symbols": ",".join(tickers_of(pair)), "start": s, "end": e, "limit": 5, "sort": "asc"}, keys)
    items = data.get("news", [])
    print(f"Keys accepted. Period {start} - {end}: {len(items)} news items in the first test page (next page: {'yes' if data.get('next_page_token') else 'no'}).")
    for n in items:
        print(f"  {n['created_at']}  [{','.join(n.get('symbols', []))}]  {n['headline'][:90]}")
    if not items:
        print("No news: the history of the period may not be accessible with your plan, or there are no news on these tickers.")


def download(pair: str = NEWS_SET, start: str = NEWS_START, end: str = TRAIN_END, include_content: bool = False) -> int:
    """Downloads all the news of the stocks in the period, in chronological order, and saves every raw page. Returns the number of pages.

    The pages go to a temporary folder that replaces the archive only when the download is finished:
    if it stops halfway, the previous archive stays whole."""
    keys = load_keys()
    s, e = _bounds(start, end)
    symbols = ",".join(tickers_of(pair))
    out = RAW_NEWS / f"{pair}_{start}_{end}"
    tmp = out.with_name(out.name + ".incomplete")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    token, page = None, 0
    while True:
        params = {"symbols": symbols, "start": s, "end": e, "limit": PAGE_LIMIT, "sort": "asc", "include_content": str(include_content).lower()}
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
    return page


def build_table(pair: str = NEWS_SET, start: str = NEWS_START, end: str = TRAIN_END) -> pd.DataFrame:
    """From the raw pages to the clean table: New York times, one row per news item, sorted by time."""
    rows = []
    for f in sorted((RAW_NEWS / f"{pair}_{start}_{end}").glob("page_*.json")):
        rows += json.loads(f.read_text()).get("news", [])
    if not rows:
        raise RuntimeError("no news in the raw files: run the download first")
    df = pd.DataFrame(rows)
    to_ny = lambda col: pd.to_datetime(df[col], utc=True).dt.tz_convert(NY).dt.tz_localize(None)
    out = pd.DataFrame({
        "id": df["id"], "ts": to_ny("created_at"), "updated_at_ny": to_ny("updated_at"),
        "headline": df["headline"].str.strip(), "summary": df["summary"].fillna("").str.strip(), "source": df["source"], "author": df["author"], "url": df["url"],
        "symbols": df["symbols"].apply(lambda s: ",".join(s)), "n_symbols": df["symbols"].apply(len),
    })
    for t in tickers_of(pair):
        out[f"mentions_{t}"] = df["symbols"].apply(lambda s: t in s)
    out = out.drop_duplicates("id").sort_values(["ts", "id"]).reset_index(drop=True)
    return out


def save_table(table: pd.DataFrame, path: Path) -> None:
    """Saves to parquet with duckdb, like the other files of the pipeline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    duckdb.register("table_to_save", table)
    duckdb.sql(f"COPY table_to_save TO '{path.as_posix()}' (FORMAT parquet)")


def load_news(pair: str = NEWS_SET) -> pd.DataFrame:
    """Reads the clean table built by `python -m src.news`."""
    path = PROCESSED / f"news_{pair}_train.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path.name} does not exist: from the project folder run `uv run python -m src.news`")
    return read_parquet(path)


def news_before_signals(signals: pd.DataFrame, news: pd.DataFrame, hours: int = 24) -> pd.DataFrame:
    """For each signal, the news published in the `hours` hours before that tag one of the two stocks of the pair:
    one row per (signal, news item). Signals without news do not appear.

    Only news with ts <= t_signal are kept (publication time, never updated_at_ny): this is the filter
    that prevents the agent from reading a news item published after the signal."""
    news = news.sort_values("ts").reset_index(drop=True)
    focused = news.n_symbols <= MAX_SYMBOLS_FOCUSED
    rows = []
    for _, s in signals.iterrows():
        mA, mB = news[f"mentions_{s.ticker_A}"], news[f"mentions_{s.ticker_B}"]
        w = news[(mA | mB) & (news.ts <= s.t_signal) & (news.ts > s.t_signal - pd.Timedelta(hours=hours))]
        for i, n in w.iterrows():
            rows.append(dict(signal_id=s.signal_id, pair=s.pair, t_signal=s.t_signal, direction=s.direction, most_moved_leg=s.most_moved_leg, news_id=n.id, news_ts=n.ts,
                             minutes_before=(s.t_signal - n.ts).total_seconds() / 60, headline=n.headline, summary=n.summary, source=n.source, symbols=n.symbols,
                             n_symbols=n.n_symbols, focused=bool(focused[i]), mentions_A=bool(mA[i]), mentions_B=bool(mB[i]), url=n.url))
    link = pd.DataFrame(rows)
    assert (link.news_ts <= link.t_signal).all(), "a news item comes after the signal"
    return link


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pair", default=NEWS_SET, help=f"{NEWS_SET} (all the stocks, default) or a single pair, for example KO-PEP")
    ap.add_argument("--start", default=NEWS_START)
    ap.add_argument("--end", default=TRAIN_END)
    ap.add_argument("--probe", action="store_true", help="a single test call, saving nothing")
    ap.add_argument("--content", action="store_true", help="also download the full text of the articles (much heavier)")
    a = ap.parse_args()
    if a.probe:
        probe(a.pair, a.start, a.end)
    else:
        pages = download(a.pair, a.start, a.end, a.content)
        table = build_table(a.pair, a.start, a.end)
        save_table(table, PROCESSED / f"news_{a.pair}_train.parquet")
        print(f"\n{pages} pages, {len(table)} unique news items from {table.ts.min()} to {table.ts.max()} (New York time)")
        print(f"saved data/processed/news_{a.pair}_train.parquet")
