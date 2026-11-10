"""Agente di notizie: per ogni segnale del train decide `entra` o `blocca` leggendo le notizie uscite prima.

Il modello linguistico gira in locale, dietro un server compatibile con l'API di OpenAI (LM Studio, Ollama, vLLM,
llama.cpp), sullo stesso computer o su un altro. Indirizzo e nome del modello si scrivono in .env (vedi .env.example)
o si passano dal terminale. Dalla cartella del progetto:
    uv run python -m src.agent --signals 12,40,41    prova su pochi segnali: stampa le decisioni, non scrive la tabella
    uv run python -m src.agent                       tutti i segnali del train: crea data/processed/agent_decisions_15pairs_v2_train.csv
In un notebook:
    from src.agent import load_decisions
    B = apply_version(trades, "B", load_decisions())

Come decide (docs/Programma.md, Passaggio 5):
- nessuna notizia nella finestra: `entra`, senza chiamare il modello
- notizia strutturale (acquisizione, indagine, frode, cambio del management) su uno solo dei due titoli: `blocca`
- solo rumore (risultati, commenti di analisti, elenchi) o notizie che riguardano entrambi: `entra`
- risposta non valida, errore o timeout: `blocca`

Ogni risposta del modello è salvata in data/raw/agent/ con orario e nome del modello. Se la risposta a una domanda
c'è già viene riletta, quindi rieseguire non richiama il modello e dà lo stesso risultato.

Il modello può conoscere già gli eventi del periodo se è stato addestrato dopo (lookahead del modello): va scelto
con data di fine addestramento precedente al 1 giugno 2026 e dichiarato nel report.
"""
import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.request

import pandas as pd

from src.backtest import load_trades
from src.config import AGENT_DECISIONS, AGENT_RAW, NEWS_FOR_SIGNALS, TRAIN_END, env

BASE_URL = "http://localhost:1234/v1"   # server locale di LM Studio; Ollama usa http://localhost:11434/v1
WINDOW_H = 24                           # ore di notizie prima del segnale: copre la sera prima per i segnali subito dopo l'apertura
TIMEOUT = 300                           # secondi per chiamata; il primo caricamento del modello in memoria può essere lento
MAX_TOKENS = 400

CATEGORIES = ("strutturale", "rumore")
NEWS_DIRECTIONS = ("positiva", "negativa", "incerta")

SYSTEM = """You assist an intraday pairs-trading strategy on two similar US stocks, A and B.

The strategy has just seen the price gap between A and B move unusually far from its recent average. It wants to bet that the gap closes within about 90 minutes. That bet works when the move is noise. It fails when the move is caused by a real change in one of the two companies, because then the gap has a reason to stay open.

You receive the news published before the signal that mention A or B. Decide whether any of it is a structural fact about only one of the two companies.

- "strutturale": a fact that changes one company and not the other, such as an acquisition, merger or spin-off, an investigation, lawsuit or regulatory action, fraud or an accounting problem, a change of top management.
- "rumore": everything else, such as quarterly results, analyst ratings and price targets, market commentary, lists of many stocks, options activity, and news that affects both companies or the whole sector alike.

Rules:
- Use only the news listed. Do not use anything you may know about what happened after the signal time.
- Each item says how many minutes before the signal it was published and how many tickers it mentions. An item that mentions many tickers is usually a generic list.
- If a structural fact concerns only A or only B, the decision is "blocca". In every other case the decision is "entra".

Answer with one JSON object and nothing else. Classify first, decide last. The fields, in this order:
- "categoria": "strutturale" if at least one item is a structural fact, otherwise "rumore"
- "titolo_coinvolto": the ticker of the one company that fact is about, or "entrambi" if it concerns both, or "nessuno" if no item matters
- "direzione": the effect of that fact on that company's price: "positiva", "negativa" or "incerta"
- "notizia": the id of the item that decided your answer, or null
- "motivo": one sentence, in Italian
- "decisione": "blocca" when categoria is "strutturale" and titolo_coinvolto is a single ticker, "entra" in every other case. No other value is allowed.

Two examples of the format, for a pair with tickers AAA and BBB:
{"categoria": "rumore", "titolo_coinvolto": "nessuno", "direzione": "incerta", "notizia": null, "motivo": "Solo un cambio di target price e un elenco generico di titoli.", "decisione": "entra"}
{"categoria": "strutturale", "titolo_coinvolto": "AAA", "direzione": "negativa", "notizia": 12345, "motivo": "AAA è sotto indagine dell'autorità di vigilanza, BBB non è coinvolta.", "decisione": "blocca"}"""


def response_schema(ticker_a: str, ticker_b: str) -> dict:
    """Formato fisso della risposta, passato al server perché costringa il modello a rispettarlo."""
    return {"type": "json_schema", "json_schema": {"name": "decisione", "strict": True, "schema": {
        "type": "object", "additionalProperties": False,
        "required": ["categoria", "titolo_coinvolto", "direzione", "notizia", "motivo", "decisione"],
        "properties": {
            "categoria": {"type": "string", "enum": list(CATEGORIES)},
            "titolo_coinvolto": {"type": "string", "enum": [ticker_a, ticker_b, "entrambi", "nessuno"]},
            "direzione": {"type": "string", "enum": list(NEWS_DIRECTIONS)},
            "notizia": {"type": ["integer", "null"]},
            "motivo": {"type": "string"},
            "decisione": {"type": "string", "enum": ["entra", "blocca"]},
        }}}}


def call_model(system: str, user: str, schema: dict, model: str, base_url: str) -> dict:
    """L'unica funzione che parla con il modello: una domanda, la risposta grezza del server.
    Per passare a un altro servizio (per esempio un'API a pagamento) si cambia solo questa."""
    body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": schema, "temperature": 0, "seed": 0, "max_tokens": MAX_TOKENS, "stream": False}
    headers = {"Content-Type": "application/json"}
    if env("AGENT_API_KEY"):
        headers["Authorization"] = f"Bearer {env('AGENT_API_KEY')}"
    req = urllib.request.Request(f"{base_url.rstrip('/')}/chat/completions", data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)


def load_inputs(hours: int = WINDOW_H) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Segnali del train e, per ognuno, le notizie che il modello può vedere.

    Il filtro è qui, nel codice, e non nelle istruzioni date al modello: passano solo le notizie pubblicate
    fino all'orario del segnale (news_ts, l'orario di pubblicazione) e non più vecchie di `hours` ore."""
    signals = load_trades()   # rifiuta la tabella se contiene trade dopo TRAIN_END
    if not NEWS_FOR_SIGNALS.exists():
        raise FileNotFoundError(f"manca {NEWS_FOR_SIGNALS.name}: esegui prima src/04_notizie.ipynb")
    news = pd.read_csv(NEWS_FOR_SIGNALS, parse_dates=["t_signal", "news_ts"])
    news = news[news.signal_id.isin(signals.signal_id)]
    news = news[(news.news_ts <= news.t_signal) & (news.news_ts > news.t_signal - pd.Timedelta(hours=hours))]
    assert news.empty or ((news.news_ts <= news.t_signal).all() and news.t_signal.max() < pd.Timestamp(TRAIN_END) + pd.Timedelta(days=1))
    return signals, news.sort_values(["signal_id", "news_ts", "news_id"]).reset_index(drop=True)


def build_prompt(signal, news: pd.DataFrame) -> str:
    """Il testo che il modello legge per un segnale: coppia, orario, direzione e le notizie, dalla più vecchia."""
    lines = [
        f"Pair: {signal.pair} (A = {signal.ticker_A}, B = {signal.ticker_B})",
        f"Signal time (New York): {signal.t_signal:%Y-%m-%d %H:%M}",
        f"Trade the strategy wants to open: {signal.direction}",
        f"Stock that moved most in the last 30 minutes: {signal.leg_piu_mosso}",
        "",
        "News published before the signal, oldest first:",
    ]
    for n in news.itertuples():
        about = " and ".join(t for t, m in ((signal.ticker_A, n.mentions_A), (signal.ticker_B, n.mentions_B)) if m)
        summary = "" if pd.isna(n.summary) or not str(n.summary).strip() else f" | {str(n.summary).strip()}"
        lines.append(f"- id {n.news_id} | {n.minutes_before:.0f} minutes before | mentions {about}, {n.n_symbols} tickers in total | {n.headline}{summary}")
    return "\n".join(lines)


def _cache_file(signal_id: int, model: str, system: str, user: str):
    """Un file per domanda: se cambiano il modello, le istruzioni o le notizie, la domanda è un'altra e non rilegge la vecchia risposta."""
    key = hashlib.sha256(json.dumps([model, system, user]).encode()).hexdigest()[:12]
    return AGENT_RAW / re.sub(r"[^A-Za-z0-9._-]+", "_", model) / f"signal_{int(signal_id):05d}_{key}.json"


def parse_answer(raw: dict, ticker_a: str, ticker_b: str, news_ids: set) -> dict:
    """Controlla la risposta grezza del server. Restituisce i campi validi oppure solleva ValueError con il motivo."""
    text = re.sub(r"<think>.*?</think>", "", raw["choices"][0]["message"]["content"], flags=re.S)   # alcuni modelli scrivono prima il ragionamento
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("nella risposta non c'è un oggetto JSON")
    a = json.loads(text[start:end + 1])
    if a.get("decisione") not in ("entra", "blocca"):
        raise ValueError(f"decisione non valida: {a.get('decisione')!r}")
    if a.get("titolo_coinvolto") not in (ticker_a, ticker_b, "entrambi", "nessuno"):
        raise ValueError(f"titolo coinvolto non valido: {a.get('titolo_coinvolto')!r}")
    if a.get("categoria") not in CATEGORIES:
        raise ValueError(f"categoria non valida: {a.get('categoria')!r}")
    if not isinstance(a.get("motivo"), str) or not a["motivo"].strip():
        raise ValueError("manca il motivo")
    if a.get("notizia") is not None and a["notizia"] not in news_ids:
        raise ValueError(f"cita una notizia che non gli è stata data: {a['notizia']!r}")
    # la decisione deve seguire la regola del Programma: si blocca solo per un fatto strutturale su uno solo dei due titoli
    expected = "blocca" if a["categoria"] == "strutturale" and a["titolo_coinvolto"] in (ticker_a, ticker_b) else "entra"
    if a["decisione"] != expected:
        raise ValueError(f"decisione {a['decisione']!r} incoerente con categoria {a['categoria']!r} e titolo {a['titolo_coinvolto']!r}")
    return a


def decide(signal, news: pd.DataFrame, model: str, base_url: str) -> dict:
    """La decisione per un segnale. `news` sono le sue righe della tabella notizie-segnali, già filtrate da load_inputs."""
    row = dict(signal_id=signal.signal_id, decision="entra", ticker="nessuno", category="nessuna_notizia", reason="", news_direction="",
               news_id=None, n_news=len(news), outcome="nessuna notizia", model="", answered_at="")
    if news.empty:
        row["reason"] = "nessuna notizia nella finestra prima del segnale"
        return row
    user = build_prompt(signal, news)
    f = _cache_file(signal.signal_id, model, SYSTEM, user)
    if f.exists():
        saved = json.loads(f.read_text())
    else:
        try:
            t0 = time.time()
            raw = call_model(SYSTEM, user, response_schema(signal.ticker_A, signal.ticker_B), model, base_url)
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            if isinstance(getattr(e, "reason", None), ConnectionRefusedError):
                raise SystemExit(f"Nessun server risponde a {base_url}: avvia il server del modello (o correggi AGENT_BASE_URL) e riesegui.") from None
            # nessuna risposta da salvare: alla prossima esecuzione la chiamata si ripete
            return row | dict(decision="blocca", category="", outcome="errore", model=model, reason=f"{type(e).__name__}: {e}"[:200])
        saved = dict(signal_id=int(signal.signal_id), model=model, answered_at=pd.Timestamp.now().isoformat(timespec="seconds"),
                     seconds=round(time.time() - t0, 1), system=SYSTEM, user=user, response=raw)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(saved, ensure_ascii=False, indent=1))
    row |= dict(model=saved["model"], answered_at=saved["answered_at"])
    try:
        a = parse_answer(saved["response"], signal.ticker_A, signal.ticker_B, set(news.news_id))
    except (ValueError, KeyError, IndexError, TypeError) as e:
        return row | dict(decision="blocca", category="", outcome="risposta non valida", reason=str(e)[:200])
    return row | dict(decision=a["decisione"], ticker=a["titolo_coinvolto"], category=a["categoria"], reason=a["motivo"].strip(),
                      news_direction=a.get("direzione") if a.get("direzione") in NEWS_DIRECTIONS else "", news_id=a.get("notizia"), outcome="risposta valida")


def run(model: str, base_url: str = BASE_URL, hours: int = WINDOW_H, signal_ids: list[int] | None = None) -> pd.DataFrame:
    """Una riga per segnale con la decisione. `signal_ids` limita il lavoro ad alcuni segnali (prova)."""
    signals, news = load_inputs(hours)
    if signal_ids is not None:
        signals = signals[signals.signal_id.isin(signal_ids)]
    by_signal = dict(tuple(news.groupby("signal_id")))
    empty = news.iloc[0:0]
    rows = []
    for i, s in enumerate(signals.itertuples(), 1):
        rows.append(decide(s, by_signal.get(s.signal_id, empty), model, base_url))
        if rows[-1]["outcome"] != "nessuna notizia":
            why = "" if rows[-1]["outcome"] == "risposta valida" else f": {rows[-1]['reason']}"
            print(f"[{i}/{len(signals)}] segnale {s.signal_id} {s.pair} {s.t_signal:%Y-%m-%d %H:%M}: {rows[-1]['decision']} ({rows[-1]['outcome']}{why})", flush=True)
    return pd.DataFrame(rows)


def load_decisions() -> pd.DataFrame:
    """La tabella delle decisioni, nel formato che `backtest.apply_version(trades, "B", decisions)` legge così com'è."""
    if not AGENT_DECISIONS.exists():
        raise FileNotFoundError(f"manca {AGENT_DECISIONS.name}: dalla cartella del progetto esegui `uv run python -m src.agent`")
    return pd.read_csv(AGENT_DECISIONS)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", default=env("AGENT_MODEL"), help="nome del modello sul server (default: AGENT_MODEL in .env)")
    ap.add_argument("--base-url", default=env("AGENT_BASE_URL", BASE_URL), help=f"indirizzo del server (default: AGENT_BASE_URL in .env, altrimenti {BASE_URL})")
    ap.add_argument("--hours", type=int, default=WINDOW_H, help="ore di notizie prima del segnale")
    ap.add_argument("--signals", help="solo questi signal_id, separati da virgola: prova, non scrive la tabella")
    a = ap.parse_args()
    if not a.model:
        raise SystemExit("Manca il nome del modello: scrivi AGENT_MODEL in .env oppure usa --model")
    ids = [int(x) for x in a.signals.split(",")] if a.signals else None
    out = run(a.model, a.base_url, a.hours, ids)
    print(f"\n{len(out)} segnali: " + ", ".join(f"{k} {v}" for k, v in out.decision.value_counts().items()) + " | " + ", ".join(f"{k} {v}" for k, v in out.outcome.value_counts().items()))
    if ids is not None:
        print(out[["signal_id", "decision", "ticker", "category", "news_direction", "n_news", "outcome", "reason"]].to_string(index=False))
    else:
        out.to_csv(AGENT_DECISIONS, index=False)
        print(f"salvato data/processed/{AGENT_DECISIONS.name}")
        n_err = int((out.outcome == "errore").sum())
        if n_err:
            print(f"ATTENZIONE: {n_err} chiamate senza risposta, bloccate per regola. Riesegui lo stesso comando: ripete solo quelle, le risposte già arrivate si rileggono.")
