"""Percorsi, date e nomi dei file della pipeline: l'unico posto in cui sono scritti.

    from src.config import PROCESSED, TRAIN_END, read_parquet

I percorsi partono dalla posizione di questo file, non dalla cartella da cui si lancia il codice.
"""
import os
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
PROCESSED = ROOT / "data/processed"

# Taglio train/test, in date di calendario e uguale per tutte le coppie. Il test (dal 17 settembre) si usa una volta sola,
# alla fine, con regole e parametri bloccati: se un file di segnali, notizie o decisioni contiene giorni successivi,
# il backtest non vale più niente.
TRAIN_END = "2026-09-16"
# Le notizie partono due settimane prima dei prezzi intraday (16 giugno), perché l'agente guarda indietro dal segnale.
NEWS_START = "2026-06-01"

GICS = ROOT / "data/gics.csv"                                               # classificazione GICS, esportata da Bloomberg
SELECTED = PROCESSED / "selected_pairs_2.csv"                               # le 15 coppie (01_coppie.ipynb)
PAIRS_DIR = PROCESSED / "pairs_intraday_v2"                                 # prezzi puliti per coppia (02_intraday.ipynb)
SIGNALS = PROCESSED / "signals_15pairs_v2_train.csv"                        # segnali del train (03_segnali.ipynb)
NEWS_SET = "ALL15_V2"                                                       # i 30 titoli delle 15 coppie, scaricati insieme
NEWS = PROCESSED / f"news_{NEWS_SET}_train.parquet"                         # notizie (python -m src.news)
NEWS_FOR_SIGNALS = PROCESSED / "news_for_signals_15pairs_v2_train.csv"      # notizie prima di ogni segnale (04_notizie.ipynb)
AGENT_RAW = RAW / "agent"                                                   # risposte grezze del modello (python -m src.agent)
AGENT_DECISIONS = PROCESSED / "agent_decisions_15pairs_v2_train.csv"        # decisione dell'agente per ogni segnale


def env(name: str, default: str = "") -> str:
    """Una impostazione personale (chiave, indirizzo): dalle variabili d'ambiente, altrimenti dal file .env nella cartella
    del progetto (righe NOME=valore), che git ignora. Il valore non viene mai stampato."""
    if os.environ.get(name):
        return os.environ[name]
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == name:
                    return v.strip().strip('"').strip("'") or default
    return default


def read_parquet(path: Path) -> pd.DataFrame:
    """Un file parquet in pandas, letto con duckdb come in tutta la pipeline (stessi tipi delle colonne ovunque)."""
    return duckdb.sql(f"SELECT * FROM '{Path(path).as_posix()}'").df()
