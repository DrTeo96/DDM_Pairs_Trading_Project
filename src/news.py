"""Notizie di Alpaca (fonte Benzinga): scaricamento, archivio locale, tabella pulita e notizie prima di ogni segnale.

Servono le chiavi di Alpaca nel file .env nella cartella del progetto (vedi .env.example) e la lista delle coppie
(src/01_coppie.ipynb), da cui viene l'elenco dei titoli. Dal terminale, nella cartella del progetto:
    uv run python -m src.news --probe    una sola chiamata di prova: dice se le chiavi funzionano, non salva niente
    uv run python -m src.news            scarica le notizie dei 30 titoli fino a TRAIN_END e crea la tabella pulita
In un notebook:
    from src.news import load_news
    news = load_news()

La tabella ha una riga per notizia:
- ts: orario di pubblicazione (created_at) in ora di New York, senza indicazione del fuso, come i prezzi
- updated_at_ny: ultimo aggiornamento. Non va usato per decidere se una notizia era nota: può essere molto più tardi (lookahead)
- headline, summary, source, url, author
- symbols (tutti i ticker associati alla notizia), n_symbols, mentions_<ticker> per ogni titolo delle coppie
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

RAW_NEWS = RAW / "news/alpaca"   # risposte grezze, una pagina per file: l'archivio da cui la tabella si può sempre ricostruire

URL = "https://data.alpaca.markets/v1beta1/news"
PAGE_LIMIT = 50                  # massimo consentito da Alpaca per pagina
PAUSE = 0.4                      # secondi tra due chiamate: il piano gratuito ne consente 200 al minuto, così sono al massimo 150
MAX_RETRIES = 5
NY = "America/New_York"
MAX_SYMBOLS_FOCUSED = 3          # una notizia è "mirata" se cita al massimo 3 ticker; le altre sono elenchi generici


def tickers_of(name: str = NEWS_SET) -> list[str]:
    """I ticker di Alpaca di NEWS_SET (i titoli di tutte le coppie) o di una coppia sola, per esempio "KO-PEP".
    Il ticker di Alpaca è la prima parola del ticker Bloomberg (MA UN Equity -> MA)."""
    if not SELECTED.exists():
        raise FileNotFoundError(f"manca {SELECTED.name}: l'elenco dei titoli viene dalla lista delle coppie, esegui prima src/01_coppie.ipynb")
    pairs = {r.pair: [r.A.split()[0], r.B.split()[0]] for r in pd.read_csv(SELECTED).itertuples()}
    if name == NEWS_SET:
        return sorted({t for ts in pairs.values() for t in ts})
    if name not in pairs:
        raise ValueError(f"{name} non è {NEWS_SET} né una delle coppie: {', '.join(pairs)}")
    return pairs[name]


def load_keys() -> dict:
    """Le chiavi di Alpaca, da .env o dalle variabili d'ambiente."""
    keys = {k: env(k) for k in ("ALPACA_API_KEY_ID", "ALPACA_API_SECRET_KEY")}
    missing = [k for k, v in keys.items() if not v]
    if missing:
        raise RuntimeError(f"Mancano {', '.join(missing)}: copia .env.example in .env e inserisci le chiavi di Alpaca")
    return keys


def _get(params: dict, keys: dict) -> dict:
    """Una chiamata all'API, con nuovi tentativi se il limite di chiamate è superato (429) o il server è in errore (5xx)."""
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
            hint = {401: " (chiavi non valide)", 403: " (il piano non permette questa richiesta)", 422: " (parametri non validi)"}.get(e.code, "")
            raise RuntimeError(f"Alpaca ha risposto {e.code}{hint}: {body}") from None
    raise RuntimeError("troppi tentativi")


def _bounds(start: str, end: str) -> tuple[str, str]:
    """Da due date a due istanti in UTC: dalla mezzanotte di New York di `start` alla mezzanotte di New York dopo `end`."""
    if pd.Timestamp(end) > pd.Timestamp(TRAIN_END):
        raise ValueError(f"{end} è dopo la fine del train ({TRAIN_END}): le notizie del test non si scaricano")
    s = pd.Timestamp(start).tz_localize(NY).tz_convert("UTC")
    e = (pd.Timestamp(end) + pd.Timedelta(days=1)).tz_localize(NY).tz_convert("UTC")
    return s.strftime("%Y-%m-%dT%H:%M:%SZ"), e.strftime("%Y-%m-%dT%H:%M:%SZ")


def probe(pair: str = NEWS_SET, start: str = NEWS_START, end: str = TRAIN_END) -> None:
    """Una sola chiamata con 5 notizie, per controllare chiavi e accesso allo storico prima di scaricare tutto."""
    keys = load_keys()
    s, e = _bounds(start, end)
    data = _get({"symbols": ",".join(tickers_of(pair)), "start": s, "end": e, "limit": 5, "sort": "asc"}, keys)
    items = data.get("news", [])
    print(f"Chiavi accettate. Periodo {start} - {end}: {len(items)} notizie nella prima pagina di prova (pagina successiva: {'sì' if data.get('next_page_token') else 'no'}).")
    for n in items:
        print(f"  {n['created_at']}  [{','.join(n.get('symbols', []))}]  {n['headline'][:90]}")
    if not items:
        print("Nessuna notizia: lo storico del periodo potrebbe non essere accessibile col tuo piano, oppure non ci sono notizie su questi ticker.")


def download(pair: str = NEWS_SET, start: str = NEWS_START, end: str = TRAIN_END, include_content: bool = False) -> int:
    """Scarica tutte le notizie dei titoli nel periodo, in ordine cronologico, e salva ogni pagina grezza. Restituisce il numero di pagine.

    Le pagine vanno in una cartella provvisoria che sostituisce l'archivio solo a scaricamento finito:
    se si interrompe a metà, l'archivio di prima resta intero."""
    keys = load_keys()
    s, e = _bounds(start, end)
    symbols = ",".join(tickers_of(pair))
    out = RAW_NEWS / f"{pair}_{start}_{end}"
    tmp = out.with_name(out.name + ".incompleto")
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
        print(f"pagina {page}: {n} notizie, fino a {data['news'][-1]['created_at'] if n else '-'}")
        token = data.get("next_page_token")
        if not token:
            break
        time.sleep(PAUSE)
    if out.exists():
        shutil.rmtree(out)
    tmp.rename(out)
    return page


def build_table(pair: str = NEWS_SET, start: str = NEWS_START, end: str = TRAIN_END) -> pd.DataFrame:
    """Dalle pagine grezze alla tabella pulita: orari in ora di New York, una riga per notizia, ordinata per orario."""
    rows = []
    for f in sorted((RAW_NEWS / f"{pair}_{start}_{end}").glob("page_*.json")):
        rows += json.loads(f.read_text()).get("news", [])
    if not rows:
        raise RuntimeError("nessuna notizia nei file grezzi: esegui prima il download")
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
    """Salva in parquet con duckdb, come gli altri file della pipeline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    duckdb.register("table_to_save", table)
    duckdb.sql(f"COPY table_to_save TO '{path.as_posix()}' (FORMAT parquet)")


def load_news(pair: str = NEWS_SET) -> pd.DataFrame:
    """Legge la tabella pulita creata da `python -m src.news`."""
    path = PROCESSED / f"news_{pair}_train.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path.name} non esiste: dalla cartella del progetto esegui `uv run python -m src.news`")
    return read_parquet(path)


def news_before_signals(signals: pd.DataFrame, news: pd.DataFrame, hours: int = 24) -> pd.DataFrame:
    """Per ogni segnale, le notizie uscite nelle `hours` ore prima che citano uno dei due titoli della coppia:
    una riga per (segnale, notizia). I segnali senza notizie non compaiono.

    Si tengono solo le notizie con ts <= t_signal (orario di pubblicazione, mai updated_at_ny): è il filtro
    che impedisce all'agente di leggere una notizia uscita dopo il segnale."""
    news = news.sort_values("ts").reset_index(drop=True)
    focused = news.n_symbols <= MAX_SYMBOLS_FOCUSED
    rows = []
    for _, s in signals.iterrows():
        mA, mB = news[f"mentions_{s.ticker_A}"], news[f"mentions_{s.ticker_B}"]
        w = news[(mA | mB) & (news.ts <= s.t_signal) & (news.ts > s.t_signal - pd.Timedelta(hours=hours))]
        for i, n in w.iterrows():
            rows.append(dict(signal_id=s.signal_id, pair=s.pair, t_signal=s.t_signal, direction=s.direction, leg_piu_mosso=s.leg_piu_mosso, news_id=n.id, news_ts=n.ts,
                             minutes_before=(s.t_signal - n.ts).total_seconds() / 60, headline=n.headline, summary=n.summary, source=n.source, symbols=n.symbols,
                             n_symbols=n.n_symbols, focused=bool(focused[i]), mentions_A=bool(mA[i]), mentions_B=bool(mB[i]), url=n.url))
    link = pd.DataFrame(rows)
    assert (link.news_ts <= link.t_signal).all(), "una notizia è successiva al segnale"
    return link


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pair", default=NEWS_SET, help=f"{NEWS_SET} (tutti i titoli, default) oppure una coppia sola, per esempio KO-PEP")
    ap.add_argument("--start", default=NEWS_START)
    ap.add_argument("--end", default=TRAIN_END)
    ap.add_argument("--probe", action="store_true", help="una sola chiamata di prova, senza salvare nulla")
    ap.add_argument("--content", action="store_true", help="scarica anche il testo completo degli articoli (molto più pesante)")
    a = ap.parse_args()
    if a.probe:
        probe(a.pair, a.start, a.end)
    else:
        pages = download(a.pair, a.start, a.end, a.content)
        table = build_table(a.pair, a.start, a.end)
        save_table(table, PROCESSED / f"news_{a.pair}_train.parquet")
        print(f"\n{pages} pagine, {len(table)} notizie uniche dal {table.ts.min()} al {table.ts.max()} (ora di New York)")
        print(f"salvato data/processed/news_{a.pair}_train.parquet")
