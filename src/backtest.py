"""Simulazione (Passaggio 6): costi, tre versioni (A, B, C) e metriche sui trade dei segnali del Passaggio 4.

Il motore non rifà il segnale: parte dalla tabella dei trade di 03_segnali.ipynb (orari, prezzi, direzione, guadagno lordo)
e ci applica, in questo ordine, la decisione della versione (A, B o C), i costi e il capitale.
In un notebook:
    from src.backtest import load_trades, apply_version, add_costs, summary, daily_pnl
    trades = load_trades()                                  # trade del train
    a = add_costs(apply_version(trades, "A"), cost_bps=5)   # versione A, 5 bps per operazione
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
"""
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import SIGNALS, TRAIN_END
from src.signals import list_pairs, load_pair

NOTIONAL_LEG = 10_000         # dollari per gamba (scelta di Bea): importo uguale sulle due gambe, senza leva
CAPITAL_PER_PAIR = 2 * NOTIONAL_LEG
OPERATIONS_PER_TRADE = 4      # apertura e chiusura di due gambe
COST_SCENARIOS = [0, 2, 5, 10]  # punti base per operazione (decisione 8)
MAIN_COST = 5                 # scenario realistico, deciso prima di guardare i risultati
DAYS_PER_YEAR = 252
OPEN_WINDOW = (15, 30)        # minuti dall'apertura del segnale: "gap della notte" se il segnale cade qui

DECISIONS = {"entra", "blocca", "segui"}  # decisioni possibili dell'agente (Passaggio 5)


def load_trades(path: Path = SIGNALS, allow_test: bool = False) -> pd.DataFrame:
    """Trade del Passaggio 4. Orari come datetime; minuto del segnale dall'apertura delle 9:30."""
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


def apply_version(trades: pd.DataFrame, version: str, decisions: pd.DataFrame | None = None) -> pd.DataFrame:
    """Seleziona i trade della versione A, B o C.

    A: tutti i segnali entrano, senza agente.
    B: l'agente può solo bloccare. `decisions` ha le colonne signal_id e decision ('entra' o 'blocca'): i trade bloccati escono.
    C: l'agente decide anche la direzione ('segui'). Non è ancora implementata: seguire la notizia cambia la direzione del trade
       e quindi anche l'uscita, per cui va rifatta la simulazione barra per barra; ribaltare il segno del guadagno darebbe un numero falso.
    Se per un segnale non c'è nessuna decisione, nelle versioni B e C si blocca (regola di sicurezza del Passaggio 5)."""
    if version == "A":
        return trades.copy()
    if decisions is None:
        raise ValueError(f"la versione {version} richiede le decisioni dell'agente")
    bad = set(decisions.decision) - DECISIONS
    if bad:
        raise ValueError(f"decisioni sconosciute: {bad}")
    if version == "C" or "segui" in set(decisions.decision):
        raise NotImplementedError("versione C: serve la simulazione con direzione scelta dall'agente")
    if version != "B":
        raise ValueError("versione deve essere A, B o C")
    ok = trades.merge(decisions[["signal_id", "decision"]], on="signal_id", how="left")
    return ok[ok.decision == "entra"].drop(columns="decision").reset_index(drop=True)


def random_decisions(trades: pd.DataFrame, p_block: float = 0.2, seed: int = 0) -> pd.DataFrame:
    """Decisioni finte (blocco casuale), solo per verificare che il motore funzioni: non vanno interpretate."""
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"signal_id": trades.signal_id, "decision": np.where(rng.random(len(trades)) < p_block, "blocca", "entra")})


def add_costs(trades: pd.DataFrame, cost_bps: float) -> pd.DataFrame:
    """Aggiunge il costo, il guadagno netto in punti base e il guadagno netto in dollari."""
    t = trades.copy()
    t["cost_bps"] = OPERATIONS_PER_TRADE * cost_bps
    t["net_bps"] = t.gross_bps - t.cost_bps
    t["pnl_usd"] = t.net_bps / 1e4 * NOTIONAL_LEG
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
    """Metriche dei trade (in punti base) e, se si passano i giorni, del portafoglio giornaliero."""
    net = trades.net_bps if "net_bps" in trades else trades.gross_bps
    n = len(net)
    wins, losses = net[net > 0], net[net < 0]
    out = {
        "trade": n,
        "gross_bps": trades.gross_bps.mean(),
        "net_bps": net.mean(),
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
