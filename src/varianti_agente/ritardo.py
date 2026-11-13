"""Varianti 16 (B_k) e 17 (C_k): decisione e ingresso k minuti dopo il segnale, contro una A ritardata dello stesso k. Regole in registro_varianti.md.

Per ogni segnale della A (barra i): decisione alla chiusura della barra i + k, ingresso all'apertura della barra dopo, uscita con le regole
di signals.run_rules (rientro, stop, MAX_HOLD, fine giornata). Con k = 0 deve riprodurre i 973 trade della A (controllo).
L'agente FinBERT legge le notizie dall'inizio dell'episodio (variante 14) alla chiusura della barra della decisione.

Legge le decisioni di episodio.py (inizio dell'episodio). Scrive in Results/varianti_agente/ritardo/: ritardo.csv e i trade di A_k, B_k, C_k.
Uso: uv run python -m src.varianti_agente.ritardo
"""
import re
from math import comb

import numpy as np
import pandas as pd
from src.backtest import _z_for, add_costs, load_trades, summary, trading_days
from src.config import DEC_FINBERT_EPISODIO, FINBERT_SCORES, NEWS, RESULTS, VARIANTI, read_parquet
from src.signals import LOOKBACK, MAX_HOLD

OUT = VARIANTI / "ritardo"
DELAYS = (5, 15)
MAX_SYMBOLS, STRONG, FOLLOW_MIN = 3, 0.8, 0.5
EVENT_RE = re.compile(r"\b(acqui\w*|merg\w*|takeover|buyout|divest\w*|spin-?off|investigat\w*|probe|subpoena\w*|lawsuit|sues|sued|settle\w*|fraud\w*|recall\w*|bankrupt\w*|"
                      r"chapter 11|resign\w*|steps? down|ousted|fired|retire\w*|new (ceo|cfo)|appoint\w*|names? (a )?(new )?(ceo|cfo)|delist\w*|going private)\b", re.I)
pd.options.display.float_format = "{:,.2f}".format
pd.options.display.width = 220

trades, days = load_trades(), trading_days()
ep = pd.read_csv(DEC_FINBERT_EPISODIO, parse_dates=["ep_start"]).set_index("signal_id").ep_start
news = read_parquet(NEWS).merge(pd.read_parquet(FINBERT_SCORES), on="id")
news = news[news.n_symbols <= MAX_SYMBOLS]
news["strong"] = news[["p_pos", "p_neg"]].max(axis=1) >= STRONG
news["event"] = (news.headline.fillna("") + " " + news.summary.fillna("")).map(lambda s: bool(EVENT_RE.search(s)))
cache = {}


def simulate(t, d, z, i: int, k: int, long_A: bool, with_stop: bool):
    """Un trade con decisione alla barra i + k. long_A: direzione del trade. with_stop: la A usa lo stop, la C che segue no. None se non si entra."""
    dec = i + k
    if dec + 1 >= len(d.ts) or d.day_id[dec] != d.day_id[i] or d.last_of_day[dec]:
        return None, "giornata finita nell'attesa"
    side = np.sign(z[i])
    if k > 0 and side * z[dec] <= t.exit_z:
        return None, "rientrato nell'attesa"
    e = dec + 1
    s_in, j = np.log(d.oA[e] / d.oB[e]), e
    while True:
        if d.last_of_day[j]:
            reason, a_out, b_out = "fine_giornata", d.cA[j], d.cB[j]
            break
        zj = side * z[j]
        reason = "rientro" if zj <= t.exit_z else "stop" if (with_stop and zj >= t.stop_z) else "tempo" if j - e + 1 >= MAX_HOLD else None
        if reason:
            j += 1
            a_out, b_out = d.oA[j], d.oB[j]
            break
        j += 1
    sign = 1 if long_A else -1
    t_exit = d.ts[j]
    return dict(signal_id=t.signal_id, pair=t.pair, t_entry=d.ts[e], t_exit=t_exit, exit_reason=reason,
                gross_bps=sign * (np.log(a_out / b_out) - s_in) * 1e4, minutes_in_trade=(t_exit - d.ts[e]).total_seconds() / 60, day=t_exit.normalize()), None


def agent(t, d, i: int, k: int) -> tuple[str, bool | None, int]:
    """Decisione FinBERT (regole delle varianti 14 e 15) con le notizie fino alla chiusura della barra della decisione."""
    dec = i + k
    w = news[(news.ts >= ep.loc[t.signal_id]) & (news.ts < d.ts[dec] + pd.Timedelta(minutes=1))]
    mA, mB = w[f"mentions_{t.ticker_A}"].astype(bool), w[f"mentions_{t.ticker_B}"].astype(bool)
    keep = mA ^ mB
    tg = w[keep].assign(side=np.where(mA[keep], "A", "B"))
    st = tg[tg.strong]
    block = bool(len(st)) and st.side.nunique() == 1 and bool(st.event.any())
    sA = tg.loc[tg.side == "A", "score"].mean() if (tg.side == "A").any() else 0.0
    sB = tg.loc[tg.side == "B", "score"].mean() if (tg.side == "B").any() else 0.0
    rel = sA - sB
    start = max(dec - LOOKBACK + 1, d.day_start[dec])
    move = np.log(d.cA[dec] / d.oA[start]) - np.log(d.cB[dec] / d.oB[start])
    if abs(rel) >= FOLLOW_MIN and np.sign(rel) == np.sign(move):
        return "segui", rel > 0, len(tg)
    return ("blocca" if block else "entra"), None, len(tg)


def fisher(a, b, c, dd):
    r1, c1, n = a + b, a + c, a + b + c + dd
    p = lambda x: comb(c1, x) * comb(n - c1, r1 - x) / comb(n, r1)   # noqa: E731
    return min(1.0, sum(p(x) for x in range(max(0, r1 + c1 - n), min(r1, c1) + 1) if p(x) <= p(a) * (1 + 1e-9)))


# ---------------------------------------------------------------- controllo: con k = 0 si riproduce la A
check = []
for t in trades.itertuples():
    d, z = _z_for(t.pair, t.hl_min, t.ema, cache)
    i = d.ts.get_loc(t.t_signal)
    r, _ = simulate(t, d, z, i, 0, t.direction.startswith("long"), True)
    check.append(r["gross_bps"])
assert np.allclose(check, trades.gross_bps.values), "con k = 0 la simulazione non riproduce la A"
print(f"controllo ok: con k = 0 i {len(trades)} trade coincidono con la A (lordo medio {np.mean(check):.2f} bps)\n")

rows, detail = [], []
for k in DELAYS:
    A_k, B_k, C_k, skipped, blocked_ids, follow_rows = [], [], [], {}, [], []
    for t in trades.itertuples():
        d, z = _z_for(t.pair, t.hl_min, t.ema, cache)
        i = d.ts.get_loc(t.t_signal)
        a_long = t.direction.startswith("long")
        ra, why = simulate(t, d, z, i, k, a_long, True)
        if ra is None:
            skipped[why] = skipped.get(why, 0) + 1
            continue
        A_k.append(ra)
        dec, f_long, n_news = agent(t, d, i, k)
        if dec == "blocca":
            blocked_ids.append(t.signal_id)
            continue
        B_k.append(ra)
        if dec == "segui" and f_long != a_long:
            rc, _ = simulate(t, d, z, i, k, f_long, False)
            if rc is not None:
                C_k.append(rc | {"c_kind": "segui"})
                follow_rows.append({"signal_id": t.signal_id, "gross_C": rc["gross_bps"], "gross_A_k": ra["gross_bps"]})
        else:
            C_k.append(ra | {"c_kind": "entra"})
    A_k, B_k, C_k = pd.DataFrame(A_k), pd.DataFrame(B_k), pd.DataFrame(C_k)
    OUT.mkdir(parents=True, exist_ok=True)
    for letter, tt in (("A", A_k), ("B", B_k), ("C", C_k)):
        add_costs(tt, 0).to_csv(OUT / f"trades_{letter}_{k}min.csv", index=False)
    # nei trade della C che segue non c'è blocco: i bloccati restano fuori anche dalla C (come nella variante 15)
    print(f"k = {k} minuti: segnali senza trade {skipped} | A_k {len(A_k)} trade | B_k blocca {len(blocked_ids)} | C_k segue (direzione invertita) {len(follow_rows)}")
    for name, tt in ((f"A ritardata {k} min", A_k), (f"16 B FinBERT {k} min", B_k), (f"17 C FinBERT {k} min", C_k)):
        for c in (0, 5):
            sm = summary(add_costs(tt, c), days)
            rows.append({"versione": name, "costo": c, "trade": sm["trade"], "net_bps": sm["net_bps"], "pnl_usd": sm["pnl_usd"], "sharpe": sm["sharpe"]})
    Ak = A_k.assign(rientro=A_k.exit_reason.eq("rientro"))
    blk, kept = Ak[Ak.signal_id.isin(blocked_ids)], Ak[~Ak.signal_id.isin(blocked_ids)]
    if len(blk):
        p = fisher(int(blk.rientro.sum()), len(blk) - int(blk.rientro.sum()), int(kept.rientro.sum()), len(kept) - int(kept.rientro.sum()))
        print(f"   bloccati: rientro {blk.rientro.mean():.0%} contro {kept.rientro.mean():.0%} (p Fisher {p:.2f}), lordo medio {blk.gross_bps.mean():.1f}, mediano {blk.gross_bps.median():.1f}")
    if follow_rows:
        f = pd.DataFrame(follow_rows)
        print(f"   seguiti: notizia giusta {(f.gross_C > 0).mean():.0%}, lordo medio C {f.gross_C.mean():.1f} (mediano {f.gross_C.median():.1f}), A_k sugli stessi {f.gross_A_k.mean():.1f}")

res = pd.DataFrame(rows)
A0 = summary(add_costs(trades, 0), days)
print(f"\nA senza ritardo, costo 0: {len(trades)} trade, {A0['net_bps']:.2f} bps, {A0['pnl_usd']:,.0f} $, Sharpe {A0['sharpe']:.2f}")
print(res.to_string(index=False))
res.to_csv(OUT / "ritardo.csv", index=False)
print(f"\nsalvato in {OUT.relative_to(RESULTS.parent)}: ritardo.csv e trades_<A|B|C>_<k>min.csv")
