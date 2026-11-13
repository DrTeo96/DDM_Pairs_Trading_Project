"""Tutte le varianti dell'agente in un formato unico, per 06_backtest.ipynb (confronto) e 07_robustezza.ipynb (controlli). Solo train.

Ogni variante è un insieme di trade con un riferimento: la A per quasi tutte, la A ritardata dello stesso tempo per le varianti che
decidono ed entrano k minuti dopo il segnale. Le differenze (delta) sono sempre variante meno riferimento.

    from src.varianti_agente.confronto import riferimenti, tutte_le_varianti, confronto
"""
from dataclasses import dataclass
from math import comb

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.backtest import (DAYS_PER_YEAR, VERSIONS, add_costs, apply_version, available_versions, blocked_vs_random, daily_pnl, summary,
                          version_trades)
from src.config import SELECTED, SPY_DAILY, VARIANTI

DELAYS = (5, 15)
DIMENSIONE = {   # variante -> (file in Results/varianti_agente/dimensione/, descrizione)
    "spark24h_size_agente": ("trades_spark24h_size_agente.csv", "spark_24h: metà dimensione quando l'agente segnala rumore, blocco come la B"),
    "spark24h_blocca_mezzo": ("trades_spark24h_blocca_mezzo.csv", "spark_24h: metà dimensione invece del blocco"),
    "3b_mezzo": ("trades_3b_mezzo.csv", "3b_6h: metà dimensione invece del blocco e quando l'agente consiglia di ridurre"),
    "finbert_forte_mezzo": ("trades_finbert_forte_mezzo.csv", "FinBERT: metà dimensione con almeno una notizia mirata con sentiment forte"),
}


@dataclass
class Variante:
    nome: str
    versione: str        # B, C oppure "B ridotta" (dimensione ridotta invece del blocco)
    riferimento: str     # A, A_5min, A_15min
    prima: bool          # regola scritta prima di vedere i risultati del train
    descrizione: str
    trades: pd.DataFrame


def _read(path) -> pd.DataFrame:
    t = pd.read_csv(path)
    for c in ("t_signal", "t_entry", "t_exit", "day"):
        if c in t:
            t[c] = pd.to_datetime(t[c])
    return t


def riferimenti(trades: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """La A e le A ritardate (decisione e ingresso 5 o 15 minuti dopo il segnale, prodotte da ritardo.py)."""
    return {"A": apply_version(trades, "A")} | {f"A_{k}min": _read(VARIANTI / f"ritardo/trades_A_{k}min.csv") for k in DELAYS}


def tutte_le_varianti(trades: pd.DataFrame) -> list[Variante]:
    """Set di decisioni di VERSIONS (solo quelli completi e disponibili), dimensione ridotta, ingresso ritardato, B_esagerazione."""
    out = [Variante(n, letter, "A", True, VERSIONS[n]["label"], t)
           for n in available_versions(complete=True) for letter, t in version_trades(trades, n).items() if letter != "A"]
    out += [Variante(n, "B ridotta", "A", True, d, _read(VARIANTI / "dimensione" / f)) for n, (f, d) in DIMENSIONE.items()]
    out += [Variante(f"finbert_ritardo_{k}min", letter, f"A_{k}min", True,
                     f"Regole di finbert_episodio, decisione e ingresso {k} minuti dopo il segnale", _read(VARIANTI / f"ritardo/trades_{letter}_{k}min.csv"))
            for k in DELAYS for letter in "BC"]
    out.append(Variante("b_esagerazione", "B", "A", False, "spark_24h che entra quando la notizia conferma il movimento (Orfeo, dopo i risultati)",
                        _read(VARIANTI / "post_train/trades_B_esagerazione.csv")))
    return out


def elenco(varianti: list[Variante]) -> pd.DataFrame:
    """Una riga per variante e versione: cosa si confronta."""
    return pd.DataFrame([dict(variante=v.nome, versione=v.versione, riferimento=v.riferimento, regola_prima=v.prima, descrizione=v.descrizione)
                         for v in varianti]).set_index(["variante", "versione"])


def identica_al_riferimento(v: Variante, rif: dict) -> bool:
    """True se la variante fa esattamente gli stessi trade del suo riferimento (per esempio una regola che sul train non scatta mai)."""
    # segnale, guadagno (un trade invertito cambia segno) e dimensione (le varianti a dimensione ridotta hanno gli stessi trade della A)
    key = lambda t: sorted(zip(t.signal_id, t.gross_bps.round(9), t["size"] if "size" in t else [1.0] * len(t)))   # noqa: E731
    return key(v.trades) == key(rif[v.riferimento])


# ---------------------------------------------------------------- confronto (06)

def confronto(varianti: list[Variante], rif: dict, days: pd.DatetimeIndex, costs=(0, 5)) -> pd.DataFrame:
    """Metriche di ogni variante e differenza dal suo riferimento, per costo. Ordinata per delta in dollari a costo 0 (dal migliore)."""
    rows = []
    for v in varianti:
        for c in costs:
            s, r = summary(add_costs(v.trades, c), days), summary(add_costs(rif[v.riferimento], c), days)
            rows.append(dict(variante=v.nome, versione=v.versione, cost_bps=c, riferimento=v.riferimento, regola_prima=v.prima, trade=s["trade"],
                             net_bps=s["net_bps"], win_rate=s["win_rate"], pnl_usd=s["pnl_usd"], delta_pnl_usd=s["pnl_usd"] - r["pnl_usd"],
                             sharpe=s["sharpe"], delta_sharpe=s["sharpe"] - r["sharpe"], max_drawdown_pct=100 * s["max_drawdown"]))
    out = pd.DataFrame(rows)
    order = out[out.cost_bps == costs[0]].sort_values("delta_pnl_usd", ascending=False)[["variante", "versione"]].apply(tuple, axis=1)
    return out.set_index(["variante", "versione", "cost_bps"]).reindex([(*k, c) for k in order for c in costs])


def fisher(a: int, b: int, c: int, d: int) -> float:
    """Test esatto di Fisher a due code su [[a, b], [c, d]], adatto a pochi casi."""
    r1, c1, n = a + b, a + c, a + b + c + d
    p = lambda x: comb(c1, x) * comb(n - c1, r1 - x) / comb(n, r1)   # noqa: E731
    return float(min(1.0, sum(p(x) for x in range(max(0, r1 + c1 - n), min(r1, c1) + 1) if p(x) <= p(a) * (1 + 1e-9))))


def valuta_blocchi(varianti: list[Variante], rif: dict) -> pd.DataFrame:
    """B: i trade bloccati (nel riferimento ma non nella variante) rientrano meno di quelli tenuti? E sono peggiori di un blocco a caso?
    p_fisher: quota di rientro, bloccati contro tenuti. p_caso: quota di blocchi casuali dello stesso numero che tolgono trade ancora
    peggiori; vicino a 1 vuol dire che l'agente toglie proprio i trade migliori."""
    rows = []
    for v in varianti:
        if v.versione != "B":
            continue
        ref = rif[v.riferimento].assign(rientro=lambda t: t.exit_reason.eq("rientro"))
        blk = ref.signal_id.isin(set(ref.signal_id) - set(v.trades.signal_id))
        b, k = ref[blk], ref[~blk]
        dec = pd.DataFrame({"signal_id": ref.signal_id, "decision": np.where(blk, "blocca", "entra")})
        n = len(b)
        rows.append(dict(variante=v.nome, riferimento=v.riferimento, bloccati=n,
                         rientro_bloccati=b.rientro.mean() if n else np.nan, rientro_tenuti=k.rientro.mean(),
                         p_fisher=fisher(int(b.rientro.sum()), n - int(b.rientro.sum()), int(k.rientro.sum()), len(k) - int(k.rientro.sum())) if n else np.nan,
                         lordo_medio_bloccati=b.gross_bps.mean() if n else np.nan, lordo_mediano_bloccati=b.gross_bps.median() if n else np.nan,
                         lordo_medio_tenuti=k.gross_bps.mean(), p_caso=blocked_vs_random(ref, dec)["p_value"] if n else np.nan))
    return pd.DataFrame(rows).set_index("variante")


def valuta_segui(varianti: list[Variante], rif: dict) -> pd.DataFrame:
    """C: quando la variante segue la notizia nel verso opposto al riferimento, la notizia aveva ragione (trade C in guadagno)?
    I `segui` nello stesso verso del riferimento ("segui, come A") restano il trade del riferimento e non si contano."""
    rows = []
    for v in varianti:
        if v.versione != "C":
            continue
        f = v.trades[v.trades.c_kind == "segui"].merge(rif[v.riferimento][["signal_id", "gross_bps"]], on="signal_id", suffixes=("", "_rif"))
        n = len(f)
        rows.append(dict(variante=v.nome, riferimento=v.riferimento, segui=n, notizia_giusta=(f.gross_bps > 0).mean() if n else np.nan,
                         lordo_medio_C=f.gross_bps.mean() if n else np.nan, lordo_mediano_C=f.gross_bps.median() if n else np.nan,
                         lordo_medio_rif_stessi=f.gross_bps_rif.mean() if n else np.nan))
    return pd.DataFrame(rows).set_index("variante")


# ---------------------------------------------------------------- robustezza (07)

def delta_giornaliero(v: Variante, rif: dict, days: pd.DatetimeIndex, cost: float = 0) -> pd.Series:
    """Differenza in dollari, giorno per giorno, tra la variante e il suo riferimento."""
    return daily_pnl(add_costs(v.trades, cost), days).pnl_usd - daily_pnl(add_costs(rif[v.riferimento], cost), days).pnl_usd


def bootstrap(delta: pd.Series, n: int = 10_000, seed: int = 0) -> dict:
    """Intervallo di confidenza al 95% della differenza totale, ricampionando i giorni con reinserimento.
    quota_sotto_zero: quota di ricampionamenti in cui la variante guadagna meno del riferimento."""
    rng = np.random.default_rng(seed)
    d = delta.to_numpy()
    tot = d[rng.integers(0, len(d), (n, len(d)))].sum(axis=1)
    return dict(delta_usd=d.sum(), ic95_basso=np.percentile(tot, 2.5), ic95_alto=np.percentile(tot, 97.5), quota_sotto_zero=(tot < -1e-6).mean())


def mercato(days: pd.DatetimeIndex) -> pd.Series:
    """Rendimento giornaliero di SPY (prezzi aggiustati per dividendi, da Alpaca: python -m src.spy) nei giorni del train."""
    if not SPY_DAILY.exists():
        raise FileNotFoundError(f"manca {SPY_DAILY.name}: dalla cartella del progetto esegui `uv run python -m src.spy`")
    spy = pd.read_parquet(SPY_DAILY).set_index("date").close
    return spy.pct_change().reindex(days)


def beta_alpha(ret: pd.Series, mkt: pd.Series) -> dict:
    """Regressione dei rendimenti giornalieri sul mercato: beta, alpha annualizzato e le loro statistiche t."""
    m = sm.OLS(ret.to_numpy(), sm.add_constant(mkt.to_numpy())).fit()
    return dict(beta=m.params[1], t_beta=m.tvalues[1], alpha_annuo=m.params[0] * DAYS_PER_YEAR, t_alpha=m.tvalues[0])


def settori() -> pd.Series:
    """Settore (gruppo) di ogni coppia, da selected_pairs_2.csv."""
    return pd.read_csv(SELECTED).set_index("pair").gruppo
