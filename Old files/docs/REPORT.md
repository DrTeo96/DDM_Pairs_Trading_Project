# Report: the strategy and the news agent put to the backtest

This report explains what we tried and what came out. The numbers of sections 1-9 come from [src/06_backtest.ipynb](../src/06_backtest.ipynb) and concern the **training period** (train, from 16 June to 16 September 2026, 64 trading days). Section 10 concerns the **test period** (from 17 September to 30 October 2026, 32 trading days), used only once: the numbers come from [src/06_test_backtest.ipynb](../src/06_test_backtest.ipynb) and [src/07_test_robustness.ipynb](../src/07_test_robustness.ipynb). The tables are in this folder and in [test/](test/). The summary of research question, results and the professor's requests is in [Sintesi.md](../Old%20files/docs/Sintesi.md) (in Italian).

## In short

- The base strategy (version A) makes 973 trades and earns on average 7.4 basis points per trade, i.e. 0.074%. On a capital of 300,000 dollars that is 7,239 dollars in three months (+2.4%).
- The profit is so small that trading costs wipe it out: a cost of 1.9 basis points per operation is enough to bring it to zero. With a realistic cost of 5 basis points the strategy loses 12,221 dollars (-4.1%).
- The news agent was supposed to avoid the wrong trades. Instead it blocks trades that on average earned **more** than the others: 27.8 basis points against 7.4. It did worse than a random block.
- Following the news (version C) makes things even worse: the 13 trades in which the agent follows the news lose on average 155 basis points.
- A simpler version without artificial intelligence, which counts the positive and negative words of the news, blocks in a way that cannot be told apart from chance.
- These results depend on very few trades, above all on one day (13 August). They are an indication, not a proof.
- Among 21 variants of the agent the group chose `finbert_episode` and tried it **on the test**, on data never looked at before. There too the news do not help: blocking earns 189 dollars less than A, following the news 1,242 dollars less. The base strategy still earns without costs (+2,472 dollars), but less than on the train.

## 1. The idea, in simple words

Two companies in the same line of business, for example Coca-Cola and Pepsi, have stock prices that move together: if the soft-drink market does well, both rise. Every now and then, during the day, one of the two moves more than the other without a real reason, maybe only because someone bought or sold a lot at that moment. Usually the gap closes again shortly after.

The strategy bets precisely on this reversion. When the gap between the two is unusually large:

- it **buys** the stock that lagged behind (it earns if it rises);
- it **sells short** the stock that ran ahead (it earns if it falls). Selling short means borrowing a share, selling it at once and buying it back later: if in the meantime the price has fallen, the difference is earned.

The two trades have the same amount, 10,000 dollars each. If the whole market rises or falls, what is earned on one side is lost on the other: only how the two stocks move **relative to each other** counts. The trade earns if the gap closes, and loses if it widens further. Everything is closed by the end of the day.

**The problem.** Sometimes the gap widens for a real reason: one of the two companies is bought by another, receives an investigation, changes its chief executive. In that case the gap may never close, and the bet loses. The **news agent** is a program with an artificial intelligence model that reads the news published in the hours before each signal and, if it finds such a fact on only one of the two companies, says not to enter.

## 2. The words to know

| Word | What it means |
|---|---|
| Pair | Two companies of the same sector, for example Visa and Mastercard. We use 15. |
| Spread | The gap between the prices of the two stocks (precisely: the difference of their logarithms). It is what is bet on. |
| z-score | How unusual the spread is at this moment, measured in "standard deviations" from its recent mean. The trade enters when it goes beyond 2 (very unusual) and exits when it goes back to 0 (normal). |
| Signal | The moment in which the z-score goes beyond the threshold: the strategy would like to enter. In the train there are 973. |
| Trade | A complete operation: opening of the two positions and their closing. |
| Basis point (bps) | One hundredth of a percentage point: 1 bps = 0.01%. On 10,000 dollars, 1 bps = 1 dollar. |
| Gross and net | Gross: profit before costs. Net: after costs. |
| Cost per operation | How much it costs to buy or sell (commissions and the difference between buying and selling price). A trade has 4 operations: opening and closing two stocks. With 5 bps per operation the trade costs 20 bps. |
| Break-even cost | The cost per operation at which the mean profit becomes zero. |
| Exit | How a trade ends: **reversion** (the spread went back to normal: usually a profit), **stop** (the spread widened too much: closed at a loss), **time** (after 90 minutes it is closed anyway), **end of day**. |
| Win rate | The share of trades closed in profit. |
| Profit factor | How much was earned in the winning trades divided by how much was lost in the losing ones. Above 1: there is a profit overall. |
| Standard error | How uncertain a mean is. If the mean is 7.4 and the standard error 2.0, the true mean is roughly between 3.4 and 11.4. |
| Sharpe ratio | Profit divided by how much the profits swing day by day, scaled to a year. The higher it is, the steadier the profit. Over 64 days and with tiny daily profits it is inflated: a value like 8 must not be compared with that of a fund. |
| Drawdown | The largest loss from the highest point reached. |
| Train and test | The stock-market period is split in two. On the train (up to 16 September) the strategy is built and tried; the test (from 17 September) is used only once at the end, with frozen rules, to see whether it works on data never seen. **The test was used only once, on 14 November 2026** (section 10). |
| p-value | Here: the probability that a random block gives a result as good as or better than the agent's. Small (below 0.05) = the agent chooses better than chance. Close to 1 = the agent chooses worse than chance. |

## 3. How we put the strategy to the test

A **backtest** redoes on the past, minute by minute, what the strategy would have done, with the rules decided before looking at the results:

- 10,000 dollars on each of the two stocks, without borrowing to increase the amount;
- total capital of 300,000 dollars (20,000 for each of the 15 pairs): each pair has at most one open trade at a time;
- everything closed by the end of the day;
- costs: main scenario **0** (the professor's indication for these 15 pairs), then 2, 5 and 10 bps per operation to see how much they weigh. 5 is the realistic scenario.

## 4. The three versions and the five decision sets

The **versions** are three ways of using the news:

| Version | What it does |
|---|---|
| **A**, no agent | It enters at every signal. It is the benchmark. |
| **B**, the agent blocks | If the agent finds a real fact on only one company, it does not enter. Otherwise it enters like A. |
| **C**, the agent decides | Like B, but in some cases, instead of standing still, it bets in the direction of the news: if the news is good for the company that rose, it bets that it keeps rising against the other. It is the opposite bet to A. It exits when the spread reverts (the news was wrong), after 90 minutes or at the end of the day. |

The **decision sets** are who decides, signal by signal, whether to block or follow:

| Set | Who decides | Signals | Blocks (B) | Follows (C) |
|---|---|---|---|---|
| `spark_24h` (main) | The agent with the Spark X2.6 4B model, reading the news of the previous 24 hours | 973 | 48 | 13 |
| `spark_6h` | The same agent, with the news of the previous 6 hours | 973 | 25 | 9 |
| `lexicon` | No model: it counts the positive and negative words of the news with a finance dictionary (Loughran-McDonald) | 973 | 166 | 61 |
| `spark_24h_reasoning` | The agent with the model that "reasons" before answering (much slower) | 40 | 5 | 2 |
| `manual` | The group, which classified the news by hand, with the same rule as the agent | 40 | 5 | 1 |

The last two exist only for a sample of 40 signals, because classifying by hand and making the model reason take a lot of time.

## 5. Results of version A

| Cost per operation | Trades | Mean profit per trade | Trades in profit | Total profit | On capital |
|---|---|---|---|---|---|
| 0 bps | 973 | +7.4 bps | 60% | +7,239 $ | +2.4% |
| 2 bps | 973 | -0.6 bps | 53% | -545 $ | -0.2% |
| 5 bps | 973 | -12.6 bps | 39% | -12,221 $ | -4.1% |
| 10 bps | 973 | -32.6 bps | 20% | -31,681 $ | -10.6% |

How to read it:

- **There is a profit but it is small**: 7.4 bps per trade, with an uncertainty of ±2 bps. On 10,000 dollars that is 7.4 dollars per trade.
- **Costs eat it all.** The break-even cost is 1.86 bps per operation: a trade costs 4 operations, so 7.4 bps, exactly what it earns on average. A realistic cost is higher.
- **There is a profit only when the spread reverts.** The 464 trades that exit on reversion earn on average 38.8 bps; the 422 that exit on time lose 23.2 bps and the 31 that exit on stop lose 32.1 bps.
- **The profit is concentrated at the open.** The signals between the 15th and the 30th minute of trading (457) earn 11.4 bps: it is the reversion of the moves accumulated overnight. The later ones (516) only 3.9 bps.

## 6. Results of version B: does the agent block the wrong trades?

The comparison with A, at cost 0:

| Set | Trades | Mean profit per trade | Total profit | Difference from A |
|---|---|---|---|---|
| A, no agent | 973 | +7.44 bps | +7,239 $ | |
| B, `spark_24h` | 925 | +6.38 bps | +5,905 $ | -1,334 $ |
| B, `spark_6h` | 948 | +6.14 bps | +5,819 $ | -1,420 $ |
| B, `lexicon` | 807 | +7.08 bps | +5,712 $ | -1,527 $ |

**All the sets earn less than A.** To understand why, we look at how much the blocked trades would have earned and compare it with a random block of the same number of trades (5,000 draws):

| Set | Blocked trades | Mean profit of the blocked ones | Random blocks, on average | p-value |
|---|---|---|---|---|
| `spark_24h` | 48 | +27.8 bps | +7.3 bps | 0.97 |
| `spark_6h` | 25 | +56.8 bps | +7.1 bps | 1.00 |
| `lexicon` | 166 | +9.2 bps | +7.5 bps | 0.67 |

The main agent removed precisely trades better than the average: almost four times the average. 97% of the random blocks would have done better. The lexicon does neither better nor worse than chance.

**Why it happens.** A real news item on a single company produces the largest widenings of the spread, and in these three months many of those widenings closed again within the day anyway: 23 of the 48 blocked trades would have exited on reversion, with +29.5 bps on average. The largest examples are real acquisitions: Silver Lake in talks to buy Workday (13 August, the blocked trade would have earned 985 bps) and a buyout proposal for PayPal (15 July, 564 bps).

**But be careful.** The result depends on very few cases. The median of the blocked trades (the central value) is 7.6 bps, practically like the general mean. Removing the 3 largest trades, the mean profit of the blocked ones becomes -6.6 bps, i.e. the agent would have done well. So the honest conclusion is: **there is no evidence that blocking on the news helps**, and there is a fragile indication that it removes some of the best trades.

**The case of the lexicon with costs.** With a cost of 5 bps the lexicon B loses 10,428 dollars instead of 12,221, so it looks better than A. Not because it chooses well: at that cost every trade loses on average, and whoever makes fewer trades pays fewer costs. Blocking 166 trades at random would give the same effect.

## 7. Results of version C: following the news

| Set | Trades that follow the news | Their mean profit | A on the same signals | Difference from A, cost 0 |
|---|---|---|---|---|
| `spark_24h` | 13 | -154.9 bps | +125.7 bps | -3,348 $ |
| `spark_6h` | 9 | -224.9 bps | +182.6 bps | -3,444 $ |
| `lexicon` | 61 | -16.0 bps | +16.0 bps | -2,502 $ |

Following the news means making the bet opposite to A. When A earned (the spread reverted), C loses the same amount; when A lost, C earns. The two differ only if A exits on stop, because C has no stop. On these signals A earned, so C loses. Above all three signals of Salesforce-Workday on 13 August weigh (-985 and -615 bps the two worst).

With 9-13 trades (61 for the lexicon) these are cases to read one by one, not a statistic.

## 8. The sample of 40 signals

On 40 signals the group classified the news by hand. Result:

- agent and group take the **same decision on 38 signals out of 40 (95%)**;
- with reasoning on, the agent's decisions do not change;
- the two disagreements: on signal 489 (Home Depot-Lowe's) the group blocks and the agent does not, on 901 (PayPal-Block) the opposite. In both cases A earned (64 and 82 bps).

So the agent classifies the news more or less as a person would: the problem is not that the agent reads wrongly, but that the rule "real fact on a company, so do not enter" did not work in this period.

## 9. The equity curves

![Equity curves of the versions](equity_curves.png)

Each line shows how the capital grows (or falls) day after day, at cost 0: A (black) and the three variants closest to it, the candidates for the test, each with its reference (the delayed A, dashed, for the variants that enter 5 or 15 minutes later). A stays above the three candidates; only `b_exaggeration` (grey), whose rule was written after seeing these results, ends above it. The jump of mid-August is 13 August, the Salesforce-Workday day. The comparison with all the variants and costs is in [version_comparison.csv](version_comparison.csv).

## 10. The test: the chosen variant, on data never seen

**Which variant.** Besides the main agent (`spark_24h`), the group tried other variants on the train: different models, different news windows, FinBERT (a model that gives each news item a positive or negative score), text rules. 21 in all, listed in [src/agent_variants/README.md](../src/agent_variants/README.md). None beat A. The group chose the one that lost the least considering B and C together and entered at the time of the signal like A: **`finbert_episode`**. It reads the news published while the spread was moving away from the mean; it blocks if it finds a strong news item on a single company with a word like "acquisition", "investigation", "resignation"; it follows the news if its score goes in the same direction as the move.

**The rules, written beforehand.** Before downloading the test data the group wrote in [docs/Test.md](../docs/Test.md) what to try and how to judge it: only `finbert_episode`, with A, B and C; main criterion the dollar difference from A at cost 0; the same checks as the train. The test was done only once and is not redone.

**The results, at cost 0.**

| | Test (32 days) | Train (64 days) |
|---|---|---|
| A, no agent | 500 trades, +4.9 bps per trade, **+2,472 $** | 973 trades, +7.4 bps, +7,239 $ |
| B, the agent blocks | 493 trades, **-189 $** relative to A | -285 $ |
| C, the agent blocks or follows | 495 trades, **-1,242 $** relative to A | -651 $ |

How to read it:

- **The base strategy holds, but earns less.** The break-even cost drops to 1.24 bps per operation; with 5 bps A loses 7,528 dollars.
- **Blocking does not help.** The agent blocks 7 trades, which would have earned on average +27 bps, against +4.6 for the others. 90% of the random blocks would have done better. Looking at the news one sees why: the blocks come from press releases of law firms that "investigate" and from acquisitions made by the company itself, i.e. news that do not really push the two prices apart.
- **Following the news makes things worse.** In 21 cases C bets in the direction of the news: it is right only 5 times out of 21 (24%; in the train it was 55%).
- **Luck or real?** Resampling the days, the difference of B goes from -527 to +135 dollars: it cannot be told apart from A. That of C goes from -2,183 to -374: it is worse than A with some confidence.
- **Same direction as the train.** In all the comparisons (B and C, cost 0 and 5) the difference from A is negative, as in the train. In the train the loss of B came from a single trade on PayPal-Block; in the test it is spread over several pairs.
- **Market neutral.** The link with the S&P 500 is minimal (beta -0.04), as in the train.

![Equity curves of the test](test/equity_curves.png)

**The +1 / 0 / -1 signal asked by the professor.** The course instructions ask that the strategy say, for each stock and in each minute, whether to buy it (+1), sell it short (-1) or not hold it (0), and that the profit be computed as the return of the stock times that signal. We reason in pairs, but it is the same thing: in a trade "buy Coca-Cola and sell Pepsi" Coca-Cola has +1 and Pepsi -1. [src/08_signal.ipynb](../src/08_signal.ipynb) writes this signal for the 30 stocks, on the train and on the test, and recomputes the profit with the professor's formula: it comes out practically the same (for the test A 2,477 dollars instead of 2,472) and the differences of B and C from A do not change.

**The strategy against the market.** As the professor asks, [src/09_curves_metrics.ipynb](../src/09_curves_metrics.ipynb) compares the three versions with SPY, the S&P 500 bought and held, starting from 100 (returns from the signal, cost 0):

| | A, no agent | B, the agent blocks | C, the agent blocks or follows | SPY |
|---|---|---|---|---|
| **Train:** profit over the period | +2.42% | +2.32% | +2.20% | +0.15% |
| annual swing (volatility) | 1.2% | 1.1% | 1.2% | 11.7% |
| largest loss from a peak | -0.14% | -0.14% | -0.14% | -3.4% |
| Sharpe | 8.2 | 8.2 | 7.5 | 0.1 |
| **Test:** profit over the period | +0.83% | +0.76% | +0.41% | +0.47% |
| annual swing (volatility) | 1.3% | 1.3% | 1.2% | 11.4% |
| largest loss from a peak | -0.17% | -0.19% | -0.21% | -3.0% |
| Sharpe | 4.9 | 4.7 | 2.8 | 0.4 |

Without costs all three swing much less than the stock market, because they are invested only during the day and in a few trades at a time; with 5 basis points of cost they all lose (on the test -2.5% A and B, -2.9% C). The agent does not help: B is almost the same as A, C worse, and on the test it earns less even than SPY. None of the three follows the stock market: on the test days when SPY falls they earn a little on average (+4.0 basis points a day A, +3.6 B, +2.8 C).

**Is the Sharpe higher than SPY's just luck?** The professor gives an extra point if on the test the strategy has a higher Sharpe and a lower drawdown than the market, and if a statistical test confirms the Sharpe difference. The drawdown is lower for all three. For the Sharpe we redrew at random 10,000 times the 32 days of the test, the same for the strategy and for SPY: the difference in favour of A goes from -4.6 to +12.5 (95% interval), and in about one draw in seven SPY has the higher Sharpe; for B and C it is similar or worse. Since the interval contains zero, the difference is not confirmed and the extra point cannot be claimed. The reason is that 32 days are few to measure the Sharpe of the stock market.

![Equity curve from 100, test](test/equity_curve_100.png)

## 11. What we can conclude, and what we cannot

We can say:

- the base strategy has a small gross profit, which does not survive realistic costs;
- on the train, no way of using the news that we tried improves the strategy;
- on the test, the chosen variant does not improve the strategy: blocking cannot be told apart from A, following the news is worse;
- the agent reads the news in a way similar to the group (95% agreement).

We cannot say:

- that the agent is harmful in general: the difference depends on 2-3 trades and one day;
- that the strategy will or will not work in the future: the test covers 32 days, with 7 blocks and 21 news followed;
- that no news agent can work: we tried a single variant on the test, with simple rules;
- that a variant other than `finbert_episode` would have done better on the test: trying them now, after seeing the results, would mean fitting to the test data.

## 12. Limits

- **Train and test.** The signal and the rules of the agent were built on the train, so the train results are optimistic. The test is more honest but short: 32 days.
- **The test has more news.** 2,725 news in 44 calendar days, against 2,106 in 108 in the train: the October earnings season probably weighs.
- **The test rules** were written before the run but committed to git afterwards: there is no proof on git of the order. The criterion with which the variant was chosen was made precise after seeing the train, but before the test.
- **Few cases.** 25-166 blocks and 9-61 trades that follow the news: every conclusion is fragile.
- **The C rule is ours**: no stop, exit at 90 minutes. In 2 cases a trade that follows the news is still open when the next signal of the same pair arrives, and so uses the capital of that pair twice.
- **The lexicon** is a ready-made file: the code that produces it is not in this repository.
- **Estimated costs**, not measured; no cost for borrowing the stocks sold short; part of the trades use a price of a minute without trades (stale price).
- **The model may "know" the future.** If it was trained on texts later than June 2026 it may recognise the events. To reduce the risk the company names are replaced with "Company A" and "Company B", but that is not enough to rule it out.

## 13. What remains to be done

The test is done and the bootstrap, beta and alpha are computed on both the train and the test. What remains:

1. write the report and the presentation, stating the limits of section 12;
2. do not redo the test and do not change rules by looking at its results.

## Where the files are

| File | Content |
|---|---|
| [version_comparison.csv](version_comparison.csv) | All the variants: metrics and difference from the reference, at cost 0 and 5 |
| [blocked_vs_random.csv](blocked_vs_random.csv) | Blocked trades: reversion share and comparison with a random block |
| [news_right_C.csv](news_right_C.csv) | Version C: how many times the followed news was right |
| [candidates.csv](candidates.csv) | The 3 candidates for the test according to the group's criterion (dollars at cost 0, rule written beforehand) |
| [B_and_C_by_variant.csv](B_and_C_by_variant.csv) | B and C of the same variant side by side: differences, ranks, right news |
| [comparison_sample_40.csv](comparison_sample_40.csv) | The 40 signals of the sample |
| [A_by_cost.csv](A_by_cost.csv), [A_by_pair.csv](A_by_pair.csv) | Version A per cost and per pair |
| [trades_A.csv](trades_A.csv), `agent_variants/<variant>/trades_*.csv` | Every trade of every version |
| [agent_variants/spark_24h/agent_decisions_15pairs_v2_train.csv](agent_variants/spark_24h/agent_decisions_15pairs_v2_train.csv) | The decisions of the main agent, signal by signal |
| [robustness/](robustness/final_table.csv) | Step 7: bootstrap, beta and alpha, costs, pairs, sectors, period |
| [test/version_comparison.csv](test/version_comparison.csv) | Test: A, B and C of `finbert_episode`, at cost 0 and 5, with the difference from A |
| [test/consistency_with_train.csv](test/consistency_with_train.csv) | Test: the difference from A, next to that of the train |
| [test/blocked_vs_random.csv](test/blocked_vs_random.csv), [test/news_right_C.csv](test/news_right_C.csv) | Test: the blocks and the trades that follow the news, next to the train |
| [test/robustness/](test/robustness/final_table.csv) | Test: bootstrap, beta and alpha, costs, pairs, sectors, without PYPL-XYZ |
| [test/decisions.csv](test/decisions.csv), `test/trades_*.csv` | Test: the decisions of the agent and every trade of A, B and C |
| `signal_A.parquet`, `agent_variants/finbert_episode/signal_*.parquet`, `test/signal_*.parquet` | The +1/0/-1 signal per stock and per minute of A, B and C, train and test |
| [signal_returns.csv](signal_returns.csv), [test/signal_returns.csv](test/signal_returns.csv) | Daily return of A, B and C computed from the signal |
| [signal_vs_trade_comparison.csv](signal_vs_trade_comparison.csv) | Profit from the trades and from the signal, compared |
| [metrics_train_test.csv](metrics_train_test.csv) | Metrics of A, B, C and SPY on train and test: cumulative and annualised return, volatility, Sharpe, drawdown, profit factor |
| [market_neutrality.csv](market_neutrality.csv) | Beta, correlation with SPY and return on the days when SPY falls |
| [test/sharpe_vs_spy.csv](test/sharpe_vs_spy.csv) | Test: Sharpe difference of A, B and C from SPY with the bootstrap interval, and the drawdowns |
| [equity_curve_100.png](equity_curve_100.png), [test/equity_curve_100.png](test/equity_curve_100.png) | Equity curves from 100 with SPY, train and test |

The agent's free-text reasons in the decision tables (columns `reason`, `rationale`) are in Italian: the model was asked to write them in Italian, and they are kept as the model wrote them.

To redo everything: [src/README.md](../src/README.md), steps 6 and 7. The test is not redone: its results are read with the notebooks `06_test_backtest.ipynb` and `07_test_robustness.ipynb`.
