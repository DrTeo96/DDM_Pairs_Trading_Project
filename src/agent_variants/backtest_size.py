"""Variant 12 (point 3): reduce instead of blocking. Every A trade has a size of 1, 0.5 or 0; dollar profit and costs
are multiplied by the size. Rules written in LOG.md before the run.

It reads the decisions in Results/agent_variants/; it writes to Results/agent_variants/size/: size.csv and the trades of each variant
(trades_<name>.csv, at cost 0, with the size column and pnl_usd already multiplied by the size).
Usage: uv run python -m src.agent_variants.backtest_size
"""
import numpy as np
import pandas as pd
from src.backtest import add_costs, apply_version, load_trades, summary, trading_days
from src.config import AGENT_DECISIONS_COPY, DEC_3B_6H, DEC_FINBERT_SESSION, RESULTS, VARIANTS

OUT = VARIANTS / "size"

pd.options.display.float_format = "{:,.2f}".format
pd.options.display.width = 200
A, days = apply_version(load_trades(), "A"), trading_days()

spark = pd.read_csv(AGENT_DECISIONS_COPY).set_index("signal_id")
b3 = pd.read_csv(DEC_3B_6H).set_index("signal_id")
fb = pd.read_csv(DEC_FINBERT_SESSION, keep_default_na=False).set_index("signal_id")
s = A.signal_id

SIZES = {
    "A, no agent": pd.Series(1.0, index=s.values),
    "B spark_24h, block (Giulio)": spark.decision.map({"block": 0.0, "enter": 1.0}).reindex(s).values,
    "12a spark_24h with its own size": np.where(spark.decision.reindex(s) == "block", 0.0, spark["size"].reindex(s)),
    "12b spark_24h, block = 0.5": spark.decision.map({"block": 0.5, "enter": 1.0}).reindex(s).values,
    "12c 3B 6h, block and reduced = 0.5": np.where(b3.decision_full.reindex(s).isin(["block", "enter_reduced"]), 0.5, 1.0),
    "12d FinBERT, strong news = 0.5": np.where(fb.n_strong.reindex(s) > 0, 0.5, 1.0),
}

# the saved trades: only the variants 12a-12d (A and the spark_24h B are already in their folders)
TRADE_FILES = {"12a spark_24h with its own size": "spark24h_agent_size", "12b spark_24h, block = 0.5": "spark24h_block_half",
               "12c 3B 6h, block and reduced = 0.5": "3b_half", "12d FinBERT, strong news = 0.5": "finbert_strong_half"}

rows = []
for name, size in SIZES.items():
    size = np.asarray(size, dtype=float)
    assert not np.isnan(size).any(), f"{name}: size missing for some signal"
    for c in (0, 5):
        t = add_costs(A, c)
        t["pnl_usd"] = t.pnl_usd * size
        port = summary(t[size > 0], days)     # the portfolio metrics use pnl_usd, already weighted
        w = size[size > 0]
        rows.append({"variant": name, "cost_bps": c, "trade": int((size > 0).sum()), "reduced": int((size == 0.5).sum()), "blocked": int((size == 0).sum()),
                     "net_bps_per_dollar": float(np.average(t.net_bps[size > 0], weights=w)), "pnl_usd": port["pnl_usd"],
                     "total_return": port["total_return"], "sharpe": port["sharpe"], "max_drawdown": port["max_drawdown"]})
    # how do the reduced trades do: do they revert less than the others? (gross, without costs)
    red = A[size == 0.5]
    if len(red):
        print(f"{name}: {len(red)} reduced trades, reversion {red.exit_reason.eq('reversion').mean():.0%} (all {A.exit_reason.eq('reversion').mean():.0%}), "
              f"mean gross {red.gross_bps.mean():.1f} bps, median {red.gross_bps.median():.1f}")

out = pd.DataFrame(rows)
print()
print(out.to_string(index=False))
OUT.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT / "size.csv", index=False)
for name, slug in TRADE_FILES.items():
    size = np.asarray(SIZES[name], dtype=float)
    t = add_costs(A, 0).assign(size=size)
    t["pnl_usd"] = t.pnl_usd * size
    t[size > 0].to_csv(OUT / f"trades_{slug}.csv", index=False)
print(f"\nsaved in {OUT.relative_to(RESULTS.parent)}: size.csv and " + ", ".join(f"trades_{s}.csv" for s in TRADE_FILES.values()))
