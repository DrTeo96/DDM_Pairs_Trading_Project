# News agent variants

This folder holds the code of all the agent variants tried by the group: those of Giulio, Orfeo and Beatrice. Each variant has a results folder in [Results/agent_variants/](../../Results/agent_variants/), on git. All the variants are compared **on the train only**: the backtest and the comparison are in [06_backtest.ipynb](../06_backtest.ipynb) (table in [Results/version_comparison.csv](../../Results/version_comparison.csv)), the robustness checks in [07_robustness.ipynb](../07_robustness.ipynb). The functions used by both notebooks are in [comparison.py](comparison.py): they load each variant with its reference (A, or the delayed A) and compute the differences.

On the train the group chose `finbert_episode` (reasons in `06_backtest.ipynb`, section 7). The test (17 September - 30 October) was used only once, on 14 November 2026, only for that variant and with the rules of [docs/Test.md](../../docs/Test.md): results in [06_test_backtest.ipynb](../06_test_backtest.ipynb) and [07_test_robustness.ipynb](../07_test_robustness.ipynb). The other variants were not tried on the test and must not be tried now.

Beatrice's rules, written before each try, with their outcomes, are in [LOG.md](LOG.md). The "Log" column gives the number of the variant there.

## The variants

**Decision sets.** For each signal `enter`, `block` or `follow`. They are compared in `06_backtest.ipynb` through `VERSIONS` in [backtest.py](../backtest.py).

| Variant (folder) | Who | Log | Versions | What it does | Code |
|---|---|---|---|---|---|
| `spark_24h` | Giulio | 1, 2 | B, C | Spark X2.6 4B, news of the previous 24 hours, hidden names, reasoning off (main version) | `agent.py` |
| `spark_6h` | Giulio | 3, 4 | B, C | Like `spark_24h`, with the news of the previous 6 hours | `agent.py --hours 6` |
| `lexicon` | Giulio | 5, 6 | B, C | Baseline without a model: positive and negative words of the Loughran-McDonald lexicon | not in the repo (decisions only) |
| `spark_24h_reasoning` | Giulio | 7 | B | Like `spark_24h` with reasoning on, only on the 40 signals of the sample | `agent.py --agreement --reasoning on` |
| `manual` | Giulio (group) | 7 | B | The group's hand classification of the 40 signals, with the agent's rule | `agent.py --sample 40`, then `--agreement` |
| `3b_6h` | Beatrice | 8 | B | Llama 3.2 3B with Ollama, 6 hours, full prompt; every block needs an event word in the text | `agent_3b.py` |
| `finbert_session` | Beatrice | 9, 10 | B, C | FinBERT on targeted news (a single company, at most 3 tickers). Window tied to the session: from the last close for the overnight gap, from 9:30 for the rest | `score_finbert.py`, `agent_finbert.py` |
| `c_fresh` | Beatrice | 13 | C | Follows only news of the session published in the 60 minutes before, with an event, strong sentiment and the same direction as the move | `c_fresh.py` |
| `finbert_episode` | Beatrice | 14, 15 | B, C | Rules of `finbert_session`, with the news published while the spread was moving away from the mean | `episode.py` |

**Variants that change the backtest itself.** They have their own script, which saves the trades; notebook 06 reads them from `Results/agent_variants/`.

| Variant (folder) | Who | Log | What it does | Code |
|---|---|---|---|---|
| `ma_rules` | Beatrice | 11, 11b | Text rules for M&A news: it blocks only a definitive acquisition in which a stock of the pair is the target. On the train it finds no case: it coincides with A, so no trades, only the list of news | `ma_rules.py` |
| `size` | Beatrice | 12a-12d | Halve the size instead of blocking, with the decisions of `spark_24h`, `3b_6h` and `finbert_session` | `backtest_size.py` |
| `delay` | Beatrice | 16, 17 | Decision and entry 5 or 15 minutes after the signal, against an A delayed by the same time | `delay.py` |
| `post_train` | Orfeo | — | `B_exaggeration`: enters when the news confirms the move. Chosen **after** seeing the train results: the numbers are optimistic | `post_train.py` |

Whether the agent chooses well (do the blocked trades revert less? when C follows the news, is the news right?) is shown in section 4 of `06_backtest.ipynb`.

## How to redo them

From the project folder, with the environment of `uv sync`. All the scripts read only the train.

```bash
uv run python -m src.agent_variants.agent              # Giulio: needs the model server, see src/README.md (step 5)
uv run python -m src.agent_variants.agent_3b           # needs Ollama with llama3.2:3b; hours of computation
uv run --with torch --with transformers python -m src.agent_variants.score_finbert   # only if the news change
uv run python -m src.agent_variants.agent_finbert
uv run python -m src.agent_variants.c_fresh
uv run python -m src.agent_variants.ma_rules
uv run python -m src.agent_variants.episode            # before delay: delay uses the start of the episode
uv run python -m src.agent_variants.delay
uv run python -m src.agent_variants.backtest_size
uv run python -m src.agent_variants.post_train
```

Then rerun `06_backtest.ipynb`, which compares everything and saves the trades of the decision sets in their folders, and `07_robustness.ipynb`.

There is no need to run the models: the decisions and the FinBERT scores are on git. The FinBERT, rule and backtest scripts run in a few seconds or minutes.

**The model prompts are in Italian on purpose.** The prompts of `agent.py` and `agent_3b.py` are kept exactly as they were when the decisions were produced: they ask the model for a short reason in Italian, and `agent.py` names the label fields and values in Italian (`riguarda`, `sottotipo`, `entrambi`...). Translating them would change the questions, so the saved answers would no longer match (the cache key of `agent.py` is a hash of the prompt). The code translates the answers to English right after reading them; the free-text reasons written by the models (`rationale`, `reason`, `verification_rationale` columns) stay in Italian.

## Where the files are

- **Decisions.** Ours and Orfeo's are in `Results/agent_variants/<variant>/`: `decisions.csv`, or `agent_decisions_15pairs_v2_train.csv` for `spark_24h`. Giulio's raw answers (`data/raw/agent/`) are only on Giulio's computer. For this reason `backtest.py` uses the copy on git when the original is missing.
- **Copies of `spark_6h` and `lexicon`.** They were rebuilt from their saved trades. The check: with the copies, the backtest redoes exactly the same trades.
- **`spark_24h_reasoning` and `manual`.** They have no copy: without Giulio's files the notebook shows the already saved table of the sample (`Results/comparison_sample_40.csv`).
- **Trades.** `trades_B.csv` and `trades_C.csv` for the decision sets, written by notebook 06; the `trades_*.csv` files of the other variants are written by their scripts. All at cost 0: costs are added with `backtest.add_costs`.
