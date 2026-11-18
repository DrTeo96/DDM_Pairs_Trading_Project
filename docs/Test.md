# The test: rules written before looking at it

This file fixes what is done on the test period and how the result is judged. It was written on 14 November 2026, before downloading the test news and before computing any signal or trade of the test. The rules are not changed after seeing the results.

*Translated from Italian on 17 November 2026, with the file and variant names of the English version of the code (for example `finbert_episodio` became `finbert_episode`). The rules are unchanged; the original Italian text is in the git history.*

## What is tested

On the train (16 June - 16 September 2026) the group compared 21 variants of the news agent and chose `finbert_episode`. The choice and the criterion are explained in [src/06_backtest.ipynb](../src/06_backtest.ipynb) and [src/07_robustness.ipynb](../src/07_robustness.ipynb).

Only three versions go to the test, with the rules of the train:

| Version | What it does |
|---|---|
| **A** | Enters at every signal, without the agent. It is the reference |
| **B** | `finbert_episode` can block the trade |
| **C** | `finbert_episode` can block or follow the news (enter in the direction opposite to A) |

No other variant goes to the test.

## The period and the data

- **Test:** from 17 September to 30 October 2026, the last day with intraday prices. That is 32 trading days; 5 pairs (CSX-UNP, HD-LOW, DHR-TMO, GS-MS, ISRG-SYK) have prices from 18 September, so 31 days, just as in the train they had 60 days instead of 64.
- **Prices:** the files of `pairs_intraday_v2/`, the same as the train, which already run to 30 October.
- **News:** Alpaca (Benzinga), downloaded only from 17 September to 30 October, in a file separate from the train one. The "overnight" episodes of 17 September start at 16:00 of the 16th: the news of those hours are already in the train archive and are used from there, with the FinBERT scores already computed.
- **Sentiment:** FinBERT (`ProsusAI/finbert`) on headline and summary of each new news item, as in the train.
- **Market:** daily SPY from Alpaca, adjusted for dividends, from 16 September (the close of the day before is needed for the return of the 17th) to 30 October.

## The rules, frozen

**Signal** (as in `03_signals.ipynb` and [src/signals.py](../src/signals.py)): log spread with beta 1, z-score with a continuous EMA and a 60-minute half-life, entry at |z| ≥ 2, exit at |z| ≤ 0, stop at |z| ≥ 3.5, maximum time 90 minutes, no entries in the first 15 and in the last 30 minutes, no entry if a leg has a filled bar, execution at the open of the next bar. The EMA runs on from the train: the z-score of 17 September uses past prices, never future ones.

**`finbert_episode`** (as in [src/agent_variants/episode.py](../src/agent_variants/episode.py)):
- start of the episode: going back from the signal, the first bar in a row with z beyond 1 with the same sign, minus 5 minutes; if the episode reaches the first bar of the day, from 16:00 of the previous trading day;
- end of the window: the close of the signal bar;
- targeted news item: it tags only one of the two companies and has at most 3 tickers; strong news item: the winning FinBERT class has probability of at least 0.8;
- **B:** blocks if there is at least one strong targeted news item, all the strong ones are about the same company and at least one contains an event word (the same list as the train). Otherwise it enters;
- **C:** follows if the difference of the mean scores (company A minus company B) has absolute value at least 0.5 and the same sign as the relative move of the 30 minutes before; otherwise it decides as B. The followed trade exits at the first of spread reversion, 90 minutes and end of the day, without stop.

**Backtest** (as in [src/backtest.py](../src/backtest.py)): 10,000 dollars per leg, no leverage, everything closed at the end of the day; capital of 20,000 dollars per pair, 300,000 in total; a trade has 4 operations.

**Costs:** 0 basis points per operation (main scenario, the professor's indication) and 5 as a comparison.

## How it is judged

**Main criterion:** the dollar difference between B and A, and between C and A, at cost 0. It is the same criterion with which `finbert_episode` was chosen on the train.

**Checks** (the same as the train, computed also on the test):
1. 95% confidence interval of the difference, resampling the days with replacement (10,000 times): it says whether the difference can be told apart from zero;
2. B only: profit of the blocked trades against 5,000 random blocks of the same number (`p_random`);
3. B only: reversion share of the blocked trades against that of the kept ones, with Fisher's exact test;
4. C only: share of the followed trades in profit ("news right") and their mean profit;
5. for A, B and C: net profit per trade, win rate, profit factor, Sharpe, drawdown. The Sharpe over 32 days is not very reliable and is reported as such;
6. the same results at cost 5;
7. difference from A per pair, per sector and without PYPL-XYZ;
8. beta and alpha against SPY;
9. consistency with the train: does the difference from A have the same sign as on the train (B −285 $, C −651 $)?

The comparison between the two halves of the period and the "without 13 August" check, which is a train day, **are not done**.

**If the agent blocks or follows nothing.** If on the test the agent blocks no trade, B coincides with A and the test says nothing about the blocks; the same for C if it follows no news. It is reported as such, without changing the rules.

## Only once

The test was done once, on 14 November 2026, and **is not redone**: redoing it after seeing the results would take value away from the test.

- Before the test, the same scripts redid the train and found exactly the 973 signals of `03_signals.ipynb` and the decisions and trades of `finbert_episode` saved in `Results/agent_variants/finbert_episode/`. Had they not matched, the test would not have started.
- [src/test_final.py](../src/test_final.py) computed signals, decisions and trades of the test and saved them in `Results/test/`.
- The notebooks [src/06_test_backtest.ipynb](../src/06_test_backtest.ipynb) and [src/07_test_robustness.ipynb](../src/07_test_robustness.ipynb) read only the files saved in `Results/test/`: they can be rerun as many times as needed without redoing the test.

## How it was done

From the project folder, in this order. The commands are here to document the work: they must not be run again. (On 14 November the scripts had their Italian names, `test_dati` and `test_finale`; `uv run python -m src.test_final --check-only` repeats only the check on the train and reads nothing of the test.)

```bash
uv run python -m src.test_data                                              # news and SPY of the test, with the Alpaca keys in .env
uv run --with torch --with transformers python -m src.test_finbert          # FinBERT on the test news
uv run python -m src.test_final                                             # the test
```

Then `06_test_backtest.ipynb` and `07_test_robustness.ipynb` are run.
