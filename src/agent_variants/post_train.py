"""Post-train experiment: where the agent blocks well. OUTSIDE the pipeline fixed before the results.

Written on 13 November 2026, AFTER seeing the train results in 06_backtest.ipynb: the choices in here were made by
looking at the same data they are measured on, so the numbers are optimistic. It uses only the train (load_trades refuses the test).
From the project folder:
    uv run python -m src.agent_variants.post_train    prints the tables and saves them in Results/agent_variants/post_train/

Starting point. In Step 6, version B (the agent blocks a structural fact on a single stock) removes trades that earned
more than the average. Here we look inside those blocks, with information that the agent already produces (no new model call):
- the direction of the news according to the agent (positive, negative, uncertain);
- the move of the stock with the news against the other in the 30 minutes before the signal, the same as the C rule in agent.py.
Three cases:
- confirms: positive news and the stock went up against the other, or negative and the stock went down (in C: 'follow');
- contradicts: direction of the news opposite to the move;
- uncertain direction: the agent cannot say whether the news is good or bad, or several structural news have different directions.
A variant of B, born by looking at the train results:
- B_exaggeration: blocks contradicts and uncertain direction, enters when the news confirms the move (in C: 'follow').
The table by case also shows which of the three groups loses: it is an observation, not one more variant.
Costs as in Step 6: main scenario 0 (the lecturer's indication), MAIN_COST per operation as a comparison.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.backtest import MAIN_COST, add_costs, apply_version, blocked_vs_random, daily_pnl, load_trades, save_results, summary, trading_days
from src.config import AGENT_DECISIONS, AGENT_DECISIONS_COPY, RESULTS, RUN_24H, VARIANTS

OUT = VARIANTS / "post_train"
CASES = ["confirms", "contradicts", "uncertain direction", "no block in B"]


def load_decisions() -> pd.DataFrame:
    """The decisions of the main agent (spark_24h): the full run if it is on the computer, otherwise the copy on git in Results/."""
    for p in (RUN_24H, AGENT_DECISIONS, AGENT_DECISIONS_COPY):
        if p.exists() and "decision_C" in pd.read_csv(p, nrows=0):
            print(f"decisions from {p.relative_to(RESULTS.parent)}")
            return pd.read_csv(p)
    raise FileNotFoundError("no table of agent decisions with the decision_C column")


def classify(trades: pd.DataFrame, dec: pd.DataFrame) -> pd.DataFrame:
    """For each signal the case: confirms, contradicts, uncertain direction, or no block in B."""
    m = dec.merge(trades[["signal_id", "pair", "t_signal", "ticker_A", "ticker_B", "ret_A_30m", "ret_B_30m", "gross_bps", "exit_reason"]],
                  on="signal_id")
    one = (m.category == "structural") & (m.ticker != "both")
    m["rel"] = np.where(m.ticker == m.ticker_A, m.ret_A_30m - m.ret_B_30m, m.ret_B_30m - m.ret_A_30m)   # move of the stock with the news
    m["case"] = np.select([~one, m.news_direction == "uncertain", (m.news_direction == "positive") == (m.rel > 0)],
                          ["no block in B", "uncertain direction", "confirms"], default="contradicts")
    # the cases match the C rule in agent.py
    assert (m[m.case == "confirms"].decision_C == "follow").all()
    assert (m[m.case.isin(["contradicts", "uncertain direction"])].decision_C == "block").all()
    return m


def main() -> None:
    pd.options.display.float_format = "{:,.2f}".format
    pd.options.display.width = 250
    pd.options.display.max_columns = None
    trades, days = load_trades(), trading_days()
    dec = load_decisions()
    b0 = add_costs(apply_version(trades, "B", dec), 0)
    assert len(b0) == 925 and round(b0.gross_bps.mean(), 2) == 6.38, "the decisions are not those of Step 6"

    m = classify(trades, dec)
    by_case = m.groupby("case").gross_bps.agg(trade="size", gross_mean_bps="mean", median_bps="median",
                                              share_winning=lambda x: (x > 0).mean()).loc[CASES]
    print("\n1. The B blocks by case (profit the trade would have made in A):")
    print(by_case)

    variants = {
        "B (Step 6)": dec[["signal_id", "decision"]],
        "B_exaggeration": m.assign(decision=np.where(m.decision_C == "block", "block", "enter"))[["signal_id", "decision"]],
    }
    books = {"A": apply_version(trades, "A")} | {k: apply_version(trades, "B", v) for k, v in variants.items()}
    half = {"1st half": days[:len(days) // 2], "2nd half": days[len(days) // 2:]}
    rows = []
    for name, t in books.items():
        for c in (0, MAIN_COST):
            x = add_costs(t, c)
            s = summary(x, days)
            r = dict(version=name, cost_bps=c, trade=s["trade"], gross_bps=s["gross_bps"], net_bps=s["net_bps"], se_bps=s["se_bps"],
                     win_rate=s["win_rate"], profit_factor=s["profit_factor"], pnl_usd=s["pnl_usd"], sharpe=s["sharpe"],
                     max_drawdown=s["max_drawdown"])
            for h, d in half.items():
                r[f"net_bps {h}"] = x[x.day.isin(d)].net_bps.mean()
            rows.append(r)
    comparison = pd.DataFrame(rows).set_index(["version", "cost_bps"])
    print("\n2. The variant against A and B:")
    print(comparison)

    blocked = pd.DataFrame({k: blocked_vs_random(trades, v) for k, v in variants.items()}).T
    print("\n3. Blocked trades against random blocks of the same number:")
    print(blocked)

    OUT.mkdir(parents=True, exist_ok=True)
    cols = ["signal_id", "pair", "t_signal", "ticker", "news_direction", "rel", "gross_bps", "exit_reason", "reason", "case"]
    written = save_results({"agent_variants/post_train/by_case": by_case, "agent_variants/post_train/comparison": comparison,
                            "agent_variants/post_train/blocked_vs_random": blocked,
                            "agent_variants/post_train/blocks_B": m[m.case != "no block in B"][cols].reset_index(drop=True),
                            "agent_variants/post_train/trades_B_exaggeration": add_costs(books["B_exaggeration"], 0)})
    fig, ax = plt.subplots(figsize=(11, 4.5))
    for name, t in books.items():
        d = daily_pnl(add_costs(t, 0), days)
        ax.plot(d.index, 100 * (1 + d.equity), label=name, lw=2 if name == "A" else 1.3, color="k" if name == "A" else None)
    ax.axhline(100, color="grey", lw=0.6)
    ax.set_title("Equity curve at cost 0, train (start = 100)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "equity_curves.png", dpi=150)
    plt.close(fig)
    print("\nsaved:", ", ".join(str(p.relative_to(RESULTS.parent)) for p in written), "and Results/agent_variants/post_train/equity_curves.png")


if __name__ == "__main__":
    main()
