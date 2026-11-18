"""Paths, dates and file names of the pipeline: the only place where they are written.

    from src.config import PROCESSED, TRAIN_END, read_parquet

Paths start from the location of this file, not from the folder the code is launched from.
"""
import os
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
PROCESSED = ROOT / "data/processed"

# Train/test split, in calendar dates and the same for every pair. The test (from 17 September) is used only once,
# at the end, with frozen rules and parameters: if a file of signals, news or decisions contains later days,
# the backtest is worthless.
TRAIN_END = "2026-09-16"
# News start two weeks before the intraday prices (16 June), because the agent looks back from the signal.
NEWS_START = "2026-06-01"

GICS = ROOT / "data/gics.csv"                                               # GICS classification, exported from Bloomberg (names in Italian)
SELECTED = PROCESSED / "selected_pairs_2.csv"                               # the 15 pairs (01_pairs.ipynb)
PAIRS_DIR = PROCESSED / "pairs_intraday_v2"                                 # clean prices per pair (02_intraday.ipynb)
SIGNALS = PROCESSED / "signals_15pairs_v2_train.csv"                        # train signals (03_signals.ipynb)
NEWS_SET = "ALL15_V2"                                                       # the 30 stocks of the 15 pairs, downloaded together
NEWS = PROCESSED / f"news_{NEWS_SET}_train.parquet"                         # news (python -m src.news)
NEWS_FOR_SIGNALS = PROCESSED / "news_for_signals_15pairs_v2_train.csv"      # news before each signal (04_news.ipynb)
AGENT_RAW = RAW / "agent"                                                   # raw model answers (python -m src.agent_variants.agent)
AGENT_DECISIONS = PROCESSED / "agent_decisions_15pairs_v2_train.csv"        # the agent's decision for each signal
AGENT_MANUAL = PROCESSED / "agent_manual_15pairs_v2_train.csv"              # sample classified by hand by the group (python -m src.agent_variants.agent --sample)

# The result versions compared by the backtest (06_backtest.ipynb). Every agent run has its own folder in AGENT_RAW.
AGENT_RUN_DIR = AGENT_RAW / "spark-x2.6-4b"
RUN_24H = AGENT_RUN_DIR / "h24_direct_anon/decisions.csv"                   # 24-hour window, reasoning off: the main version
RUN_6H = AGENT_RUN_DIR / "h6_direct_anon/decisions.csv"                     # 6-hour window, reasoning off
RUN_24H_REASONING = AGENT_RUN_DIR / "h24_reasoning_anon/signal_agreement.csv"  # reasoning on, only on the 40 signals of the hand sample
MANUAL_DECISIONS = AGENT_RUN_DIR / "h24_direct_anon/signal_agreement.csv"   # decisions derived from the hand classification (manual_* columns)
BASELINE_LEXICON = PROCESSED / "baseline_lexicon_decisions_15pairs_v2_train.csv"  # baseline without a model: Loughran-McDonald lexicon
RESULTS = ROOT / "Results"                                                  # backtest tables and trades, on git
DAILY = PROCESSED / "daily_all.parquet"                                     # daily prices (python -m src.data): calendar of trading days
SPY_DAILY = PROCESSED / "spy_daily_train.parquet"                           # SPY daily prices from Alpaca (python -m src.spy)

# The agent variants: code in src/agent_variants/, one results folder per variant in Results/agent_variants/ (on git).
# The decisions live in the variant's folder, so whoever did not run the model can still redo the backtest.
VARIANTS = RESULTS / "agent_variants"
AGENT_DECISIONS_COPY = VARIANTS / "spark_24h" / AGENT_DECISIONS.name       # copy on git of the main agent's decisions
FINBERT_SCORES = VARIANTS / "finbert_session/news_finbert.parquet"         # FinBERT sentiment of every news item (score_finbert.py)
DEC_3B_6H = VARIANTS / "3b_6h/decisions.csv"                                # Llama 3.2 3B, 6 hours, full prompt (agent_3b.py)
DEC_FINBERT_SESSION = VARIANTS / "finbert_session/decisions.csv"            # FinBERT, window tied to the session (agent_finbert.py)
DEC_C_FRESH = VARIANTS / "c_fresh/decisions.csv"                            # C only on fresh and strong news (c_fresh.py)
DEC_FINBERT_EPISODE = VARIANTS / "finbert_episode/decisions.csv"            # FinBERT, episode window (episode.py)

# The test: used only once, for the variant chosen on the train (finbert_episode), with the rules written in docs/Test.md.
# The test scripts are separate from the train ones: test_data.py, test_finbert.py, test_final.py; the notebooks 06_test_backtest and
# 07_test_robustness read the results. The test was done once, on 14 November 2026: it is not redone.
TEST_START = "2026-09-17"                                                   # first day of the test
TEST_END = "2026-10-30"                                                     # last day with intraday prices
NEWS_TEST = PROCESSED / f"news_{NEWS_SET}_test.parquet"                     # test news (python -m src.test_data)
SPY_TEST = PROCESSED / "spy_daily_test.parquet"                             # SPY from 16 September (the previous close is needed) to TEST_END
RESULTS_TEST = RESULTS / "test"                                             # test results, on git
FINBERT_SCORES_TEST = RESULTS_TEST / "news_finbert_test.parquet"            # FinBERT sentiment of the test news (python -m src.test_finbert)


def env(name: str, default: str = "") -> str:
    """A personal setting (key, address): from the environment variables, otherwise from the .env file in the project
    folder (lines NAME=value), which git ignores. The value is never printed."""
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
    """A parquet file in pandas, read with duckdb as everywhere in the pipeline (same column types everywhere)."""
    return duckdb.sql(f"SELECT * FROM '{Path(path).as_posix()}'").df()
