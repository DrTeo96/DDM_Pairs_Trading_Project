"""Esperimento post-train: dove l'agente blocca bene. FUORI dalla pipeline fissata prima dei risultati.

Scritto il 13 novembre 2026, DOPO aver visto i risultati del train in 06_backtest.ipynb: le scelte qui dentro sono state fatte
guardando gli stessi dati su cui vengono misurate, quindi i numeri sono ottimistici. Usa solo il train (load_trades rifiuta il test).
Dalla cartella del progetto:
    uv run python -m src.post_train         stampa le tabelle e le salva in Results/post_train/

Da dove parte. Nel Passaggio 6 la versione B (l'agente blocca un fatto strutturale su un solo titolo) toglie trade che guadagnavano
più della media. Qui si guarda dentro quei blocchi, con informazioni che l'agente produce già (nessuna nuova chiamata al modello):
- la direzione della notizia secondo l'agente (positiva, negativa, incerta);
- il movimento del titolo con la notizia rispetto all'altro nei 30 minuti prima del segnale, lo stesso della regola C in agent.py.
Tre casi:
- conferma: notizia positiva e titolo salito rispetto all'altro, oppure negativa e titolo sceso (nella C: 'segui');
- contraddice: direzione della notizia opposta al movimento;
- direzione incerta: l'agente non sa dire se la notizia è buona o cattiva, o più notizie strutturali hanno direzioni diverse.
Una variante della B, nata guardando i risultati del train:
- B_esagerazione: blocca contraddice e direzione incerta, entra quando la notizia conferma il movimento (nella C: 'segui').
La tabella per caso mostra anche quale dei tre gruppi perde: è un'osservazione, non una variante in più.
Costi come nel Passaggio 6: scenario principale 0 (indicazione del docente), MAIN_COST per operazione come confronto.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.backtest import MAIN_COST, add_costs, apply_version, blocked_vs_random, daily_pnl, load_trades, save_results, summary, trading_days
from src.config import AGENT_DECISIONS, RESULTS, RUN_24H

OUT = RESULTS / "post_train"
CASES = ["conferma", "contraddice", "direzione incerta", "nessun blocco nella B"]


def load_decisions() -> pd.DataFrame:
    """Le decisioni dell'agente principale (spark_24h): il giro completo se c'è sul computer, altrimenti la copia su git in Results/."""
    for p in (RUN_24H, AGENT_DECISIONS, RESULTS / AGENT_DECISIONS.name):
        if p.exists() and "decision_C" in pd.read_csv(p, nrows=0):
            print(f"decisioni da {p.relative_to(p.parents[2])}")
            return pd.read_csv(p)
    raise FileNotFoundError("nessuna tabella di decisioni dell'agente con la colonna decision_C")


def classify(trades: pd.DataFrame, dec: pd.DataFrame) -> pd.DataFrame:
    """Per ogni segnale il caso: conferma, contraddice, direzione incerta, oppure nessun blocco nella B."""
    m = dec.merge(trades[["signal_id", "pair", "t_signal", "ticker_A", "ticker_B", "ret_A_30m", "ret_B_30m", "gross_bps", "exit_reason"]],
                  on="signal_id")
    one = (m.category == "strutturale") & (m.ticker != "entrambi")
    m["rel"] = np.where(m.ticker == m.ticker_A, m.ret_A_30m - m.ret_B_30m, m.ret_B_30m - m.ret_A_30m)   # movimento del titolo con la notizia
    m["caso"] = np.select([~one, m.news_direction == "incerta", (m.news_direction == "positiva") == (m.rel > 0)],
                          ["nessun blocco nella B", "direzione incerta", "conferma"], default="contraddice")
    # i casi coincidono con la regola della C in agent.py
    assert (m[m.caso == "conferma"].decision_C == "segui").all()
    assert (m[m.caso.isin(["contraddice", "direzione incerta"])].decision_C == "blocca").all()
    return m


def main() -> None:
    pd.options.display.float_format = "{:,.2f}".format
    pd.options.display.width = 250
    pd.options.display.max_columns = None
    trades, days = load_trades(), trading_days()
    dec = load_decisions()
    b0 = add_costs(apply_version(trades, "B", dec), 0)
    assert len(b0) == 925 and round(b0.gross_bps.mean(), 2) == 6.38, "le decisioni non sono quelle del Passaggio 6"

    m = classify(trades, dec)
    per_caso = m.groupby("caso").gross_bps.agg(trade="size", lordo_medio_bps="mean", mediana_bps="median",
                                                 in_guadagno=lambda x: (x > 0).mean()).loc[CASES]
    print("\n1. I blocchi della B per caso (guadagno che il trade avrebbe fatto nella A):")
    print(per_caso)

    variants = {
        "B (Passaggio 6)": dec[["signal_id", "decision"]],
        "B_esagerazione": m.assign(decision=np.where(m.decision_C == "blocca", "blocca", "entra"))[["signal_id", "decision"]],
    }
    books = {"A": apply_version(trades, "A")} | {k: apply_version(trades, "B", v) for k, v in variants.items()}
    half = {"1a meta": days[:len(days) // 2], "2a meta": days[len(days) // 2:]}
    rows = []
    for name, t in books.items():
        for c in (0, MAIN_COST):
            x = add_costs(t, c)
            s = summary(x, days)
            r = dict(versione=name, cost_bps=c, trade=s["trade"], gross_bps=s["gross_bps"], net_bps=s["net_bps"], se_bps=s["se_bps"],
                     win_rate=s["win_rate"], profit_factor=s["profit_factor"], pnl_usd=s["pnl_usd"], sharpe=s["sharpe"],
                     max_drawdown=s["max_drawdown"])
            for h, d in half.items():
                r[f"net_bps {h}"] = x[x.day.isin(d)].net_bps.mean()
            rows.append(r)
    confronto = pd.DataFrame(rows).set_index(["versione", "cost_bps"])
    print("\n2. La variante contro A e B:")
    print(confronto)

    bloccati = pd.DataFrame({k: blocked_vs_random(trades, v) for k, v in variants.items()}).T
    print("\n3. Trade bloccati contro blocchi a caso dello stesso numero:")
    print(bloccati)

    OUT.mkdir(parents=True, exist_ok=True)
    cols = ["signal_id", "pair", "t_signal", "ticker", "news_direction", "rel", "gross_bps", "exit_reason", "reason", "caso"]
    written = save_results({"post_train/per_caso": per_caso, "post_train/confronto": confronto, "post_train/bloccati_contro_caso": bloccati,
                            "post_train/blocchi_B": m[m.caso != "nessun blocco nella B"][cols].reset_index(drop=True),
                            "post_train/trades_B_esagerazione": add_costs(books["B_esagerazione"], 0)})
    fig, ax = plt.subplots(figsize=(11, 4.5))
    for name, t in books.items():
        d = daily_pnl(add_costs(t, 0), days)
        ax.plot(d.index, 100 * (1 + d.equity), label=name, lw=2 if name == "A" else 1.3, color="k" if name == "A" else None)
    ax.axhline(100, color="grey", lw=0.6)
    ax.set_title("Curva di capitale a costo 0, train (partenza 100)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "curve_capitale.png", dpi=150)
    plt.close(fig)
    print("\nsalvati:", ", ".join(str(p.relative_to(RESULTS.parent)) for p in written), "e Results/post_train/curve_capitale.png")


if __name__ == "__main__":
    main()
