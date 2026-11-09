"""Segnali di pairs trading (Passaggio 4) per tutte le coppie: spread, z-score con EMA, regole di ingresso e uscita.

Sono le stesse regole di segnale_mav.ipynb (coppia MA-V), scritte come funzioni per poterle applicare alle 10 coppie.
Serve un ambiente con duckdb, pandas e numpy.
In un notebook dentro src/:
    from signals import list_pairs, load_pair, zscore, run_rules
    d = load_pair("KO-PEP")
    z = zscore(d.S, hl=120)
    trades, blocked = run_rules(d, z, entry=2.0, exit_=0.0)

Le regole (spiegate con le motivazioni in segnale_mav.ipynb):
- spread logaritmico con beta = 1: S = ln(prezzo A) - ln(prezzo B), perché gli importi sulle due gambe sono uguali
- z-score = (S - EMA(S)) / deviazione standard esponenziale; EMA continua su tutta la serie (la notte conta come una barra)
- ingresso alla chiusura della barra t se |z| >= soglia, esecuzione all'apertura della barra t+1 (niente lookahead)
- non si apre se una delle due gambe ha la barra t riempita (nessuno scambio in quel minuto: prezzo vecchio)
- uscita al primo tra: rientro (|z| <= soglia di uscita), stop (|z| >= ingresso + STOP_EXTRA), tempo (MAX_HOLD minuti), fine giornata
- guadagno lordo in punti base sull'importo di una gamba: senza costi (i costi sono nel Passaggio 6)
"""
from dataclasses import dataclass
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PAIRS_DIR = ROOT / "data/processed/pairs_intraday"     # file puliti del Passaggio 2
SELECTED = ROOT / "data/processed/selected_pairs.csv"  # le 10 coppie del Passaggio 1 (versione 1)
PAIRS_DIR_V2 = ROOT / "data/processed/pairs_intraday_v2"   # versione 2: file puliti del Passaggio 2 per le 15 coppie
SELECTED_V2 = ROOT / "data/processed/selected_pairs_2.csv"  # versione 2: le 15 coppie del Passaggio 1

TRAIN_END = "2026-09-16"   # ultimo giorno del train, uguale per tutte le coppie (date di calendario); il test è dal 17 settembre
N_MINUTES = 390            # barre da 1 minuto nella seduta: 09:30-15:59
EMA_MIN_PERIODS = 60       # barre di storia necessarie prima di fidarsi di media e deviazione standard della EMA
OPEN_SKIP = 15             # niente nuovi ingressi nei primi 15 minuti
CLOSE_SKIP = 30            # niente nuovi ingressi negli ultimi 30 minuti
MAX_HOLD = 90              # tempo massimo di permanenza, in minuti
STOP_EXTRA = 1.5           # stop-loss: ingresso + 1.5 in unità di z
LOOKBACK = 30              # minuti usati solo per la colonna descrittiva "titolo più mosso"


def list_pairs(version: int = 1) -> pd.DataFrame:
    """Le coppie con i ticker Bloomberg (colonne pair, A, B) e i ticker brevi (sym_A, sym_B). version=1: le 10 coppie; version=2: le 15 coppie della versione 2."""
    sel = pd.read_csv(SELECTED if version == 1 else SELECTED_V2)[["pair", "A", "B"]]
    sel["sym_A"] = sel["A"].str.split().str[0]
    sel["sym_B"] = sel["B"].str.split().str[0]
    return sel


@dataclass
class PairData:
    pair: str
    sym_A: str
    sym_B: str
    ts: pd.DatetimeIndex
    S: pd.Series              # spread logaritmico, indicizzato per orario
    day_id: np.ndarray        # numero del giorno di seduta, 0, 1, 2...
    minute: np.ndarray        # minuti dall'apertura: 0 = barra delle 09:30, 389 = barra delle 15:59
    last_of_day: np.ndarray   # True sull'ultima barra di ogni giorno
    day_start: np.ndarray     # indice della prima barra della giornata di ogni barra
    oA: np.ndarray            # prezzi di apertura e di chiusura dei due titoli
    oB: np.ndarray
    cA: np.ndarray
    cB: np.ndarray
    stale: np.ndarray         # True se almeno una delle due gambe ha la barra riempita
    filled_A: np.ndarray
    filled_B: np.ndarray
    is_train: np.ndarray      # True per le barre dei giorni fino a TRAIN_END


def load_pair(pair: str, version: int = 1) -> PairData:
    """Legge il file pulito a 1 minuto di una coppia (Passaggio 2) e prepara gli array usati dal motore. version=2: coppie della versione 2."""
    row = list_pairs(version).set_index("pair").loc[pair]
    folder = PAIRS_DIR if version == 1 else PAIRS_DIR_V2
    raw = duckdb.sql(f"SELECT * FROM '{(folder / f'{pair}_1min.parquet').as_posix()}'").df()
    wide = lambda col: raw.pivot(index="ts", columns="ticker", values=col).sort_index()
    close, open_, filled = wide("close"), wide("open"), wide("filled")
    assert close.isna().sum().sum() == 0, f"{pair}: ci sono prezzi mancanti"
    ts = close.index
    day = ts.normalize()
    n = len(ts)
    day_id = pd.factorize(day)[0]
    first_of_day = np.r_[True, day_id[1:] != day_id[:-1]]
    return PairData(
        pair=pair, sym_A=row["sym_A"], sym_B=row["sym_B"], ts=ts,
        S=np.log(close[row["A"]]) - np.log(close[row["B"]]),
        day_id=day_id, minute=(ts.hour * 60 + ts.minute - (9 * 60 + 30)).to_numpy(),
        last_of_day=np.r_[day_id[1:] != day_id[:-1], True],
        day_start=np.maximum.accumulate(np.where(first_of_day, np.arange(n), 0)),
        oA=open_[row["A"]].to_numpy(), oB=open_[row["B"]].to_numpy(), cA=close[row["A"]].to_numpy(), cB=close[row["B"]].to_numpy(),
        stale=(filled[row["A"]] | filled[row["B"]]).to_numpy(), filled_A=filled[row["A"]].to_numpy(), filled_B=filled[row["B"]].to_numpy(),
        is_train=np.asarray(day <= pd.Timestamp(TRAIN_END)),
    )


def zscore(S: pd.Series, hl: float, reset_daily: bool = False) -> np.ndarray:
    """Z-score di S con media e deviazione standard esponenziali. hl = emivita in barre da 1 minuto.
    reset_daily=False: EMA continua su tutta la serie (scelta del gruppo). reset_daily=True: la EMA riparte ogni mattina (confronto).
    Causale: il valore di una barra usa solo barre passate e la barra stessa."""
    if reset_daily:
        g = S.groupby(S.index.normalize())
        mean = g.transform(lambda x: x.ewm(halflife=hl, min_periods=30).mean())
        std = g.transform(lambda x: x.ewm(halflife=hl, min_periods=30).std())
    else:
        mean = S.ewm(halflife=hl, min_periods=EMA_MIN_PERIODS).mean()
        std = S.ewm(halflife=hl, min_periods=EMA_MIN_PERIODS).std()
    return ((S - mean) / std).to_numpy()


def run_rules(d: PairData, z: np.ndarray, entry: float, exit_: float, stop: float | None = None, active: np.ndarray | None = None):
    """Applica le regole alla serie di z-score, barra per barra, in ordine cronologico, solo sulle barre `active` (di default il train).
    Restituisce (tabella dei trade, numero di barre candidate scartate perché una gamba era riempita)."""
    stop = entry + STOP_EXTRA if stop is None else stop
    active = d.is_train if active is None else active
    n, ts = len(d.ts), d.ts
    trades, blocked, i = [], 0, 0
    while i < n - 1:
        if not active[i]:
            i += 1
            continue
        candidate = (not np.isnan(z[i])) and abs(z[i]) >= entry and OPEN_SKIP <= d.minute[i] <= N_MINUTES - 1 - CLOSE_SKIP
        if not candidate:
            i += 1
            continue
        if d.stale[i]:                     # una gamba ha il prezzo vecchio: non si apre
            blocked += 1
            i += 1
            continue
        side = np.sign(z[i])               # +1: spread alto (short A, long B); -1: spread basso (long A, short B)
        e = i + 1                          # esecuzione alla barra successiva
        s_in = np.log(d.oA[e] / d.oB[e])
        k = e
        while True:
            reason = None
            if d.last_of_day[k]:
                reason, a_out, b_out = "fine_giornata", d.cA[k], d.cB[k]
                break
            zk = side * z[k]
            if zk <= exit_: reason = "rientro"
            elif zk >= stop: reason = "stop"
            elif k - e + 1 >= MAX_HOLD: reason = "tempo"
            if reason:
                k += 1                     # l'uscita si esegue all'apertura della barra successiva
                a_out, b_out = d.oA[k], d.oB[k]
                break
            k += 1
        s_out = np.log(a_out / b_out)
        start = max(i - LOOKBACK + 1, d.day_start[i])
        trades.append(dict(
            pair=d.pair, t_signal=ts[i], t_entry=ts[e], t_exit=ts[k], side=-int(side), z_signal=z[i], exit_reason=reason,
            price_A_in=d.oA[e], price_B_in=d.oB[e], price_A_out=a_out, price_B_out=b_out, exec_price_stale=bool(d.stale[e]),
            ret_A_30m=np.log(d.cA[i] / d.oA[start]), ret_B_30m=np.log(d.cB[i] / d.oB[start]),
            gross_bps=-side * (s_out - s_in) * 1e4,
        ))
        i = k + 1                          # una barra di pausa dopo ogni uscita
    out = pd.DataFrame(trades)
    if len(out):
        out["ticker_A"], out["ticker_B"] = d.sym_A, d.sym_B
        out["leg_piu_mosso"] = np.where(out.ret_A_30m.abs() >= out.ret_B_30m.abs(), d.sym_A, d.sym_B)
        out["direction"] = np.where(out.side > 0, f"long {d.sym_A} / short {d.sym_B}", f"short {d.sym_A} / long {d.sym_B}")
        out["minutes_in_trade"] = (out.t_exit - out.t_entry).dt.total_seconds() / 60
        out["minute_of_day"] = (out.t_entry.dt.hour * 60 + out.t_entry.dt.minute) - (9 * 60 + 30)
    return out, blocked
