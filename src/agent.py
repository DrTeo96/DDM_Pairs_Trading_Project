"""Agente di notizie: per ogni segnale del train decide `entra`, `blocca` o `segui`.

L'agente è un grafo LangGraph a passi fissi, uguale per ogni segnale:
    cerca -> classifica -> verifica -> decidi -> registra

- cerca: le notizie sui due titoli uscite nelle `hours` ore che finiscono all'orario del segnale,
  lette dall'archivio news_ALL15_V2_train.parquet. Il filtro sull'orario è nel codice, non nelle istruzioni al modello.

- classifica: una notizia alla volta. Gli elenchi con più di MAX_SYMBOLS_LIST ticker sono rumore per
  regola, senza chiamare il modello. Per le altre il modello dice a chi si riferisce (A, B, entrambi, nessuno), di che tipo
  è e con quale direzione. Il modello vede solo la notizia e la sotto-industria della coppia, non direzione e orario del segnale.

- verifica: solo per un fatto strutturale su uno solo dei due titoli, una seconda domanda al modello: quell'azienda è davvero
  il compratore, il venditore, il bersaglio, l'indagato o l'azienda che cambia capo? Se no, la notizia diventa rumore.
  Serve perché il modello confonde l'azienda a cui la notizia è collegata con quella di cui parla.

- decidi: la regola è nel codice, il modello non decide e non vede le soglie del segnale.

- registra: un file JSON per segnale con notizie trovate, classificazioni, decisione e impostazioni.

La regola (decidi):
- ricerca fallita, server senza risposta, risposta non valida anche dopo RETRIES nuovi tentativi: `blocca`
- nessuna notizia nella finestra: `entra`, dimensione 1, senza chiamare il modello
- fatto strutturale (acquisizione, indagine, frode, cambio del management) su uno solo dei due titoli: `blocca`.
  
  Versione alt: `segui` se la direzione della notizia (positiva o negativa) è la stessa del movimento relativo dei 30 minuti
  prima del segnale. Il trade va nel verso della notizia sulle due gambe, per esempio notizia negativa su A: short A / long B.
  Con direzione incerta o in disaccordo con il movimento: `blocca`

- fatti strutturali su entrambi i titoli, oppure solo rumore: `entra`. Dimensione ridotta (SIZE_REDUCED) se almeno una notizia
  non è un elenco e riguarda uno dei due titoli; la colonna `size` è informativa, il backtest per ora non la usa

Sono rumore i risultati e la guidance, gli analisti, gli accordi commerciali, le partnership e i prodotti, il settore e la
macroeconomia, gli elenchi.

Anonimizzazione (attiva di default). Un modello può già sapere come è andata a finire per un'azienda, se ha visto in
addestramento notizie successive al periodo (lookahead del modello). Per renderglielo più difficile, nomi,
ticker, marchi e dirigenti delle due aziende diventano "Company A" e "Company B" (tabella ALIASES), e il modello non vede
la data. Non è una garanzia: cifre, luoghi, altre aziende citate e la sotto-industria possono ancora far riconoscere il
caso, e un marchio o un dirigente che manca nella tabella resta in chiaro. Va dichiarato nel report. Le istruzioni dicono al
modello che ogni azienda nominata con il suo nome è un'altra; nella verifica, un fatto strutturale su un titolo che titolo e
sommario non nominano diventa rumore senza chiedere al modello.

Due controlli sullo stesso campione: `--real-names` (stesso modello, nomi in chiaro) e un modello con data di fine
addestramento nota e lontana, per esempio `--model google/gemma-3-4b` (agosto 2024). Se l'agente va molto meglio con i
nomi in chiaro, il modello sta usando ciò che sa sulle aziende.

Il modello gira in locale dietro un server compatibile con l'API di OpenAI (LM Studio). Indirizzo e nome
del modello stanno in .env (vedi .env.example).

 cartella del progetto:
    uv run python -m src.agent --signals 0,1,2            prova su pochi segnali: stampa le decisioni, non scrive la tabella
    uv run python -m src.agent                            tutti i segnali del train: crea data/processed/agent_decisions_15pairs_v2_train.csv
    uv run python -m src.agent --reasoning on             il modello ragiona prima di rispondere: circa 70 s a notizia invece di 4
    uv run python -m src.agent --hours 6                  finestra di 6 ore (confronto); le notizie già classificate non si richiedono
    uv run python -m src.agent --sample 40                estrae il campione da classificare a mano in agent_manual_15pairs_v2_train.csv
    uv run python -m src.agent --agreement                accordo tra il gruppo e l'agente sul campione compilato
La tabella principale è scritta dall'ultimo giro completo con finestra WINDOW_H, nomi nascosti e il modello di .env, con
ragionamento acceso o spento (la colonna `reasoning` dice quale). Le altre varianti (finestra diversa, nomi in chiaro,
altro modello) scrivono le decisioni solo nella loro cartella in data/raw/agent/.

Ragionamento. Spark X2.6 4B ragiona prima di rispondere. Misurato su questo Mac (M4, 16 GB): circa 70 s a notizia con il
ragionamento e una risposta su tre che supera MAX_TOKENS, circa 4 s senza. Per le 958 notizie da classificare sono circa
20 ore contro circa un'ora: il default è senza ragionamento. Il ragionamento acceso si prova sul campione classificato a
mano (`--agreement --reasoning on`), e si sceglie la modalità con l'accordo migliore. Se il ragionamento supera
MAX_TOKENS la stessa notizia si richiede senza ragionamento, e la classificazione è segnata con `fallback`.
In un notebook:
    from src.agent import load_decisions
    B = apply_version(trades, "B", load_decisions())

Salvataggio. Ogni risposta del modello è salvata in data/raw/agent/<modello>/notizie/ con orario, richiesta e risposta
grezza; se la stessa domanda è già stata fatta, la risposta viene riletta, quindi rieseguire dà lo stesso risultato senza
server. Gli errori di rete o del server non si salvano: alla esecuzione successiva la chiamata si ripete.
Le decisioni di ogni giro sono in data/raw/agent/<modello>/<impostazioni>/: un JSON per segnale, decisions.csv, classifications.csv.
"""
import argparse
import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, replace
from functools import cache
from typing import TypedDict

import numpy as np
import pandas as pd
from langgraph.graph import END, START, StateGraph

from src.backtest import load_trades
from src.config import AGENT_DECISIONS, AGENT_MANUAL, AGENT_RAW, TRAIN_END, env
from src.news import load_news

BASE_URL = "http://127.0.0.1:1234/v1"   # server locale di LM Studio
WINDOW_H = 24                           # ore di notizie prima del segnale: copre la sera prima per i segnali subito dopo l'apertura
MAX_SYMBOLS_LIST = 5                    # una notizia con più ticker è un elenco: rumore per regola, senza chiamare il modello
SIZE_REDUCED = 0.5                      # dimensione suggerita quando si entra con notizie di rumore o fatti su entrambi
RETRIES = 2                             # nuovi tentativi dopo un errore o una risposta non valida, prima di bloccare
TIMEOUT = 300                           # secondi per chiamata; il primo caricamento del modello in memoria può essere lento
MAX_TOKENS = {True: 2000, False: 400}   # una notizia chiede circa 650 token di ragionamento; oltre 2000 il modello gira a vuoto e si ripiega senza ragionamento

STRUCTURAL = ("acquisizione", "indagine", "frode", "management")
NOISE = ("risultati", "analisti", "accordo_prodotto", "settore_macro", "elenco", "altro")
SUBTYPES = STRUCTURAL + NOISE
SIDES = ("A", "B", "entrambi", "nessuno")
NEWS_DIRECTIONS = ("positiva", "negativa", "incerta")

# La sotto-industria della coppia, in inglese: è l'unico contesto che il modello riceve oltre alla notizia.
SUB_INDUSTRY = {
    "MA-V": "transaction and payment processing services", "PYPL-XYZ": "transaction and payment processing services",
    "CSX-UNP": "rail transportation", "HD-LOW": "home improvement retail", "DHR-TMO": "life sciences tools and services",
    "CRM-WDAY": "application software", "JPM-WFC": "diversified banks", "BAC-C": "diversified banks", "NXPI-TXN": "semiconductors",
    "ELV-UNH": "managed health care", "CL-PG": "household products", "GS-MS": "investment banking and brokerage",
    "ISRG-SYK": "health care equipment", "KO-PEP": "soft drinks and non-alcoholic beverages", "COP-EOG": "oil and gas exploration and production",
}

# Nomi da nascondere per ogni titolo: ragione sociale, marchi, dirigenti. Distingue le maiuscole, come nei titoli delle notizie.
# Ricavata dalle notizie del train (nomi più frequenti per titolo) e da nomi noti; ciò che manca resta in chiaro.
ALIASES = {
    "MA": dict(name=["Mastercard Incorporated", "Mastercard Inc", "Mastercard", "MasterCard"], person=["Michael Miebach"]),
    "V": dict(name=["Visa Inc", "Visa"], brand=["VisaNet"], person=["Ryan McInerney"]),
    "CSX": dict(name=["CSX Corporation", "CSX Corp", "CSX"], person=["Joe Hinrichs", "Steve Angel"]),
    "UNP": dict(name=["Union Pacific Corporation", "Union Pacific Railroad", "Union Pacific Corp", "Union Pacific"], person=["Jim Vena"]),
    "PYPL": dict(name=["PayPal Holdings", "PayPal"], brand=["Venmo", "Braintree"], person=["Alex Chriss", "Enrique Lores"]),
    "XYZ": dict(name=["Block, Inc.", "Block Inc", "Block"], brand=["Cash App", "Square", "Afterpay", "Tidal"], person=["Jack Dorsey", "Dorsey"]),
    "HD": dict(name=["The Home Depot", "Home Depot"], brand=["SRS Distribution"], person=["Ted Decker"]),
    "LOW": dict(name=["Lowe's Companies", "Lowe's", "Lowes"], person=["Marvin Ellison"]),
    "DHR": dict(name=["Danaher Corporation", "Danaher Corp", "Danaher"], brand=["Leica Biosystems", "Beckman Coulter", "Cepheid", "Cytiva", "Abcam"], person=["Rainer Blair"]),
    "TMO": dict(name=["Thermo Fisher Scientific", "Thermo Fisher", "Thermo"], brand=["Fisher Scientific", "Patheon", "Olink"], person=["Marc Casper"]),
    "CRM": dict(name=["Salesforce, Inc.", "Salesforce Inc", "Salesforce.com", "Salesforce"], brand=["Agentforce", "Slack", "Tableau", "MuleSoft", "Informatica"],
                person=["Marc Benioff", "Benioff"]),
    "WDAY": dict(name=["Workday Inc", "Workday"], person=["Carl Eschenbach", "Aneel Bhusri"]),
    "JPM": dict(name=["JPMorgan Chase & Co.", "JPMorgan Chase & Co", "JPMorgan Chase", "JPMorgan", "JP Morgan", "J.P. Morgan", "J.P.Morgan", "Chase"],
                person=["Jamie Dimon", "Dimon", "Doug Petno", "Marianne Lake"]),
    "WFC": dict(name=["Wells Fargo & Company", "Wells Fargo & Co", "Wells Fargo"], person=["Charlie Scharf", "Scharf", "Mike Santomassimo", "Santomassimo"]),
    "NXPI": dict(name=["NXP Semiconductors", "NXP"], person=["Kurt Sievers", "Rafael Sotomayor"]),
    "TXN": dict(name=["Texas Instruments"], person=["Haviv Ilan", "Julie Knecht", "Rafael Lizardi"]),
    "ELV": dict(name=["Elevance Health", "Elevance"], brand=["Anthem", "Carelon", "Wellpoint"], person=["Gail Boudreaux"]),
    "UNH": dict(name=["UnitedHealth Group", "UnitedHealthcare", "UnitedHealth"], brand=["Optum"], person=["Stephen Hemsley", "Andrew Witty"]),
    "CL": dict(name=["Colgate-Palmolive", "Colgate", "Palmolive"], brand=["Hill's Pet Nutrition"], person=["Noel Wallace"]),
    "PG": dict(name=["Procter & Gamble", "Procter and Gamble", "Procter", "P&G"], brand=["Tide", "Gillette", "Pampers"], person=["Jon Moeller", "Shailesh Jejurikar"]),
    "GS": dict(name=["Goldman Sachs Group", "Goldman Sachs", "Goldman"], person=["David Solomon", "Solomon"]),
    "MS": dict(name=["Morgan Stanley"], brand=["E*Trade", "E*TRADE"], person=["Ted Pick"]),
    "ISRG": dict(name=["Intuitive Surgical", "Intuitive"], brand=["da Vinci"], person=["Dave Rosa", "Gary Guthart"]),
    "SYK": dict(name=["Stryker Corporation", "Stryker Corp", "Stryker"], brand=["Mako"], person=["Kevin Lobo"]),
    "KO": dict(name=["The Coca-Cola Company", "Coca-Cola", "Coca Cola", "Coke"], brand=["Sprite", "Fanta", "Costa Coffee"], person=["James Quincey", "Henrique Braun"]),
    "PEP": dict(name=["PepsiCo", "Pepsi"], brand=["Frito-Lay", "Gatorade", "Doritos", "Lay's", "Quaker", "Mountain Dew"], person=["Ramon Laguarta"]),
    "BAC": dict(name=["Bank of America", "Bank Of America", "BofA", "B of A", "Merrill Lynch", "Merrill"], person=["Brian Moynihan", "Moynihan"]),
    "C": dict(name=["Citigroup", "Citibank", "Citi"], person=["Jane Fraser"]),
    "COP": dict(name=["ConocoPhillips", "Conoco"], person=["Ryan Lance"]),
    "EOG": dict(name=["EOG Resources", "EOG"], person=["Ezra Yacob"]),
}
EXCHANGES = r"(?:NYSE|NASDAQ|Nasdaq|NYSE American|NYSEArca|AMEX)"

SYSTEM = """You classify one news item for an intraday pairs-trading strategy on two similar US companies from the same sub-industry, Company A and Company B.

The strategy bets that a sudden gap between the two stock prices closes within about 90 minutes. That bet works when the gap is noise. It fails when one of the two companies has had a real, lasting change, because then the gap has a reason to stay open. Your label tells the strategy which case this news item is.

{names}

Fields, in this order:
- "motivo": one short sentence in Italian that explains the label.
- "riguarda": the company the item is really about: "A", "B", "entrambi" (both of them, or the whole sector or market alike), "nessuno" (neither in a meaningful way).
  The tag only says that the news provider linked the item to A or B, not that the item is about them. If the item is about other companies, for example another company buying a third one, "riguarda" is "nessuno", unless Company A or Company B is itself the buyer, the target or the party under investigation.
  "sottotipo" describes what happens to the company in "riguarda": with "nessuno", use a noise subtype.
- "sottotipo": the kind of news, exactly one of:
  structural facts about a company:
  - "acquisizione": acquisition, merger, takeover bid, spin-off, sale of a business unit
  - "indagine": investigation, lawsuit, regulatory action, fine, ban
  - "frode": fraud, accounting problem, restatement of accounts
  - "management": the CEO, the CFO or the chair leaves or is replaced
  noise:
  - "risultati": quarterly results, guidance, dividends, buybacks
  - "analisti": analyst ratings, price targets, start of coverage
  - "accordo_prodotto": commercial deals, partnerships, contracts, product launches, investments
  - "settore_macro": sector, market, macroeconomic or political news
  - "elenco": lists of many stocks, "how much would you have made", options or trading activity
  - "altro": anything else
- "direzione": the likely effect on the stock price of the company the item is about: "positiva", "negativa" or "incerta".

Answer with one JSON object and nothing else."""

NAMES_HIDDEN = ("The names, tickers, brands and executives of the two companies have been replaced with \"Company A\" and \"Company B\" on purpose. "
                "So every company that appears in the text with its own name is a different company, never Company A or Company B. "
                "Do not try to guess who they are, and do not use anything you may know about what happened later: judge only from the text.")
NAMES_SHOWN = "Company A is {a} and Company B is {b}. Judge only from the text: do not use anything you may know about what happened later."


@dataclass(frozen=True)
class Settings:
    """Le impostazioni di un giro. Ognuna cambia le domande fatte al modello, quindi ha la sua cartella di decisioni."""
    model: str
    base_url: str = BASE_URL
    hours: int = WINDOW_H
    reasoning: bool = False
    anonymize: bool = True

    @property
    def folder(self):
        return AGENT_RAW / re.sub(r"[^A-Za-z0-9._-]+", "_", self.model)

    @property
    def run_dir(self):
        return self.folder / f"h{self.hours}_{'ragiona' if self.reasoning else 'diretto'}_{'anonimo' if self.anonymize else 'nomi'}"

    def is_main(self) -> bool:
        """Solo il giro con le impostazioni principali scrive la tabella letta dal backtest."""
        return self.hours == WINDOW_H and self.anonymize and self.model == env("AGENT_MODEL")


def normalize_url(url: str) -> str:
    """Toglie spazi e caratteri invisibili (un copia-incolla li porta con sé)"""
    url = re.sub(r"[\s\u200b\u200c\u200d\ufeff]", "", url).rstrip("/")
    return url


# ---------------------------------------------------------------- strumento 1: ricerca delle notizie

@cache
def _archive() -> pd.DataFrame:
    news = load_news()
    if news.ts.max() >= pd.Timestamp(TRAIN_END) + pd.Timedelta(days=1):
        raise ValueError("l'archivio delle notizie contiene giorni del test")
    return news


def clean_text(text) -> str:
    """Testo come lo leggerebbe una persona: entità HTML sciolte (&amp;, &#39;), spazi normali, apostrofi dritti."""
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return ""
    return re.sub(r"\s+", " ", html.unescape(str(text)).replace("’", "'")).strip()


def search_news(ticker_a: str, ticker_b: str, t_signal: pd.Timestamp, hours: int) -> list[dict]:
    """Le notizie che citano A o B, pubblicate nelle `hours` ore che finiscono all'orario del segnale, dalla più vecchia.
    Si usa l'orario di pubblicazione (ts), mai quello di aggiornamento."""
    n = _archive()
    m_a, m_b = n[f"mentions_{ticker_a}"], n[f"mentions_{ticker_b}"]
    w = n[(m_a | m_b) & (n.ts <= t_signal) & (n.ts > t_signal - pd.Timedelta(hours=hours))].sort_values(["ts", "id"])
    assert (w.ts <= t_signal).all() and t_signal < pd.Timestamp(TRAIN_END) + pd.Timedelta(days=1)
    return [dict(news_id=int(r.id), ts=r.ts, minutes_before=round((t_signal - r.ts).total_seconds() / 60, 1), headline=clean_text(r.headline),
                 summary=clean_text(r.summary), url=r.url, n_symbols=int(r.n_symbols), mentions_A=bool(m_a[i]), mentions_B=bool(m_b[i]))
            for i, r in zip(w.index, w.itertuples())]


# ---------------------------------------------------------------- anonimizzazione

@cache
def _patterns(ticker: str) -> list[tuple[re.Pattern, str]]:
    """Espressioni che trovano un titolo nel testo, dalla più lunga, con il tipo di sostituzione."""
    names = ALIASES.get(ticker, {})
    terms = [(t, kind) for kind in ("name", "brand", "person") for t in names.get(kind, [])]
    # un nome di più parole si toglie anche se è attaccato alla parola dopo (refusi come "Wells Fargoto")
    out = [(re.compile(rf"(?<![\w&*.]){re.escape(t)}" + ("" if " " in t else r"(?![\w&*])")), kind) for t, kind in sorted(terms, key=lambda x: -len(x[0]))]
    tk = re.escape(ticker)
    out.append((re.compile(rf"\(\s*{EXCHANGES}\s*:\s*{tk}\s*\)"), "ticker_paren"))   # (NYSE:JPM), (NYSE: JPM)
    out.append((re.compile(rf"{EXCHANGES}\s*:\s*{tk}\b"), "ticker"))
    out.append((re.compile(rf"\${tk}\b"), "ticker"))
    out.append((re.compile(rf"\({tk}\)"), "ticker_paren"))
    if len(ticker) >= 3:
        out.append((re.compile(rf"(?<![\w$]){tk}(?![\w])"), "ticker"))
    else:   # un ticker di una o due lettere (C, V, KO, MS) da solo è spesso una sigla qualsiasi: si toglie solo dove fa da ticker
        out.append((re.compile(rf"(?<![\w$&]){tk}(?=\s+(?:stock|shares|Stock|Shares)\b|'s\b|,\s*[A-Z]{{1,5}}\b|\s+and\s+[A-Z]{{1,5}}\b)"), "ticker"))
        out.append((re.compile(rf"(?<=[A-Z]{{2}},\s){tk}(?![\w])"), "ticker"))   # in un elenco di ticker: "RKT, HONA, MA"
        if len(ticker) == 2:
            out.append((re.compile(rf"(?<=worth of ){tk}(?=\.)"), "ticker"))
    return out


def anonymize(text: str, ticker_a: str, ticker_b: str) -> str:
    """Sostituisce nomi, ticker, marchi e dirigenti di A e B con Company A e Company B."""
    for ticker, label in ((ticker_a, "Company A"), (ticker_b, "Company B")):
        repl = {"name": label, "ticker": label, "ticker_paren": f"({label})", "brand": f"[{label} brand]", "person": f"[{label} executive]"}
        for pattern, kind in _patterns(ticker):
            text = pattern.sub(repl[kind], text)
    return text


# ---------------------------------------------------------------- strumento 2: classificazione di una notizia

class ServerError(RuntimeError):
    """Il server ha risposto, ma con un errore al posto della risposta (LM Studio lo fa anche con stato 200)."""


def response_schema() -> dict:
    """Formato fisso della risposta, passato al server perché costringa il modello a rispettarlo."""
    return {"type": "json_schema", "json_schema": {"name": "classificazione", "strict": True, "schema": {
        "type": "object", "additionalProperties": False, "required": ["motivo", "riguarda", "sottotipo", "direzione"],
        "properties": {
            "motivo": {"type": "string"},
            "riguarda": {"type": "string", "enum": list(SIDES)},
            "sottotipo": {"type": "string", "enum": list(SUBTYPES)},
            "direzione": {"type": "string", "enum": list(NEWS_DIRECTIONS)},
        }}}}


def call_model(system: str, user: str, s: Settings, schema: dict | None = None) -> dict:
    """L'unica funzione che parla con il modello: una domanda, la risposta grezza del server.
    Per passare a un altro servizio (per esempio un'API a pagamento) si cambia solo questa."""
    body = {"model": s.model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": schema or response_schema(), "temperature": 0, "seed": 0, "max_tokens": MAX_TOKENS[s.reasoning], "stream": False}
    if not s.reasoning:
        body["reasoning_effort"] = "none"   # con LM Studio spegne il ragionamento; "low" non cambia niente (provato)
    headers = {"Content-Type": "application/json"}
    if env("AGENT_API_KEY"):
        headers["Authorization"] = f"Bearer {env('AGENT_API_KEY')}"
    req = urllib.request.Request(f"{s.base_url}/chat/completions", data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = json.load(r)
    if "choices" not in raw:
        raise ServerError(str(raw.get("error", raw))[:200])
    return raw


def build_messages(pair: str, ticker_a: str, ticker_b: str, item: dict, hide_names: bool) -> tuple[str, str]:
    """Istruzioni e testo per una notizia. Niente data e niente dati del segnale: la classificazione vale per ogni segnale."""
    shown = (lambda t: anonymize(t, ticker_a, ticker_b)) if hide_names else (lambda t: t)
    system = SYSTEM.format(names=NAMES_HIDDEN if hide_names else NAMES_SHOWN.format(a=ticker_a, b=ticker_b))
    tagged = " and ".join(name for name, m in (("Company A", item["mentions_A"]), ("Company B", item["mentions_B"])) if m)
    user = "\n".join([
        f"Sub-industry of both companies: {SUB_INDUSTRY.get(pair, 'same sub-industry')}",
        f"The news is tagged with: {tagged} ({item['n_symbols']} tickers in total)",
        f"Headline: {shown(item['headline'])}",
        f"Summary: {shown(item['summary']) or '(none)'}",
    ])
    return system, user


def parse_label(raw: dict) -> dict:
    """Controlla la risposta grezza. Restituisce i campi validi oppure solleva ValueError con il motivo."""
    text = re.sub(r"<think>.*?</think>", "", raw["choices"][0]["message"].get("content") or "", flags=re.S)   # alcuni modelli scrivono il ragionamento nel testo
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError(f"nella risposta non c'è un oggetto JSON (finish_reason {raw['choices'][0].get('finish_reason')!r})")
    a = json.loads(text[start:end + 1])
    for field, allowed in (("riguarda", SIDES), ("sottotipo", SUBTYPES), ("direzione", NEWS_DIRECTIONS)):
        if a.get(field) not in allowed:
            raise ValueError(f"{field} non valido: {a.get(field)!r}")
    if not isinstance(a.get("motivo"), str) or not a["motivo"].strip():
        raise ValueError("manca il motivo")
    return a


def _cache_file(s: Settings, pair: str, news_id: int, system: str, user: str):
    """Un file per domanda: se cambiano modello, ragionamento, istruzioni o testo, la domanda è un'altra e non rilegge la vecchia risposta."""
    key = hashlib.sha256(json.dumps([s.model, s.reasoning, system, user]).encode()).hexdigest()[:12]
    return s.folder / "notizie" / f"{pair}_{news_id}_{key}.json"


def _ask(system: str, user: str, s: Settings, schema: dict | None = None, check=parse_label) -> tuple[dict | None, str]:
    """Fino a 1 + RETRIES chiamate. Restituisce l'ultima risposta arrivata (valida se possibile) e l'ultimo errore."""
    saved, error = None, ""
    for attempt in range(1, RETRIES + 2):
        t0 = time.time()
        try:
            raw = call_model(system, user, s, schema)
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ServerError) as e:
            if isinstance(getattr(e, "reason", None), ConnectionRefusedError):
                raise SystemExit(f"Nessun server risponde a {s.base_url}: avvia il server del modello (o correggi AGENT_BASE_URL) e riesegui.") from None
            error = f"{type(e).__name__}: {e}"[:200]
            continue
        saved = dict(model=s.model, served_model=raw.get("model"), reasoning=s.reasoning, answered_at=pd.Timestamp.now().isoformat(timespec="seconds"),
                     seconds=round(time.time() - t0, 1), attempt=attempt, system=system, user=user, response=raw)
        try:
            check(raw)
            return saved, ""
        except (ValueError, KeyError, IndexError, TypeError) as e:
            error = str(e)[:200]
        if raw["choices"][0].get("finish_reason") == "length":   # finiti i token: a temperatura 0 la stessa domanda finirebbe uguale
            break
    return saved, error


def classify_news(signal: dict, item: dict, s: Settings) -> dict:
    """La classificazione di una notizia per la coppia del segnale: per regola (elenchi), dalla cache o dal modello."""
    a, b = signal["ticker_A"], signal["ticker_B"]
    label = dict(news_id=item["news_id"], news_ts=str(item["ts"]), minutes_before=item["minutes_before"], n_symbols=item["n_symbols"],
                 mentions_A=item["mentions_A"], mentions_B=item["mentions_B"], headline=item["headline"])
    if item["n_symbols"] > MAX_SYMBOLS_LIST:
        side = "entrambi" if item["mentions_A"] and item["mentions_B"] else (a if item["mentions_A"] else b)
        return label | dict(source="regola", valid=True, outcome="regola", riguarda=side, sottotipo="elenco", tipo="rumore", direzione="incerta",
                            motivo=f"elenco di {item['n_symbols']} titoli: rumore per regola, senza chiamare il modello")
    system, user = build_messages(signal["pair"], a, b, item, s.anonymize)
    label |= dict(source="modello", text_shown=user, fallback=False)
    saved, f, error, label["fallback"] = _answer(s, signal["pair"], item["news_id"], system, user)
    if saved is None:   # nessuna risposta: non si salva, alla prossima esecuzione la chiamata si ripete
        return label | dict(valid=False, outcome="errore", error=error)
    label |= dict(answered_at=saved["answered_at"], seconds=saved["seconds"], cache=f.name)
    try:
        p = parse_label(saved["response"])
    except (ValueError, KeyError, IndexError, TypeError) as e:
        return label | dict(valid=False, outcome="risposta non valida", error=str(e)[:200])
    side = {"A": a, "B": b}.get(p["riguarda"], p["riguarda"])
    return label | dict(valid=True, outcome="risposta valida", riguarda=side, sottotipo=p["sottotipo"],
                        tipo="strutturale" if p["sottotipo"] in STRUCTURAL else "rumore", direzione=p["direzione"], motivo=p["motivo"].strip())


def _answer(s: Settings, pair: str, news_id: int, system: str, user: str, schema: dict | None = None, check=parse_label):
    """La risposta salvata a questa domanda, oppure una nuova (salvata se è arrivata). Se il ragionamento non si ferma entro
    MAX_TOKENS, la stessa domanda senza ragionamento. Restituisce risposta, file, errore e se c'è stato il ripiego."""
    def once(st: Settings):
        f = _cache_file(st, pair, news_id, system, user)
        if f.exists():
            return json.loads(f.read_text()), f, ""
        saved, error = _ask(system, user, st, schema, check)
        if saved is not None:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(saved, ensure_ascii=False, indent=1))
        return saved, f, error

    saved, f, error = once(s)
    if saved is not None and s.reasoning and saved["response"]["choices"][0].get("finish_reason") == "length":
        return *once(replace(s, reasoning=False)), True
    return saved, f, error, False


VERIFY_SYSTEM = """You check one label for an intraday pairs-trading strategy on two similar US companies, Company A and Company B.
A previous step said that the news below is a structural fact ("{sub}") about Company {side}. Structural means that Company {side} itself buys or sells a business, is bought, merges, is investigated, sued or fined, has an accounting problem, or changes its CEO, CFO or chair.

{names}

Check it. Answer "si" only if Company {side} itself is directly the buyer, the seller, the target, the party under investigation or the company whose top manager changes.
Answer "no" if the fact is about other companies, if Company {side} is only an advisor, lender, partner or one of many companies involved, or if it is a commercial deal, a partnership or a product.

Answer with one JSON object and nothing else, with the fields "motivo" (one sentence in Italian) and "risposta" ("si" or "no")."""


def verify_schema() -> dict:
    return {"type": "json_schema", "json_schema": {"name": "verifica", "strict": True, "schema": {
        "type": "object", "additionalProperties": False, "required": ["motivo", "risposta"],
        "properties": {"motivo": {"type": "string"}, "risposta": {"type": "string", "enum": ["si", "no"]}}}}}


def parse_verify(raw: dict) -> dict:
    text = re.sub(r"<think>.*?</think>", "", raw["choices"][0]["message"].get("content") or "", flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError(f"nella verifica non c'è un oggetto JSON (finish_reason {raw['choices'][0].get('finish_reason')!r})")
    a = json.loads(text[start:end + 1])
    if a.get("risposta") not in ("si", "no"):
        raise ValueError(f"risposta di verifica non valida: {a.get('risposta')!r}")
    return a


def verify_label(signal: dict, label: dict, s: Settings) -> dict:
    """Seconda domanda, solo per un fatto strutturale su uno solo dei due titoli: l'azienda è davvero parte del fatto?
    Un 4B confonde spesso l'azienda a cui la notizia è collegata con quella di cui parla (Yum! che vende Pizza Hut, collegata a PEP).
    Se la verifica dice no, la notizia diventa rumore; se la verifica fallisce, resta strutturale e il segnale si blocca."""
    a, b = signal["ticker_A"], signal["ticker_B"]
    if not (label.get("source") == "modello" and label.get("valid") and label.get("tipo") == "strutturale" and label.get("riguarda") in (a, b)):
        return label
    side = "A" if label["riguarda"] == a else "B"
    body = "\n".join(x for x in label["text_shown"].splitlines() if x.startswith(("Headline:", "Summary:")))
    if s.anonymize and f"Company {side}" not in body:
        # con i nomi nascosti l'azienda compare solo come "Company A/B": se titolo e sommario non la nominano, il fatto è di altri
        # (il modello lo sbaglia anche con l'istruzione esplicita, per esempio "Nvidia (Company A)"). Vale finché ALIASES copre i nomi.
        return label | dict(verifica="no", verifica_motivo=f"regola: titolo e sommario non nominano Company {side}", tipo="rumore",
                            sottotipo_prima=label["sottotipo"], sottotipo="altro")
    names = NAMES_HIDDEN if s.anonymize else NAMES_SHOWN.format(a=a, b=b)
    system = VERIFY_SYSTEM.format(sub=label["sottotipo"], side=side, names=names)
    saved, f, error, fallback = _answer(s, signal["pair"], label["news_id"], system, label["text_shown"], verify_schema(), parse_verify)
    if saved is None:
        return label | dict(verifica="errore", verifica_motivo=error)
    try:
        v = parse_verify(saved["response"])
    except (ValueError, KeyError, IndexError, TypeError) as e:
        return label | dict(verifica="non valida", verifica_motivo=str(e)[:200], verifica_cache=f.name)
    out = label | dict(verifica=v["risposta"], verifica_motivo=str(v.get("motivo", "")).strip(), verifica_cache=f.name, verifica_fallback=fallback)
    if v["risposta"] == "no":
        out |= dict(tipo="rumore", sottotipo_prima=label["sottotipo"], sottotipo="altro")
    return out


# ---------------------------------------------------------------- regola di decisione

def apply_rule(signal: dict, labels: list[dict], search_error: str = "") -> dict:
    """Dalle classificazioni alla decisione per le versioni B e C. È la stessa per l'agente e per la classificazione a mano."""
    a, b = signal["ticker_A"], signal["ticker_B"]
    out = dict(decision="entra", size=1.0, decision_C="entra", follow_side="", ticker="nessuno", category="nessuna_notizia", reason="",
               news_direction="", news_id=None, structural_on_moved_leg=None, n_news=len(labels),
               n_lists=sum(lab.get("sottotipo") == "elenco" and lab.get("source") == "regola" for lab in labels), outcome="nessuna notizia")
    if search_error:
        return out | dict(decision="blocca", decision_C="blocca", category="errore", outcome="errore", reason=f"ricerca fallita: {search_error}"[:200])
    if not labels:
        return out | dict(reason="nessuna notizia nella finestra prima del segnale")
    bad = [lab for lab in labels if not lab["valid"]]
    if bad:
        outcome = "errore" if any(lab["outcome"] == "errore" for lab in bad) else "risposta non valida"
        return out | dict(decision="blocca", decision_C="blocca", category="errore", outcome=outcome, news_id=bad[0]["news_id"],
                          reason=f"{len(bad)} notizie senza classificazione valida: {bad[0].get('error', '')}"[:200])
    out["outcome"] = "risposta valida" if any(lab["source"] != "regola" for lab in labels) else "solo elenchi"

    hits = {a: [], b: []}
    for lab in labels:
        if lab["tipo"] == "strutturale":
            for t in (a, b) if lab["riguarda"] == "entrambi" else (lab["riguarda"],) if lab["riguarda"] in hits else ():
                hits[t].append(lab)
    hit = [t for t in (a, b) if hits[t]]
    if len(hit) == 1:
        x = hit[0]
        y = b if x == a else a
        items = sorted(hits[x], key=lambda lab: lab["minutes_before"])   # la più vicina al segnale per prima
        dirs = {lab["direzione"] for lab in items}
        d = dirs.pop() if len(dirs) == 1 else "incerta"
        out |= dict(decision="blocca", decision_C="blocca", ticker=x, category="strutturale", reason=items[0]["motivo"], news_direction=d,
                    news_id=items[0]["news_id"], structural_on_moved_leg=x == signal["leg_piu_mosso"])
        rel = signal["ret_A_30m"] - signal["ret_B_30m"] if x == a else signal["ret_B_30m"] - signal["ret_A_30m"]   # movimento di x rispetto a y
        if (d == "positiva" and rel > 0) or (d == "negativa" and rel < 0):
            side = {x: "long" if d == "positiva" else "short", y: "short" if d == "positiva" else "long"}
            out |= dict(decision_C="segui", follow_side=f"{side[a]} {a} / {side[b]} {b}")
        return out

    relevant = [lab for lab in labels if lab["riguarda"] != "nessuno" and lab["sottotipo"] != "elenco"]
    size = SIZE_REDUCED if relevant else 1.0
    if hit:
        first = min((lab for t in hit for lab in hits[t]), key=lambda lab: lab["minutes_before"])
        return out | dict(category="strutturale", ticker="entrambi", size=size, news_id=first["news_id"],
                          reason=f"fatti strutturali su entrambi i titoli, lo spread non ha un motivo per restare aperto: {first['motivo']}"[:300])
    kinds = pd.Series([lab["sottotipo"] for lab in labels]).value_counts()
    return out | dict(category="rumore", ticker="nessuno", size=size, reason="solo rumore: " + ", ".join(f"{k} {v}" for k, v in kinds.items()))


# ---------------------------------------------------------------- il grafo

class State(TypedDict, total=False):
    signal: dict
    news: list[dict]
    search_error: str
    labels: list[dict]
    result: dict


def build_graph(s: Settings):
    """cerca -> classifica -> verifica -> decidi -> registra. Senza notizie, o se la ricerca fallisce, si va subito a decidi."""
    def cerca(state: State) -> State:
        sig = state["signal"]
        try:
            return {"news": search_news(sig["ticker_A"], sig["ticker_B"], sig["t_signal"], s.hours), "search_error": ""}
        except Exception as e:   # qualsiasi guasto della ricerca porta a bloccare, per regola
            return {"news": [], "search_error": f"{type(e).__name__}: {e}"[:200]}

    def classifica(state: State) -> State:
        return {"labels": [classify_news(state["signal"], item, s) for item in state["news"]]}

    def verifica(state: State) -> State:
        return {"labels": [verify_label(state["signal"], lab, s) for lab in state["labels"]]}

    def decidi(state: State) -> State:
        result = apply_rule(state["signal"], state.get("labels", []), state.get("search_error", ""))
        answered = [lab["answered_at"] for lab in state.get("labels", []) if lab.get("answered_at")]
        return {"result": dict(signal_id=state["signal"]["signal_id"]) | result | dict(
            model=s.model, answered_at=max(answered) if answered else "", hours=s.hours, reasoning=s.reasoning, anonymized=s.anonymize)}

    def registra(state: State) -> State:
        sig = state["signal"]
        f = s.run_dir / f"signal_{int(sig['signal_id']):05d}.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        log = dict(settings=asdict(s) | dict(max_symbols_list=MAX_SYMBOLS_LIST, retries=RETRIES), written_at=pd.Timestamp.now().isoformat(timespec="seconds"),
                   signal=sig, search_error=state.get("search_error", ""), news=state.get("news", []), labels=state.get("labels", []), result=state["result"])
        f.write_text(json.dumps(log, ensure_ascii=False, indent=1, default=str))
        return {}

    g = StateGraph(State)
    for name, fn in (("cerca", cerca), ("classifica", classifica), ("verifica", verifica), ("decidi", decidi), ("registra", registra)):
        g.add_node(name, fn)
    g.add_edge(START, "cerca")
    g.add_conditional_edges("cerca", lambda st: "classifica" if st["news"] and not st["search_error"] else "decidi", ["classifica", "decidi"])
    g.add_edge("classifica", "verifica")
    g.add_edge("verifica", "decidi")
    g.add_edge("decidi", "registra")
    g.add_edge("registra", END)
    return g.compile()


def _signal_dict(row: pd.Series) -> dict:
    """Una riga della tabella dei segnali come dizionario, con i parametri del segnale (finiscono nel registro, l'agente non li usa)."""
    return {k: (v.item() if isinstance(v, np.generic) else v) for k, v in row.items()}


def run(s: Settings, signal_ids: list[int] | None = None, verbose: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Una riga per segnale con la decisione e una riga per (segnale, notizia) con la classificazione."""
    signals = load_trades()   # rifiuta la tabella se contiene trade dopo TRAIN_END
    if signal_ids is not None:
        signals = signals[signals.signal_id.isin(signal_ids)]
    if verbose:
        todo = {_cache_file(s, sig.pair, item["news_id"], *build_messages(sig.pair, sig.ticker_A, sig.ticker_B, item, s.anonymize))
                for sig in signals.itertuples() for item in search_news(sig.ticker_A, sig.ticker_B, sig.t_signal, s.hours) if item["n_symbols"] <= MAX_SYMBOLS_LIST}
        new = sum(not f.exists() for f in todo)
        print(f"{len(signals)} segnali, {len(todo)} notizie da classificare, {new} senza risposta salvata "
              f"(stima {new * (70 if s.reasoning else 4) / 60:.0f} minuti)", flush=True)
    graph = build_graph(s)
    rows, labels, t0 = [], [], time.time()
    for i, (_, row) in enumerate(signals.iterrows(), 1):
        out = graph.invoke({"signal": _signal_dict(row)})
        rows.append(out["result"])
        labels += [dict(signal_id=row.signal_id, pair=row.pair) | lab for lab in out.get("labels", [])]
        r = out["result"]
        if verbose and r["outcome"] != "nessuna notizia":
            why = "" if r["outcome"] in ("risposta valida", "solo elenchi") else f": {r['reason']}"
            print(f"[{i}/{len(signals)} {time.time() - t0:.0f}s] segnale {row.signal_id} {row.pair} {row.t_signal:%Y-%m-%d %H:%M}: "
                  f"{r['decision']} / C {r['decision_C']} ({r['category']}, {r['outcome']}{why})", flush=True)
    return pd.DataFrame(rows), pd.DataFrame(labels)


def load_decisions(path=AGENT_DECISIONS) -> pd.DataFrame:
    """La tabella delle decisioni, nel formato che `backtest.apply_version(trades, "B", decisions)` legge così com'è.
    Per una variante: load_decisions(<cartella del giro>/decisions.csv)."""
    if not path.exists():
        raise FileNotFoundError(f"manca {path.name}: dalla cartella del progetto esegui `uv run python -m src.agent`")
    return pd.read_csv(path)


# ---------------------------------------------------------------- classificazione a mano e accordo

MANUAL_FIELDS = ["mano_riguarda", "mano_sottotipo", "mano_direzione", "mano_note"]


def make_manual_sample(s: Settings, n: int = 40, seed: int = 0) -> pd.DataFrame:
    """Campione cieco per la classificazione a mano: n segnali con almeno una notizia che non sia un elenco, distribuiti
    sulle coppie, una riga per notizia, senza nessuna colonna dell'agente. Il gruppo compila le colonne mano_*."""
    if AGENT_MANUAL.exists():
        raise SystemExit(f"{AGENT_MANUAL.name} esiste già e potrebbe contenere classificazioni a mano: spostalo o cancellalo tu, poi riesegui.")
    signals = load_trades()
    rows = []
    for sig in signals.itertuples():
        for item in search_news(sig.ticker_A, sig.ticker_B, sig.t_signal, s.hours):
            if item["n_symbols"] <= MAX_SYMBOLS_LIST:
                rows.append(dict(signal_id=sig.signal_id, pair=sig.pair, ticker_A=sig.ticker_A, ticker_B=sig.ticker_B, t_signal=sig.t_signal,
                                 direction=sig.direction, leg_piu_mosso=sig.leg_piu_mosso, news_id=item["news_id"], news_ts=item["ts"],
                                 minutes_before=item["minutes_before"], n_symbols=item["n_symbols"],
                                 tagged="+".join(t for t, m in ((sig.ticker_A, item["mentions_A"]), (sig.ticker_B, item["mentions_B"])) if m),
                                 headline=item["headline"], summary=item["summary"], url=item["url"]))
    pool = pd.DataFrame(rows)
    rng = np.random.default_rng(seed)
    per_pair = {p: list(rng.permutation(g.signal_id.unique())) for p, g in pool.groupby("pair")}
    chosen = []
    while len(chosen) < n and any(per_pair.values()):   # a turno tra le coppie, così ogni coppia ha 2-3 segnali
        for p in sorted(per_pair):
            if per_pair[p] and len(chosen) < n:
                chosen.append(per_pair[p].pop())
    sample = pool[pool.signal_id.isin(chosen)].sort_values(["signal_id", "news_ts"]).reset_index(drop=True)
    for c in MANUAL_FIELDS:
        sample[c] = ""
    AGENT_MANUAL.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(AGENT_MANUAL, index=False)
    return sample


def cohen_kappa(x: pd.Series, y: pd.Series) -> float:
    """Accordo oltre il caso tra due classificazioni: 1 accordo perfetto, 0 come tirare a sorte con le stesse frequenze."""
    x, y = x.astype(str).reset_index(drop=True), y.astype(str).reset_index(drop=True)
    po = (x == y).mean()
    pe = sum(x.eq(k).mean() * y.eq(k).mean() for k in set(x) | set(y))
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def agreement(s: Settings) -> pd.DataFrame:
    """Confronta il campione compilato dal gruppo con l'agente: quota di accordo e kappa per notizia (a chi si riferisce,
    tipo, sottotipo, direzione) e per segnale (decisione B e C, con la stessa regola applicata alle etichette del gruppo)."""
    if not AGENT_MANUAL.exists():
        raise SystemExit(f"manca {AGENT_MANUAL.name}: crealo con `uv run python -m src.agent --sample 40` e fallo compilare al gruppo")
    m = pd.read_csv(AGENT_MANUAL, dtype={c: str for c in MANUAL_FIELDS}).fillna({c: "" for c in MANUAL_FIELDS})
    for c in MANUAL_FIELDS[:3]:
        m[c] = m[c].str.strip()
    m = m[m.mano_sottotipo != ""]
    if m.empty:
        raise SystemExit(f"{AGENT_MANUAL.name} non ha ancora righe compilate (colonna mano_sottotipo)")
    m["mano_riguarda"] = [{"A": r.ticker_A, "B": r.ticker_B}.get(r.mano_riguarda, r.mano_riguarda) for r in m.itertuples()]
    for c, allowed in (("mano_sottotipo", SUBTYPES), ("mano_direzione", NEWS_DIRECTIONS)):
        bad = m[~m[c].isin(allowed)]
        if len(bad):
            raise SystemExit(f"{c}: valori non validi {sorted(set(bad[c]))} (righe {list(bad.index[:5] + 2)}); ammessi: {', '.join(allowed)}")
    bad = m[[r.mano_riguarda not in (r.ticker_A, r.ticker_B, "entrambi", "nessuno") for r in m.itertuples()]]
    if len(bad):
        raise SystemExit(f"mano_riguarda: valori non validi {sorted(set(bad.mano_riguarda))}; ammessi: A, B, il ticker, entrambi, nessuno")
    m["mano_tipo"] = np.where(m.mano_sottotipo.isin(STRUCTURAL), "strutturale", "rumore")

    ids = sorted(m.signal_id.unique())
    decisions, labels = run(s, ids, verbose=False)
    model_labels = labels[labels.source == "modello"]
    news = m.merge(model_labels, on=["signal_id", "news_id"], how="inner", suffixes=("", "_agente"))
    lines = [dict(livello="notizia", campo=c, n=len(news), accordo=(news[f"mano_{c}"] == news[c]).mean(), kappa=cohen_kappa(news[f"mano_{c}"], news[c]))
             for c in ("riguarda", "tipo", "sottotipo", "direzione") if len(news)]

    trades = load_trades().set_index("signal_id")
    human = []
    for sid in ids:
        sig = _signal_dict(trades.loc[sid].copy()) | dict(signal_id=sid)
        own = [dict(news_id=r.news_id, minutes_before=r.minutes_before, source="mano", valid=True, outcome="mano", riguarda=r.mano_riguarda,
                    sottotipo=r.mano_sottotipo, tipo=r.mano_tipo, direzione=r.mano_direzione, motivo=r.mano_note or "classificazione a mano")
               for r in news[news.signal_id == sid].itertuples()]
        rule = [lab for lab in labels[(labels.signal_id == sid) & (labels.source == "regola")].to_dict("records")]
        human.append(dict(signal_id=sid) | {f"mano_{k}": v for k, v in apply_rule(sig, own + rule).items() if k in ("decision", "decision_C", "category")})
    sig_cmp = pd.DataFrame(human).merge(decisions, on="signal_id")
    lines += [dict(livello="segnale", campo=c, n=len(sig_cmp), accordo=(sig_cmp[f"mano_{c}"] == sig_cmp[c]).mean(), kappa=cohen_kappa(sig_cmp[f"mano_{c}"], sig_cmp[c]))
              for c in ("decision", "decision_C", "category")]
    table = pd.DataFrame(lines)

    s.run_dir.mkdir(parents=True, exist_ok=True)
    keep = ["signal_id", "pair", "news_id", "headline", "mano_riguarda", "riguarda", "mano_sottotipo", "sottotipo", "mano_direzione", "direzione", "motivo", "mano_note"]
    news[(news.mano_tipo != news.tipo) | (news.mano_riguarda != news.riguarda)][keep].to_csv(s.run_dir / "disaccordi_notizie.csv", index=False)
    sig_cmp.to_csv(s.run_dir / "accordo_segnali.csv", index=False)
    table.to_csv(s.run_dir / "accordo.csv", index=False)
    return table


# ---------------------------------------------------------------- terminale

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", default=env("AGENT_MODEL"), help="nome del modello sul server (default: AGENT_MODEL in .env)")
    ap.add_argument("--base-url", default=env("AGENT_BASE_URL", BASE_URL), help=f"indirizzo del server (default: AGENT_BASE_URL in .env, altrimenti {BASE_URL})")
    ap.add_argument("--hours", type=int, default=WINDOW_H, help="ore di notizie prima del segnale")
    ap.add_argument("--reasoning", choices=["on", "off"], default="off", help="on: il modello ragiona prima di rispondere (circa 70 s a notizia); off: risponde subito (circa 4 s)")
    ap.add_argument("--real-names", action="store_true", help="controllo del lookahead: il modello vede i nomi veri delle aziende")
    ap.add_argument("--signals", help="solo questi signal_id, separati da virgola: prova, non scrive la tabella")
    ap.add_argument("--sample", type=int, metavar="N", help="estrae N segnali da classificare a mano e si ferma")
    ap.add_argument("--agreement", action="store_true", help="accordo tra la classificazione a mano e l'agente")
    a = ap.parse_args()
    if not a.model and not a.sample:
        raise SystemExit("Manca il nome del modello: scrivi AGENT_MODEL in .env oppure usa --model")
    s = Settings(model=a.model, base_url=normalize_url(a.base_url), hours=a.hours, reasoning=a.reasoning == "on", anonymize=not a.real_names)

    if a.sample:
        sample = make_manual_sample(s, a.sample)
        print(f"salvato data/processed/{AGENT_MANUAL.name}: {sample.signal_id.nunique()} segnali, {len(sample)} notizie (elenchi esclusi).\n"
              f"Compila per ogni riga mano_riguarda (A, B, entrambi, nessuno), mano_sottotipo ({', '.join(SUBTYPES)}),\n"
              f"mano_direzione ({', '.join(NEWS_DIRECTIONS)}) e, se serve, mano_note. Poi: uv run python -m src.agent --agreement")
        raise SystemExit
    if a.agreement:
        print(agreement(s).to_string(index=False, float_format=lambda x: f"{x:.2f}"))
        print(f"dettagli in {s.run_dir.relative_to(AGENT_RAW.parents[2])}/: accordo.csv, accordo_segnali.csv, disaccordi_notizie.csv")
        raise SystemExit

    ids = [int(x) for x in a.signals.split(",")] if a.signals else None
    out, labels = run(s, ids)
    print(f"\n{len(out)} segnali | B: " + ", ".join(f"{k} {v}" for k, v in out.decision.value_counts().items())
          + " | C: " + ", ".join(f"{k} {v}" for k, v in out.decision_C.value_counts().items())
          + " | " + ", ".join(f"{k} {v}" for k, v in out.outcome.value_counts().items()))
    if ids is not None:
        print(out[["signal_id", "decision", "decision_C", "size", "ticker", "category", "news_direction", "n_news", "outcome", "reason"]].to_string(index=False))
    else:
        s.run_dir.mkdir(parents=True, exist_ok=True)
        out.to_csv(s.run_dir / "decisions.csv", index=False)
        labels.to_csv(s.run_dir / "classifications.csv", index=False)
        print(f"salvato {s.run_dir.relative_to(AGENT_RAW.parents[2])}/decisions.csv e classifications.csv")
        if s.is_main():
            out.to_csv(AGENT_DECISIONS, index=False)
            print(f"salvato data/processed/{AGENT_DECISIONS.name}")
        else:
            print("variante: la tabella principale non è stata toccata")
        n_err = int((out.outcome == "errore").sum())
        if n_err:
            print(f"ATTENZIONE: {n_err} segnali bloccati perché il server non ha risposto. Riesegui lo stesso comando: ripete solo quelle chiamate.")
