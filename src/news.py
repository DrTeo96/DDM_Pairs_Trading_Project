"""Notizie di Alpaca (fonte Benzinga): scaricamento, archivio locale e tabella pulita. Passaggio 3 del programma.

Servono solo pandas e duckdb (già nell'ambiente): le richieste usano la libreria standard.
Prima di usarlo servono le chiavi API di Alpaca nel file .env nella cartella del progetto (vedi .env.example).
Dal terminale, nella cartella del progetto:
    python -m src.news --probe      una sola chiamata di prova: dice se le chiavi funzionano e se lo storico del periodo è accessibile
    python -m src.news              scarica MA-V dal 1 giugno al 16 settembre 2026 in data/raw/news/alpaca/ e crea data/processed/news_MA-V_train.parquet
    python -m src.news --pair ALL10     scarica i 20 titoli delle 10 coppie insieme e crea data/processed/news_ALL10_train.parquet
                                        (una colonna mentions_<ticker> per ogni titolo; una notizia con più ticker compare una volta sola)
    python -m src.news --pair ALL15_V2  come ALL10, per i 30 titoli delle 15 coppie della versione 2 (news_ALL15_V2_train.parquet)
In un notebook dentro src/:
    from news import load_news
    news = load_news("MA-V")

Cosa contiene la tabella (una riga per notizia):
- ts: orario di pubblicazione (created_at) in ora di New York, senza indicazione del fuso, come i prezzi
- updated_at_ny: ultimo aggiornamento. NON va usato per decidere se una notizia era nota: può essere molto più tardi (lookahead)
- headline, summary, source, url, author
- symbols (tutti i ticker associati alla notizia), n_symbols, mentions_<ticker> per i titoli della coppia
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_NEWS = ROOT / "data/raw/news/alpaca"          # risposte grezze, una pagina per file (la cartella data/ è ignorata da git)
PROCESSED = ROOT / "data/processed"

URL = "https://data.alpaca.markets/v1beta1/news"
PAGE_LIMIT = 50                  # massimo consentito da Alpaca per pagina
PAUSE = 0.4                      # secondi tra due chiamate: il piano gratuito ha 200 chiamate al minuto, qui ne facciamo al massimo 150
MAX_RETRIES = 5
NY = "America/New_York"

# coppie e periodo: stessi del Passaggio 4. Si parte il 1 giugno (2 settimane prima del 16 giugno) perché l'agente guarda indietro dal segnale
PAIRS = {"MA-V": ["MA", "V"]}


def _add_selected_pairs() -> None:
    """Aggiunge le 10 coppie del Passaggio 1 (da selected_pairs.csv) e ALL10, i 20 titoli insieme: `python -m src.news --pair ALL10`.
    Il ticker di Alpaca è la prima parola del ticker Bloomberg (MA UN Equity -> MA)."""
    f = PROCESSED / "selected_pairs.csv"
    if not f.exists():
        return
    sel = pd.read_csv(f)
    for _, r in sel.iterrows():
        PAIRS[r["pair"]] = [r["A"].split()[0], r["B"].split()[0]]
    PAIRS["ALL10"] = sorted({t for ts in PAIRS.values() for t in ts})
    # versione 2 (15 coppie, selected_pairs_2.csv): ALL15_V2 sono i 30 titoli insieme, `python -m src.news --pair ALL15_V2`.
    # ALL10 resta calcolato sopra, quindi la versione 1 non cambia.
    f2 = PROCESSED / "selected_pairs_2.csv"
    if f2.exists():
        v2 = {r["pair"]: [r["A"].split()[0], r["B"].split()[0]] for _, r in pd.read_csv(f2).iterrows()}
        PAIRS.update(v2)
        PAIRS["ALL15_V2"] = sorted({t for ts in v2.values() for t in ts})


_add_selected_pairs()
DEFAULT_START = "2026-06-01"
DEFAULT_END = "2026-09-16"        # ultimo giorno del train, incluso: il test (dal 17 settembre) non si scarica


def load_keys() -> dict:
    """Legge le chiavi da .env (righe CHIAVE=valore) o dalle variabili d'ambiente. Non le stampa mai."""
    keys = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                keys[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("ALPACA_API_KEY_ID", "ALPACA_API_SECRET_KEY"):
        keys[k] = os.environ.get(k, keys.get(k, ""))
    missing = [k for k in ("ALPACA_API_KEY_ID", "ALPACA_API_SECRET_KEY") if not keys[k]]
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
    s = pd.Timestamp(start).tz_localize(NY).tz_convert("UTC")
    e = (pd.Timestamp(end) + pd.Timedelta(days=1)).tz_localize(NY).tz_convert("UTC")
    return s.strftime("%Y-%m-%dT%H:%M:%SZ"), e.strftime("%Y-%m-%dT%H:%M:%SZ")


def probe(pair: str = "MA-V", start: str = DEFAULT_START, end: str = DEFAULT_END) -> None:
    """Una sola chiamata con 5 notizie, per controllare chiavi e accesso allo storico prima di scaricare tutto."""
    keys = load_keys()
    s, e = _bounds(start, end)
    data = _get({"symbols": ",".join(PAIRS[pair]), "start": s, "end": e, "limit": 5, "sort": "asc"}, keys)
    items = data.get("news", [])
    print(f"Chiavi accettate. Periodo {start} - {end}: {len(items)} notizie nella prima pagina di prova (pagina successiva: {'sì' if data.get('next_page_token') else 'no'}).")
    for n in items:
        print(f"  {n['created_at']}  [{','.join(n.get('symbols', []))}]  {n['headline'][:90]}")
    if not items:
        print("Nessuna notizia: lo storico del periodo potrebbe non essere accessibile col tuo piano, oppure non ci sono notizie su questi ticker.")


def download(pair: str = "MA-V", start: str = DEFAULT_START, end: str = DEFAULT_END, include_content: bool = False) -> int:
    """Scarica tutte le notizie dei titoli della coppia nel periodo, in ordine cronologico, e salva ogni pagina grezza. Restituisce il numero di pagine."""
    keys = load_keys()
    s, e = _bounds(start, end)
    out = RAW_NEWS / f"{pair}_{start}_{end}"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("page_*.json"):       # si riparte sempre da zero, per non mescolare scaricamenti diversi
        old.unlink()
    token, page = None, 0
    while True:
        params = {"symbols": ",".join(PAIRS[pair]), "start": s, "end": e, "limit": PAGE_LIMIT, "sort": "asc", "include_content": str(include_content).lower()}
        if token:
            params["page_token"] = token
        data = _get(params, keys)
        page += 1
        (out / f"page_{page:04d}.json").write_text(json.dumps(data, ensure_ascii=False))
        n = len(data.get("news", []))
        print(f"pagina {page}: {n} notizie, fino a {data['news'][-1]['created_at'] if n else '-'}")
        token = data.get("next_page_token")
        if not token:
            break
        time.sleep(PAUSE)
    return page


def build_table(pair: str = "MA-V", start: str = DEFAULT_START, end: str = DEFAULT_END) -> pd.DataFrame:
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
    for t in PAIRS[pair]:
        out[f"mentions_{t}"] = df["symbols"].apply(lambda s: t in s)
    out = out.drop_duplicates("id").sort_values(["ts", "id"]).reset_index(drop=True)
    return out


def save_table(table: pd.DataFrame, path: Path) -> None:
    """Salva in parquet con duckdb (pandas da solo non scrive parquet nel nostro ambiente: manca pyarrow)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    duckdb.register("table_to_save", table)
    duckdb.sql(f"COPY table_to_save TO '{path.as_posix()}' (FORMAT parquet)")


def load_news(pair: str = "MA-V") -> pd.DataFrame:
    """Legge la tabella pulita creata da `python -m src.news`."""
    path = PROCESSED / f"news_{pair}_train.parquet"
    if not path.exists():
        raise FileNotFoundError(f"{path.name} non esiste: dalla cartella del progetto esegui `uv run python -m src.news`")
    return duckdb.sql(f"SELECT * FROM '{path.as_posix()}'").df()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pair", default="MA-V")
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--end", default=DEFAULT_END)
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
