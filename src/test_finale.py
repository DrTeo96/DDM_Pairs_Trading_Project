"""Il test: segnali, decisioni di finbert_episodio e trade di A, B e C dal 17 settembre al 30 ottobre 2026.

    uv run python -m src.test_finale                  controllo sul train, poi il test (fatto una volta il 14 novembre 2026: non si rifà)
    uv run python -m src.test_finale --solo-controllo solo il controllo sul train: non legge niente del test

Le regole sono scritte in docs/Test.md e sono quelle del train, senza cambiamenti:
- segnali come in 03_segnali.ipynb (emivita 60 minuti, ingresso 2, uscita 0, stop 3,5, 90 minuti), con la EMA continua dal train;
- decisioni come in varianti_agente/episodio.py (episodio con z oltre 1 e 5 minuti di margine, FinBERT, notizie mirate con al massimo
  3 ticker, forte da 0,8, segui da 0,5, stessa lista di parole dell'evento);
- trade come in backtest.apply_version.

Prima del test, le stesse funzioni rifanno il train e devono ritrovare esattamente i segnali di 03_segnali.ipynb e le decisioni e i trade
di finbert_episodio salvati in Results/varianti_agente/finbert_episodio/. Se non coincidono, il test non parte. Lo script non stampa
guadagni: i risultati si leggono in 06_test_backtest.ipynb e 07_test_robustezza.ipynb.

Scrive in Results/test/: segnali_test.csv, decisioni.csv, trades_A.csv, trades_B.csv e trades_C.csv.
I signal_id del test ripartono da 0: non vanno confrontati con quelli del train.
"""
import argparse
import re

import numpy as np
import pandas as pd

from src.backtest import _z_for, apply_version, load_trades
from src.config import DEC_FINBERT_EPISODIO, FINBERT_SCORES, FINBERT_SCORES_TEST, NEWS, NEWS_TEST, RESULTS_TEST, ROOT, SIGNALS, TEST_END, TEST_START, read_parquet
from src.signals import STOP_EXTRA, list_pairs, load_pair, run_rules, zscore
from src.varianti_agente.comune import giorni_di_borsa

# segnale: come 03_segnali.ipynb
HL, ENTRY, EXIT = 60, 2.0, 0.0
SIGNAL_COLS = ["signal_id", "pair", "ticker_A", "ticker_B", "t_signal", "t_entry", "t_exit", "direction", "z_signal", "leg_piu_mosso", "ret_A_30m", "ret_B_30m",
               "price_A_in", "price_B_in", "price_A_out", "price_B_out", "exit_reason", "gross_bps", "minutes_in_trade", "exec_price_stale", "ema", "hl_min",
               "entry_z", "exit_z", "stop_z"]

# finbert_episodio: come varianti_agente/episodio.py (non si importa da lì perché quello script gira appena lo si importa)
EPISODE_Z = 1.0
EPISODE_BUFFER = pd.Timedelta(minutes=5)
DECISION_LAG = pd.Timedelta(minutes=1)
MAX_SYMBOLS, STRONG, FOLLOW_MIN = 3, 0.8, 0.5
EVENT_RE = re.compile(r"\b(acqui\w*|merg\w*|takeover|buyout|divest\w*|spin-?off|investigat\w*|probe|subpoena\w*|lawsuit|sues|sued|settle\w*|fraud\w*|recall\w*|bankrupt\w*|"
                      r"chapter 11|resign\w*|steps? down|ousted|fired|retire\w*|new (ceo|cfo)|appoint\w*|names? (a )?(new )?(ceo|cfo)|delist\w*|going private)\b", re.I)


def segnali(periodo: str) -> pd.DataFrame:
    """I trade della A in un periodo ('train' o 'test'), con le regole di 03_segnali.ipynb, nel formato di SIGNALS."""
    all_trades = []
    for p in list_pairs().pair:
        d = load_pair(p)
        day = d.ts.normalize()
        active = d.is_train if periodo == "train" else np.asarray((day >= pd.Timestamp(TEST_START)) & (day <= pd.Timestamp(TEST_END)))
        tr, _ = run_rules(d, zscore(d.S, HL), ENTRY, EXIT, active=active)
        all_trades.append(tr)
    out = pd.concat(all_trades, ignore_index=True).sort_values(["t_signal", "pair"]).reset_index(drop=True)
    out["signal_id"] = out.index
    out["ema"] = "continua"
    out["hl_min"], out["entry_z"], out["exit_z"], out["stop_z"] = HL, ENTRY, EXIT, ENTRY + STOP_EXTRA
    return out[SIGNAL_COLS]


def notizie(periodo: str) -> pd.DataFrame:
    """Notizie con i punteggi FinBERT. Per il test anche quelle del train, che servono agli episodi "dalla notte" del 17 settembre
    (dalle 16:00 del 16): le finestre prendono comunque solo notizie uscite prima della decisione."""
    news = read_parquet(NEWS).merge(pd.read_parquet(FINBERT_SCORES), on="id")
    if periodo == "test":
        test = read_parquet(NEWS_TEST).merge(pd.read_parquet(FINBERT_SCORES_TEST), on="id")
        assert len(test) == len(read_parquet(NEWS_TEST)), "manca il punteggio FinBERT di qualche notizia del test"
        news = pd.concat([news, test[news.columns]], ignore_index=True).drop_duplicates("id").sort_values(["ts", "id"]).reset_index(drop=True)
    news["strong"] = news[["p_pos", "p_neg"]].max(axis=1) >= STRONG
    news["event"] = (news.headline.fillna("") + " " + news.summary.fillna("")).map(lambda s: bool(EVENT_RE.search(s)))
    return news


def decisioni(trades: pd.DataFrame, news: pd.DataFrame) -> pd.DataFrame:
    """Decisioni B e C di finbert_episodio per ogni segnale, come in varianti_agente/episodio.py (passi 1 e 2)."""
    tdays = giorni_di_borsa()
    cache, rows = {}, []
    for t in trades.itertuples():
        # 1. inizio dell'episodio
        d, z = _z_for(t.pair, t.hl_min, t.ema, cache)
        i = d.ts.get_loc(t.t_signal)
        assert np.isclose(z[i], t.z_signal), f"segnale {t.signal_id}: z diverso dai segnali"
        side, j, first = np.sign(z[i]), i, d.day_start[i]
        while j - 1 >= first and side * z[j - 1] > EPISODE_Z:
            j -= 1
        if j == first and side * z[j] > EPISODE_Z:
            start, kind = tdays[tdays < t.t_signal.normalize()].max() + pd.Timedelta(hours=16), "dalla notte"
        else:
            start, kind = d.ts[j] - EPISODE_BUFFER, "in seduta"
        # 2. decisioni
        w = news[(news.ts >= start) & (news.ts < t.t_signal + DECISION_LAG) & (news.n_symbols <= MAX_SYMBOLS)]
        mA, mB = w[f"mentions_{t.ticker_A}"].astype(bool), w[f"mentions_{t.ticker_B}"].astype(bool)
        keep = mA ^ mB
        tg = w[keep].assign(side=np.where(mA[keep], "A", "B"))
        st = tg[tg.strong]
        block = bool(len(st)) and st.side.nunique() == 1 and bool(st.event.any())
        sA = tg.loc[tg.side == "A", "score"].mean() if (tg.side == "A").any() else 0.0
        sB = tg.loc[tg.side == "B", "score"].mean() if (tg.side == "B").any() else 0.0
        rel, move = sA - sB, t.ret_A_30m - t.ret_B_30m
        follow = abs(rel) >= FOLLOW_MIN and np.sign(rel) == np.sign(move)
        dec = "blocca" if block else "entra"
        rows.append(dict(signal_id=t.signal_id, pair=t.pair, t_signal=t.t_signal, ep_kind=kind, ep_start=start, n_targeted=len(tg), n_strong=len(st),
                         n_in_signal_bar=int(((tg.ts >= t.t_signal) & (tg.ts < t.t_signal + DECISION_LAG)).sum()),
                         rel_score=rel, decision=dec, decision_C="segui" if follow else dec,
                         follow_side=(f"long {t.ticker_A} / short {t.ticker_B}" if rel > 0 else f"short {t.ticker_A} / long {t.ticker_B}") if follow else "",
                         headlines=" | ".join(tg.headline.astype(str))))
    return pd.DataFrame(rows)


def _same(a: pd.DataFrame, b: pd.DataFrame, cols, what: str) -> None:
    a, b = a.reset_index(drop=True), b.reset_index(drop=True)
    if len(a) != len(b):
        raise SystemExit(f"CONTROLLO FALLITO ({what}): {len(a)} righe invece di {len(b)}. Il test non parte.")
    for c in cols:
        x, y = a[c], b[c]
        ok = np.allclose(x.astype(float), y.astype(float), equal_nan=True) if pd.api.types.is_numeric_dtype(y) and not pd.api.types.is_bool_dtype(y) \
            else (x.astype(str).fillna("") == y.astype(str).fillna("")).all()
        if not ok:
            raise SystemExit(f"CONTROLLO FALLITO ({what}): la colonna {c} non coincide. Il test non parte.")


def controllo_train() -> None:
    """Le funzioni di questo script, applicate al train, devono rifare esattamente i file del train."""
    sig = segnali("train")
    saved = pd.read_csv(SIGNALS, parse_dates=["t_signal", "t_entry", "t_exit"])
    _same(sig, saved, SIGNAL_COLS, "segnali del train")
    trades = load_trades()
    dec = decisioni(trades, notizie("train"))
    saved_dec = pd.read_csv(DEC_FINBERT_EPISODIO).fillna({"follow_side": ""})
    _same(dec.assign(follow_side=dec.follow_side.fillna("")), saved_dec, ["signal_id", "decision", "decision_C", "follow_side", "n_targeted", "n_strong", "rel_score"],
          "decisioni di finbert_episodio sul train")
    for letter, col in (("B", "decision"), ("C", "decision_C")):
        t = apply_version(trades, letter, dec)
        ref = pd.read_csv(DEC_FINBERT_EPISODIO.parent / f"trades_{letter}.csv")
        _same(t.sort_values("signal_id"), ref.sort_values("signal_id"), ["signal_id", "gross_bps"], f"trade {letter} di finbert_episodio sul train")
    print(f"controllo sul train superato: {len(sig)} segnali, decisioni e trade B e C di finbert_episodio identici a quelli salvati")


def test() -> None:
    news_test = read_parquet(NEWS_TEST)
    sig = segnali("test")
    assert sig.t_signal.min() >= pd.Timestamp(TEST_START) and sig.t_exit.max() < pd.Timestamp(TEST_END) + pd.Timedelta(days=1), "segnali fuori dal test"
    RESULTS_TEST.mkdir(parents=True, exist_ok=True)
    sig.to_csv(RESULTS_TEST / "segnali_test.csv", index=False)
    trades = load_trades(RESULTS_TEST / "segnali_test.csv", allow_test=True)
    dec = decisioni(trades, notizie("test"))
    out = {"segnali_test": sig, "decisioni": dec, "trades_A": apply_version(trades, "A"),
           "trades_B": apply_version(trades, "B", dec), "trades_C": apply_version(trades, "C", dec)}
    for name, df in out.items():
        if name != "segnali_test":
            df.to_csv(RESULTS_TEST / f"{name}.csv", index=False)
    print(f"test fatto: {len(sig)} segnali in {sig.t_signal.dt.normalize().nunique()} giorni, {(dec.decision == 'blocca').sum()} blocchi nella B, "
          f"{(dec.decision_C == 'segui').sum()} segui nella C ({len(news_test)} notizie del test)")
    print(f"salvati in {RESULTS_TEST.relative_to(ROOT)}: {', '.join(out)}. I risultati si leggono in 06_test_backtest.ipynb e 07_test_robustezza.ipynb.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--solo-controllo", action="store_true", help="solo il controllo sul train, senza leggere il test")
    a = ap.parse_args()
    controllo_train()
    if not a.solo_controllo:
        test()
