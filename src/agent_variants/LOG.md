# Log of the agent variants (train only, test never read)

Log kept by Beatrice during the tries (13 November 2026), copied here as it was; only the file paths changed, which are now in
`Results/agent_variants/`. Translated from Italian in November 2026, with the variant and file names of the English version of the code
(for example `lessico` became `lexicon`, `finbert_seduta` became `finbert_session`): the rules, dates and outcomes are unchanged.
The index of all the variants, with code and commands, is in [README.md](README.md).

Each variant is written here **before** it is launched, with rule, reason and thresholds. It is launched only once and is not retouched after
seeing the results. All the variants, including those that went badly, go into the report with the total number of tries.

## Variants already tried

| # | Variant | Who | Outcome on the train (gross, cost 0) |
|---|---|---|---|
| 1 | B `spark_24h` (Spark X2.6 4B, 24 hours) | Giulio | 925 trades, +6.38 bps (A: +7.44) |
| 2 | C `spark_24h` | Giulio | +4.15 bps |
| 3 | B `spark_6h` | Giulio | +6.14 bps |
| 4 | C `spark_6h` | Giulio | +3.97 bps |
| 5 | B `lexicon` (Loughran-McDonald) | Giulio | +7.08 bps |
| 6 | C `lexicon` | Giulio | +5.46 bps |
| 7 | B `spark_24h_reasoning` and `manual` (only 40 signals) | Giulio | sample |
| 8 | B 3B 6 hours, full prompt, keyword filter | us | 958 trades, +7.03 bps |
| 9 | B FinBERT, window tied to the session | us | 964 trades, +7.02 bps; blocked: 1 in 9 reverts |
| 10 | C FinBERT, window tied to the session | us | +6.05 bps; news right 40% |

## Variant 11 (point 1, rule-based): has the price become definitive?

Written on 13 November 2026, before searching the news.

**Reason.** A definitive acquisition with a fixed price pins the price of the target close to the offer: the spread of the pair cannot
revert. Talks, a rumour or an unagreed offer often cause an excessive reaction, which can revert. The buyer and the
other news (results, analysts, products) are noise for this rule.

**News considered.** News that tag at least one of the 30 stocks and have at most 3 tickers in total (no lists).

**Text rules (headline and summary, in English):**
1. It is an M&A news item if it contains acquisition or merger words (acquire, merger, takeover, buyout, deal to buy, bid for, tender offer, go private...).
2. Stage: **definitive** if there is a signed agreement or a fixed price (definitive agreement, agreed to acquire / be acquired, to be acquired by,
   per share, all-cash, all-stock); **talks** if there are words of uncertainty (in talks, exploring, considering, weighs, reportedly,
   people familiar, approach, bid, offer, interest, could, may, potential); **completed** if the deal is closed (completes, completed, closes);
   **approval** if it is a green light from an authority. If both definitive and uncertain words appear, it counts as **talks**.
3. Role of each stock of the pair: **target** if it is the one being bought (acquire / buy / offer for <company>, <company> to be acquired / sold to),
   **buyer** if it is the one buying (<company> to acquire / acquires / agrees to acquire / buys), otherwise **mentioned**.

**Decisions (to be applied after showing the list to the group, without changing the rules):**
- B: `block` if in the window tied to the session (overnight gap: from the last close; rest of the session: from 9:30) there is a
  **definitive** M&A news item in which a stock of the pair is the **target**. Otherwise `enter`.
- C: no `follow`: with the price of the target pinned to the offer, following the news has no economic reason.

**Variant 11b (perfect agent).** The M&A news found are also classified by hand (stage and role). The same decisions with the hand
labels say how much the rule is worth if the classifier never makes a mistake.

**Outcome (13 November).** 61 M&A news on the 30 stocks; no definitive acquisition of one of the 30 companies (the targets are only two
sets of talks: PayPal on 15 July, Workday on 13 August). Variant 11 blocks no trade: on the train it coincides with A and its hypothesis
cannot be checked. List in `Results/agent_variants/ma_rules/ma_news.csv`.

## Variant 12 (point 3): reduce instead of blocking

Written on 13 November 2026, before launching it.

**Reason.** The plan foresees "enter, possibly with a reduced size". The blocks sometimes remove the best trades (the large moves
that revert): halving the amount limits the losses of the trades with a news item without losing entirely the profits of those that revert.

**How it is computed.** Each trade has a size: 1 (10,000 dollars per leg), 0.5 or 0. Dollar profit and costs are multiplied by the
size (costs are proportional to the amount). We report dollars, return on capital (always 300,000 dollars), Sharpe and mean profit
per dollar invested (mean of the bps weighted by the size). Costs 0 and 5 bps per operation.

**Variants (no new run of the models):**
- 12a: Giulio's `spark_24h` with its `size` column: 0.5 if there is noise on a stock, 1 otherwise, 0 if it blocks.
- 12b: Giulio's `spark_24h`, reduce instead of blocking: block becomes 0.5, everything else 1.
- 12c: our 3B 6 hours: block and `enter_reduced` become 0.5, everything else 1.
- 12d: FinBERT with the window tied to the session: 0.5 if there is at least one targeted news item with strong sentiment (113 signals), 1 otherwise.

**Outcome (13 November), cost 0.** No variant beats A in dollars (A +7,239 $; 12a +4,075; 12b +6,572; 12c +6,818; 12d +6,137).
The Sharpe of 12b (8.59) and 12d (8.29) is just above that of A (8.13): not a significant difference over 64 days. In all the variants the
reduced trades earned more than the average (from +9.8 to +27.8 gross bps). Table in `Results/agent_variants/size/size.csv`.

## Variant 13 (point 5): C only on fresh and strong news

Written on 13 November 2026, before launching it.

**Reason.** An important news item just published during the session may not yet be fully in the price (underreaction and drift after
news, literature to be checked before citing it): the widening of the spread can continue. An overnight news item instead is already
incorporated in the opening gap, and that gap tends to revert: there we never follow.

**Rule.** `follow` only if all of these hold:
1. the signal is not in the overnight gap (minutes 15-29 from the open);
2. there is a news item published during today's session (from 9:30) and within 60 minutes before the signal;
3. the news item is targeted: it tags only one of the two companies and has at most 3 tickers;
4. the news item has a strong event: an event word (acquisition, investigation, resignation...) or a guidance change (same expressions as our 3B agent);
5. FinBERT gives a clear direction: probability of the winning class at least 0.8;
6. the direction of the news for the pair (positive on A or negative on B = A rises against B) has the same sign as the relative move
   of the 30 minutes before the signal.
The trade goes in the direction of the news and exits as in Giulio's C (reversion, 90 minutes, end of the day; no stop). In all the other cases
`enter` as A: the differences from A come only from the trades that follow the news.

**Outcome (13 November).** No `follow`: the variant coincides with A and its hypothesis cannot be checked on the train. The news with an event,
strong sentiment and at most 3 tickers are 59 out of 2,106; none is published during the session in the 60 minutes before a signal outside the gap (the
two found are before gap signals). Descriptive: of the 516 signals outside the gap, 34 have any targeted news item in the 60 minutes
before and 16 one with strong sentiment, but none with an event. Decisions in `Results/agent_variants/c_fresh/decisions.csv`.

## Variants 14 and 15: news at the same time as the move (episode window)

Written on 13 November 2026, before launching them.

**Reason.** The right question is not "is there a news item in the last N hours?" but "is there a news item that explains *this* widening?". We look at
the news published while the spread was moving away from the mean, up to the moment of the decision.

**Moment of the decision (checked).** The bars are labelled with their starting minute: the z-score of the signal uses the close of the
`t_signal` bar and the entry is at the open of the next bar. The decision is therefore at the end of the signal bar: news with
`ts < t_signal + 1 minute` are used (before: `ts <= t_signal`, which excluded the news published during the signal bar).

**Start of the episode.** From the signal bar we go back as long as the z-score stays beyond 1 with the same sign as the signal, without leaving
the day. The episode starts at the first of these bars, with a 5-minute buffer before (a news item moves the price in a few seconds).
If the episode reaches the first bar of the day, the move was born overnight: we start from the close of the previous trading day (16:00).

**Rules on the news: the same as variants 9 and 10 (FinBERT)**, so that only the window changes:
- 14 (B): blocks if there is at least one targeted news item (a single company, at most 3 tickers) with strong sentiment (at least 0.8), all the strong ones
  are about the same company and at least one has an event word. Otherwise it enters.
- 15 (C): follows if the relative score (A minus B) has absolute value at least 0.5 and the same sign as the move of the 30 minutes before; otherwise as 14.
They are evaluated as in point 4 (reversion share of the blocked ones, random block, news right in C) and with the backtest at cost 0 and 5.

**Outcome (13 November), cost 0.** Episodes: 802 born in session (median length 11 minutes), 171 overnight. Only 96 signals have a targeted
news item in the episode (71 overnight, 25 in session), 3 in the signal bar. 14 B: 5 blocks, all in the overnight gap, none reverts
(p Fisher 0.06), mean gross +57 because of PayPal (+564), median -9; 968 trades, +6,955 $ (A +7,239). 15 C: 20 inverted trades, news right 55%,
mean gross -8.9, median +5.8; +6,589 $. Two blocks out of five come from "settle" in non-legal contexts (share buyback, FTC settlement
of another company). Table in `Results/agent_variants/finbert_episode/episode.csv`.

## Variants 16 and 17: deciding k minutes after the signal (option 3)

Written on 13 November 2026, before launching them.

**Reason.** A news item can be published right after the start of the move. To be able to read it without lookahead, both the
decision and the entry must be moved later. It is a strategy different from A: it is compared with a "delayed A" with the same delay, so the difference measures
only the value of the agent; the comparison between A and the delayed A measures the cost of waiting.

**Delays:** k = 5 and k = 15 minutes, fixed beforehand (two tries).

**Delayed A (A_k).** The same 973 signals. The decision is at the close of the `t_signal + k` bar, the entry at the open of the next bar,
in the same direction as A. Exit with the same rules as `signals.run_rules` (reversion, stop at z 3.5, 90 minutes, end of the day). No
trade if at the decision bar the spread has already reverted (z beyond the exit threshold) or if the day ends before the entry.
With k = 0 the simulation must reproduce exactly the 973 A trades (check).

**Agent (FinBERT, same rules as variants 14 and 15).** Window from the start of the episode (variant 14) to the close of the
decision bar. Relative 30-minute move for C computed up to the decision bar.
- 16 (B_k): blocks as 14; otherwise enters as A_k.
- 17 (C_k): follows as 15, in the direction of the news, exiting on reversion, 90 minutes or end of the day, without stop; otherwise as 16.

**Outcome (13 November), cost 0.** Check passed: with k = 0 the 973 trades match A. Cost of waiting: A delayed by 5 minutes
964 trades, +5.26 bps, +5,071 $; by 15 minutes 941 trades (32 signals already reverted), +7.18 bps, +6,752 $ (A: +7,239 $). Value of the agent
relative to the delayed A: k = 5, B 4 blocks (none reverts, median -49 bps), -75 $; C 22 trades followed, news right 45%, -788 $.
k = 15, B 6 blocks (1 reverts, median -63 bps), -63 $; C 23 followed, news right 35%, -1,227 $. Table in `Results/agent_variants/delay/delay.csv`.
