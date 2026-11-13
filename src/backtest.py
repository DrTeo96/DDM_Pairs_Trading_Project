"""Simulazione: costi, tre versioni (A, B, C), confronto tra le versioni di risultati e metriche sui trade dei segnali.

Il motore non rifà il segnale: parte dalla tabella dei trade di 03_segnali.ipynb (orari, prezzi, direzione, guadagno lordo)
e ci applica, in questo ordine, la decisione della versione (A, B o C), i costi e il capitale.
In un notebook:
    from src.backtest import load_trades, load_version, apply_version, add_costs, summary
    trades = load_trades()                                  # trade del train
    a = add_costs(apply_version(trades, "A"), cost_bps=5)   # versione A, 5 bps per operazione
    b = apply_version(trades, "B", load_version("spark_24h"))
    print(summary(a))

Le regole:
- importo fisso e uguale sulle due gambe (NOTIONAL_LEG dollari per gamba), nessuna leva, tutto chiuso a fine giornata
- un trade ha 4 operazioni (apertura e chiusura di due gambe): costo del trade = 4 x cost_bps, in punti base sull'importo di una gamba,
  la stessa base del guadagno lordo (`gross_bps`)
- guadagno netto = lordo - costo; in dollari = netto / 10.000 x NOTIONAL_LEG
- capitale del portafoglio = CAPITAL_PER_PAIR per coppia (due gambe da NOTIONAL_LEG): ogni coppia può avere un trade aperto alla volta
- i rendimenti giornalieri sono il guadagno in dollari dei trade chiusi quel giorno diviso per il capitale; i giorni senza trade valgono 0
- niente tasso privo di rischio nello Sharpe (3 mesi di dati, trade chiusi ogni sera): dichiarato nel report
- il periodo di test non si legge: `load_trades` rifiuta qualsiasi trade dopo TRAIN_END, se non gli si chiede `allow_test=True`

Le versioni:
- A: tutti i segnali entrano, senza agente.
- B: l'agente può solo bloccare (colonna `decision`).
- C: l'agente può anche seguire la notizia (colonna `decision_C` = 'segui', direzione in `follow_side`). Un trade 'segui' apre alla
  stessa barra della A ma nella direzione della notizia, cioè scommette che lo spread continui ad allargarsi, ed esce al primo tra:
  rientro dello spread (|z| <= soglia di uscita: la notizia aveva torto), MAX_HOLD minuti, fine giornata. Niente stop oltre al rientro.

Le versioni di risultati (VERSIONS) sono i set di decisioni da confrontare: i giri dell'agente, la baseline a lessico e la
classificazione a mano del gruppo e le varianti dell'agente in src/varianti_agente/. `load_version` li porta tutti allo stesso
formato (signal_id, decision, decision_C, follow_side). Se il file originale non c'è (per esempio le risposte grezze dell'agente, che
stanno solo sul computer di chi l'ha fatto girare), si legge la copia su git in Results/varianti_agente/<nome>/ (`copy`), già in
questo formato.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import (AGENT_DECISIONS_COPY, BASELINE_LEXICON, DEC_3B_6H, DEC_C_FRESCA, DEC_FINBERT_EPISODIO, DEC_FINBERT_SEDUTA,
                        MANUAL_DECISIONS, RESULTS, RUN_6H, RUN_24H, RUN_24H_REASONING, SIGNALS, TRAIN_END, VARIANTI)
from src.signals import MAX_HOLD, list_pairs, load_pair, zscore

NOTIONAL_LEG = 10_000         # dollari per gamba: importo uguale sulle due gambe, senza leva
CAPITAL_PER_PAIR = 2 * NOTIONAL_LEG
OPERATIONS_PER_TRADE = 4      # apertura e chiusura di due gambe
COST_SCENARIOS = [0, 2, 5, 10]  # punti base per operazione
MAIN_COST = 5                 # scenario realistico, deciso prima di guardare i risultati
DAYS_PER_YEAR = 252
OPEN_WINDOW = (15, 30)        # minuti dall'apertura del segnale: "gap della notte" se il segnale cade qui

DECISIONS = {"entra", "blocca", "segui"}  # decisioni possibili dell'agente (varianti_agente/agent.py)

# I set di decisioni confrontati nel backtest. complete=True: una decisione per ognuno dei 973 segnali del train;
# complete=False: solo i 40 segnali del campione classificato a mano, quindi si confrontano solo su quei segnali.
# path: file originale; copy: copia su git nel formato di load_version (None se non serve); chi: chi ha fatto la variante;
# letters: le versioni che il set prevede, se non sono B e C (3b_6h decide solo la B, c_fresca solo la C).
# Le varianti che cambiano il backtest stesso (dimensione ridotta, ingresso ritardato, B_esagerazione) non sono set di decisioni:
# i loro trade sono in Results/varianti_agente/ e il notebook 06 li legge da lì.
VERSIONS = {
    "spark_24h": dict(path=RUN_24H, copy=AGENT_DECISIONS_COPY, kind="agente", complete=True, chi="Giulio",
                      label="Agente Spark X2.6 4B, notizie delle 24 ore prima, ragionamento spento (versione principale)"),
    "spark_6h": dict(path=RUN_6H, copy=VARIANTI / "spark_6h/decisioni.csv", kind="agente", complete=True, chi="Giulio",
                     label="Agente Spark X2.6 4B, notizie delle 6 ore prima, ragionamento spento"),
    "lessico": dict(path=BASELINE_LEXICON, copy=VARIANTI / "lessico/decisioni.csv", kind="lessico", complete=True, chi="Giulio",
                    label="Baseline senza modello: parole positive e negative del lessico Loughran-McDonald"),
    "3b_6h": dict(path=DEC_3B_6H, copy=None, kind="agente", complete=True, chi="Beatrice", letters=("B",),
                  label="Agente Llama 3.2 3B, notizie delle 6 ore prima, prompt completo, filtro a parole chiave sul blocco (solo B)"),
    "finbert_seduta": dict(path=DEC_FINBERT_SEDUTA, copy=None, kind="agente", complete=True, chi="Beatrice",
                           label="FinBERT sulle notizie mirate, finestra legata alla seduta (gap della notte: dall'ultima chiusura)"),
    "c_fresca": dict(path=DEC_C_FRESCA, copy=None, kind="agente", complete=True, chi="Beatrice", letters=("C",),
                     label="Solo C: segue notizie fresche (60 minuti, in seduta), forti, con un evento e direzione uguale al movimento"),
    "finbert_episodio": dict(path=DEC_FINBERT_EPISODIO, copy=None, kind="agente", complete=True, chi="Beatrice",
                             label="FinBERT, regole di finbert_seduta con le notizie uscite mentre lo spread si allontanava"),
    "spark_24h_ragiona": dict(path=RUN_24H_REASONING, copy=None, kind="agente", complete=False, chi="Giulio",
                              label="Agente Spark X2.6 4B, 24 ore, ragionamento acceso (solo campione)"),
    "mano": dict(path=MANUAL_DECISIONS, copy=None, kind="mano", complete=False, chi="Giulio",
                 label="Classificazione a mano del gruppo, con la stessa regola dell'agente (solo campione)"),
}


def version_file(name: str) -> tuple[Path | None, bool]:
    """Il file da cui leggere un set di decisioni: l'originale se c'è, altrimenti la copia su git. Il secondo valore dice se è la copia."""
    v = VERSIONS[name]
    if v["path"].exists():
        return v["path"], False
    if v["copy"] is not None and v["copy"].exists():
        return v["copy"], True
    return None, False


def available_versions(complete: bool | None = None) -> list[str]:
    """I set di decisioni che si possono leggere su questo computer (originale o copia)."""
    return [n for n, v in VERSIONS.items() if version_file(n)[0] is not None and (complete is None or v["complete"] == complete)]


def load_trades(path: Path = SIGNALS, allow_test: bool = False) -> pd.DataFrame:
    """Trade di 03_segnali.ipynb. Orari come datetime; minuto del segnale dall'apertura delle 9:30."""
    t = pd.read_csv(path, parse_dates=["t_signal", "t_entry", "t_exit"])
    if not allow_test and (t.t_exit.dt.normalize() > pd.Timestamp(TRAIN_END)).any():
        raise ValueError("la tabella contiene trade dopo la fine del train: il test si usa una sola volta, con allow_test=True")
    t["signal_minute"] = t.t_signal.dt.hour * 60 + t.t_signal.dt.minute - (9 * 60 + 30)
    t["day"] = t.t_exit.dt.normalize()
    return t


def trading_days() -> pd.DatetimeIndex:
    """Giorni di seduta del train, dai file di prezzi puliti (serve per contare anche i giorni senza trade)."""
    d = load_pair(list_pairs().pair.iloc[0])
    return pd.DatetimeIndex(d.ts[d.is_train].normalize().unique())


def load_version(name: str) -> pd.DataFrame:
    """Un set di decisioni di VERSIONS, nel formato che `apply_version` legge: signal_id, decision, decision_C, follow_side.

    agente: le colonne ci sono già (decisions.csv di un giro, oppure le colonne dell'agente in accordo_segnali.csv).
    lessico: `decision` com'è; `action` = 'flat' vuol dire bloccare; 'solo_A' o 'solo_B' con `side` (long/short) vuol dire seguire la
             notizia su quel titolo. Per confrontarla con l'agente la C del lessico è simulata con la coppia coperta: long sul titolo
             indicato e short sull'altro (o il contrario), non con una gamba sola.
    mano: le colonne mano_decision e mano_decision_C; senza direzione da seguire, quindi solo versione B."""
    if name not in VERSIONS:
        raise ValueError(f"versione sconosciuta: {name}. Possibili: {', '.join(VERSIONS)}")
    v = VERSIONS[name]
    path, is_copy = version_file(name)
    if path is None:
        raise FileNotFoundError(f"manca {v['path']}: è il file della versione {name}")
    d = pd.read_csv(path)
    if v["kind"] == "agente" or is_copy:
        # un set solo B (nessuna colonna decision_C) nella C decide come nella B; un set solo C (nessuna colonna decision) nella B entra sempre
        d = d.assign(decision=d.decision if "decision" in d else "entra")
        d = d.assign(decision_C=d.decision_C if "decision_C" in d else d.decision, follow_side=d.follow_side if "follow_side" in d else "")
        out = d[["signal_id", "decision", "decision_C", "follow_side"]].copy()
    elif v["kind"] == "mano":
        out = d[["signal_id", "mano_decision", "mano_decision_C"]].rename(columns={"mano_decision": "decision", "mano_decision_C": "decision_C"})
        out["follow_side"] = ""
    else:
        trades = load_trades()[["signal_id", "ticker_A", "ticker_B"]]
        d = d.merge(trades, on="signal_id", how="left")
        follow = d.action.isin(["solo_A", "solo_B"])
        a_long = ((d.action == "solo_A") & (d.side == "long")) | ((d.action == "solo_B") & (d.side == "short"))
        side_txt = np.where(a_long, "long " + d.ticker_A + " / short " + d.ticker_B, "short " + d.ticker_A + " / long " + d.ticker_B)
        out = pd.DataFrame({
            "signal_id": d.signal_id,
            "decision": d.decision,
            "decision_C": np.where(follow, "segui", np.where(d.decision == "entra", "entra", "blocca")),
            "follow_side": np.where(follow, side_txt, ""),
        })
    out["follow_side"] = out.follow_side.fillna("")
    return out.reset_index(drop=True)


def _z_for(pair: str, hl: float, ema: str, cache: dict):
    """Prezzi e z-score di una coppia, letti una volta sola per chiamata di simulate_follow."""
    key = (pair, hl, ema)
    if key not in cache:
        d = load_pair(pair)
        cache[key] = (d, zscore(d.S, hl=hl, reset_daily=ema != "continua"))
    return cache[key]


def simulate_follow(trades: pd.DataFrame, follow_side: pd.Series) -> pd.DataFrame:
    """Versione C: rifà, barra per barra, i trade in cui l'agente segue la notizia.

    trades: righe di load_trades da seguire; follow_side: per ogni riga 'long X / short Y' (stesso indice di trades).
    Se la direzione da seguire è la stessa del trade A, il trade resta quello della A. Altrimenti si apre alla stessa barra
    della A (t_entry) nella direzione opposta e si esce al primo tra rientro dello spread (|z| <= exit_z), MAX_HOLD minuti e
    fine giornata, all'apertura della barra successiva come in signals.run_rules (a fine giornata, alla chiusura)."""
    cache, rows = {}, []
    for idx, t in trades.iterrows():
        a_long_A = t.direction.startswith("long")
        a_long_F = str(follow_side.loc[idx]).startswith("long")
        r = t.to_dict()
        if a_long_A == a_long_F:
            rows.append(r | dict(c_kind="segui, come A"))
            continue
        d, z = _z_for(t.pair, t.hl_min, t.ema, cache)
        i = d.ts.get_loc(t.t_signal)
        e = d.ts.get_loc(t.t_entry)
        assert np.isclose(z[i], t.z_signal), f"segnale {t.signal_id}: lo z-score non coincide con quello di 03_segnali"
        side = np.sign(z[i])               # come in run_rules: +1 spread alto
        k = e
        while True:
            if d.last_of_day[k]:
                reason, a_out, b_out = "fine_giornata", d.cA[k], d.cB[k]
                break
            if side * z[k] <= t.exit_z:
                reason = "rientro"
            elif k - e + 1 >= MAX_HOLD:
                reason = "tempo"
            else:
                k += 1
                continue
            k += 1
            a_out, b_out = d.oA[k], d.oB[k]
            break
        s_in, s_out = np.log(d.oA[e] / d.oB[e]), np.log(a_out / b_out)
        sign = 1 if a_long_F else -1        # +1: long A / short B
        t_exit = d.ts[k]
        rows.append(r | dict(
            direction=follow_side.loc[idx], t_exit=t_exit, price_A_out=a_out, price_B_out=b_out, exit_reason=reason,
            gross_bps=sign * (s_out - s_in) * 1e4, minutes_in_trade=(t_exit - t.t_entry).total_seconds() / 60,
            day=t_exit.normalize(), c_kind="segui",
        ))
    return pd.DataFrame(rows, columns=[*trades.columns, "c_kind"])


def apply_version(trades: pd.DataFrame, version: str, decisions: pd.DataFrame | None = None) -> pd.DataFrame:
    """Seleziona (e per la C rifà) i trade della versione A, B o C.

    A: tutti i segnali entrano, senza agente.
    B: `decisions` ha le colonne signal_id e decision ('entra' o 'blocca'): i trade bloccati escono.
    C: `decisions` ha anche decision_C ('entra', 'blocca', 'segui') e follow_side: 'entra' resta il trade A, 'blocca' esce,
       'segui' è rifatto da simulate_follow nella direzione della notizia.
    Se per un segnale non c'è nessuna decisione, nelle versioni B e C si blocca (regola di sicurezza dell'agente)."""
    if version == "A":
        return trades.copy()
    if decisions is None:
        raise ValueError(f"la versione {version} richiede le decisioni dell'agente")
    if version == "B":
        bad = set(decisions.decision) - (DECISIONS - {"segui"})
        if bad:
            raise ValueError(f"decisioni non valide per la versione B: {bad}")
        ok = trades.merge(decisions[["signal_id", "decision"]], on="signal_id", how="left")
        return ok[ok.decision == "entra"].drop(columns="decision").reset_index(drop=True)
    if version != "C":
        raise ValueError("versione deve essere A, B o C")
    if "decision_C" not in decisions:
        raise ValueError("la versione C richiede la colonna decision_C")
    bad = set(decisions.decision_C) - DECISIONS
    if bad:
        raise ValueError(f"decisioni sconosciute: {bad}")
    ok = trades.merge(decisions[["signal_id", "decision_C", "follow_side"]], on="signal_id", how="left")
    follow = ok[ok.decision_C == "segui"]
    if (follow.follow_side.fillna("") == "").any():
        raise ValueError("ci sono decisioni 'segui' senza la direzione da seguire (follow_side)")
    keep = ok[ok.decision_C == "entra"].assign(c_kind="entra")
    out = pd.concat([keep, simulate_follow(follow.drop(columns=["decision_C", "follow_side"]), follow.follow_side)], ignore_index=True)
    return out.drop(columns=["decision_C", "follow_side"], errors="ignore").sort_values("t_signal").reset_index(drop=True)


def random_decisions(trades: pd.DataFrame, p_block: float = 0.2, seed: int = 0) -> pd.DataFrame:
    """Decisioni finte (blocco casuale), solo per verificare che il motore funzioni: non vanno interpretate."""
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"signal_id": trades.signal_id, "decision": np.where(rng.random(len(trades)) < p_block, "blocca", "entra")})


def add_costs(trades: pd.DataFrame, cost_bps: float) -> pd.DataFrame:
    """Aggiunge il costo, il guadagno netto in punti base e il guadagno netto in dollari.
    Se c'è la colonna `size` (dimensione del trade: 1 intera, 0,5 metà), guadagno e costi in dollari si moltiplicano per la dimensione."""
    t = trades.copy()
    t["cost_bps"] = OPERATIONS_PER_TRADE * cost_bps
    t["net_bps"] = t.gross_bps - t.cost_bps
    t["pnl_usd"] = t.net_bps / 1e4 * NOTIONAL_LEG * (t["size"] if "size" in t else 1)
    return t


def daily_pnl(trades: pd.DataFrame, days: pd.DatetimeIndex, n_pairs: int | None = None) -> pd.DataFrame:
    """Guadagno in dollari, rendimento sul capitale e curva di capitale per giorno (i giorni senza trade valgono 0).
    n_pairs: coppie su cui è allocato il capitale; di default tutte quelle della lista, anche se una non ha trade."""
    pnl = trades.groupby("day").pnl_usd.sum().reindex(days, fill_value=0.0)
    capital = (len(list_pairs()) if n_pairs is None else n_pairs) * CAPITAL_PER_PAIR
    out = pd.DataFrame({"pnl_usd": pnl, "ret": pnl / capital})
    out["equity"] = out.ret.cumsum()          # capitale fisso, quindi si somma (niente reinvestimento)
    out["drawdown"] = out.equity - out.equity.cummax().clip(lower=0)
    return out


def summary(trades: pd.DataFrame, days: pd.DatetimeIndex | None = None, n_pairs: int | None = None) -> dict:
    """Metriche dei trade (in punti base) e, se si passano i giorni, del portafoglio giornaliero.
    Con la colonna `size`, guadagno lordo e netto medi sono pesati con la dimensione (guadagno per dollaro investito)."""
    net = trades.net_bps if "net_bps" in trades else trades.gross_bps
    n = len(net)
    wins, losses = net[net > 0], net[net < 0]
    w = trades["size"] if "size" in trades else None
    out = {
        "trade": n,
        "gross_bps": np.average(trades.gross_bps, weights=w) if n else np.nan,
        "net_bps": np.average(net, weights=w) if n else np.nan,
        "se_bps": net.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan,
        "win_rate": (net > 0).mean(),
        "profit_factor": wins.sum() / abs(losses.sum()) if len(losses) else np.nan,
        "avg_win_bps": wins.mean(),
        "avg_loss_bps": losses.mean(),
        "avg_minutes": trades.minutes_in_trade.mean(),
    }
    if days is not None and "pnl_usd" in trades:
        d = daily_pnl(trades, days, n_pairs)
        out.update(
            pnl_usd=d.pnl_usd.sum(),
            total_return=d.equity.iloc[-1],
            sharpe=d.ret.mean() / d.ret.std(ddof=1) * np.sqrt(DAYS_PER_YEAR) if d.ret.std() > 0 else np.nan,
            max_drawdown=d.drawdown.min(),
        )
    return out


def breakeven_cost(trades: pd.DataFrame) -> float:
    """Costo per operazione (in punti base) a cui il guadagno netto medio va a zero."""
    return trades.gross_bps.mean() / OPERATIONS_PER_TRADE


def by_cost(trades: pd.DataFrame, days: pd.DatetimeIndex, costs=COST_SCENARIOS) -> pd.DataFrame:
    """Una riga per scenario di costo."""
    return pd.DataFrame({c: summary(add_costs(trades, c), days) for c in costs}).T.rename_axis("cost_bps_per_operation")


def by_group(trades: pd.DataFrame, key, cost_bps: float = MAIN_COST) -> pd.DataFrame:
    """Guadagno lordo e netto per gruppo (coppia, finestra d'ingresso, motivo di uscita...)."""
    t = add_costs(trades, cost_bps)
    g = t.groupby(key)
    return pd.DataFrame({
        "trade": g.size(),
        "gross_bps": g.gross_bps.mean(),
        "net_bps": g.net_bps.mean(),
        "se_bps": g.net_bps.std(ddof=1) / np.sqrt(g.size()),
        "win_rate": g.net_bps.apply(lambda x: (x > 0).mean()),
    })


def entry_window(trades: pd.DataFrame) -> pd.Series:
    """'apertura' se il segnale cade tra i minuti 15 e 30 dall'apertura (gap della notte), 'dopo' altrimenti."""
    lo, hi = OPEN_WINDOW
    return pd.Series(np.where(trades.signal_minute.between(lo, hi - 1), "apertura (15-30 min)", "dopo i 30 min"), index=trades.index, name="finestra")


# ---------------------------------------------------------------- confronto tra le versioni di risultati

def version_trades(trades: pd.DataFrame, name: str, letters=("A", "B", "C")) -> dict[str, pd.DataFrame]:
    """I trade di una versione di risultati, per lettera. Per le versioni parziali, tutte le lettere (anche la A) sono
    ristrette ai segnali che hanno una decisione, così il confronto è sugli stessi segnali."""
    dec = load_version(name)
    if not VERSIONS[name]["complete"]:
        trades = trades[trades.signal_id.isin(dec.signal_id)]
    if "letters" in VERSIONS[name]:
        letters = [x for x in letters if x == "A" or x in VERSIONS[name]["letters"]]
    elif (dec.follow_side == "").all():
        letters = [x for x in letters if x != "C"]   # senza direzione da seguire la C non si può simulare
    return {x: apply_version(trades, x, None if x == "A" else dec) for x in letters}


def compare_versions(trades: pd.DataFrame, days: pd.DatetimeIndex | None, names, costs=(0, MAIN_COST),
                     letters=("A", "B", "C")) -> pd.DataFrame:
    """Una riga per versione di risultati, lettera (A, B, C) e costo per operazione, con le metriche di `summary`.
    days=None: solo metriche per trade (per le versioni parziali, dove il portafoglio giornaliero non ha senso).
    La A compare una volta sola per sottoinsieme di segnali: è uguale per tutte le versioni complete."""
    rows, seen_A = [], set()
    for name in names:
        by_letter = version_trades(trades, name, letters)
        ids = frozenset(by_letter["A"].signal_id)
        n_all = len(ids)
        for letter, t in by_letter.items():
            label = "nessun agente" if letter == "A" else name
            if letter == "A":
                if ids in seen_A:
                    continue
                seen_A.add(ids)
            for c in costs:
                s = summary(add_costs(t, c), days if VERSIONS[name]["complete"] else None)
                rows.append(dict(decisioni=label, versione=letter, segnali=n_all, cost_bps=c, trade_esclusi=n_all - len(t)) | s)
    return pd.DataFrame(rows).set_index(["decisioni", "versione", "segnali", "cost_bps"])


def blocked_vs_random(trades: pd.DataFrame, decisions: pd.DataFrame, n_draws: int = 5000, seed: int = 0) -> dict:
    """L'agente blocca i trade giusti o a caso? Guadagno lordo medio dei trade bloccati, contro blocchi casuali dello stesso numero.

    p_value: quota di blocchi casuali che tolgono trade con guadagno medio uguale o più basso di quelli bloccati dall'agente.
    Piccolo (sotto 0,05) vuol dire che l'agente toglie trade peggiori di quanto farebbe il caso. Il costo è uguale per ogni
    trade, quindi il confronto sul lordo vale per qualsiasi scenario di costo."""
    m = trades.merge(decisions[["signal_id", "decision"]], on="signal_id", how="left")
    blocked = m.decision != "entra"
    g = m.gross_bps.to_numpy()
    k = int(blocked.sum())
    rng = np.random.default_rng(seed)
    draws = np.array([g[rng.choice(len(g), k, replace=False)].mean() for _ in range(n_draws)]) if k else np.array([np.nan])
    obs = g[blocked].mean() if k else np.nan
    return dict(segnali=len(g), bloccati=k, lordo_bloccati_bps=obs, lordo_tenuti_bps=g[~blocked].mean(), lordo_tutti_bps=g.mean(),
                lordo_bloccati_a_caso_bps=np.nanmean(draws), p_value=(draws <= obs).mean() if k else np.nan)


def save_results(tables: dict[str, pd.DataFrame]) -> list[Path]:
    """Scrive ogni tabella in Results/<nome>.csv (il nome può contenere una sottocartella, per esempio 'spark_24h/trades_B')."""
    written = []
    for key, df in tables.items():
        path = RESULTS / f"{key}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=not isinstance(df.index, pd.RangeIndex))
        written.append(path)
    return written
