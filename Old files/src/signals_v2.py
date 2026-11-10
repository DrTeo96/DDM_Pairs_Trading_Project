"""Segnali di pairs trading, versione 2 (rilettura del Passaggio 4 dopo il backtest con costi del Passaggio 6).

Stesse regole di signals.py, con tre parametri in più che signals.py non ha (quel file non è modificato):
- soglia minima in punti base: si entra solo se lo scostamento |S - EMA| vale almeno `min_dev_bps`, oltre a |z| >= ingresso
- tempo massimo `max_hold` come parametro (in signals.py è una costante); 390 = solo chiusura di fine giornata
- barre del segnale da 1 o 5 minuti: con 5 minuti lo z-score si calcola sulle barre da 5 e si decide alla chiusura di ogni barra
  (l'ultimo minuto della barra); l'esecuzione è sempre all'apertura del minuto dopo, sui dati al minuto, quindi niente lookahead

In un notebook dentro src/:
    from signals_v2 import run_grid, finalize
    trades = finalize(run_grid(pairs, bars_list=[1, 5], dev_list=[0, 8, 20], hold_list=[90, 180, 390]))
"""
import duckdb
import numpy as np
import pandas as pd

from signals import (PAIRS_DIR, EMA_MIN_PERIODS, OPEN_SKIP, CLOSE_SKIP, N_MINUTES, STOP_EXTRA, LOOKBACK,
                     PairData, list_pairs, load_pair)

HL_MIN = 60              # emivita in minuti, uguale per tutte le coppie (Passaggio 4)
BAR_MINUTES_EMA_MIN = 60  # minuti di storia necessari alla EMA: 60 barre da 1 minuto o 12 da 5 minuti


def ema_z(S: pd.Series, hl: float, min_periods: int) -> tuple[np.ndarray, np.ndarray]:
    """Z-score (EMA continua, come signals.zscore) e scostamento S - EMA in punti base. Causali."""
    mean = S.ewm(halflife=hl, min_periods=min_periods).mean()
    std = S.ewm(halflife=hl, min_periods=min_periods).std()
    return ((S - mean) / std).to_numpy(), ((S - mean) * 1e4).to_numpy()


def signal_arrays(d: PairData, bars: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """z, scostamento in bps e barra riempita, sulla griglia del minuto di `d`.
    bars=1: i tre array sono quelli di signals.py. bars=5: z e scostamento valgono solo all'ultimo minuto di ogni barra da 5 (NaN altrove),
    quindi ingressi e uscite per z-score avvengono solo a quel punto; la barra è 'riempita' se una gamba non ha avuto nessuno scambio nei 5 minuti."""
    if bars == 1:
        z, dev = ema_z(d.S, HL_MIN, EMA_MIN_PERIODS)
        return z, dev, d.stale
    row = list_pairs().set_index("pair").loc[d.pair]
    raw = duckdb.sql(f"SELECT * FROM '{(PAIRS_DIR / f'{d.pair}_{bars}min.parquet').as_posix()}'").df()
    close = raw.pivot(index="ts", columns="ticker", values="close").sort_index()
    share = raw.pivot(index="ts", columns="ticker", values="filled_share").sort_index()
    S = np.log(close[row["A"]]) - np.log(close[row["B"]])
    z, dev = ema_z(S, HL_MIN / bars, BAR_MINUTES_EMA_MIN // bars)
    stale = ((share[row["A"]] >= 1) | (share[row["B"]] >= 1)).to_numpy()
    decision = S.index + pd.Timedelta(minutes=bars - 1)    # la barra si chiude all'ultimo minuto
    on_grid = lambda x, fill: pd.Series(x, index=decision).reindex(d.ts, fill_value=fill).to_numpy()
    return on_grid(z, np.nan), on_grid(dev, np.nan), on_grid(stale, False).astype(bool)


def run_rules_v2(d: PairData, z, dev, stale, entry: float, exit_: float, stop: float | None, max_hold: int, min_dev_bps: float,
                 active: np.ndarray | None = None):
    """Come signals.run_rules, con soglia minima in bps, tempo massimo e barra riempita come parametri.
    Restituisce (tabella dei trade, numero di barre candidate scartate per gamba ferma)."""
    stop = entry + STOP_EXTRA if stop is None else stop
    active = d.is_train if active is None else active
    n, ts = len(d.ts), d.ts
    trades, blocked, i = [], 0, 0
    while i < n - 1:
        if not active[i]:
            i += 1
            continue
        candidate = ((not np.isnan(z[i])) and abs(z[i]) >= entry and abs(dev[i]) >= min_dev_bps
                     and OPEN_SKIP <= d.minute[i] <= N_MINUTES - 1 - CLOSE_SKIP)
        if not candidate:
            i += 1
            continue
        if stale[i]:
            blocked += 1
            i += 1
            continue
        side = np.sign(z[i])
        e = i + 1
        s_in = np.log(d.oA[e] / d.oB[e])
        k = e
        while True:
            reason = None
            if d.last_of_day[k]:
                reason, a_out, b_out = "fine_giornata", d.cA[k], d.cB[k]
                break
            zk = side * z[k]                     # NaN fuori dai minuti di decisione: nessuna uscita per z-score
            if zk <= exit_: reason = "rientro"
            elif zk >= stop: reason = "stop"
            elif k - e + 1 >= max_hold: reason = "tempo"
            if reason:
                k += 1
                a_out, b_out = d.oA[k], d.oB[k]
                break
            k += 1
        s_out = np.log(a_out / b_out)
        start = max(i - LOOKBACK + 1, d.day_start[i])
        trades.append(dict(
            pair=d.pair, t_signal=ts[i], t_entry=ts[e], t_exit=ts[k], side=-int(side), z_signal=z[i], dev_bps=dev[i], exit_reason=reason,
            price_A_in=d.oA[e], price_B_in=d.oB[e], price_A_out=a_out, price_B_out=b_out, exec_price_stale=bool(d.stale[e]),
            ret_A_30m=np.log(d.cA[i] / d.oA[start]), ret_B_30m=np.log(d.cB[i] / d.oB[start]),
            gross_bps=-side * (s_out - s_in) * 1e4,
        ))
        i = k + 1
    out = pd.DataFrame(trades)
    if len(out):
        out["ticker_A"], out["ticker_B"] = d.sym_A, d.sym_B
        out["leg_piu_mosso"] = np.where(out.ret_A_30m.abs() >= out.ret_B_30m.abs(), d.sym_A, d.sym_B)
        out["direction"] = np.where(out.side > 0, f"long {d.sym_A} / short {d.sym_B}", f"short {d.sym_A} / long {d.sym_B}")
        out["minutes_in_trade"] = (out.t_exit - out.t_entry).dt.total_seconds() / 60
    return out, blocked


def run_grid(pairs, bars_list, dev_list, hold_list, entry: float = 2.0, exit_: float = 0.0, stop: float = 3.5) -> pd.DataFrame:
    """Tutti i trade del train di tutte le combinazioni; le colonne bars, min_dev_bps, max_hold dicono di quale combinazione sono."""
    out = []
    for pair in pairs:
        d = load_pair(pair)
        for bars in bars_list:
            z, dev, stale = signal_arrays(d, bars)
            for min_dev in dev_list:
                for hold in hold_list:
                    tr, _ = run_rules_v2(d, z, dev, stale, entry, exit_, stop, hold, min_dev)
                    if len(tr):
                        out.append(tr.assign(bars=bars, min_dev_bps=min_dev, max_hold=hold))
    return pd.concat(out, ignore_index=True)


def finalize(trades: pd.DataFrame) -> pd.DataFrame:
    """Aggiunge le colonne usate da backtest.py (signal_id, minuto del segnale, giorno) e ordina per orario."""
    t = trades.sort_values(["t_signal", "pair"]).reset_index(drop=True)
    t["signal_minute"] = t.t_signal.dt.hour * 60 + t.t_signal.dt.minute - (9 * 60 + 30)
    t["day"] = t.t_exit.dt.normalize()
    return t
