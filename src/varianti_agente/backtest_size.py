"""Variante 12 (punto 3): ridurre invece di bloccare. Ogni trade della A ha una dimensione 1, 0,5 o 0; guadagno e costi in dollari
si moltiplicano per la dimensione. Regole scritte in registro_varianti.md prima del run.

Legge le decisioni in Results/varianti_agente/; scrive in Results/varianti_agente/dimensione/: size.csv e i trade di ogni variante
(trades_<nome>.csv, a costo 0, con la colonna size e pnl_usd già moltiplicato per la dimensione).
Uso: uv run python -m src.varianti_agente.backtest_size
"""
import numpy as np
import pandas as pd
from src.backtest import add_costs, apply_version, load_trades, summary, trading_days
from src.config import AGENT_DECISIONS_COPY, DEC_3B_6H, DEC_FINBERT_SEDUTA, RESULTS, VARIANTI

OUT = VARIANTI / "dimensione"

pd.options.display.float_format = "{:,.2f}".format
pd.options.display.width = 200
A, days = apply_version(load_trades(), "A"), trading_days()

giulio = pd.read_csv(AGENT_DECISIONS_COPY).set_index("signal_id")
mio = pd.read_csv(DEC_3B_6H).set_index("signal_id")
fb = pd.read_csv(DEC_FINBERT_SEDUTA, keep_default_na=False).set_index("signal_id")
s = A.signal_id

SIZES = {
    "A, senza agente": pd.Series(1.0, index=s.values),
    "B spark_24h, blocco (Giulio)": giulio.decision.map({"blocca": 0.0, "entra": 1.0}).reindex(s).values,
    "12a spark_24h con la sua size": np.where(giulio.decision.reindex(s) == "blocca", 0.0, giulio["size"].reindex(s)),
    "12b spark_24h, blocca = 0,5": giulio.decision.map({"blocca": 0.5, "entra": 1.0}).reindex(s).values,
    "12c 3B 6h, blocca e ridotto = 0,5": np.where(mio.decision_full.reindex(s).isin(["block", "enter_reduced"]), 0.5, 1.0),
    "12d FinBERT, notizia forte = 0,5": np.where(fb.n_strong.reindex(s) > 0, 0.5, 1.0),
}

# i trade salvati: solo le varianti 12a-12d (la A e la B di spark_24h sono già nelle loro cartelle)
TRADE_FILES = {"12a spark_24h con la sua size": "spark24h_size_agente", "12b spark_24h, blocca = 0,5": "spark24h_blocca_mezzo",
               "12c 3B 6h, blocca e ridotto = 0,5": "3b_mezzo", "12d FinBERT, notizia forte = 0,5": "finbert_forte_mezzo"}

rows = []
for name, size in SIZES.items():
    size = np.asarray(size, dtype=float)
    assert not np.isnan(size).any(), f"{name}: dimensione mancante per qualche segnale"
    for c in (0, 5):
        t = add_costs(A, c)
        t["pnl_usd"] = t.pnl_usd * size
        port = summary(t[size > 0], days)     # le metriche di portafoglio usano pnl_usd, già pesato
        w = size[size > 0]
        rows.append({"variante": name, "costo": c, "trade": int((size > 0).sum()), "ridotti": int((size == 0.5).sum()), "bloccati": int((size == 0).sum()),
                     "net_bps_per_dollaro": float(np.average(t.net_bps[size > 0], weights=w)), "pnl_usd": port["pnl_usd"],
                     "total_return": port["total_return"], "sharpe": port["sharpe"], "max_drawdown": port["max_drawdown"]})
    # come vanno i trade ridotti: rientrano meno degli altri? (lordo, senza costi)
    red = A[size == 0.5]
    if len(red):
        print(f"{name}: {len(red)} trade ridotti, rientro {red.exit_reason.eq('rientro').mean():.0%} (tutti {A.exit_reason.eq('rientro').mean():.0%}), "
              f"lordo medio {red.gross_bps.mean():.1f} bps, mediano {red.gross_bps.median():.1f}")

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
print(f"\nsalvato in {OUT.relative_to(RESULTS.parent)}: size.csv e " + ", ".join(f"trades_{s}.csv" for s in TRADE_FILES.values()))
