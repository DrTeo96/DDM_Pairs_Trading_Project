# Post-train experiment: where the agent blocks well

**This experiment was decided on 13 November 2026, after seeing the train results in [../../REPORT.md](../../REPORT.md).** It is not part of the rules fixed before the results. The numbers come from [src/agent_variants/post_train.py](../../../src/agent_variants/post_train.py) (`uv run python -m src.agent_variants.post_train`) and concern only the **training period** (train, from 16 June to 16 September 2026). The test was not used.

## In short

- In the backtest version B (the agent blocks a real fact on a single company) removes 48 trades that earned **more** than the average: +27.8 basis points against +7.4.
- Looking inside those 48 blocks, they behave in three different ways depending on the **direction** of the news and the **move** of the stock in the 30 minutes before.
- A variant of B, **B_exaggeration**, enters when the news confirms the move instead of blocking. On the train it beats A by about **+0.6 basis points per trade**, in both halves of the period.
- **It is not a proof**: the variant was built by looking at these same numbers, and the result depends on a few cases. It is a hypothesis to check on new data.

## 1. The three cases

When the agent finds a real fact (acquisition, investigation, fraud, change of management) on only one of the two companies, it also says whether the news is **positive**, **negative** or **uncertain** for that company. The rule of version C compares this direction with the move of the stock against the other in the 30 minutes before the signal. Three cases follow:

| Case | What it means | Example |
|---|---|---|
| **Confirms** | Positive news and the stock rose against the other, or negative and it fell | Silver Lake in talks to buy Workday, and Workday rises against Salesforce |
| **Contradicts** | The news goes in the direction opposite to the move | Positive news, but the stock falls against the other |
| **Uncertain direction** | The agent cannot say whether the news is good or bad, or several real news on the same stock go in different directions | |

## 2. How much they would have earned

The profit is the one the trade would have made in version A, i.e. entering anyway and betting on the reversion.

| Case | Trades | Mean profit | Central value (median) | In profit |
|---|---|---|---|---|
| Confirms | 13 | +125.7 bps | +15.4 bps | 69% |
| Contradicts | 17 | +7.2 bps | +17.7 bps | 59% |
| Uncertain direction | 18 | -23.4 bps | -14.0 bps | 44% |
| No block in B | 925 | +6.4 bps | +10.9 bps | 60% |

How to read it:

- **Confirms**: on average they earn a lot, but the median is +15: the result depends on two days, PayPal (15 July) and Workday (13 August). When the news confirms the move, the market has already reacted and has often overdone it: the spread reverts.
- **Contradicts**: they earn like the normal trades.
- **Uncertain direction**: it is the only group that loses. It is an observation, not a rule: it is based on 18 trades and emerged by looking at these data.

## 3. The B_exaggeration variant

**What it does.** It uses the decisions that the agent already produces, without new calls to the model: it blocks where version C blocks (contradicts and uncertain direction, 35 trades) and enters on the reversion, like A, where C would follow the news (confirms, 13 trades).

Results at cost 0 (main scenario, as in the backtest report):

| Version | Trades | Mean profit per trade | Total profit | Sharpe | 1st half | 2nd half |
|---|---|---|---|---|---|---|
| A, no agent | 973 | +7.44 bps | +7,239 $ | 8.13 | +9.17 | +5.59 |
| B of the backtest | 925 | +6.38 bps | +5,905 $ | 8.06 | +8.47 | +4.13 |
| **B_exaggeration** | 938 | **+8.04 bps** | **+7,539 $** | **8.30** | **+9.72** | **+6.22** |

The blocked trades, against random blocks of the same number (5,000 draws, same function as the backtest):

| Version | Blocked | Mean profit of the blocked ones | Random blocks, on average | p-value |
|---|---|---|---|---|
| B of the backtest | 48 | +27.8 bps | +7.3 bps | 0.97 |
| B_exaggeration | 35 | -8.6 bps | +7.5 bps | 0.044 |

A small p-value means that few random blocks would have removed trades as bad: B_exaggeration chooses better than chance, the B of the backtest worse.

With 5 basis points of cost per operation all the versions lose, as in the backtest report: B_exaggeration loses a bit less than A (-11,221 $ against -12,221 $).

## 4. What we can conclude, and what we cannot

We can say:

- the agent does not read the news badly (95% agreement with the group on the sample of 40): the problem of B is the rule, which also blocks cases in which the gap reverts;
- inside the blocks there is a structure that depends on the direction of the news.

We cannot say:

- that B_exaggeration is better than A in general: it was chosen by looking at the same data it is measured on;
- that the story "the market overreacts when the news confirms the move" is true: it is based on 13 trades and two events;
- anything about the test, which was not used.

## 5. If the variant goes to the test

It must be decided **before** opening the test, written down with the date and declared as a choice made after seeing the train. It must be counted as one more try (for example in the Deflated Sharpe Ratio). On the test of about 32 days, the difference from A (about +0.6 basis points per trade) would have an uncertainty of about 0.5 basis points: visible as an estimate, not as strong evidence.

## Where the files are

| File | Content |
|---|---|
| [by_case.csv](by_case.csv) | Profit of the 48 B blocks per case (confirms, contradicts, uncertain direction) |
| [blocks_B.csv](blocks_B.csv) | The 48 blocks one by one, with direction, move, profit and reason given by the agent (the agent's reason is in Italian, as its prompt asked) |
| [comparison.csv](comparison.csv) | A, B and B_exaggeration at cost 0 and 5, with the two halves of the train |
| [blocked_vs_random.csv](blocked_vs_random.csv) | Blocked trades against random blocks |
| [trades_B_exaggeration.csv](trades_B_exaggeration.csv) | Every trade of the variant |
| [equity_curves.png](equity_curves.png) | Equity curves at cost 0 |
