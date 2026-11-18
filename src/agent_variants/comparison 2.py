"""All the agent variants in a single format, for 06_backtest.ipynb (comparison) and 07_robustness.ipynb (checks). Train only.

Each variant is a set of trades with a reference: A for almost all of them, A delayed by the same time for the variants that
decide and enter k minutes after the signal. The differences (delta) are always variant minus reference.

    from src.agent_variants.comparison import references, all_variants, compare
"""
from dataclasses import dataclass
from math import comb

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.backtest import (DAYS_PER_YEAR, VERSIONS, add_costs, apply_version, available_versions, blocked_vs_random, daily_pnl, summary,
                          version_trades)
from src.config import SELECTED, SPY_DAILY, VARIANTS

DELAYS = (5, 15)
SIZE_VARIANTS = {   # variant -> (file in Results/agent_variants/size/, description)
    "spark24h_agent_size": ("trades_spark24h_agent_size.csv", "spark_24h: half size when the agent flags noise, block as in B"),
    "spark24h_block_half": ("trades_spark24h_block_half.csv", "spark_24h: half size instead of the block"),
    "3b_half": ("trades_3b_half.csv", "3b_6h: half size instead of the block and when the agent advises reducing"),
    "finbert_strong_half": ("trades_finbert_strong_half.csv", "FinBERT: half size with at least one targeted news item with strong sentiment"),
}


@dataclass
class Variant:
    name: str
    version: str         # B, C or "B reduced" (reduced size instead of the block)
    reference: str       # A, A_5min, A_15min
    before: bool         # rule written before seeing the train results
    description: str
    trades: pd.DataFrame


def _read(path) -> pd.DataFrame:
    t = pd.read_csv(path)
    for c in ("t_signal", "t_entry", "t_exit", "day"):
        if c in t:
            t[c] = pd.to_datetime(t[c])
    return t


def references(trades: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """A and the delayed A (decision and entry 5 or 15 minutes after the signal, produced by delay.py)."""
    return {"A": apply_version(trades, "A")} | {f"A_{k}min": _read(VARIANTS / f"delay/trades_A_{k}min.csv") for k in DELAYS}


def all_variants(trades: pd.DataFrame) -> list[Variant]:
    """Decision sets of VERSIONS (only the complete and available ones), reduced size, delayed entry, B_exaggeration."""
    out = [Variant(n, letter, "A", True, VERSIONS[n]["label"], t)
           for n in available_versions(complete=True) for letter, t in version_trades(trades, n).items() if letter != "A"]
    out += [Variant(n, "B reduced", "A", True, d, _read(VARIANTS / "size" / f)) for n, (f, d) in SIZE_VARIANTS.items()]
    out += [Variant(f"finbert_delay_{k}min", letter, f"A_{k}min", True,
                    f"Rules of finbert_episode, decision and entry {k} minutes after the signal", _read(VARIANTS / f"delay/trades_{letter}_{k}min.csv"))
            for k in DELAYS for letter in "BC"]
    out.append(Variant("b_exaggeration", "B", "A", False, "spark_24h that enters when the news confirms the move (Orfeo, after the results)",
                       _read(VARIANTS / "post_train/trades_B_exaggeration.csv")))
    return out


def listing(variants: list[Variant]) -> pd.DataFrame:
    """One row per variant and version: what is compared."""
    return pd.DataFrame([dict(variant=v.name, version=v.version, reference=v.reference, rule_before=v.before, description=v.description)
                         for v in variants]).set_index(["variant", "version"])


def same_as_reference(v: Variant, ref: dict) -> bool:
    """True if the variant makes exactly the same trades as its reference (for example a rule that never fires on the train)."""
    # signal, profit (an inverted trade changes sign) and size (the reduced-size variants have the same trades as A)
    key = lambda t: sorted(zip(t.signal_id, t.gross_bps.round(9), t["size"] if "size" in t else [1.0] * len(t)))   # noqa: E731
    return key(v.trades) == key(ref[v.reference])


# ---------------------------------------------------------------- comparison (06)

def compare(variants: list[Variant], ref: dict, days: pd.DatetimeIndex, costs=(0, 5)) -> pd.DataFrame:
    """Metrics of every variant and difference from its reference, per cost. Sorted by dollar delta at cost 0 (best first)."""
    rows = []
    for v in variants:
        for c in costs:
            s, r = summary(add_costs(v.trades, c), days), summary(add_costs(ref[v.reference], c), days)
            rows.append(dict(variant=v.name, version=v.version, cost_bps=c, reference=v.reference, rule_before=v.before, trade=s["trade"],
                             net_bps=s["net_bps"], win_rate=s["win_rate"], pnl_usd=s["pnl_usd"], delta_pnl_usd=s["pnl_usd"] - r["pnl_usd"],
                             sharpe=s["sharpe"], delta_sharpe=s["sharpe"] - r["sharpe"], max_drawdown_pct=100 * s["max_drawdown"]))
    out = pd.DataFrame(rows)
    order = out[out.cost_bps == costs[0]].sort_values("delta_pnl_usd", ascending=False)[["variant", "version"]].apply(tuple, axis=1)
    return out.set_index(["variant", "version", "cost_bps"]).reindex([(*k, c) for k in order for c in costs])


def by_variant(cmp: pd.DataFrame, follows: pd.DataFrame, cost: float = 0) -> pd.DataFrame:
    """B and C of the same variant side by side: dollar difference from the reference, rank in the comparison table (which is
    sorted by the difference at cost 0), share of right news in C. Only the variants that have both B and C.
    Sorted by the sum of the two differences."""
    c = cmp.xs(cost, level="cost_bps").reset_index()
    c["rank"] = np.arange(1, len(c) + 1)
    b, cc = c[c.version == "B"].set_index("variant"), c[c.version == "C"].set_index("variant")
    both = b.index.intersection(cc.index)
    out = pd.DataFrame({
        "reference": b.loc[both, "reference"], "rule_before": b.loc[both, "rule_before"],
        "delta_B_usd": b.loc[both, "delta_pnl_usd"], "delta_C_usd": cc.loc[both, "delta_pnl_usd"],
        "rank_B": b.loc[both, "rank"], "rank_C": cc.loc[both, "rank"],
        "news_right_C": follows.news_right.reindex(both),
    })
    out["delta_B_plus_C_usd"] = out.delta_B_usd + out.delta_C_usd
    out["rank_mean"] = (out.rank_B + out.rank_C) / 2
    return out.sort_values("delta_B_plus_C_usd", ascending=False)[
        ["reference", "rule_before", "delta_B_usd", "delta_C_usd", "delta_B_plus_C_usd", "rank_B", "rank_C", "rank_mean", "news_right_C"]]

def fisher(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact test on [[a, b], [c, d]], suited to few cases."""
    r1, c1, n = a + b, a + c, a + b + c + d
    p = lambda x: comb(c1, x) * comb(n - c1, r1 - x) / comb(n, r1)   # noqa: E731
    return float(min(1.0, sum(p(x) for x in range(max(0, r1 + c1 - n), min(r1, c1) + 1) if p(x) <= p(a) * (1 + 1e-9))))


def evaluate_blocks(variants: list[Variant], ref: dict) -> pd.DataFrame:
    """B: do the blocked trades (in the reference but not in the variant) revert less than the kept ones? And are they worse than a random block?
    p_fisher: reversion share, blocked against kept. p_random: share of random blocks of the same number that remove even
    worse trades; close to 1 means that the agent removes precisely the best trades."""
    rows = []
    for v in variants:
        if v.version != "B":
            continue
        r = ref[v.reference].assign(reversion=lambda t: t.exit_reason.eq("reversion"))
        blk = r.signal_id.isin(set(r.signal_id) - set(v.trades.signal_id))
        b, k = r[blk], r[~blk]
        dec = pd.DataFrame({"signal_id": r.signal_id, "decision": np.where(blk, "block", "enter")})
        n = len(b)
        rows.append(dict(variant=v.name, reference=v.reference, blocked=n,
                         reversion_blocked=b.reversion.mean() if n else np.nan, reversion_kept=k.reversion.mean(),
                         p_fisher=fisher(int(b.reversion.sum()), n - int(b.reversion.sum()), int(k.reversion.sum()), len(k) - int(k.reversion.sum())) if n else np.nan,
                         gross_mean_blocked=b.gross_bps.mean() if n else np.nan, gross_median_blocked=b.gross_bps.median() if n else np.nan,
                         gross_mean_kept=k.gross_bps.mean(), p_random=blocked_vs_random(r, dec)["p_value"] if n else np.nan))
    return pd.DataFrame(rows).set_index("variant")


def evaluate_follows(variants: list[Variant], ref: dict) -> pd.DataFrame:
    """C: when the variant follows the news in the direction opposite to the reference, was the news right (C trade in profit)?
    The `follow`s in the same direction as the reference ("follow, same as A") stay the reference trade and are not counted."""
    rows = []
    for v in variants:
        if v.version != "C":
            continue
        f = v.trades[v.trades.c_kind == "follow"].merge(ref[v.reference][["signal_id", "gross_bps"]], on="signal_id", suffixes=("", "_ref"))
        n = len(f)
        rows.append(dict(variant=v.name, reference=v.reference, follow=n, news_right=(f.gross_bps > 0).mean() if n else np.nan,
                         gross_mean_C=f.gross_bps.mean() if n else np.nan, gross_median_C=f.gross_bps.median() if n else np.nan,
                         gross_mean_ref_same=f.gross_bps_ref.mean() if n else np.nan))
    return pd.DataFrame(rows).set_index("variant")


# ---------------------------------------------------------------- robustness (07)

def daily_delta(v: Variant, ref: dict, days: pd.DatetimeIndex, cost: float = 0) -> pd.Series:
    """Dollar difference, day by day, between the variant and its reference."""
    return daily_pnl(add_costs(v.trades, cost), days).pnl_usd - daily_pnl(add_costs(ref[v.reference], cost), days).pnl_usd


def bootstrap(delta: pd.Series, n: int = 10_000, seed: int = 0) -> dict:
    """95% confidence interval of the total difference, resampling the days with replacement.
    share_below_zero: share of resamples in which the variant earns less than the reference."""
    rng = np.random.default_rng(seed)
    d = delta.to_numpy()
    tot = d[rng.integers(0, len(d), (n, len(d)))].sum(axis=1)
    return dict(delta_usd=d.sum(), ci95_low=np.percentile(tot, 2.5), ci95_high=np.percentile(tot, 97.5), share_below_zero=(tot < -1e-6).mean())


def market(days: pd.DatetimeIndex) -> pd.Series:
    """Daily return of SPY (prices adjusted for dividends, from Alpaca: python -m src.spy) on the train days."""
    if not SPY_DAILY.exists():
        raise FileNotFoundError(f"{SPY_DAILY.name} is missing: from the project folder run `uv run python -m src.spy`")
    spy = pd.read_parquet(SPY_DAILY).set_index("date").close
    return spy.pct_change().reindex(days)


def beta_alpha(ret: pd.Series, mkt: pd.Series) -> dict:
    """Regression of the daily returns on the market: beta, annualised alpha and their t statistics."""
    m = sm.OLS(ret.to_numpy(), sm.add_constant(mkt.to_numpy())).fit()
    return dict(beta=m.params[1], t_beta=m.tvalues[1], alpha_annual=m.params[0] * DAYS_PER_YEAR, t_alpha=m.tvalues[0])


def sectors() -> pd.Series:
    """Sector (GICS industry group) of each pair, from selected_pairs_2.csv."""
    return pd.read_csv(SELECTED).set_index("pair").industry_group
