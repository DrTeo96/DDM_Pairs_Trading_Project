# The pipeline, from start to finish

This folder holds all the code of the strategy, in the order in which it runs: from the Bloomberg files to the signals, the news agent's decisions, the backtest, the robustness checks, the test and the final metrics. By following the steps below you get the same files and the same numbers as the group on your own computer.

The pipeline works on the 15 pairs chosen in `01_pairs.ipynb`. Steps 0-7 use only the training period (train), which ends on 16 September 2026. The test (17 September - 30 October) was used only once, on 14 November 2026, for the variant chosen on the train: see [The test](#the-test-once-only). Steps 8 and 9 read both periods, but only from saved files. The group's decisions and commented results, step by step, are in the group's log, [Programma.md](../Old%20files/docs/Programma.md) (in Italian, kept in `Old files/`).

## Run order at a glance

Most of the work is no longer a single line of notebooks: there are the base pipeline (steps 0-4), the agent and its variants (steps 5 and 5b), the evaluation notebooks (6-9) and the test (already done). The order below is the one to follow when you rebuild everything from scratch.

| Order | What                                                                                                       | Where it is described                                 | Needs                                                                              |
| ----- | ---------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 1     | Steps 0-3: datasets, pairs, intraday prices, signals                                                       | [The steps](#the-steps)                                | Bloomberg files                                                                    |
| 2     | Step 4: news, plus `src.spy` for SPY                                                                     | [Step 4](#step-4-news) and [Step 7](#step-7-robustness) | Alpaca keys in `.env`                                                            |
| 3     | Step 5: the agent of Giulio (`agent.py`)                                                                 | [Step 5](#step-5-news-agent)                           | A local model server, **or** the folder `data/raw/agent/` from a colleague |
| 4     | Step 5b: the other variants                                                                                | [Step 5b](#step-5b-the-other-agent-variants)           | Nothing for most of them: decisions and FinBERT scores are on git                  |
| 5     | Step 6: `06_backtest.ipynb`                                                                              | [Step 6](#step-6-backtest)                             | Steps 3, 5 and 5b                                                                  |
| 6     | Step 7: `07_robustness.ipynb`                                                                            | [Step 7](#step-7-robustness)                           | Step 6 and `spy_daily_train.parquet`                                             |
| 7     | The test: **do not rerun**; read it with `06_test_backtest.ipynb` and `07_test_robustness.ipynb` | [The test](#the-test-once-only)                        | Files in `Results/test/`, `spy_daily_test.parquet`                             |
| 8     | Step 8: `08_signal.ipynb`                                                                               | [Step 8](#step-8-the-signal-1--0---1)                  | Steps 6 and 7 of train and test                                                    |
| 9     | Step 9: `09_curves_metrics.ipynb`                                                                        | [Step 9](#step-9-equity-curves-and-metrics)            | Step 8 and SPY of train and test                                                   |

Dependencies you must not break: `episode.py` runs before `delay.py`; `06_backtest.ipynb` runs before `08_signal.ipynb` (it writes the trades of `finbert_episode` that step 8 reads); `08_signal.ipynb` runs before `09_curves_metrics.ipynb`.

## Before you start

1. **Environment.** Install uv following [docs/setup.md](../docs/setup.md), then from the project folder:

   ```bash
   uv sync
   ```

   Two libraries are **not** in the project environment and are passed on the command line only when needed: `torch` and `transformers` (FinBERT scores). The commands that need them already include `--with torch --with transformers`.
2. **Bloomberg data.** They are not on git: whoever downloaded them copies them into `data/`.

   | Where                     | Content                                                                                                                 |
   | ------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
   | `data/raw/daily/`       | one file per stock (`AAPL_UW_Equity.parquet`): `PX_LAST`, `PX_VOLUME`, `TOT_RETURN_INDEX_GROSS_DVDS`, from 2006 |
   | `data/raw/intraday_1m/` | one file per stock: 1-minute bars in UTC, from 16 June to 30 October 2026                                               |
   | `data/raw/sentiment/`   | number of news items and daily sentiment per stock, from 2006                                                           |
   | `data/gics.csv`         | GICS classification of the stocks                                                                                       |
3. **`.env` file.** Needed from step 4. Copy the template and fill in the values, without spaces and without quotes:

   ```bash
   cp .env.example .env
   ```

   The `.env` file stays on your computer: git ignores it. Keys are not shared and not pasted in chats, notebooks or commits.
4. **Files that are not on git and that you need beyond Bloomberg.** `data/processed/spy_daily_test.parquet` (SPY for the test) and the folder `data/raw/agent/` (raw answers of the model) exist only on the computer of whoever produced them. Ask them for a copy if you need steps 5 or 9 from scratch. Everything else a colleague needs to read the results is in `Results/`, on git.
5. **A copy of `data/` made before the English renaming** (17 November 2026) still has Italian folder names and Italian values in the agent's tables. Rerun steps 0-4 (seconds), and move out of `data/` the folder `data/raw/agent/` and the files `data/processed/agent_decisions_15pairs_v2_train.csv`, `agent_manual_15pairs_v2_train.csv` and `baseline_lexicon_decisions_15pairs_v2_train.csv`: without them the backtest reads the English copies on git in `Results/agent_variants/`. The naming table is in the [main README](../README.md#naming).

## How to run a step

All commands are launched **from the project folder** (the one containing `pyproject.toml`). If `No module named 'src'` appears, the terminal is in another folder.

A notebook runs in one of two ways:

- in VS Code: open it, choose the project kernel (*Select Kernel → Python Environments → .venv*) and press *Run All*;
- from the terminal, for example for step 1:

  ```bash
  uv run --with nbconvert jupyter nbconvert --to notebook --execute --inplace src/01_pairs.ipynb
  ```

## The steps

Time and memory were measured on a Mac with 16 GB (M4 processor). Memory is the peak of the step: how much free RAM you need for it to run without slowing down. "Not measured" means the step was added or changed after the measurements were made.

| Step          | What to run                                                                                                                    | Reads                                                                                                 | Writes in `data/processed/` (or where stated)                                                                                                                                                                                                                                                  | Time                                    | Memory       |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------- | ------------ |
| 0             | `uv run python -m src.data`                                                                                                  | `data/raw/daily`, `intraday_1m`, `sentiment`                                                    | `daily_all.parquet`, `intraday_1m_all.parquet`, `sentiment_all.parquet`                                                                                                                                                                                                                    | 15 s                                    | 4.0 GB       |
| 0, optional   | `00_exploration.ipynb`                                                                                                      | the three files of step 0                                                                             | nothing (charts)                                                                                                                                                                                                                                                                                 | 5 s                                     | 4.1 GB       |
| 1             | `01_pairs.ipynb`                                                                                                            | `daily_all.parquet`, `data/gics.csv`                                                              | `selected_pairs_2.csv`                                                                                                                                                                                                                                                                         | 3 s                                     | 0.9 GB       |
| 2             | `02_intraday.ipynb`                                                                                                          | `selected_pairs_2.csv`, `intraday_1m_all.parquet`, `daily_all.parquet`                          | `pairs_intraday_v2/` (60 files and `quality_summary.csv`)                                                                                                                                                                                                                                    | 6 s                                     | 0.9 GB       |
| 3             | `03_signals.ipynb`                                                                                                           | `selected_pairs_2.csv`, `pairs_intraday_v2/`                                                      | `signals_15pairs_v2_train.csv`                                                                                                                                                                                                                                                                 | 4 s                                     | 0.3 GB       |
| 4             | `uv run python -m src.news --probe`, then `uv run python -m src.news`                                                      | Alpaca (keys in `.env`), `selected_pairs_2.csv`                                                   | `news_ALL15_V2_train.parquet`; raw pages in `data/raw/news/alpaca/`                                                                                                                                                                                                                          | about 1 minute (estimate)               | 0.1 GB       |
| 4             | `04_news.ipynb`                                                                                                           | `news_ALL15_V2_train.parquet`, `signals_15pairs_v2_train.csv`                                     | `news_for_signals_15pairs_v2_train.csv`                                                                                                                                                                                                                                                        | 1 s                                     | 0.2 GB       |
| 5             | `uv run python -m src.agent_variants.agent`                                                                                 | `signals_15pairs_v2_train.csv`, `news_ALL15_V2_train.parquet`, the model server                   | `agent_decisions_15pairs_v2_train.csv`; raw answers and logs in `data/raw/agent/`                                                                                                                                                                                                            | see below                               | see below    |
| 5b            | the scripts of [agent_variants/](agent_variants/README.md), in the order given in [Step 5b](#step-5b-the-other-agent-variants) | train signals, news, FinBERT scores, decisions of the other steps                                     | `Results/agent_variants/<variant>/` (on git): decisions and trades of each variant                                                                                                                                                                                                            | seconds to minutes; `agent_3b`: hours | not measured |
| 6             | `06_backtest.ipynb`                                                                                                          | `signals_15pairs_v2_train.csv`, `pairs_intraday_v2/`, the decisions of every version (see step 6) | `Results/` (on git): tables, `equity_curves.png`; trades and decisions of each variant in `Results/agent_variants/`                                                                                                                                                                      | 10 s (before the extra variants)        | 0.3 GB       |
| 7             | `uv run python -m src.spy`, then `07_robustness.ipynb`                                                                     | as step 6, plus `spy_daily_train.parquet`                                                           | `Results/robustness/` (on git): final table with bootstrap, beta and alpha; costs, pairs, sectors, periods                                                                                                                                                                                     | less than 1 minute                      | not measured |
| Test, done    | `src.test_data`, `src.test_finbert`, `src.test_final`: **do not rerun**                                           | Alpaca, the train files, `pairs_intraday_v2/`                                                       | `news_ALL15_V2_test.parquet`, `spy_daily_test.parquet`; `Results/test/` (on git)                                                                                                                                                                                                           | a few minutes in total                  | not measured |
| Test, reading | `06_test_backtest.ipynb`, `07_test_robustness.ipynb`                                                                       | `Results/test/`, `spy_daily_test.parquet`, the train tables in `Results/`                       | tables in `Results/test/` and `Results/test/robustness/`, `equity_curves.png`                                                                                                                                                                                                             | less than 1 minute                      | not measured |
| 8             | `08_signal.ipynb`                                                                                                           | the A, B and C trades of `finbert_episode` (train and test) and `pairs_intraday_v2/`             | train: `Results/signal_A.parquet`, `Results/agent_variants/finbert_episode/signal_B.parquet` and `signal_C.parquet`, `Results/signal_returns.csv`, `Results/signal_vs_trade_comparison.csv`; test: `signal_A/B/C.parquet` and `signal_returns.csv` in `Results/test/` | less than 1 minute                      | not measured |
| 9             | `09_curves_metrics.ipynb`                                                                                                    | `signal_returns.csv` and `signal_*.parquet` (train and test), SPY of train and test          | `Results/`: `equity_curve_100.png`, `metrics_train_test.csv`, `market_neutrality.csv`; `Results/test/`: `equity_curve_100.png`, `sharpe_vs_spy.csv`                                                                                                                      | less than 1 minute                      | not measured |

A step is redone only when the files it reads change. In the group's log the steps are numbered differently: there the news are step 3 and the signals step 4 (the notebook titles keep that numbering). Here the signals come first, because the news-signals table needs the signals.

### Step 0. From the Bloomberg files to the datasets

It merges the raw files into three tables, converts the intraday times to New York time and prints the quality checks. What to know before using the data:

- the universe is today's index constituents: whoever left the index is missing (survivorship bias);
- in the daily data `PX_LAST` is adjusted for splits and dividends; some series have gaps of years, so returns use the `ret` column of `load("daily")`;
- in the intraday data prices are **not** adjusted: a split appears as a jump;
- in the sentiment data the value -134217.7 is Bloomberg's placeholder for "missing data": `load("sentiment")` turns it into NaN.

### Step 1. Pair selection

It picks 15 pairs from the same sub-industry with the distance method, using only daily prices up to 15 June 2026, the day before the intraday data start.

### Step 2. Intraday prices per pair

For each pair it aligns the two stocks on the same minutes (session 09:30-15:59), keeps the days in which both are present and fills the minutes without trades with the last price of the same day, marking them with `filled`. The files run to 30 October: they also contain the prices of the test period, which the following steps do not use.

### Step 3. Signals

It computes spread and z-score and applies the entry and exit rules of [signals.py](signals.py), on the train only. Each row of the file is a trade with times, prices, exit reason and gross profit.

### Step 4. News

The news come from Alpaca's free API (source: Benzinga). Everyone creates their own keys:

1. create a free account at [alpaca.markets](https://alpaca.markets); the Paper Trading account is enough;
2. in the dashboard, under Paper Trading, in the API Keys box, press Generate New Keys: the Key ID and the Secret Key appear, and the Secret Key is shown only once;
3. write the two values in `.env`, after `ALPACA_API_KEY_ID=` and `ALPACA_API_SECRET_KEY=`.

```bash
uv run python -m src.news --probe    # a single call: tells you whether the keys work, saves nothing
uv run python -m src.news            # downloads the news of the 30 stocks, from 1 June to 16 September 2026
```

The download replaces the archive only when it is finished: if it is interrupted, the previous one stays whole. An end date after 16 September is refused. Then `04_news.ipynb` checks the coverage and builds, for each signal, the list of the news published in the 24 hours before.

### Step 5. News agent

This step describes Giulio's agent, [agent_variants/agent.py](agent_variants/agent.py). All the group's agent variants (Giulio, Orfeo and Beatrice), with their code, commands and results, are listed in [agent_variants/README.md](agent_variants/README.md) and summarised in [Step 5b](#step-5b-the-other-agent-variants).

The agent is a fixed-step [LangGraph](https://langchain-ai.github.io/langgraph/) graph, the same for every signal: it **searches** the news about the two stocks in the 24 hours before the signal, **classifies** each news item, **verifies** the structural facts, **decides** with a rule written in code and **records** everything. The language model only classifies: it does not decide, does not see the signal thresholds, does not see the date. The complete rules are in the docstring of [agent_variants/agent.py](agent_variants/agent.py).

- No news: `enter`, without calling the model.
- Lists with more than 5 tickers: noise by rule, without calling the model.
- Structural fact (acquisition, investigation, fraud, change of management) on only one of the two stocks: `block`. For version C, `follow` if the direction of the news matches the move of the 30 minutes before.
- Verification: when the model finds a structural fact on only one stock, the code first checks that the headline and summary really name that company, then the model answers a second question: is the company the buyer, the seller, the target, the investigated party or the one changing its head? If not, the news becomes noise. This is needed because the model confuses the company the news is tagged to with the one it is about: on the cases tried it corrected Yum! selling Pizza Hut (tagged to PEP), Nvidia buying Hugging Face (tagged to CRM), a DOJ investigation of all US banks and an IPO in which JPMorgan acts as advisor.
- Only noise (earnings, analysts, deals, products, sector) or facts on both: `enter`, with a suggested size of 0.5 in the `size` column, which the backtest does not use for now.
- Failed search, server not answering, invalid answer: `block`.

**Anonymisation.** Before reaching the model, names, tickers, brands and executives of the two companies become "Company A" and "Company B". This reduces the model's lookahead, that is, the risk that it recognises the company and already knows how things went. It does not eliminate it: figures, other companies mentioned and sub-industry can still give the case away. It must be declared in the report. On the 958 train news items that reach the model, none of the names in the `ALIASES` table remains visible. The instructions tell the model that every company named with its own name is another company, not A or B. Two checks: `--real-names` (same model, names in clear) and a model with a distant training date (`--model google/gemma-3-4b`).

The model runs locally behind a server that speaks the OpenAI API protocol. In `.env` you write the server address and the model name; if the address does not end with `/v1`, the code adds it:

```
AGENT_BASE_URL=http://127.0.0.1:1234/v1
AGENT_MODEL=spark-x2.6-4b
```

| Server                                  | How to start it                                                                                                 | `AGENT_BASE_URL`             | Tried with this code                                                                                                              |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| LM Studio                               | Developer tab, Start Server (or `lms server start`); model name from `curl http://127.0.0.1:1234/v1/models` | `http://127.0.0.1:1234/v1`   | yes, with Spark X2.6 4B (GGUF Q4_K_M)                                                                                             |
| Ollama                                  | `ollama serve`; model name from `ollama list`                                                               | `http://localhost:11434/v1`  | only `agent_3b.py` (Llama 3.2 3B), which calls `http://localhost:11434` directly and ignores `.env`; `agent.py` not tried |
| mlx-lm (only Macs with Apple processor) | `uv run --no-project --python 3.12 --with mlx-lm python -m mlx_lm.server --model <model folder> --port 8089`  | `http://localhost:8089/v1`   | yes, with Gemma 3 4B and the previous version of agent.py                                                                         |
| another computer                        | one of the servers above, started there                                                                         | `http://<address>:<port>/v1` | no                                                                                                                                |

```bash
uv run python -m src.agent_variants.agent --signals 0,1,2,3          # test on a few signals: prints the decisions, does not write the table
uv run python -m src.agent_variants.agent                            # all 973 signals: 586 have news, 958 news items to classify
uv run python -m src.agent_variants.agent --sample 40                # creates data/processed/agent_manual_15pairs_v2_train.csv to fill in by hand
uv run python -m src.agent_variants.agent --agreement                # agreement between the group and the agent (add --reasoning on for the other mode)
uv run python -m src.agent_variants.agent --hours 6                  # variant: 6-hour window
```

- **Reasoning.** Spark X2.6 4B is a model that reasons before answering. Measured on this Mac: about 70 s per news item with reasoning on (one answer in three exceeds the 2000-token ceiling and has to be asked again without reasoning), about 4 s with reasoning off. A full run takes about one hour without reasoning and about 20 hours with reasoning on, so the default is off. The two modes give different answers on the same news item: the choice is made with the agreement on the hand-classified sample.
- **Hand classification.** `--sample 40` draws 40 signals with news, spread across the pairs, without the agent's answers: the group does not see them before classifying. For each news item you fill in `manual_about` (A, B, both, none), `manual_subtype`, `manual_news_direction` and, if needed, `manual_notes`. `--agreement` computes the share of agreement and Cohen's kappa, per news item and per decision. The group's decision is derived from its labels with the same rule as the agent. The command refuses to overwrite an existing sample.
- **Which model.** A model trained after June 2026 may already know the events of the period. The end-of-training date of Spark X2.6 4B must be checked and declared in the report. Gemma 3 declares August 2024: it is the check.
- **Rerunning is free.** Every answer of the model is saved in `data/raw/agent/<model>/news/` with time, request and raw answer. If the same question was already asked, the answer is read again without calling the server; changing window does not require re-classifying the news already classified. Network or server errors are not saved: at the next run the call is repeated.
- **Logs.** Each run writes in `data/raw/agent/<model>/<settings>/` one JSON per signal (news found, text shown to the model, classifications, decision), plus `decisions.csv` and `classifications.csv`.
- **Same decisions for the whole group.** One person does the full run and passes the folder `data/raw/agent/` to the others: with that, and with the same model name in `.env`, the command recreates the table without a server.

### Step 5b. The other agent variants

Besides Giulio's agent, the group tried other ways of deciding on the news. Their code is in [agent_variants/](agent_variants/README.md), each variant writes to its own folder `Results/agent_variants/<variant>/` (on git) and all of them are compared **on the train only**. The rules of Beatrice's variants, written before each try, with their outcomes, are in [agent_variants/LOG.md](agent_variants/LOG.md). The test used only one of them, `finbert_episode`.

You do not need to run the models again: decisions and FinBERT scores are on git. The scripts below run in seconds or minutes, except `agent_3b`, which takes hours. Run them from the project folder, in this order:

```bash
uv run python -m src.agent_variants.agent_3b           # Beatrice: needs Ollama with llama3.2:3b; hours of computation
uv run --with torch --with transformers python -m src.agent_variants.score_finbert   # only if the news change
uv run python -m src.agent_variants.agent_finbert      # finbert_session
uv run python -m src.agent_variants.c_fresh           # C only, fresh and strong news
uv run python -m src.agent_variants.ma_rules          # M&A rules: only a list of news, no trades
uv run python -m src.agent_variants.episode            # finbert_episode, the variant chosen for the test. Before delay
uv run python -m src.agent_variants.delay              # decision and entry 5 or 15 minutes after the signal
uv run python -m src.agent_variants.backtest_size      # half size instead of blocking
uv run python -m src.agent_variants.post_train         # Orfeo's B_exaggeration, chosen after seeing the train: optimistic numbers
```

| Variant              | Who      | Script                                     | What it does                                                                                                                       |
| -------------------- | -------- | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| `3b_6h`            | Beatrice | `agent_3b.py`                            | Llama 3.2 3B with Ollama, 6 hours, full prompt, a word of the event must appear in the text to block                               |
| `finbert_session`   | Beatrice | `score_finbert.py`, `agent_finbert.py` | FinBERT on targeted news; window tied to the session                                                                               |
| `c_fresh`         | Beatrice | `c_fresh.py`                            | C follows only fresh news (last 60 minutes of the session) with an event, strong sentiment and the same direction as the move      |
| `finbert_episode` | Beatrice | `episode.py`                            | Rules of `finbert_session`, with the news published while the spread was moving away from the mean. **Chosen for the test** |
| `ma_rules`        | Beatrice | `ma_rules.py`                           | Text rules for M&A news. On the train it finds no case: same as A, so no trades, only the list of news                             |
| `size`       | Beatrice | `backtest_size.py`                       | Halve the size instead of blocking                                                                                                 |
| `delay`          | Beatrice | `delay.py`                             | Decision and entry 5 or 15 minutes after the signal, against an A delayed by the same amount                                       |
| `post_train`       | Orfeo    | `post_train.py`                          | `B_exaggeration`: enters when the news confirms the move. Chosen **after** seeing the train                                |

The shared functions are in [agent_variants/common.py](agent_variants/common.py) (trading days) and [agent_variants/comparison.py](agent_variants/comparison.py) (loads every variant with its reference and computes the differences, used by notebooks 06 and 07).

### Step 6. Backtest

It applies costs and capital to the trades of step 3 and compares three versions:

- **A**: every signal enters, without agent;
- **B**: the agent can block (column `decision`);
- **C**: the agent can also follow the news (column `decision_C` = `follow`, direction in `follow_side`). The trade that follows the news opens at the same bar as A, in the opposite direction, and is redone bar by bar on the prices of `pairs_intraday_v2/`: it exits at the first of spread reversion (z back to 0), 90 minutes and end of day, with no stop.

The versions run on every **set of decisions** listed in `VERSIONS` ([backtest.py](backtest.py)); the paths are in [config.py](config.py):

| Name                  | File                                                                                                                                                                  | Signals |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| `spark_24h`         | `data/raw/agent/spark-x2.6-4b/h24_direct_anon/decisions.csv` (main, same as `agent_decisions_15pairs_v2_train.csv`)                                           | 973     |
| `spark_6h`          | `data/raw/agent/spark-x2.6-4b/h6_direct_anon/decisions.csv` (`--hours 6`)                                                                                     | 973     |
| `lexicon`           | `data/processed/baseline_lexicon_decisions_15pairs_v2_train.csv`: baseline without a model, Loughran-McDonald lexicon. The code that produces it is not in the repo | 973     |
| `spark_24h_reasoning` | `data/raw/agent/spark-x2.6-4b/h24_reasoning_anon/signal_agreement.csv` (`--agreement --reasoning on`)                                                             | 40      |
| `manual`              | `manual_*` columns of `h24_direct_anon/signal_agreement.csv` (`--agreement`): B only, because the direction to follow is missing                               | 40      |
| `3b_6h`             | `Results/agent_variants/3b_6h/decisions.csv` (`agent_variants/agent_3b.py`): B only                                                                             | 973     |
| `finbert_session`    | `Results/agent_variants/finbert_session/decisions.csv` (`agent_variants/agent_finbert.py`)                                                                       | 973     |
| `c_fresh`          | `Results/agent_variants/c_fresh/decisions.csv` (`agent_variants/c_fresh.py`): C only                                                                          | 973     |
| `finbert_episode`  | `Results/agent_variants/finbert_episode/decisions.csv` (`agent_variants/episode.py`)                                                                          | 973     |

When the original file is not there (the raw answers of the agent are only on the computer of whoever ran it), `load_version` reads the copy on git in `Results/agent_variants/<name>/`. The variants that change the backtest itself (reduced size, delayed entry, Orfeo's `B_exaggeration`) are not decision sets: the notebook reads their trades from `Results/agent_variants/`. The notebook compares everything **on the train only** (`Results/version_comparison.csv`), with the functions of [agent_variants/comparison.py](agent_variants/comparison.py).

The 40-signal sets are compared only on the signals of the hand-classified sample. For the lexicon, `flat` means block and `only_A`/`only_B` with `long`/`short` means follow: C is simulated with the hedged pair, as for the agent.

```python
from src.backtest import load_trades, trading_days, load_version, apply_version
from src.agent_variants.comparison import references, all_variants, compare

trades, days = load_trades(), trading_days()
B = apply_version(trades, "B", load_version("spark_24h"))          # a single variant
cmp = compare(all_variants(trades), references(trades), days)   # all of them, sorted by dollars at cost 0 against the reference
```

The notebook saves tables and chart in `Results/` and the trades of each decision set in `Results/agent_variants/<name>/`, all on git, so the results can be read even without the data. The commentary on the numbers for people who do not know finance is in [Results/REPORT.md](../Results/REPORT.md). To add a new decision set: the path in `config.py`, a row in `VERSIONS`, then rerun the notebook.

### Step 7. Robustness

`07_robustness.ipynb` checks, for each variant and on the train only, whether the difference from the reference is real or luck:

- final table with the full metrics, the 95% confidence interval of the difference (bootstrap over days), beta and alpha against the market;
- sensitivity to costs (0, 2, 5, 10 bps);
- difference by sector and without the pair that weighs most;
- the two halves of the train and the train without 13 August.

The market is SPY: the daily prices, adjusted for dividends, are downloaded from Alpaca with the same keys as the news (`uv run python -m src.spy`, only up to the end of the train). The tables go in `Results/robustness/`.

### The test, once only

The rules of the test are in [docs/Test.md](../docs/Test.md), written before downloading the test data: only `finbert_episode`, with versions A, B and C; main criterion the difference in dollars from A at cost 0; cost 5 as a comparison; the same checks as the train, plus consistency with the train. The test was run on 14 November 2026 with three scripts separate from those of the train:

| Script                            | What it did                                                                                                                                                                   |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [test_data.py](test_data.py)       | Downloaded from Alpaca the news from 17 September to 30 October (2,725) and SPY from 16 September to 30 October                                                               |
| [test_finbert.py](test_finbert.py) | Computed FinBERT on the test news, after checking that it gives back the train scores                                                                                         |
| [test_final.py](test_final.py)   | Redid the train checking that signals, decisions and trades of `finbert_episode` were identical to the saved ones, then computed signals, decisions and trades of the test |

**The test scripts are not rerun**: `test_final.py` would redo the test and overwrite `Results/test/`. The results are read, as many times as needed, with [06_test_backtest.ipynb](06_test_backtest.ipynb) and [07_test_robustness.ipynb](07_test_robustness.ipynb), which use only saved files. `test_final.py --check-only` runs only the check on the train and reads nothing from the test.

### Step 8. The signal +1 / 0 / -1

The professor's instructions ask for a +1, 0 or -1 signal for each stock and a return equal to signal x return of the stock. `08_signal.ipynb` turns the already saved trades of A, B and C (train and test) into this signal, minute by minute, and recomputes the profit with that formula. It also lists the assumptions (execution, amounts, short selling). It changes no rule and does not redo the test: it reads only saved files. The profit from the signal matches that of the trades to within a few dollars.

### Step 9. Equity curves and metrics

`09_curves_metrics.ipynb` does the evaluation asked by the professor, on train and test, with the returns from the signal of step 8:

- equity curve starting at 100 with SPY on the same chart;
- cumulative and annualised return, annualised volatility, Sharpe (risk-free rate 0), maximum drawdown and profit factor for A, B, C and SPY, at cost 0 and 5;
- beta, correlation and return on the days when SPY falls (market neutrality);
- a statistical test (bootstrap over days) of whether the Sharpe of the strategy on the test is really higher than that of SPY, saved in `Results/test/sharpe_vs_spy.csv`.

It explains the choice of benchmarks (SPY and version A) and the calculation assumptions. It reads only saved files.

## Rules not to break

- **The train/test cut.** The train ends on 16 September 2026 and the date is written in one place only, `TRAIN_END` in [config.py](config.py). The test, from 17 September, was used only once, on 14 November 2026, with rules and parameters frozen: it is not redone, and no rule is changed by looking at its results. Signals, news and agent decisions do not contain test days: `load_trades` refuses a table that contains them and `news.py` refuses to download them.
- **File names in `data/`.** Every colleague has their own copy of `data/`: renaming an output file breaks the others' copies. The names are in `config.py`.
- **No paths in notebooks.** Paths and dates are imported from `config.py`.
- **Variants.** Each variant is written down (rules, thresholds) before it is run and run once, as in [agent_variants/LOG.md](agent_variants/LOG.md). A variant born from looking at the train results (like `post_train`) is declared as such.

## If something breaks

| Message                                                                         | What to do                                                                                                                        |
| ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `No module named 'src'` from the terminal                                     | The terminal is not in the project folder: `cd` into it                                                                         |
| `No module named 'src'` in a notebook                                         | The notebook was moved out of the project, or the first cell was not run                                                          |
| `No module named ...` (another library)                                       | The kernel is not `.venv`, or `uv sync` is missing                                                                            |
| `No module named 'torch'` or `'transformers'`                               | Run the script with `uv run --with torch --with transformers python -m ...`                                                     |
| `selected_pairs_2.csv is missing`                                             | Run `01_pairs.ipynb` first                                                                                                     |
| `ALPACA_API_KEY_ID ... missing`                                               | `.env` is missing or empty: see step 4                                                                                          |
| `Alpaca answered 401`                                                         | Wrong keys: regenerate them on the Alpaca website                                                                                 |
| `news_for_signals_15pairs_v2_train.csv` not found                             | Run `04_news.ipynb` first                                                                                                    |
| `No server answers at ...`                                                    | The model server is off or `AGENT_BASE_URL` is wrong. For `agent_3b.py` start Ollama and run `ollama pull llama3.2:3b`      |
| `ServerError: Unexpected endpoint or method`                                  | The server address is wrong: for LM Studio it is `http://127.0.0.1:1234/v1`                                                     |
| From Claude Code the agent does not reach the server, from the terminal it does | The Claude Code sandbox blocks local connections: launch the command from the terminal                                            |
| Many `invalid answer` rows in the agent                                       | The model does not respect the format: use a server that enforces the answer schema (LM Studio, Ollama) or a bigger model         |
| `08_signal.ipynb` does not find the trades of `finbert_episode`           | Run `06_backtest.ipynb` first: it writes `trades_B.csv` and `trades_C.csv` in `Results/agent_variants/finbert_episode/` |
| `09_curves_metrics.ipynb` does not find `spy_daily_test.parquet`            | The file is not on git: ask a colleague for their copy. Do not rerun the test scripts                                             |
| The computer slows down a lot at step 0                                         | Close the other applications: about 4 GB free are needed                                                                          |

## The modules

| File                                                                                            | What it contains                                                                                                                                                  |
| ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [config.py](config.py)                                                                           | Paths, `TRAIN_END`, test dates, file names, reading of `.env` and of the parquet files                                                                        |
| [data.py](data.py)                                                                               | Step 0: building the datasets, `load()`, quality checks                                                                                                         |
| [gics.py](gics.py)                                                                               | `load_gics()`: the GICS classification of `data/gics.csv` (a Bloomberg export in Italian) with the official English names                                       |
| [signals.py](signals.py)                                                                         | Spread, z-score and entry and exit rules                                                                                                                          |
| [news.py](news.py)                                                                               | Downloading and archive of the news, news before each signal                                                                                                      |
| [spy.py](spy.py)                                                                                 | Daily SPY prices from Alpaca, for beta and alpha (step 7)                                                                                                         |
| [agent_variants/](agent_variants/README.md)                                                    | All the variants of the news agent: Giulio's agent (`agent.py`), the variants of Beatrice and Orfeo, `comparison.py` and `common.py` shared by the notebooks |
| [backtest.py](backtest.py)                                                                       | Costs, versions A, B and C, decision sets to compare, metrics, saving in `Results/`                                                                             |
| [test_data.py](test_data.py), [test_finbert.py](test_finbert.py), [test_final.py](test_final.py) | The test of `finbert_episode`: data, sentiment, signals, decisions and trades. Already run, do not rerun                                                       |

What is no longer part of the pipeline is in `Old files/`, in the folder structure it had: the notebooks of the first 10 pairs, the first tests on a single pair, version 2 of the signal (discarded) and the documents of the initial plan. They are kept as they were and are not updated: they use paths and functions of that time.
