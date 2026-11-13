"""Varianti 14 (B) e 15 (C): FinBERT con la finestra dell'episodio, cioè le notizie uscite mentre lo spread si allontanava dalla media,
fino alla fine della barra del segnale. Regole in registro_varianti.md.

1. Per ogni segnale: inizio dell'episodio = prima barra di fila, andando indietro dal segnale, con z oltre EPISODE_Z dello stesso segno,
   meno EPISODE_BUFFER minuti; se l'episodio arriva alla prima barra della giornata, dalla chiusura del giorno di borsa prima.
   Fine = t_signal + 1 minuto (la decisione è alla chiusura della barra del segnale).
2. Decisioni con le regole delle varianti 9 e 10 (solo la finestra cambia).
3. Backtest (A, B, C a costo 0 e 5) e valutazione come al punto 4.

Scrive in Results/varianti_agente/finbert_episodio/: decisioni.csv, episodio.csv.
Uso: uv run python -m src.varianti_agente.episodio
"""
import re
from math import comb

import numpy as np
import pandas as pd
from src.backtest import _z_for, add_costs, apply_version, blocked_vs_random, entry_window, load_trades, summary, trading_days
from src.config import DEC_FINBERT_EPISODIO, FINBERT_SCORES, NEWS, RESULTS, read_parquet
from src.varianti_agente.comune import giorni_di_borsa

OUT = DEC_FINBERT_EPISODIO.parent
EPISODE_Z = 1.0
EPISODE_BUFFER = pd.Timedelta(minutes=5)
DECISION_LAG = pd.Timedelta(minutes=1)
MAX_SYMBOLS, STRONG, FOLLOW_MIN = 3, 0.8, 0.5
EVENT_RE = re.compile(r"\b(acqui\w*|merg\w*|takeover|buyout|divest\w*|spin-?off|investigat\w*|probe|subpoena\w*|lawsuit|sues|sued|settle\w*|fraud\w*|recall\w*|bankrupt\w*|"
                      r"chapter 11|resign\w*|steps? down|ousted|fired|retire\w*|new (ceo|cfo)|appoint\w*|names? (a )?(new )?(ceo|cfo)|delist\w*|going private)\b", re.I)

pd.options.display.float_format = "{:,.2f}".format
pd.options.display.width = 250
pd.options.display.max_colwidth = 110
trades, days = load_trades(), trading_days()
A = apply_version(trades, "A")
A["finestra"] = entry_window(A)
tdays = giorni_di_borsa()

# ---------------------------------------------------------------- 1. inizio dell'episodio

cache, starts, kinds, lens = {}, [], [], []
for t in trades.itertuples():
    d, z = _z_for(t.pair, t.hl_min, t.ema, cache)
    i = d.ts.get_loc(t.t_signal)
    assert np.isclose(z[i], t.z_signal), f"segnale {t.signal_id}: z diverso da 03_segnali"
    side, j, first = np.sign(z[i]), i, d.day_start[i]
    while j - 1 >= first and side * z[j - 1] > EPISODE_Z:
        j -= 1
    if j == first and side * z[j] > EPISODE_Z:
        start, kind = tdays[tdays < t.t_signal.normalize()].max() + pd.Timedelta(hours=16), "dalla notte"
    else:
        start, kind = d.ts[j] - EPISODE_BUFFER, "in seduta"
    starts.append(start)
    kinds.append(kind)
    lens.append((t.t_signal + DECISION_LAG - start).total_seconds() / 60)
ep = trades[["signal_id", "pair", "ticker_A", "ticker_B", "t_signal", "ret_A_30m", "ret_B_30m"]].assign(ep_start=starts, ep_kind=kinds, ep_minutes=lens)
print("episodi:", ep.ep_kind.value_counts().to_dict(), "| durata in seduta (minuti): mediana", ep.loc[ep.ep_kind == "in seduta", "ep_minutes"].median())

# ---------------------------------------------------------------- 2. decisioni con le regole delle varianti 9 e 10

news = read_parquet(NEWS).merge(pd.read_parquet(FINBERT_SCORES), on="id")
news["strong"] = news[["p_pos", "p_neg"]].max(axis=1) >= STRONG
news["event"] = (news.headline.fillna("") + " " + news.summary.fillna("")).map(lambda s: bool(EVENT_RE.search(s)))
rows = []
for s in ep.itertuples():
    w = news[(news.ts >= s.ep_start) & (news.ts < s.t_signal + DECISION_LAG) & (news.n_symbols <= MAX_SYMBOLS)]
    mA, mB = w[f"mentions_{s.ticker_A}"].astype(bool), w[f"mentions_{s.ticker_B}"].astype(bool)
    keep = mA ^ mB
    tg = w[keep].assign(side=np.where(mA[keep], "A", "B"))
    st = tg[tg.strong]
    block = bool(len(st)) and st.side.nunique() == 1 and bool(st.event.any())
    sA = tg.loc[tg.side == "A", "score"].mean() if (tg.side == "A").any() else 0.0
    sB = tg.loc[tg.side == "B", "score"].mean() if (tg.side == "B").any() else 0.0
    rel, move = sA - sB, s.ret_A_30m - s.ret_B_30m
    follow = abs(rel) >= FOLLOW_MIN and np.sign(rel) == np.sign(move)
    dec = "blocca" if block else "entra"
    rows.append(dict(signal_id=s.signal_id, pair=s.pair, t_signal=s.t_signal, ep_kind=s.ep_kind, ep_start=s.ep_start, n_targeted=len(tg), n_strong=len(st),
                     n_in_signal_bar=int(((tg.ts >= s.t_signal) & (tg.ts < s.t_signal + DECISION_LAG)).sum()),
                     rel_score=rel, decision=dec, decision_C="segui" if follow else dec,
                     follow_side=(f"long {s.ticker_A} / short {s.ticker_B}" if rel > 0 else f"short {s.ticker_A} / long {s.ticker_B}") if follow else "",
                     headlines=" | ".join(tg.headline.astype(str))))
dec = pd.DataFrame(rows)
OUT.mkdir(parents=True, exist_ok=True)
dec.to_csv(DEC_FINBERT_EPISODIO, index=False)
print(f"segnali con almeno una notizia mirata nell'episodio: {(dec.n_targeted > 0).sum()} (dalla notte {((dec.n_targeted > 0) & (dec.ep_kind == 'dalla notte')).sum()}, "
      f"in seduta {((dec.n_targeted > 0) & (dec.ep_kind == 'in seduta')).sum()}) | con notizia nella barra del segnale: {(dec.n_in_signal_bar > 0).sum()}")
print("B:", dec.decision.value_counts().to_dict(), "| C:", dec.decision_C.value_counts().to_dict())

# ---------------------------------------------------------------- 3. backtest e valutazione

B = apply_version(trades, "B", dec[["signal_id", "decision"]])
C = apply_version(trades, "C", dec[["signal_id", "decision_C", "follow_side"]])
res = []
for name, t in (("A senza agente", A), ("14 B FinBERT episodio", B), ("15 C FinBERT episodio", C)):
    for c in (0, 5):
        sm = summary(add_costs(t, c), days)
        res.append({"versione": name, "costo": c, "trade": sm["trade"], "net_bps": sm["net_bps"], "pnl_usd": sm["pnl_usd"], "sharpe": sm["sharpe"]})
res = pd.DataFrame(res)
print("\n" + res.to_string(index=False))

A["rientro"] = A.exit_reason.eq("rientro")
blk, kept = A[A.signal_id.isin(dec.query("decision == 'blocca'").signal_id)], A[~A.signal_id.isin(dec.query("decision == 'blocca'").signal_id)]


def fisher_two_sided(a, b, c, d):
    r1, c1, n = a + b, a + c, a + b + c + d
    p = lambda x: comb(c1, x) * comb(n - c1, r1 - x) / comb(n, r1)   # noqa: E731
    return min(1.0, sum(p(x) for x in range(max(0, r1 + c1 - n), min(r1, c1) + 1) if p(x) <= p(a) * (1 + 1e-9)))


if len(blk):
    print(f"\n14 B: bloccati {len(blk)}, rientro {blk.rientro.mean():.0%} contro {kept.rientro.mean():.0%} dei tenuti "
          f"(p Fisher {fisher_two_sided(int(blk.rientro.sum()), len(blk) - int(blk.rientro.sum()), int(kept.rientro.sum()), len(kept) - int(kept.rientro.sum())):.2f}); "
          f"lordo medio {blk.gross_bps.mean():.1f}, mediano {blk.gross_bps.median():.1f}; p blocco a caso {blocked_vs_random(trades, dec[['signal_id', 'decision']])['p_value']:.2f}")
    print(blk.merge(dec[["signal_id", "ep_kind", "headlines"]], on="signal_id")[["signal_id", "pair", "t_signal", "ep_kind", "exit_reason", "gross_bps", "headlines"]].to_string(index=False))
f = C[C.c_kind == "segui"].merge(A[["signal_id", "gross_bps"]].rename(columns={"gross_bps": "gross_A"}), on="signal_id")
if len(f):
    print(f"\n15 C: {len(f)} trade invertiti, notizia giusta {(f.gross_bps > 0).mean():.0%}, lordo medio C {f.gross_bps.mean():.1f} (mediano {f.gross_bps.median():.1f}), A sugli stessi {f.gross_A.mean():.1f}")
res.to_csv(OUT / "episodio.csv", index=False)
print(f"\nsalvato in {OUT.relative_to(RESULTS.parent)}: decisioni.csv, episodio.csv")
