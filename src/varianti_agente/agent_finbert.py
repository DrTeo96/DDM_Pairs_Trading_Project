"""Agente FinBERT per le versioni B e C, finestra legata alla seduta (opzione B). Solo train.

Finestra delle notizie (orari di New York, come i prezzi):
- segnale nel "gap della notte" (minuti 15-29 dall'apertura, come backtest.entry_window): notizie dall'ultima chiusura (16:00 del giorno di borsa prima) al segnale;
- tutti gli altri segnali: notizie della seduta di oggi, dalle 9:30 al segnale.
In ogni caso `ts <= t_signal` (orario di pubblicazione, mai updated_at_ny).

Notizia "mirata": cita una sola delle due aziende della coppia e ha al massimo MAX_SYMBOLS ticker in totale.
Sentiment: FinBERT, score = p_pos - p_neg. Notizia "forte": la classe vincente (positiva o negativa) ha probabilità >= STRONG.

B (può solo bloccare): blocca se c'è almeno una notizia mirata forte, tutte le notizie forti riguardano la stessa azienda e almeno una ha
una parola dell'evento (acquisizione, indagine, dimissioni...) nel titolo o nel sommario. Altrimenti entra.
C (può anche seguire): `segui` se la differenza dei punteggi medi (azienda A meno azienda B, 0 se non ha notizie mirate) ha modulo >= FOLLOW_MIN e lo stesso
segno del movimento relativo dei 30 minuti prima del segnale (ret_A_30m - ret_B_30m). Il trade va nel verso della notizia: punteggio relativo
positivo = long A / short B. Altrimenti decide la regola della B.
Il modello non vede prezzi, direzione del segnale né risultati dei trade. Soglie fissate prima di guardare i risultati.

Uso: uv run python -m src.varianti_agente.agent_finbert   ->   Results/varianti_agente/finbert_seduta/decisioni.csv
"""
import re
import numpy as np
import pandas as pd

from src.config import DEC_FINBERT_SEDUTA, FINBERT_SCORES, NEWS, SIGNALS, TRAIN_END
from src.varianti_agente.comune import giorni_di_borsa

OUT = DEC_FINBERT_SEDUTA
LAST_TRAIN_DAY = pd.Timestamp(TRAIN_END)   # il test (dal 17 settembre) non si legge

MAX_SYMBOLS = 3      # notizia mirata: al massimo 3 ticker
STRONG = 0.8         # probabilità minima della classe vincente per una notizia "forte"
FOLLOW_MIN = 0.5     # modulo minimo del punteggio relativo per seguire la notizia
OPEN_WINDOW = (15, 30)   # come backtest.OPEN_WINDOW: minuti dall'apertura del "gap della notte"

EVENT_RE = re.compile(r"\b(acqui\w*|merg\w*|takeover|buyout|divest\w*|spin-?off|investigat\w*|probe|subpoena\w*|lawsuit|sues|sued|settle\w*|fraud\w*|recall\w*|bankrupt\w*|"
                      r"chapter 11|resign\w*|steps? down|ousted|fired|retire\w*|new (ceo|cfo)|appoint\w*|names? (a )?(new )?(ceo|cfo)|delist\w*|going private)\b", re.I)

signals = pd.read_csv(SIGNALS, parse_dates=["t_signal"])
assert signals.t_signal.max().normalize() <= LAST_TRAIN_DAY, "un segnale cade nel test"
news = pd.read_parquet(NEWS).merge(pd.read_parquet(FINBERT_SCORES), on="id", how="left")
assert news.score.notna().all() and news.ts.max() < LAST_TRAIN_DAY + pd.Timedelta(days=1)
days = giorni_di_borsa()
news["strong"] = news[["p_pos", "p_neg"]].max(axis=1) >= STRONG
news["event"] = (news.headline.fillna("") + " " + news.summary.fillna("")).map(lambda s: bool(EVENT_RE.search(s)))


def window_start(t: pd.Timestamp) -> tuple[pd.Timestamp, str]:
    minute = t.hour * 60 + t.minute - (9 * 60 + 30)
    if OPEN_WINDOW[0] <= minute < OPEN_WINDOW[1]:
        prev = days[days < t.normalize()].max()                       # ultimo giorno di borsa prima di oggi
        return prev + pd.Timedelta(hours=16), "gap della notte (dall'ultima chiusura)"
    return t.normalize() + pd.Timedelta(hours=9, minutes=30), "seduta di oggi (dalle 9:30)"


rows = []
for s in signals.itertuples():
    start, kind = window_start(s.t_signal)
    w = news[(news.ts > start) & (news.ts <= s.t_signal)]
    mA, mB = w[f"mentions_{s.ticker_A}"].astype(bool), w[f"mentions_{s.ticker_B}"].astype(bool)
    targeted = w[(mA ^ mB) & (w.n_symbols <= MAX_SYMBOLS)].assign(side=np.where(mA[(mA ^ mB) & (w.n_symbols <= MAX_SYMBOLS)], "A", "B"))
    strong = targeted[targeted.strong]
    block = bool(len(strong)) and strong.side.nunique() == 1 and bool(strong.event.any())
    sA = targeted.loc[targeted.side == "A", "score"].mean() if (targeted.side == "A").any() else 0.0
    sB = targeted.loc[targeted.side == "B", "score"].mean() if (targeted.side == "B").any() else 0.0
    rel, move = sA - sB, s.ret_A_30m - s.ret_B_30m
    follow = abs(rel) >= FOLLOW_MIN and np.sign(rel) == np.sign(move)
    dec_B = "blocca" if block else "entra"
    follow_side = f"long {s.ticker_A} / short {s.ticker_B}" if rel > 0 else f"short {s.ticker_A} / long {s.ticker_B}"
    rows.append(dict(signal_id=s.signal_id, pair=s.pair, t_signal=s.t_signal, window=kind, window_start=start, n_news=len(w), n_targeted=len(targeted),
                     n_strong=len(strong), score_A=sA, score_B=sB, rel_score=rel, move30_rel=move, decision=dec_B,
                     decision_C="segui" if follow else dec_B, follow_side=follow_side if follow else "",
                     headline=(strong.sort_values("ts").iloc[-1].headline if len(strong) else "")))

out = pd.DataFrame(rows)
OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT, index=False)
print(f"{len(out)} segnali | con notizie nella finestra: {(out.n_news > 0).sum()} | con notizie mirate: {(out.n_targeted > 0).sum()} | con notizie forti: {(out.n_strong > 0).sum()}")
print("B:", out.decision.value_counts().to_dict(), "| C:", out.decision_C.value_counts().to_dict())
print(out.groupby("window")[["n_news", "n_targeted"]].agg(lambda x: (x > 0).mean()).round(2).to_string())
