"""Dati Bloomberg del progetto: dai file grezzi ai dataset puliti in pandas, con i controlli di qualità.

Dal terminale, nella cartella del progetto:
    uv run python -m src.data      ricostruisce data/processed/ dai file di data/raw/ e stampa i controlli
In un notebook:
    from src.data import load
    daily = load("daily")          # oppure "intraday_1m", "sentiment"

Da sapere prima di usare i dati (emerso dai controlli):
- l'universo sono i titoli dell'indice di oggi: chi è entrato dopo il 2006 non ha la storia completa (survivorship bias)
- daily: PX_LAST è già aggiustato per split e dividendi; alcune serie hanno buchi di anni (es. FITB),
  quindi per i rendimenti va usata la colonna ret, calcolata solo tra giorni di borsa consecutivi
- intraday_1m: orari di New York, prezzi NON aggiustati (gli split compaiono come gap: APH, CRWD, DD, MNST);
  il volume è solo una parte di PX_VOLUME, in quota diversa per borsa
- sentiment: copertura crescente, da circa il 10% dei giorni nel 2007 a circa il 60% dal 2022
"""
import datetime

import duckdb
import numpy as np
import pandas as pd

from src.config import PROCESSED, RAW

# Tetto alla memoria di duckdb: oltre, ordina appoggiandosi al disco (dentro data/) invece di occupare altra RAM.
# Con 2 GB il passo più pesante resta intorno ai 4 GB di picco invece di superare i 5.
MEMORY_LIMIT = "2GB"
TEMP_DIR = PROCESSED / ".duckdb_tmp"


def _connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{MEMORY_LIMIT}'")
    con.execute(f"SET temp_directory='{TEMP_DIR.as_posix()}'")
    return con

# il nome del file grezzo è il ticker Bloomberg: AAPL_UW_Equity.parquet -> "AAPL UW Equity"
TICKER_FROM_FILENAME = r"replace(regexp_extract(filename, '([^/\\]+)\.parquet$', 1), '_', ' ')"

# per ogni cartella di data/raw: espressioni SQL per ticker e timestamp, colonne da tenere, se togliere i duplicati
DATASETS = {
    # i minuti grezzi sono in UTC: li porto all'ora di New York (apertura 09:30, ora legale gestita)
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
    # il ticker è già una colonna; i file *_2023_2023 ripetono righe già presenti in *_2006_2026
    "sentiment": dict(
        ticker="ticker",
        ts="date",
        cols="* EXCLUDE (ticker, date, filename)",
        dedup=True,
    ),
}

# valore che Bloomberg scrive nel sentiment al posto di un dato non disponibile
SENTINEL = -134217.7


def build_processed() -> None:
    """Unisce i file grezzi di ogni cartella in data/processed/<nome>_all.parquet.

    Il timestamp diventa due colonne, date e time (sempre 00:00:00 per daily e sentiment).
    """
    PROCESSED.mkdir(parents=True, exist_ok=True)
    con = _connect()
    # scrittura in parallelo con meno memoria: i blocchi del file escono in ordine sparso, load() riordina
    con.execute("SET preserve_insertion_order=false")
    for name, cfg in DATASETS.items():
        out = PROCESSED / f"{name}_all.parquet"
        distinct = "DISTINCT ON (ticker, date, time)" if cfg["dedup"] else ""
        # la subquery evita conflitti tra i nuovi nomi date/time e le colonne grezze omonime
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
        print(f"{out.name}: {rows:,} righe")
    con.close()


def load(name: str) -> pd.DataFrame:
    """Un dataset di data/processed ("intraday_1m", "daily" o "sentiment") in pandas, ordinato per ticker, date, time.

    ticker e time sono category: pochi valori ripetuti milioni di volte, molta meno memoria.
    sentiment: i segnaposto -134217.7 diventano NaN.
    daily: in più le colonne step (giorni di borsa dal record precedente dello stesso ticker:
    1 = giorno successivo, > 1 = buco nella serie) e ret (rendimento di PX_LAST, solo dove step è 1).
    """
    path = (PROCESSED / f"{name}_all.parquet").as_posix()
    con = _connect()
    # ticker e time diventano category già dentro duckdb (tipo ENUM). Convertendoli in pandas, .df() creerebbe prima un oggetto
    # Python per ogni riga: con i 13 milioni di righe dell'intraday sono circa 6 GB di picco per una tabella che ne occupa 0,8.
    con.execute(f"CREATE TYPE ticker_t AS ENUM (SELECT DISTINCT ticker FROM '{path}' ORDER BY ticker)")
    con.execute(f"CREATE TYPE time_t AS ENUM (SELECT DISTINCT CAST(time AS VARCHAR) FROM '{path}' ORDER BY 1)")
    df = con.execute(f"""
        SELECT * REPLACE (CAST(ticker AS ticker_t) AS ticker, CAST(CAST(time AS VARCHAR) AS time_t) AS time)
        FROM '{path}' ORDER BY ticker, date, time
    """).df()
    con.close()   # libera subito la copia dei dati che duckdb tiene per sé
    df["ticker"] = df["ticker"].cat.as_unordered().cat.rename_categories(pd.Index(df["ticker"].cat.categories.astype(object)).astype("str"))
    df["time"] = df["time"].cat.as_unordered().cat.rename_categories([datetime.time.fromisoformat(t) for t in df["time"].cat.categories])
    if name == "sentiment":
        num = df.select_dtypes("number").columns
        sentinel = df[num] == SENTINEL
        print(f"sentiment: {sentinel.sum().sum()} segnaposto {SENTINEL} convertiti in NaN")
        df[num] = df[num].mask(sentinel)
    if name == "daily":
        calendar = pd.DatetimeIndex(df["date"].unique()).sort_values()  # giorni in cui quota almeno un ticker
        df["step"] = pd.Series(calendar.get_indexer(df["date"]), index=df.index).groupby(df["ticker"], observed=True).diff()
        # attraverso un buco il "rendimento" sarebbe falso: FITB farebbe +367% dopo 9 anni senza dati
        df["ret"] = df.groupby("ticker", observed=True)["PX_LAST"].pct_change().where(df["step"] == 1)
    return df


def intraday_sessions(intraday: pd.DataFrame) -> pd.DataFrame:
    """Una riga per ticker e giorno: prima apertura, ultima chiusura, volume, numero di barre e gap overnight."""
    sessions = intraday.groupby(["ticker", "date"], observed=True).agg(
        open=("open", "first"), close=("close", "last"), volume=("volume", "sum"), bars=("close", "size"))
    # gap overnight: apertura del giorno contro chiusura della seduta precedente dello stesso ticker
    sessions["gap"] = sessions["open"] / sessions.groupby(level="ticker", observed=True)["close"].shift() - 1
    return sessions


def show(table: pd.DataFrame) -> None:
    """Stampa una tabella per intero: print(table) taglierebbe righe e colonne."""
    print(table.to_string())


def check_standard(name: str, df: pd.DataFrame) -> None:
    """Controlli di base: dimensioni, periodo, tipi, valori mancanti e distinti, duplicati, statistiche."""
    rows_per_ticker = df.groupby("ticker", observed=True).size()
    print(f"\n=== {name} ===")
    print(f"righe: {len(df):,} | colonne: {df.shape[1]} | memoria: {df.memory_usage(deep=True).sum() / 1e6:,.0f} MB")
    print(f"periodo: {df['date'].min().date()} → {df['date'].max().date()} | ticker: {df['ticker'].nunique()} "
          f"| righe per ticker: min {rows_per_ticker.min():,}, mediana {rows_per_ticker.median():,.0f}, max {rows_per_ticker.max():,}")
    show(df.head(3))
    show(pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "non_null": df.notna().sum(),
        "null_%": (df.isna().mean() * 100).round(2),
        "unici": df.nunique(),
    }))
    dup_keys = df.duplicated(["ticker", "date", "time"]).sum()
    # una riga duplicata ha per forza la chiave duplicata: senza chiavi duplicate il confronto su tutte le colonne
    # (il passo che usa più memoria, sull'intraday) non serve
    dup_rows = df.duplicated().sum() if dup_keys else 0
    print(f"righe duplicate: {dup_rows} | chiavi (ticker, date, time) duplicate: {dup_keys}")
    show(df.describe().T)


def check_intraday(intraday: pd.DataFrame, sessions: pd.DataFrame) -> None:
    """Barre da 1 minuto: prezzi incoerenti, completezza, ticker mancanti, salti estremi."""
    print("\n=== intraday_1m: controlli sui prezzi ===")
    show(pd.Series({
        "prezzi <= 0": (intraday[["open", "high", "low", "close"]] <= 0).any(axis=1).sum(),
        "volume <= 0": (intraday["volume"] <= 0).sum(),
        # high e low devono contenere open e close
        "high < max(open, close)": (intraday["high"] < np.maximum(intraday["open"], intraday["close"])).sum(),
        "low > min(open, close)": (intraday["low"] > np.minimum(intraday["open"], intraday["close"])).sum(),
        "high < low": (intraday["high"] < intraday["low"]).sum(),
        "barre fuori da 09:30-15:59": (~intraday["time"].isin(pd.date_range("09:30", "15:59", freq="min").time)).sum(),
    }, name="casi").to_frame())

    # la seduta completa ha 390 barre: un minuto senza scambi non produce una barra
    bars = sessions["bars"]
    print(f"barre per ticker-giorno: mediana {bars.median():.0f} su 390, giornate complete {(bars == 390).mean():.1%}")

    # un calo improvviso dei ticker presenti indica un buco nel download, non un evento di mercato
    n_ticker = sessions.groupby(level="date").size()
    print(f"ticker per giorno: mediana {n_ticker.median():.0f}; giorni con molti ticker mancanti:")
    show(n_ticker[n_ticker < 0.95 * n_ticker.median()].to_frame("ticker"))

    # rendimenti a 1 minuto dentro la stessa seduta, senza il salto overnight
    r1m = intraday.groupby(["ticker", "date"], observed=True)["close"].pct_change()
    extreme = r1m.abs() > 0.05
    print(f"rendimenti a 1 minuto oltre ±5%: {extreme.sum()}")
    show(intraday.loc[extreme, ["ticker", "date", "time", "open", "close", "volume"]].assign(rendimento=r1m[extreme]))

    print(f"gap overnight oltre ±15%: {(sessions['gap'].abs() > 0.15).sum()} | oltre ±40%: {(sessions['gap'].abs() > 0.4).sum()}")


def check_daily(daily: pd.DataFrame) -> None:
    """Prezzi giornalieri: valori mancanti, buchi nelle serie, storia per ticker, rendimenti estremi, dividendi."""
    print("\n=== daily: controlli sui prezzi ===")
    show(pd.Series({
        "PX_LAST mancante": daily["PX_LAST"].isna().sum(),
        "PX_LAST <= 0": (daily["PX_LAST"] <= 0).sum(),
        "PX_VOLUME <= 0": (daily["PX_VOLUME"] <= 0).sum(),
    }, name="casi").to_frame())
    print("PX_LAST mancante, ticker più colpiti:", daily.loc[daily["PX_LAST"].isna(), "ticker"].value_counts().head(5).to_dict())

    holes = daily[daily["step"] > 1].groupby("ticker", observed=True)["step"].agg(
        buchi="size", giorni_mancanti=lambda s: (s - 1).sum(), buco_max="max").astype(int)
    print(f"\nticker con buchi nella serie: {len(holes)}")
    show(holes.sort_values("giorni_mancanti", ascending=False))

    span = daily.groupby("ticker", observed=True)["date"].agg(["min", "max", "size"])
    first_day = daily["date"].min()
    print(f"ticker presenti dal primo giorno ({first_day.date()}): {(span['min'] == first_day).sum()} | entrati dopo: {(span['min'] > first_day).sum()}")
    print("ultimo giorno disponibile:", span["max"].dt.strftime("%Y-%m-%d").value_counts().to_dict())
    print("ticker con meno di un anno di storia (< 252 giorni):")
    show(span[span["size"] < 252])

    print(f"rendimenti giornalieri oltre ±40%: {(daily['ret'].abs() > 0.4).sum()}; i 10 più estremi:")
    show(daily.loc[daily["ret"].abs().nlargest(10).index, ["ticker", "date", "PX_LAST", "ret"]])

    # se PX_LAST non includesse i dividendi, nei giorni di stacco il total return renderebbe di più del prezzo
    r_tr = daily.groupby("ticker", observed=True)["TOT_RETURN_INDEX_GROSS_DVDS"].pct_change().where(daily["step"] == 1)
    both = daily["ret"].notna() & r_tr.notna()
    print(f"giorni con rendimento TOT_RETURN_INDEX = rendimento PX_LAST (±0,1%): {((r_tr - daily['ret']).abs() <= 0.001)[both].mean():.2%}")


def check_intraday_vs_daily(sessions: pd.DataFrame, daily: pd.DataFrame) -> None:
    """Confronto tra le due fonti di prezzo: split, aggiustamento per dividendi, volumi."""
    print("\n=== intraday vs daily ===")
    s = sessions.join(daily.set_index(["ticker", "date"])[["PX_LAST", "PX_VOLUME", "ret"]])

    # un gap enorme nell'intraday con rendimento daily quasi nullo è uno split: il daily è aggiustato, l'intraday no
    print("gap overnight oltre ±40% e rendimento daily dello stesso giorno:")
    show(s.loc[s["gap"].abs() > 0.4, ["gap", "ret"]])

    # se la differenza tra ultima chiusura intraday e PX_LAST cresce andando indietro, PX_LAST è aggiustato per i dividendi
    diff = (s["close"] / s["PX_LAST"] - 1).abs() * 100
    month = s.index.get_level_values("date").to_period("M").rename("mese")
    show(diff.groupby(month).median().round(3).to_frame("diff. mediana close vs PX_LAST (%)"))

    # quota del volume daily catturata dalle barre intraday, per borsa (UN = NYSE, UW = Nasdaq, UF = Cboe)
    share = s["volume"] / s["PX_VOLUME"]
    exchange = s.index.get_level_values("ticker").astype(str).str.split().str[1].rename("borsa")
    show(share.groupby(exchange).median().round(2).to_frame("volume intraday / PX_VOLUME (mediana)"))


if __name__ == "__main__":
    build_processed()
    # un dataset alla volta: tenerli tutti e tre in memoria insieme non serve a nessun controllo
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
