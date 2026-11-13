"""Prezzi giornalieri di SPY da Alpaca, per beta e alpha rispetto al mercato nel Passaggio 7 (07_robustezza.ipynb).

Usa le stesse chiavi di Alpaca delle notizie (file .env, vedi .env.example). Dal terminale, nella cartella del progetto:
    uv run python -m src.spy        scarica le barre giornaliere di SPY da NEWS_START a TRAIN_END e le salva in SPY_DAILY

Prezzi aggiustati per split e dividendi (adjustment=all), così il rendimento giornaliero comprende i dividendi, come il rendimento
totale dei titoli Bloomberg. Le barre sono quelle consolidate di tutte le borse (feed sip). Come per le notizie, il test (dopo
TRAIN_END) non si scarica.
"""
import json
import urllib.parse
import urllib.request

import pandas as pd

from src.config import NEWS_START, SPY_DAILY, TRAIN_END
from src.news import load_keys

URL = "https://data.alpaca.markets/v2/stocks/SPY/bars"


def download(start: str = NEWS_START, end: str = TRAIN_END) -> pd.DataFrame:
    """Barre giornaliere di SPY tra due date (comprese), una pagina alla volta."""
    if pd.Timestamp(end) > pd.Timestamp(TRAIN_END):
        raise ValueError(f"{end} è dopo la fine del train ({TRAIN_END}): i prezzi del test non si scaricano")
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
        raise RuntimeError("Alpaca non ha restituito barre di SPY: controlla che le chiavi abbiano accesso ai dati di mercato")
    d = pd.DataFrame(rows)
    # t è l'inizio della giornata di New York espresso in UTC: la data giusta è quella di New York
    d["date"] = pd.to_datetime(d.t).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    return d.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})[["date", "open", "high", "low", "close", "volume"]]


if __name__ == "__main__":
    spy = download()
    SPY_DAILY.parent.mkdir(parents=True, exist_ok=True)
    spy.to_parquet(SPY_DAILY, index=False)
    print(f"SPY: {len(spy)} giorni, dal {spy.date.min():%d/%m/%Y} al {spy.date.max():%d/%m/%Y}, salvato in {SPY_DAILY.name}")
