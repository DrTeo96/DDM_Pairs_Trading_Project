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
AGENT_RAW = RAW / "agent"                                                   # risposte grezze del modello (python -m src.varianti_agente.agent)
AGENT_DECISIONS = PROCESSED / "agent_decisions_15pairs_v2_train.csv"        # decisione dell'agente per ogni segnale
AGENT_MANUAL = PROCESSED / "agent_manual_15pairs_v2_train.csv"              # campione classificato a mano dal gruppo (python -m src.varianti_agente.agent --sample)

# Le versioni di risultati che il backtest confronta (06_backtest.ipynb). Ogni giro dell'agente ha la sua cartella in AGENT_RAW.
AGENT_RUN_DIR = AGENT_RAW / "spark-x2.6-4b"
RUN_24H = AGENT_RUN_DIR / "h24_diretto_anonimo/decisions.csv"               # finestra 24 ore, ragionamento spento: la versione principale
RUN_6H = AGENT_RUN_DIR / "h6_diretto_anonimo/decisions.csv"                 # finestra 6 ore, ragionamento spento
RUN_24H_REASONING = AGENT_RUN_DIR / "h24_ragiona_anonimo/accordo_segnali.csv"  # ragionamento acceso, solo sui 40 segnali del campione a mano
MANUAL_DECISIONS = AGENT_RUN_DIR / "h24_diretto_anonimo/accordo_segnali.csv"  # decisioni ricavate dalla classificazione a mano (colonne mano_*)
BASELINE_LEXICON = PROCESSED / "baseline_lexicon_decisions_15pairs_v2_train.csv"  # baseline senza modello: lessico Loughran-McDonald
RESULTS = ROOT / "Results"                                                  # tabelle e trade del backtest, su git
DAILY = PROCESSED / "daily_all.parquet"                                     # prezzi giornalieri (python -m src.data): calendario dei giorni di borsa
SPY_DAILY = PROCESSED / "spy_daily_train.parquet"                           # prezzi giornalieri di SPY da Alpaca (python -m src.spy)

# Le varianti dell'agente: codice in src/varianti_agente/, una cartella di risultati per variante in Results/varianti_agente/ (su git).
# Le decisioni stanno nella cartella della variante, così chi non ha fatto girare il modello rifà il backtest lo stesso.
VARIANTI = RESULTS / "varianti_agente"
AGENT_DECISIONS_COPY = VARIANTI / "spark_24h" / AGENT_DECISIONS.name       # copia su git delle decisioni dell'agente principale
FINBERT_SCORES = VARIANTI / "finbert_seduta/news_finbert.parquet"           # sentiment FinBERT di ogni notizia (score_finbert.py)
DEC_3B_6H = VARIANTI / "3b_6h/decisioni.csv"                                # Llama 3.2 3B, 6 ore, prompt completo (agent_3b.py)
DEC_FINBERT_SEDUTA = VARIANTI / "finbert_seduta/decisioni.csv"              # FinBERT, finestra legata alla seduta (agent_finbert.py)
DEC_C_FRESCA = VARIANTI / "c_fresca/decisioni.csv"                          # C solo su notizie fresche e forti (c_fresca.py)
DEC_FINBERT_EPISODIO = VARIANTI / "finbert_episodio/decisioni.csv"          # FinBERT, finestra dell'episodio (episodio.py)

# Il test: si usa una volta sola, per la variante scelta sul train (finbert_episodio), con le regole scritte in docs/Test.md.
# Gli script del test sono separati da quelli del train: test_dati.py, test_finbert.py, test_finale.py; i notebook 06_test_backtest e
# 07_test_robustezza leggono i risultati. Il test è stato fatto una volta, il 14 novembre 2026: non si rifà.
TEST_START = "2026-09-17"                                                   # primo giorno del test
TEST_END = "2026-10-30"                                                     # ultimo giorno con prezzi intraday
NEWS_TEST = PROCESSED / f"news_{NEWS_SET}_test.parquet"                     # notizie del test (python -m src.test_dati)
SPY_TEST = PROCESSED / "spy_daily_test.parquet"                             # SPY dal 16 settembre (serve la chiusura del giorno prima) a TEST_END
RESULTS_TEST = RESULTS / "test"                                             # risultati del test, su git
FINBERT_SCORES_TEST = RESULTS_TEST / "news_finbert_test.parquet"            # sentiment FinBERT delle notizie del test (python -m src.test_finbert)


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
