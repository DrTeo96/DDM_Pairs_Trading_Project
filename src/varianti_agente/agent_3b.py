"""Agente di notizie, versione B (può solo bloccare), per le 15 coppie della versione 2. Passaggio 5 del programma.

Per ogni segnale Python cerca le notizie dei due titoli uscite PRIMA del segnale, in una finestra di ore; un LLM locale (Llama 3.2 3B di default, via Ollama)
le classifica compilando solo i fatti (categoria, titolo coinvolto, se la notizia spiega l'allargamento, permanenza...); la decisione la calcola il codice
con una tabella fissa e, per ogni blocco, un controllo a parole chiave sul testo. Il modello non vede prezzi, rendimenti né risultati dei trade.
Prima serve Ollama acceso con il modello scaricato (`ollama pull llama3.2:3b`). Non servono librerie nuove: le richieste usano la libreria standard.
Dal terminale, nella cartella del progetto:
    uv run python -m src.varianti_agente.agent_3b --dry-run --limit 5      stampa i prompt di 5 segnali senza chiamare il modello
    uv run python -m src.varianti_agente.agent_3b --limit 20               chiama il modello su 20 segnali (prova)
    uv run python -m src.varianti_agente.agent_3b                          tutti i 973 segnali del train, finestra di 6 ore, prompt completo
    uv run python -m src.varianti_agente.agent_3b --hours 24               controllo di robustezza con 24 ore
    uv run python -m src.varianti_agente.agent_3b --prompt semplice        il primo prompt (categorie semplici), per il confronto
    uv run python -m src.varianti_agente.agent_3b --model llama3.1:8b      un altro modello (file di risposte separato)
Le risposte si salvano una alla volta: con le impostazioni di default (6 ore, llama3.2:3b, prompt completo) in
Results/varianti_agente/3b_6h/decisioni.csv (DEC_3B_6H in config.py), con le altre in data/processed/agent_decisions_v2_<ore>h_<modello>_<prompt>.csv.
Se si interrompe, rilanciando riparte da dove era arrivato.
Il file ha le colonne signal_id e decision ('entra' o 'blocca'), quelle che si aspetta backtest.apply_version("B", ...).

Regole (Programma, Passaggio 5):
- nessuna notizia nella finestra: 'entra', senza chiamare il modello;
- si blocca solo con una notizia strutturale che spiega l'allargamento dello spread (tabella in decide_completo); 'enter_reduced' è salvato in decision_full ma nella versione B vale 'entra';
- ogni blocco richiede anche una parola dell'evento nel testo della notizia: se manca, il blocco cade;
- se il modello o la risposta falliscono: 'blocca' (regola di sicurezza), con l'errore scritto nella colonna `error`;
- l'agente non cambia direzione, soglie, dimensione o uscita.
"""
import argparse
import json
import re
import time
import urllib.error
import urllib.request

import pandas as pd

from src.config import DEC_3B_6H, NEWS_SET, PROCESSED, SIGNALS
from src.news import load_news

NEWS_PAIR = NEWS_SET

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:3b"           # il Llama 3.1 8B (4,9 GB) non sta nei 8 GB del Mac: va in swap e impiega minuti per segnale. Altro modello: --model
PROMPT = "completo"
WINDOW_HOURS = 6              # decisione del gruppo: 6 ore, con 24 ore come controllo di robustezza dichiarato in anticipo
GENERIC_MIN_TICKERS = 6       # decisione del gruppo: una notizia con 6 ticker o più è "generica" (liste di titoli); resta visibile, con il flag
MAX_HEADLINES = 15            # tetto di notizie nel prompt (le più recenti), per non superare il contesto del modello
MAX_SUMMARY = 300             # caratteri del sommario di ogni notizia
MAX_PROMPT_CHARS = 4500       # tetto del messaggio dell'utente (circa 1300 token): con le istruzioni e la risposta sta nei 4096 token del contesto
NUM_CTX = 4096
LAST_TRAIN_DAY = pd.Timestamp("2026-09-16 23:59:59")   # il test (dal 17 settembre) non si legge
TIMEOUT = 180                 # secondi per una risposta (la prima chiamata carica il modello in memoria)
RETRIES = 2

# campi del segnale che l'agente può vedere. Le altre colonne (uscita, prezzi di uscita, rendimenti a 30 minuti, guadagno) sono il futuro: mai nel prompt
SIGNAL_FIELDS = ["signal_id", "pair", "ticker_A", "ticker_B", "t_signal", "direction", "leg_piu_mosso", "z_signal"]

# il modello è stato addestrato prima del 2024: gli diamo i nomi, perché ticker come XYZ (Block) non li conoscerebbe
NAMES = {
    "MA": "Mastercard", "V": "Visa", "CSX": "CSX Corp", "UNP": "Union Pacific", "PYPL": "PayPal", "XYZ": "Block Inc (ex Square)",
    "HD": "Home Depot", "LOW": "Lowe's", "DHR": "Danaher", "TMO": "Thermo Fisher Scientific", "CRM": "Salesforce", "WDAY": "Workday",
    "JPM": "JPMorgan Chase", "WFC": "Wells Fargo", "NXPI": "NXP Semiconductors", "TXN": "Texas Instruments", "ELV": "Elevance Health",
    "UNH": "UnitedHealth Group", "CL": "Colgate-Palmolive", "PG": "Procter & Gamble", "GS": "Goldman Sachs", "MS": "Morgan Stanley",
    "ISRG": "Intuitive Surgical", "SYK": "Stryker", "KO": "Coca-Cola", "PEP": "PepsiCo", "BAC": "Bank of America", "C": "Citigroup",
    "COP": "ConocoPhillips", "EOG": "EOG Resources",
}

# colonne del file delle decisioni: se un file esistente ne ha altre (versione precedente del codice) si rifiuta di aggiungere righe
COLUMNS = ["signal_id", "pair", "t_signal", "window_hours", "model", "prompt", "n_news", "news_ids", "decision", "decision_full", "category", "affected_ticker",
           "explains_divergence", "permanence", "confidence", "flags", "relevant_news_id", "keyword_ok", "evidence", "evidence_ok", "reason", "error"]

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------
# Prompt semplice: categorie semplici (structural_one, both, noise, none). Si blocca con structural_one. Tenuto per il confronto (--prompt semplice).
CATEGORIES_SEMPLICE = ["structural_one", "both", "noise", "none"]
SYSTEM_SEMPLICE = """You are a careful financial news analyst helping a pairs-trading strategy.
A pairs trade bets that the price gap between two similar companies will close. It fails when a real, company-specific event changes the value of ONE of the two companies for good.
You get a trade signal and the headlines about the two companies published before it. Classify them. Do not predict prices and do not use knowledge about events after the headlines.

Categories:
- structural_one: at least one headline reports a concrete event about ONLY ONE of the two companies that can change its value lastingly: acquisition or merger, divestiture, \
investigation, lawsuit, fraud or regulatory action, change of CEO/CFO or top management, large contract won or lost, bankruptcy or financing problems, major product failure or recall.
- both: the relevant news concerns both companies or their whole sector (macro news, sector regulation, an event hitting both).
- noise: only analyst rating or price-target changes, earnings previews or results commentary, generic market commentary, lists of many stocks, partnerships, collaborations, \
integrations, product launches or product availability, conference appearances, dividend or buyback announcements.
- none: nothing in the headlines is about these two companies in a meaningful way.
Choose structural_one only if a headline EXPLICITLY states such an event. Never infer an acquisition, investigation or management change that the headline does not state. \
If a headline is about a third company (for example a company that is selling a business, or a competitor) and not about one of the two, it is not structural for them.

Reply only with JSON: category, company (the ticker involved if structural_one, otherwise "none"), evidence (the exact headline that supports your category, copied word for word, \
or "none"), reason (one short sentence in Italian)."""

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------
# Prompt completo: adattato da un prompt proposto dal gruppo. Il modello compila solo i fatti; la tabella delle decisioni sta nel codice (decide_completo).
CATEGORIES_COMPLETO = ["no_news", "noise", "common_factor", "company_temporary", "structural", "earnings", "uncertain"]
FLAGS = ["headline_only", "generic_only", "earnings_today", "rumor", "stale_news", "conflicting_news", "guidance_change"]
SYSTEM_COMPLETO = """ROLE
You are an analyst inside the backtest of an intraday pairs-trading strategy on US stocks. You give no investment advice: you classify news and return a fixed-format JSON, which the code will use. \
Reply only with one valid JSON object.

STRATEGY CONTEXT
- The pair has two companies with comparable business, A and B, historically linked. The distance between their prices (the "spread") tends to return to a normal level.
- A model found that the spread is unusually wide now and proposes a trade on its return. Field "direction":
  - short_a_long_b: A is "expensive" relative to B (A rose more than B, or B fell more than A). We sell A and buy B.
  - long_a_short_b: A is "cheap" relative to B. We buy A and sell B.
- The trade wins if the spread returns within a few hours. It loses if the widening lasts.
- Your job: understand, only from the news provided, whether the widening is TEMPORARY (noise, overreaction, market flows, news touching both companies) or due to a STRUCTURAL fact, \
something that lastingly changes the value of one company relative to the other.
- Block only when there is a specific reason written in the news you were given.

INPUT
A JSON with signal_id, ticker_a, name_a, ticker_b, name_b, direction, z (how abnormal the spread is), signal_bar_close, decision_time (New York time) and news: a list of news published before \
decision_time. Each news has index, time, minutes_before, headline, summary (may be empty), source, symbols (tickers tagged), generic (true if it tags many tickers, typically a list of moving stocks).

TIME RULES
- Reason as if it were decision_time. Use nothing you know about how prices or events went afterwards. If you recognise an event, ignore what you know about its sequel and use only the news provided.
- You do not know whether the news caused the move or came after it. Judge whether it plausibly explains the direction and size of the widening.

PROCEDURE (in order)
1. Relevance: does each news really concern A or B? Ignore "generic" news unless the headline substantially concerns one of the two. Ignore news about other companies, \
unless they clearly affect one of the two (for example a competitor buying it). A company that merely appears in the tags is not necessarily the subject.
2. Type: assign a category from the list below.
3. Direction: does the news explain why the spread widened in that direction?
   - With short_a_long_b, positive news on A or negative news on B explain it.
   - With long_a_short_b, negative news on A or positive news on B explain it.
   - News of the opposite sign does not explain it.
4. Permanence: is the effect on the company's value temporary or permanent?

CATEGORIES (news_category)
- no_news: no relevant news in the data provided.
- noise: analyst comments (rating or price-target changes), technical analysis, lists of moving stocks, options flow, routine events (usual dividend, conferences), partnerships, \
collaborations, integrations, product launches, generic sector news.
- common_factor: news hitting both companies similarly (commodity prices, rates, sector-wide regulation, macro data).
- company_temporary: news specific to one company that may explain the move but with a probably temporary effect (minor product, executive comment, small lawsuit, old news repeated).
- structural: acquisition or merger (announced, in talks or rejected), bankruptcy or restructuring, fraud, investigations or actions by authorities, CEO or CFO leaving or arriving, \
withdrawal of a main product, loss or win of a major customer or contract, spin-off or sale of a business, capital raise, dividend cut, debt downgrade, outcome of a major lawsuit, \
approval or rejection by an authority, inclusion or exclusion from a major index.
- earnings: quarterly results or guidance of one of the two companies published that day. If the headline explicitly says guidance was cut or raised strongly, add the flag guidance_change.
- uncertain: contradictory news, unconfirmed rumours, headlines too vague to judge. Add the flag rumor if it is an unconfirmed rumour.
Flags: headline_only (summary empty), generic_only, earnings_today, rumor, stale_news, conflicting_news, guidance_change.

LIMITS
- Use only the news provided. Do not invent facts, numbers or dates. Choose structural only if a headline EXPLICITLY states the event; never infer it.
- No news in the data does not prove none was published: say "no news in the data provided", never "no news in the market".
- If the data is not enough, choose uncertain; do not guess.

OUTPUT (these keys only)
news_category, relevant_news_index (index of the news that weighs most, or -1), affected_ticker ("A", "B", "both" or "none"), explains_divergence ("yes", "partly", "no" or "unknown"), \
permanence ("temporary", "permanent" or "unclear"), confidence ("low", "medium" or "high"), flags (list), evidence (the exact headline that weighs most, copied word for word, or "none"), \
reason (one sentence in Italian, max 30 words).

EXAMPLES (invented, only to show the format and the reasoning). The fields evidence and reason in the examples are placeholders: \
never copy text from the examples; evidence and reason must always come from the news you were given.
1) direction short_a_long_b, A=MA, B=V, news 0: "Illinois Rep. Sold Up to $50K Worth of Microsoft Stock" (symbols MSFT, V) ->
{"news_category":"no_news","relevant_news_index":-1,"affected_ticker":"none","explains_divergence":"unknown","permanence":"unclear","confidence":"medium","flags":[],"evidence":"<exact headline of the news you were given, or none>","reason":"<one sentence in Italian about the news you were given>"}
2) direction short_a_long_b, A=HD, B=LOW, news 0: "Analyst Raises Price Target On Home Depot" ->
{"news_category":"noise","relevant_news_index":0,"affected_ticker":"A","explains_divergence":"partly","permanence":"temporary","confidence":"medium","flags":[],"evidence":"<exact headline of the news you were given, or none>","reason":"<one sentence in Italian about the news you were given>"}
3) direction long_a_short_b, A=CRM, B=WDAY, news 0: "Workday Agrees To Be Acquired By A Private Equity Group For $40 Billion" ->
{"news_category":"structural","relevant_news_index":0,"affected_ticker":"B","explains_divergence":"yes","permanence":"permanent","confidence":"high","flags":[],"evidence":"<exact headline of the news you were given, or none>","reason":"<one sentence in Italian about the news you were given>"}
4) direction long_a_short_b, A=COP, B=EOG, news 0: "Oil Prices Jump 4% On Supply Fears" ->
{"news_category":"common_factor","relevant_news_index":0,"affected_ticker":"both","explains_divergence":"no","permanence":"temporary","confidence":"medium","flags":[],"evidence":"<exact headline of the news you were given, or none>","reason":"<one sentence in Italian about the news you were given>"}
5) direction short_a_long_b, A=ELV, B=UNH, news 0: "UnitedHealth Reports Q3 Results, Cuts Full-Year Guidance" ->
{"news_category":"earnings","relevant_news_index":0,"affected_ticker":"B","explains_divergence":"yes","permanence":"permanent","confidence":"high","flags":["earnings_today","guidance_change"],"evidence":"<exact headline of the news you were given, or none>","reason":"<one sentence in Italian about the news you were given>"}
6) direction short_a_long_b, A=PYPL, B=XYZ, news 0: "Block Partners With A Fintech To Launch A New Payments Tool" ->
{"news_category":"noise","relevant_news_index":0,"affected_ticker":"B","explains_divergence":"partly","permanence":"temporary","confidence":"medium","flags":[],"evidence":"<exact headline of the news you were given, or none>","reason":"<one sentence in Italian about the news you were given>"}"""

# parole che devono comparire nel testo di una notizia perché un blocco resti (controllo deterministico sopra il giudizio del modello)
EVENT_RE = re.compile(r"\b(acqui\w*|merg\w*|takeover|buyout|divest\w*|spin-?off|investigat\w*|probe|subpoena\w*|lawsuit|sues|sued|settle\w*|fraud\w*|recall\w*|bankrupt\w*|"
                      r"chapter 11|resign\w*|steps? down|ousted|fired|retire\w*|new (ceo|cfo)|appoint\w*|names? (a )?(new )?(ceo|cfo)|delist\w*|going private)\b", re.I)
_UP_DOWN = r"(cut|cuts|lower\w*|slash\w*|rais\w*|boost\w*|hike\w*|increas\w*|reduc\w*|withdr\w*|suspend\w*)"
GUIDANCE_RE = re.compile(rf"\b(guidance|outlook|forecast)\b.*\b{_UP_DOWN}\b|\b{_UP_DOWN}\b.*\b(guidance|outlook|forecast)\b", re.I | re.S)


def company(t: str) -> str:
    return f"{NAMES[t]} ({t})"


def select_news(sig: pd.Series, news: pd.DataFrame, hours: float) -> pd.DataFrame:
    """Notizie dei due titoli pubblicate nella finestra che TERMINA all'orario del segnale: ts <= t_signal e ts > t_signal - ore.
    Si usa `ts` (created_at), mai updated_at_ny, che può essere molto successivo (lookahead). Al massimo MAX_HEADLINES, le più recenti."""
    t = pd.Timestamp(sig["t_signal"])
    if t > LAST_TRAIN_DAY:
        raise ValueError(f"segnale {sig['signal_id']} dopo il 16 settembre: il test non si usa")
    m = news[f"mentions_{sig['ticker_A']}"] | news[f"mentions_{sig['ticker_B']}"]
    w = news[m & (news.ts <= t) & (news.ts > t - pd.Timedelta(hours=hours))]
    return w.sort_values("ts").tail(MAX_HEADLINES)


def build_prompt_semplice(sig: pd.Series, window: pd.DataFrame) -> str:
    a, b, mover = sig["ticker_A"], sig["ticker_B"], sig["leg_piu_mosso"]
    lines = [
        f"Pair: {company(a)} and {company(b)}.",
        f"Signal time (New York): {sig['t_signal']}. The spread widened mainly because {company(mover)} moved. Planned trade: {sig['direction']}.",
        "",
        f"News published in the hours before the signal, {len(window)} in total (oldest first):",
    ]
    for _, r in window.iterrows():
        about = "+".join(t for t in (a, b) if r[f"mentions_{t}"])
        summ = (r["summary"] or "")[:MAX_SUMMARY].replace("\n", " ")
        lines.append(f"- [{r['ts']:%Y-%m-%d %H:%M}] [about: {about}; tickers tagged: {r['n_symbols']}] {r['headline']}" + (f" | {summ}" if summ else ""))
    return "\n".join(lines)


def direction_ab(sig: pd.Series) -> str:
    """'long COP / short EOG' -> long_a_short_b (A è il primo titolo della coppia)."""
    return "long_a_short_b" if str(sig["direction"]).startswith(f"long {sig['ticker_A']}") else "short_a_long_b"


def build_prompt_completo(sig: pd.Series, window: pd.DataFrame) -> str:
    """Input in JSON. decision_time = signal_bar_close = t_signal: nessuna notizia dopo il segnale."""
    t = pd.Timestamp(sig["t_signal"])
    items = []
    for i, (_, r) in enumerate(window.iterrows()):
        items.append({"index": i, "time": f"{r['ts']:%Y-%m-%d %H:%M}", "minutes_before": int((t - r["ts"]).total_seconds() // 60), "headline": r["headline"],
                      "summary": (r["summary"] or "")[:MAX_SUMMARY].replace("\n", " "), "source": r["source"], "symbols": r["symbols"],
                      "generic": bool(r["n_symbols"] >= GENERIC_MIN_TICKERS)})
    a, b = sig["ticker_A"], sig["ticker_B"]
    return json.dumps({"signal_id": int(sig["signal_id"]), "ticker_a": a, "name_a": NAMES[a], "ticker_b": b, "name_b": NAMES[b], "direction": direction_ab(sig),
                       "z": round(float(sig["z_signal"]), 2), "signal_bar_close": f"{t:%Y-%m-%d %H:%M}", "decision_time": f"{t:%Y-%m-%d %H:%M}", "news": items}, ensure_ascii=False)


def schema_semplice(a: str, b: str) -> dict:
    return {"type": "object", "required": ["category", "company", "evidence", "reason"], "additionalProperties": False,
            "properties": {"category": {"type": "string", "enum": CATEGORIES_SEMPLICE}, "company": {"type": "string", "enum": [a, b, "none"]}, "evidence": {"type": "string"}, "reason": {"type": "string"}}}


def schema_completo() -> dict:
    s = lambda *vals: {"type": "string", "enum": list(vals)}   # noqa: E731
    props = {"news_category": s(*CATEGORIES_COMPLETO), "relevant_news_index": {"type": "integer"}, "affected_ticker": s("A", "B", "both", "none"),
             "explains_divergence": s("yes", "partly", "no", "unknown"), "permanence": s("temporary", "permanent", "unclear"), "confidence": s("low", "medium", "high"),
             "flags": {"type": "array", "items": s(*FLAGS)}, "evidence": {"type": "string"}, "reason": {"type": "string"}}
    return {"type": "object", "required": list(props), "additionalProperties": False, "properties": props}


def chat(model: str, system: str, user: str, fmt: dict) -> dict:
    """Una chiamata a Ollama, con risposta in JSON vincolata allo schema, temperatura 0 e seed fisso (risposte ripetibili)."""
    body = {"model": model, "stream": False, "keep_alive": "30m", "format": fmt,
            "options": {"temperature": 0, "seed": 0, "num_ctx": NUM_CTX},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(OLLAMA_URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    last = None
    for k in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(json.loads(r.read())["message"]["content"])
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as e:
            last = e
            time.sleep(2 * (k + 1))
    raise RuntimeError(str(last))


def decide_semplice(category: str) -> str:
    """Prompt semplice: si blocca solo con una notizia strutturale su un solo titolo."""
    return "blocca" if category == "structural_one" else "entra"


def decide_completo(out: dict, window: pd.DataFrame) -> tuple[str, object]:
    """Tabella delle decisioni (decisione del gruppo). Ritorna (decision_full, keyword_ok): decision_full è enter, enter_reduced o block;
    keyword_ok è None se non c'è un blocco da controllare, altrimenti True/False. Un blocco senza parole dell'evento nel testo cade."""
    cat, flags = out["news_category"], set(out["flags"])
    explains = out["explains_divergence"] in ("yes", "partly")
    i = out["relevant_news_index"]
    rel = window.iloc[[i]] if 0 <= i < len(window) else window                    # se l'indice non è valido si controlla tutta la finestra
    text = " ".join(rel["headline"] + " " + rel["summary"].fillna(""))
    if cat in ("no_news", "noise", "common_factor"):
        return "enter", None
    if cat == "company_temporary":
        return ("enter_reduced" if explains else "enter"), None
    if cat == "structural":
        full, regex = ("block" if explains else "enter_reduced"), EVENT_RE
    elif cat == "earnings":
        full, regex = ("block" if "guidance_change" in flags else "enter_reduced"), GUIDANCE_RE
    else:                                                                          # uncertain: si blocca solo una voce su acquisizione, indagine o fallimento
        full, regex = ("block" if "rumor" in flags else "enter_reduced"), EVENT_RE
    if full != "block":
        return full, None
    ok = bool(regex.search(text))
    return ("block" if ok else "enter"), ok


def run_signal(sig: pd.Series, news: pd.DataFrame, hours: float, dry_run: bool = False, model: str = MODEL, prompt_version: str = PROMPT) -> dict:
    window = select_news(sig, news, hours)
    rec = {c: "" for c in COLUMNS}
    rec.update(signal_id=sig["signal_id"], pair=sig["pair"], t_signal=sig["t_signal"], window_hours=hours, model=model, prompt=prompt_version, n_news=len(window),
              news_ids=",".join(str(i) for i in window["id"]), decision="entra", decision_full="enter", category="no_news", evidence_ok=True)
    if window.empty:
        return rec
    build = build_prompt_completo if prompt_version == "completo" else build_prompt_semplice
    prompt = build(sig, window)
    while len(prompt) > MAX_PROMPT_CHARS and len(window) > 1:     # si scartano le notizie più vecchie, mai le istruzioni
        window = window.iloc[1:]
        prompt = build(sig, window)
    rec.update(n_news=len(window), news_ids=",".join(str(i) for i in window["id"]))
    if dry_run:
        print(f"\n===== segnale {sig['signal_id']} =====\n{prompt}")
        rec["category"] = "dry_run"
        return rec
    a, b = sig["ticker_A"], sig["ticker_B"]
    try:
        if prompt_version == "semplice":
            out = chat(model, SYSTEM_SEMPLICE, prompt, schema_semplice(a, b))
            if out["category"] not in CATEGORIES_SEMPLICE:
                raise RuntimeError(f"categoria sconosciuta: {out['category']}")
            rec.update(category=out["category"], evidence=out["evidence"], reason=out["reason"], decision=decide_semplice(out["category"]))
            rec["decision_full"] = "block" if rec["decision"] == "blocca" else "enter"
            rec["affected_ticker"] = out["company"]
        else:
            out = chat(model, SYSTEM_COMPLETO, prompt, schema_completo())
            full, kw = decide_completo(out, window)
            i = out["relevant_news_index"]
            rec.update(category=out["news_category"], affected_ticker=out["affected_ticker"], explains_divergence=out["explains_divergence"], permanence=out["permanence"],
                       confidence=out["confidence"], flags=",".join(out["flags"]), relevant_news_id=int(window.iloc[i]["id"]) if 0 <= i < len(window) else "",
                       keyword_ok=("" if kw is None else kw), evidence=out["evidence"], reason=out["reason"], decision_full=full, decision=("blocca" if full == "block" else "entra"))
        text = " ".join(window["headline"] + " " + window["summary"].fillna("")).lower()
        rec["evidence_ok"] = bool(rec["evidence"] in ("none", "") or rec["evidence"].strip().lower() in text)   # la citazione esiste davvero tra le notizie?
    except (RuntimeError, KeyError, ValueError, TypeError) as e:
        rec.update(decision="blocca", decision_full="block", category="error", error=str(e)[:200])   # regola di sicurezza: se qualcosa fallisce, si blocca
    return rec


def run(hours: float = WINDOW_HOURS, limit: int | None = None, dry_run: bool = False, model: str = MODEL, prompt_version: str = PROMPT) -> pd.DataFrame:
    sigs = pd.read_csv(SIGNALS)[SIGNAL_FIELDS]       # solo i campi ammessi: il resto del file non arriva mai al modello
    news = load_news(NEWS_PAIR)
    if (hours, model, prompt_version) == (WINDOW_HOURS, MODEL, PROMPT):
        out_path = DEC_3B_6H                                                       # la variante 3b_6h, su git
    else:                                                                          # un file per modello e prompt: non si mescolano
        out_path = PROCESSED / f"agent_decisions_v2_{hours:g}h_{model.replace(':', '-')}_{prompt_version}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = pd.read_csv(out_path) if out_path.exists() and not dry_run else pd.DataFrame()
    if len(done) and list(done.columns) != COLUMNS:
        raise SystemExit(f"{out_path.name} ha colonne diverse da quelle attuali (è di una versione precedente del codice): spostalo o cancellalo e rilancia")
    if len(done) and (done.category == "error").any():
        # le righe in errore (timeout, risposta non valida) sono un guasto, non un giudizio del modello: si tolgono e si rifanno
        print(f"{(done.category == 'error').sum()} segnali in errore dal giro precedente: li rifaccio")
        done = done[done.category != "error"]
        done.to_csv(out_path, index=False)
    todo = sigs[~sigs.signal_id.isin(done.get("signal_id", []))]
    if limit:
        todo = todo.head(limit)
    print(f"{len(sigs)} segnali, {len(done)} già fatti, ne faccio {len(todo)} (finestra {hours:g} ore, modello {model}, prompt {prompt_version})")
    t0 = time.time()
    for i, (_, sig) in enumerate(todo.iterrows(), 1):
        rec = run_signal(sig, news, hours, dry_run, model, prompt_version)
        if not dry_run:
            pd.DataFrame([rec])[COLUMNS].to_csv(out_path, mode="a", header=not out_path.exists(), index=False)
            print(f"{i}/{len(todo)} segnale {rec['signal_id']} {rec['pair']}: {rec['decision']} ({rec['category']}, {rec['n_news']} notizie) {time.time() - t0:.0f}s")
    return pd.read_csv(out_path) if out_path.exists() and not dry_run else pd.DataFrame()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hours", type=float, default=WINDOW_HOURS, help="finestra delle notizie in ore prima del segnale")
    ap.add_argument("--limit", type=int, help="al massimo N segnali (per le prove)")
    ap.add_argument("--model", default=MODEL, help="modello di Ollama (default: llama3.2:3b)")
    ap.add_argument("--prompt", default=PROMPT, choices=["semplice", "completo"], help="quale prompt usare (default: completo)")
    ap.add_argument("--dry-run", action="store_true", help="stampa i prompt senza chiamare il modello e senza salvare")
    a = ap.parse_args()
    res = run(a.hours, a.limit, a.dry_run, a.model, a.prompt)
    if len(res):
        print(res.groupby(["category", "decision_full", "decision"]).size())
