# Intraday pairs trading on the S&P 500 with a news agent

Exam project (LUISS, Data-Driven Models for Investment 2026-27). The project brief is in [resources/instructions.pdf](resources/instructions.pdf).

Pairs trading bets on two similar companies. When their prices drift apart by more than usual, you buy the stock that lagged behind and sell the one that ran ahead, waiting for the gap to close. Here the gap (the spread) is measured minute by minute on 15 pairs of S&P 500 stocks, using Bloomberg data. An agent reads the news published before each signal and blocks the trade when the divergence has a real cause in only one of the two companies. The project compares three versions: A with no agent, B with the agent that can block, and C with the agent that can also follow the news. The news decisions come from several sources compared against each other: the agent with two news windows (24 and 6 hours), a lexicon baseline with no model, FinBERT, and, on a sample, reasoning switched on and the group's hand classification.

On the training period (train, 16 June - 16 September 2026) the group compared 21 variants of the agent and chose `finbert_episode`. The test period (17 September - 30 October 2026) was used only once, on 14 November, for that variant, with the rules written beforehand in [docs/Test.md](docs/Test.md). B (the agent blocks) earns 189 dollars less than A, and C (the agent follows the news) earns 1,242 dollars less. With this agent, the news do not improve the strategy.

The train and test results, explained also for readers who don't know finance, are in [Old files/docs/REPORT.md](Old files/docs/REPORT.md). The group's log, with the decisions of each step, and the summary of the research question and of how the project meets the course instructions (including the pitfall analysis) are in [Old files/docs/](Old%20files/docs/) (`Programma.md`, `Sintesi.md`, in Italian).

## Getting started

**All the information needed to run the code (required data, order of execution, inputs, outputs, time and memory) is in [src/README.md](src/README.md).** The steps below only cover the environment setup.

1. Install [uv](https://docs.astral.sh/uv/) following [docs/setup.md](docs/setup.md). You don't need to install Python: uv does it.
2. From the project folder, create the environment:

   ```bash
   uv sync    # creates .venv/ with Python and the library versions pinned in uv.lock
   ```
3. To run the code, go to [src/README.md](src/README.md): it says which data you need and, step by step, what to run, what it reads, what it writes, and how much time and memory it takes.

The results can be read without any data: tables, trades, decisions and charts are in `Results/`, and every notebook in `src/` is saved with its outputs.

## Where things are

| Where | What's in it |
|---|---|
| [src/](src/README.md) | The pipeline code, in execution order |
| [Results/](Old files/docs/REPORT.md) | Backtest results, tracked in git: tables, trades for each version, agent decisions, equity curves and the report |
| [Results/test/](Results/test/version_comparison.csv) | Test results for `finbert_episode`: signals, decisions, trades for A, B and C, tables of the criteria and of robustness |
| [src/agent_variants/](src/agent_variants/README.md) | All the variants of the news agent (Giulio, Orfeo, Beatrice): code, commands and rules; their results are in `Results/agent_variants/` |
| [docs/Test.md](docs/Test.md) | The test rules, written before looking at the test: variant, main criterion, checks |
| [docs/setup.md](docs/setup.md) | Using uv: install, run, add libraries |
| `data/` | Raw data and files produced by the pipeline. Not in git: everyone keeps their own copy |
| `resources/` | Project brief, stock names |
| `Old files/` | Whatever is no longer part of the pipeline, kept as it was (in Italian), including the group's log and the summary |
| `.env.example` | Template for the `.env` file with personal keys and addresses, which git ignores |

## Naming

The project was written in Italian and translated to English on 17 November 2026, before submission. Code, notebooks, documentation, file names, column names and values were translated; the numbers did not change (every result table was checked against the Italian one after the translation). `Old files/` and the git history before that date use the Italian names. The main correspondences:

| Italian name | English name |
|---|---|
| `src/varianti_agente/` | `src/agent_variants/` |
| `00_esplorazione`, `01_coppie`, `03_segnali`, `04_notizie` | `00_exploration`, `01_pairs`, `03_signals`, `04_news` |
| `07_robustezza`, `07_test_robustezza`, `08_segnale`, `09_curve_metriche` | `07_robustness`, `07_test_robustness`, `08_signal`, `09_curves_metrics` |
| `test_dati.py`, `test_finale.py` | `test_data.py`, `test_final.py` |
| `confronto.py`, `comune.py`, `episodio.py`, `ritardo.py`, `c_fresca.py`, `ma_regole.py`, `REGISTRO.md` | `comparison.py`, `common.py`, `episode.py`, `delay.py`, `c_fresh.py`, `ma_rules.py`, `LOG.md` |
| `Results/RESOCONTO.md`, `Results/robustezza/` | `Old files/docs/REPORT.md`, `Results/robustness/` |
| variants `finbert_episodio`, `finbert_seduta`, `lessico`, `c_fresca`, `ma_regole`, `dimensione`, `ritardo`, `B_esagerazione`, `mano` | `finbert_episode`, `finbert_session`, `lexicon`, `c_fresh`, `ma_rules`, `size`, `delay`, `B_exaggeration`, `manual` |
| decisions `entra`, `blocca`, `segui` | `enter`, `block`, `follow` |
| exit reasons `rientro`, `tempo`, `fine_giornata` | `reversion`, `time`, `end_of_day` |
| columns `variante`, `versione`, `riferimento`, `leg_piu_mosso`, `mano_*` | `variant`, `version`, `reference`, `most_moved_leg`, `manual_*` |

Two things were deliberately left in Italian:

- **The prompts of the language models** (`src/agent_variants/agent.py`, `agent_3b.py`). They are kept exactly as they were when the decisions were produced: translating them would change the questions asked to the model, and the saved answers (whose cache key is a hash of the prompt) would no longer match. The code translates the model's answers to English as soon as it reads them.
- **The free-text reasons written by the models** (`reason`, `rationale`, `verification_rationale` columns in the agent's tables): the prompts asked for them in Italian, and they are data, kept as written.

GICS sector names come from a Bloomberg export made in Italian (`data/gics.csv`); [src/gics.py](src/gics.py) translates them to the official English names when it reads the file.
