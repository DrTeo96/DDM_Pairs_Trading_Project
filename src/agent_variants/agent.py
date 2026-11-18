"""News agent: for each train signal it decides `enter`, `block` or `follow`.

The agent is a LangGraph graph with fixed steps, the same for every signal:
    search -> classify -> verify -> decide -> record

- search: the news on the two stocks published in the `hours` hours that end at the signal time,
  read from the archive news_ALL15_V2_train.parquet. The time filter is in the code, not in the instructions to the model.

- classify: one news item at a time. Lists with more than MAX_SYMBOLS_LIST tickers are noise by
  rule, without calling the model. For the others the model says what the item is about (A, B, both, none), what kind
  it is and with which direction. The model sees only the news item and the sub-industry of the pair, not the direction and time of the signal.

- verify: only for a structural fact on just one of the two stocks, a second question to the model: is that company really
  the buyer, the seller, the target, the party under investigation or the company changing its head? If not, the news item becomes noise.
  It is needed because the model confuses the company the news is linked to with the one it talks about.

- decide: the rule is in the code, the model does not decide and does not see the signal thresholds.

- record: one JSON file per signal with the news found, classifications, decision and settings.

The rule (decide):
- search failed, server not answering, invalid answer even after RETRIES new attempts: `block`
- no news in the window: `enter`, size 1, without calling the model
- structural fact (acquisition, investigation, fraud, change of management) on only one of the two stocks: `block`.

  Version C: `follow` if the direction of the news (positive or negative) is the same as the relative move of the 30 minutes
  before the signal. The trade goes in the direction of the news on both legs, for example negative news on A: short A / long B.
  With uncertain direction or disagreeing with the move: `block`

- structural facts on both stocks, or only noise: `enter`. Reduced size (SIZE_REDUCED) if at least one news item
  is not a list and is about one of the two stocks; the `size` column is informative, the backtest does not use it for now

Noise: results and guidance, analysts, commercial deals, partnerships and products, sector and
macroeconomy, lists.

Anonymisation (on by default). A model may already know how things ended for a company, if it saw in
training news later than the period (model lookahead). To make it harder, names,
tickers, brands and executives of the two companies become "Company A" and "Company B" (ALIASES table), and the model does not see
the date. It is not a guarantee: figures, places, other companies mentioned and the sub-industry can still give the
case away, and a brand or an executive missing from the table stays in clear. It must be stated in the report. The instructions tell the
model that every company named with its own name is another one; in the verification, a structural fact on a stock that headline and
summary do not name becomes noise without asking the model.

Two checks on the same sample: `--real-names` (same model, names in clear) and a model with a known and distant end of
training date, for example `--model google/gemma-3-4b` (August 2024). If the agent does much better with the
names in clear, the model is using what it knows about the companies.

The model runs locally behind a server compatible with the OpenAI API (LM Studio). Address and name
of the model are in .env (see .env.example).

What the model sees is frozen. The prompts and the JSON schema below are exactly those the recorded decisions were produced
with. They name the label fields and their values in Italian (motivo, riguarda, sottotipo, direzione; entrambi, nessuno...)
and ask the model for a one-sentence reason in Italian, so the `rationale` column holds the model's own Italian sentence.
Changing a single character would change the cache key of every answer (see _cache_file): the saved answers would no longer
be found and the decisions would come from a different prompt. The rest of the code uses English names: `_to_english`
translates the model's answer right after it is checked.

From the project folder:
    uv run python -m src.agent_variants.agent --signals 0,1,2            trial on a few signals: prints the decisions, does not write the table
    uv run python -m src.agent_variants.agent                            all the train signals: creates data/processed/agent_decisions_15pairs_v2_train.csv
    uv run python -m src.agent_variants.agent --reasoning on             the model reasons before answering: about 70 s per news item instead of 4
    uv run python -m src.agent_variants.agent --hours 6                  6-hour window (comparison); news already classified are not asked again
    uv run python -m src.agent_variants.agent --sample 40                draws the sample to classify by hand in agent_manual_15pairs_v2_train.csv
    uv run python -m src.agent_variants.agent --agreement                agreement between the group and the agent on the filled-in sample
The main table is written by the last full run with window WINDOW_H, hidden names and the model of .env, with
reasoning on or off (the `reasoning` column says which). The other variants (different window, names in clear,
another model) write the decisions only in their folder in data/raw/agent/.

Reasoning. Spark X2.6 4B reasons before answering. Measured on this Mac (M4, 16 GB): about 70 s per news item with
reasoning and one answer in three going over MAX_TOKENS, about 4 s without. For the 958 news items to classify that is about
20 hours against about one hour: the default is without reasoning. Reasoning on is tried on the hand-classified
sample (`--agreement --reasoning on`), and the mode with the best agreement is chosen. If the reasoning goes over
MAX_TOKENS the same news item is asked again without reasoning, and the classification is marked with `fallback`.
In a notebook:
    from src.agent_variants.agent import load_decisions
    B = apply_version(trades, "B", load_decisions())

Saving. Every answer of the model is saved in data/raw/agent/<model>/news/ with time, request and raw
answer; if the same question was already asked, the answer is read again, so rerunning gives the same result without a
server. Network or server errors are not saved: at the next run the call is repeated.
The decisions of each run are in data/raw/agent/<model>/<settings>/: one JSON per signal, decisions.csv, classifications.csv.
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

BASE_URL = "http://127.0.0.1:1234/v1"   # local LM Studio server
WINDOW_H = 24                           # hours of news before the signal: covers the evening before for the signals right after the open
MAX_SYMBOLS_LIST = 5                    # a news item with more tickers is a list: noise by rule, without calling the model
SIZE_REDUCED = 0.5                      # suggested size when entering with noise news or facts on both
RETRIES = 2                             # new attempts after an error or an invalid answer, before blocking
TIMEOUT = 300                           # seconds per call; the first load of the model in memory can be slow
MAX_TOKENS = {True: 2000, False: 400}   # a news item takes about 650 reasoning tokens; beyond 2000 the model spins and falls back without reasoning

# ---------------------------------------------------------------- what the model sees (frozen, in Italian: see the docstring)
MODEL_STRUCTURAL = ("acquisizione", "indagine", "frode", "management")
MODEL_NOISE = ("risultati", "analisti", "accordo_prodotto", "settore_macro", "elenco", "altro")
MODEL_SUBTYPES = MODEL_STRUCTURAL + MODEL_NOISE
MODEL_SIDES = ("A", "B", "entrambi", "nessuno")
MODEL_DIRECTIONS = ("positiva", "negativa", "incerta")

# the same labels in English, used by the rest of the code
SUBTYPE_EN = dict(zip(MODEL_SUBTYPES, ("acquisition", "investigation", "fraud", "management",
                                       "results", "analysts", "deal_product", "sector_macro", "list", "other")))
SIDE_EN = {"A": "A", "B": "B", "entrambi": "both", "nessuno": "none"}
DIRECTION_EN = {"positiva": "positive", "negativa": "negative", "incerta": "uncertain"}
VERIFY_EN = {"si": "yes", "no": "no"}
SUBTYPE_MODEL = {v: k for k, v in SUBTYPE_EN.items()}

STRUCTURAL = tuple(SUBTYPE_EN[x] for x in MODEL_STRUCTURAL)
NOISE = tuple(SUBTYPE_EN[x] for x in MODEL_NOISE)
SUBTYPES = STRUCTURAL + NOISE
SIDES = ("A", "B", "both", "none")
NEWS_DIRECTIONS = ("positive", "negative", "uncertain")

# The sub-industry of the pair, in English: it is the only context the model gets besides the news item.
SUB_INDUSTRY = {
    "MA-V": "transaction and payment processing services", "PYPL-XYZ": "transaction and payment processing services",
    "CSX-UNP": "rail transportation", "HD-LOW": "home improvement retail", "DHR-TMO": "life sciences tools and services",
    "CRM-WDAY": "application software", "JPM-WFC": "diversified banks", "BAC-C": "diversified banks", "NXPI-TXN": "semiconductors",
    "ELV-UNH": "managed health care", "CL-PG": "household products", "GS-MS": "investment banking and brokerage",
    "ISRG-SYK": "health care equipment", "KO-PEP": "soft drinks and non-alcoholic beverages", "COP-EOG": "oil and gas exploration and production",
}

# Names to hide for each stock: company name, brands, executives. Case-sensitive, as in the news headlines.
# Built from the train news (most frequent names per stock) and from well-known names; whatever is missing stays in clear.
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
    """The settings of a run. Each one changes the questions asked to the model, so it has its own decisions folder."""
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
        return self.folder / f"h{self.hours}_{'reasoning' if self.reasoning else 'direct'}_{'anon' if self.anonymize else 'names'}"

    def is_main(self) -> bool:
        """Only the run with the main settings writes the table read by the backtest."""
        return self.hours == WINDOW_H and self.anonymize and self.model == env("AGENT_MODEL")


def normalize_url(url: str) -> str:
    """Removes spaces and invisible characters (a copy-paste brings them along)"""
    url = re.sub(r"[\s​‌‍﻿]", "", url).rstrip("/")
    return url


# ---------------------------------------------------------------- tool 1: news search

@cache
def _archive() -> pd.DataFrame:
    news = load_news()
    if news.ts.max() >= pd.Timestamp(TRAIN_END) + pd.Timedelta(days=1):
        raise ValueError("the news archive contains test days")
    return news


def clean_text(text) -> str:
    """Text as a person would read it: HTML entities resolved (&amp;, &#39;), normal spaces, straight apostrophes."""
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return ""
    return re.sub(r"\s+", " ", html.unescape(str(text)).replace("’", "'")).strip()


def search_news(ticker_a: str, ticker_b: str, t_signal: pd.Timestamp, hours: int) -> list[dict]:
    """The news that tag A or B, published in the `hours` hours that end at the signal time, oldest first.
    It uses the publication time (ts), never the update time."""
    n = _archive()
    m_a, m_b = n[f"mentions_{ticker_a}"], n[f"mentions_{ticker_b}"]
    w = n[(m_a | m_b) & (n.ts <= t_signal) & (n.ts > t_signal - pd.Timedelta(hours=hours))].sort_values(["ts", "id"])
    assert (w.ts <= t_signal).all() and t_signal < pd.Timestamp(TRAIN_END) + pd.Timedelta(days=1)
    return [dict(news_id=int(r.id), ts=r.ts, minutes_before=round((t_signal - r.ts).total_seconds() / 60, 1), headline=clean_text(r.headline),
                 summary=clean_text(r.summary), url=r.url, n_symbols=int(r.n_symbols), mentions_A=bool(m_a[i]), mentions_B=bool(m_b[i]))
            for i, r in zip(w.index, w.itertuples())]


# ---------------------------------------------------------------- anonymisation

@cache
def _patterns(ticker: str) -> list[tuple[re.Pattern, str]]:
    """Expressions that find a stock in the text, longest first, with the kind of replacement."""
    names = ALIASES.get(ticker, {})
    terms = [(t, kind) for kind in ("name", "brand", "person") for t in names.get(kind, [])]
    # a name of several words is removed even if it is glued to the next word (typos like "Wells Fargoto")
    out = [(re.compile(rf"(?<![\w&*.]){re.escape(t)}" + ("" if " " in t else r"(?![\w&*])")), kind) for t, kind in sorted(terms, key=lambda x: -len(x[0]))]
    tk = re.escape(ticker)
    out.append((re.compile(rf"\(\s*{EXCHANGES}\s*:\s*{tk}\s*\)"), "ticker_paren"))   # (NYSE:JPM), (NYSE: JPM)
    out.append((re.compile(rf"{EXCHANGES}\s*:\s*{tk}\b"), "ticker"))
    out.append((re.compile(rf"\${tk}\b"), "ticker"))
    out.append((re.compile(rf"\({tk}\)"), "ticker_paren"))
    if len(ticker) >= 3:
        out.append((re.compile(rf"(?<![\w$]){tk}(?![\w])"), "ticker"))
    else:   # a one- or two-letter ticker (C, V, KO, MS) on its own is often any acronym: it is removed only where it acts as a ticker
        out.append((re.compile(rf"(?<![\w$&]){tk}(?=\s+(?:stock|shares|Stock|Shares)\b|'s\b|,\s*[A-Z]{{1,5}}\b|\s+and\s+[A-Z]{{1,5}}\b)"), "ticker"))
        out.append((re.compile(rf"(?<=[A-Z]{{2}},\s){tk}(?![\w])"), "ticker"))   # in a list of tickers: "RKT, HONA, MA"
        if len(ticker) == 2:
            out.append((re.compile(rf"(?<=worth of ){tk}(?=\.)"), "ticker"))
    return out


def anonymize(text: str, ticker_a: str, ticker_b: str) -> str:
    """Replaces names, tickers, brands and executives of A and B with Company A and Company B."""
    for ticker, label in ((ticker_a, "Company A"), (ticker_b, "Company B")):
        repl = {"name": label, "ticker": label, "ticker_paren": f"({label})", "brand": f"[{label} brand]", "person": f"[{label} executive]"}
        for pattern, kind in _patterns(ticker):
            text = pattern.sub(repl[kind], text)
    return text


# ---------------------------------------------------------------- tool 2: classification of a news item

class ServerError(RuntimeError):
    """The server answered, but with an error instead of the answer (LM Studio does it even with status 200)."""


def response_schema() -> dict:
    """Fixed format of the answer, passed to the server so that it forces the model to respect it (frozen field names)."""
    return {"type": "json_schema", "json_schema": {"name": "classificazione", "strict": True, "schema": {
        "type": "object", "additionalProperties": False, "required": ["motivo", "riguarda", "sottotipo", "direzione"],
        "properties": {
            "motivo": {"type": "string"},
            "riguarda": {"type": "string", "enum": list(MODEL_SIDES)},
            "sottotipo": {"type": "string", "enum": list(MODEL_SUBTYPES)},
            "direzione": {"type": "string", "enum": list(MODEL_DIRECTIONS)},
        }}}}


def call_model(system: str, user: str, s: Settings, schema: dict | None = None) -> dict:
    """The only function that talks to the model: one question, the raw answer of the server.
    To switch to another service (for example a paid API) only this one changes."""
    body = {"model": s.model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": schema or response_schema(), "temperature": 0, "seed": 0, "max_tokens": MAX_TOKENS[s.reasoning], "stream": False}
    if not s.reasoning:
        body["reasoning_effort"] = "none"   # with LM Studio it switches reasoning off; "low" changes nothing (tried)
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
    """Instructions and text for a news item. No date and no signal data: the classification holds for every signal."""
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
    """Checks the raw answer. Returns the valid fields (still with the model's Italian names) or raises ValueError with the reason."""
    text = re.sub(r"<think>.*?</think>", "", raw["choices"][0]["message"].get("content") or "", flags=re.S)   # some models write their reasoning in the text
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError(f"the answer contains no JSON object (finish_reason {raw['choices'][0].get('finish_reason')!r})")
    a = json.loads(text[start:end + 1])
    for field, allowed in (("riguarda", MODEL_SIDES), ("sottotipo", MODEL_SUBTYPES), ("direzione", MODEL_DIRECTIONS)):
        if a.get(field) not in allowed:
            raise ValueError(f"invalid {field}: {a.get(field)!r}")
    if not isinstance(a.get("motivo"), str) or not a["motivo"].strip():
        raise ValueError("the reason (motivo) is missing")
    return a


def _to_english(p: dict, a: str, b: str) -> dict:
    """The fields of a checked answer with English names and values; A and B become the two tickers."""
    subtype = SUBTYPE_EN[p["sottotipo"]]
    return dict(about={"A": a, "B": b}.get(p["riguarda"], SIDE_EN[p["riguarda"]]), subtype=subtype,
                kind="structural" if subtype in STRUCTURAL else "noise", news_direction=DIRECTION_EN[p["direzione"]], rationale=p["motivo"].strip())


def _cache_file(s: Settings, pair: str, news_id: int, system: str, user: str):
    """One file per question: if model, reasoning, instructions or text change, the question is a different one and the old answer is not read."""
    key = hashlib.sha256(json.dumps([s.model, s.reasoning, system, user]).encode()).hexdigest()[:12]
    return s.folder / "news" / f"{pair}_{news_id}_{key}.json"


def _ask(system: str, user: str, s: Settings, schema: dict | None = None, check=parse_label) -> tuple[dict | None, str]:
    """Up to 1 + RETRIES calls. Returns the last answer received (valid if possible) and the last error."""
    saved, error = None, ""
    for attempt in range(1, RETRIES + 2):
        t0 = time.time()
        try:
            raw = call_model(system, user, s, schema)
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ServerError) as e:
            if isinstance(getattr(e, "reason", None), ConnectionRefusedError):
                raise SystemExit(f"No server answers at {s.base_url}: start the model server (or fix AGENT_BASE_URL) and run again.") from None
            error = f"{type(e).__name__}: {e}"[:200]
            continue
        saved = dict(model=s.model, served_model=raw.get("model"), reasoning=s.reasoning, answered_at=pd.Timestamp.now().isoformat(timespec="seconds"),
                     seconds=round(time.time() - t0, 1), attempt=attempt, system=system, user=user, response=raw)
        try:
            check(raw)
            return saved, ""
        except (ValueError, KeyError, IndexError, TypeError) as e:
            error = str(e)[:200]
        if raw["choices"][0].get("finish_reason") == "length":   # out of tokens: at temperature 0 the same question would end the same way
            break
    return saved, error


def classify_news(signal: dict, item: dict, s: Settings) -> dict:
    """The classification of a news item for the pair of the signal: by rule (lists), from the cache or from the model."""
    a, b = signal["ticker_A"], signal["ticker_B"]
    label = dict(news_id=item["news_id"], news_ts=str(item["ts"]), minutes_before=item["minutes_before"], n_symbols=item["n_symbols"],
                 mentions_A=item["mentions_A"], mentions_B=item["mentions_B"], headline=item["headline"])
    if item["n_symbols"] > MAX_SYMBOLS_LIST:
        side = "both" if item["mentions_A"] and item["mentions_B"] else (a if item["mentions_A"] else b)
        return label | dict(source="rule", valid=True, outcome="rule", about=side, subtype="list", kind="noise", news_direction="uncertain",
                            rationale=f"list of {item['n_symbols']} stocks: noise by rule, without calling the model")
    system, user = build_messages(signal["pair"], a, b, item, s.anonymize)
    label |= dict(source="model", text_shown=user, fallback=False)
    saved, f, error, label["fallback"] = _answer(s, signal["pair"], item["news_id"], system, user)
    if saved is None:   # no answer: nothing is saved, the call is repeated at the next run
        return label | dict(valid=False, outcome="error", error=error)
    label |= dict(answered_at=saved["answered_at"], seconds=saved["seconds"], cache=f.name)
    try:
        p = parse_label(saved["response"])
    except (ValueError, KeyError, IndexError, TypeError) as e:
        return label | dict(valid=False, outcome="invalid answer", error=str(e)[:200])
    return label | dict(valid=True, outcome="valid answer") | _to_english(p, a, b)


def _answer(s: Settings, pair: str, news_id: int, system: str, user: str, schema: dict | None = None, check=parse_label):
    """The saved answer to this question, or a new one (saved if it arrived). If the reasoning does not stop within
    MAX_TOKENS, the same question without reasoning. Returns answer, file, error and whether there was a fallback."""
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
        raise ValueError(f"the verification contains no JSON object (finish_reason {raw['choices'][0].get('finish_reason')!r})")
    a = json.loads(text[start:end + 1])
    if a.get("risposta") not in ("si", "no"):
        raise ValueError(f"invalid verification answer: {a.get('risposta')!r}")
    return a


def verify_label(signal: dict, label: dict, s: Settings) -> dict:
    """Second question, only for a structural fact on just one of the two stocks: is the company really part of the fact?
    A 4B model often confuses the company the news is linked to with the one it talks about (Yum! selling Pizza Hut, linked to PEP).
    If the verification says no, the news item becomes noise; if the verification fails, it stays structural and the signal is blocked."""
    a, b = signal["ticker_A"], signal["ticker_B"]
    if not (label.get("source") == "model" and label.get("valid") and label.get("kind") == "structural" and label.get("about") in (a, b)):
        return label
    side = "A" if label["about"] == a else "B"
    body = "\n".join(x for x in label["text_shown"].splitlines() if x.startswith(("Headline:", "Summary:")))
    if s.anonymize and f"Company {side}" not in body:
        # with hidden names the company appears only as "Company A/B": if headline and summary do not name it, the fact is about others
        # (the model gets it wrong even with the explicit instruction, for example "Nvidia (Company A)"). It holds as long as ALIASES covers the names.
        return label | dict(verification="no", verification_rationale=f"rule: headline and summary do not name Company {side}", kind="noise",
                            subtype_before=label["subtype"], subtype="other")
    names = NAMES_HIDDEN if s.anonymize else NAMES_SHOWN.format(a=a, b=b)
    system = VERIFY_SYSTEM.format(sub=SUBTYPE_MODEL[label["subtype"]], side=side, names=names)   # the model sees its own (Italian) subtype
    saved, f, error, fallback = _answer(s, signal["pair"], label["news_id"], system, label["text_shown"], verify_schema(), parse_verify)
    if saved is None:
        return label | dict(verification="error", verification_rationale=error)
    try:
        v = parse_verify(saved["response"])
    except (ValueError, KeyError, IndexError, TypeError) as e:
        return label | dict(verification="invalid", verification_rationale=str(e)[:200], verification_cache=f.name)
    answer = VERIFY_EN[v["risposta"]]
    out = label | dict(verification=answer, verification_rationale=str(v.get("motivo", "")).strip(), verification_cache=f.name, verification_fallback=fallback)
    if answer == "no":
        out |= dict(kind="noise", subtype_before=label["subtype"], subtype="other")
    return out


# ---------------------------------------------------------------- decision rule

def apply_rule(signal: dict, labels: list[dict], search_error: str = "") -> dict:
    """From the classifications to the decision for versions B and C. It is the same for the agent and for the hand classification."""
    a, b = signal["ticker_A"], signal["ticker_B"]
    out = dict(decision="enter", size=1.0, decision_C="enter", follow_side="", ticker="none", category="no_news", reason="",
               news_direction="", news_id=None, structural_on_moved_leg=None, n_news=len(labels),
               n_lists=sum(lab.get("subtype") == "list" and lab.get("source") == "rule" for lab in labels), outcome="no news")
    if search_error:
        return out | dict(decision="block", decision_C="block", category="error", outcome="error", reason=f"search failed: {search_error}"[:200])
    if not labels:
        return out | dict(reason="no news in the window before the signal")
    bad = [lab for lab in labels if not lab["valid"]]
    if bad:
        outcome = "error" if any(lab["outcome"] == "error" for lab in bad) else "invalid answer"
        return out | dict(decision="block", decision_C="block", category="error", outcome=outcome, news_id=bad[0]["news_id"],
                          reason=f"{len(bad)} news items without a valid classification: {bad[0].get('error', '')}"[:200])
    out["outcome"] = "valid answer" if any(lab["source"] != "rule" for lab in labels) else "lists only"

    hits = {a: [], b: []}
    for lab in labels:
        if lab["kind"] == "structural":
            for t in (a, b) if lab["about"] == "both" else (lab["about"],) if lab["about"] in hits else ():
                hits[t].append(lab)
    hit = [t for t in (a, b) if hits[t]]
    if len(hit) == 1:
        x = hit[0]
        y = b if x == a else a
        items = sorted(hits[x], key=lambda lab: lab["minutes_before"])   # the closest to the signal first
        dirs = {lab["news_direction"] for lab in items}
        d = dirs.pop() if len(dirs) == 1 else "uncertain"
        out |= dict(decision="block", decision_C="block", ticker=x, category="structural", reason=items[0]["rationale"], news_direction=d,
                    news_id=items[0]["news_id"], structural_on_moved_leg=x == signal["most_moved_leg"])
        rel = signal["ret_A_30m"] - signal["ret_B_30m"] if x == a else signal["ret_B_30m"] - signal["ret_A_30m"]   # move of x against y
        if (d == "positive" and rel > 0) or (d == "negative" and rel < 0):
            side = {x: "long" if d == "positive" else "short", y: "short" if d == "positive" else "long"}
            out |= dict(decision_C="follow", follow_side=f"{side[a]} {a} / {side[b]} {b}")
        return out

    relevant = [lab for lab in labels if lab["about"] != "none" and lab["subtype"] != "list"]
    size = SIZE_REDUCED if relevant else 1.0
    if hit:
        first = min((lab for t in hit for lab in hits[t]), key=lambda lab: lab["minutes_before"])
        return out | dict(category="structural", ticker="both", size=size, news_id=first["news_id"],
                          reason=f"structural facts on both stocks, the spread has no reason to stay open: {first['rationale']}"[:300])
    kinds = pd.Series([lab["subtype"] for lab in labels]).value_counts()
    return out | dict(category="noise", ticker="none", size=size, reason="noise only: " + ", ".join(f"{k} {v}" for k, v in kinds.items()))


# ---------------------------------------------------------------- the graph

class State(TypedDict, total=False):
    signal: dict
    news: list[dict]
    search_error: str
    labels: list[dict]
    result: dict


def build_graph(s: Settings):
    """search -> classify -> verify -> decide -> record. Without news, or if the search fails, it goes straight to decide."""
    def search(state: State) -> State:
        sig = state["signal"]
        try:
            return {"news": search_news(sig["ticker_A"], sig["ticker_B"], sig["t_signal"], s.hours), "search_error": ""}
        except Exception as e:   # any failure of the search leads to blocking, by rule
            return {"news": [], "search_error": f"{type(e).__name__}: {e}"[:200]}

    def classify(state: State) -> State:
        return {"labels": [classify_news(state["signal"], item, s) for item in state["news"]]}

    def verify(state: State) -> State:
        return {"labels": [verify_label(state["signal"], lab, s) for lab in state["labels"]]}

    def decide(state: State) -> State:
        result = apply_rule(state["signal"], state.get("labels", []), state.get("search_error", ""))
        answered = [lab["answered_at"] for lab in state.get("labels", []) if lab.get("answered_at")]
        return {"result": dict(signal_id=state["signal"]["signal_id"]) | result | dict(
            model=s.model, answered_at=max(answered) if answered else "", hours=s.hours, reasoning=s.reasoning, anonymized=s.anonymize)}

    def record(state: State) -> State:
        sig = state["signal"]
        f = s.run_dir / f"signal_{int(sig['signal_id']):05d}.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        log = dict(settings=asdict(s) | dict(max_symbols_list=MAX_SYMBOLS_LIST, retries=RETRIES), written_at=pd.Timestamp.now().isoformat(timespec="seconds"),
                   signal=sig, search_error=state.get("search_error", ""), news=state.get("news", []), labels=state.get("labels", []), result=state["result"])
        f.write_text(json.dumps(log, ensure_ascii=False, indent=1, default=str))
        return {}

    g = StateGraph(State)
    for name, fn in (("search", search), ("classify", classify), ("verify", verify), ("decide", decide), ("record", record)):
        g.add_node(name, fn)
    g.add_edge(START, "search")
    g.add_conditional_edges("search", lambda st: "classify" if st["news"] and not st["search_error"] else "decide", ["classify", "decide"])
    g.add_edge("classify", "verify")
    g.add_edge("verify", "decide")
    g.add_edge("decide", "record")
    g.add_edge("record", END)
    return g.compile()


def _signal_dict(row: pd.Series) -> dict:
    """A row of the signal table as a dictionary, with the signal parameters (they end up in the log, the agent does not use them)."""
    return {k: (v.item() if isinstance(v, np.generic) else v) for k, v in row.items()}


def run(s: Settings, signal_ids: list[int] | None = None, verbose: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per signal with the decision and one row per (signal, news item) with the classification."""
    signals = load_trades()   # refuses the table if it contains trades after TRAIN_END
    if signal_ids is not None:
        signals = signals[signals.signal_id.isin(signal_ids)]
    if verbose:
        todo = {_cache_file(s, sig.pair, item["news_id"], *build_messages(sig.pair, sig.ticker_A, sig.ticker_B, item, s.anonymize))
                for sig in signals.itertuples() for item in search_news(sig.ticker_A, sig.ticker_B, sig.t_signal, s.hours) if item["n_symbols"] <= MAX_SYMBOLS_LIST}
        new = sum(not f.exists() for f in todo)
        print(f"{len(signals)} signals, {len(todo)} news items to classify, {new} without a saved answer "
              f"(estimate {new * (70 if s.reasoning else 4) / 60:.0f} minutes)", flush=True)
    graph = build_graph(s)
    rows, labels, t0 = [], [], time.time()
    for i, (_, row) in enumerate(signals.iterrows(), 1):
        out = graph.invoke({"signal": _signal_dict(row)})
        rows.append(out["result"])
        labels += [dict(signal_id=row.signal_id, pair=row.pair) | lab for lab in out.get("labels", [])]
        r = out["result"]
        if verbose and r["outcome"] != "no news":
            why = "" if r["outcome"] in ("valid answer", "lists only") else f": {r['reason']}"
            print(f"[{i}/{len(signals)} {time.time() - t0:.0f}s] signal {row.signal_id} {row.pair} {row.t_signal:%Y-%m-%d %H:%M}: "
                  f"{r['decision']} / C {r['decision_C']} ({r['category']}, {r['outcome']}{why})", flush=True)
    return pd.DataFrame(rows), pd.DataFrame(labels)


def load_decisions(path=AGENT_DECISIONS) -> pd.DataFrame:
    """The decision table, in the format that `backtest.apply_version(trades, "B", decisions)` reads as it is.
    For a variant: load_decisions(<run folder>/decisions.csv)."""
    if not path.exists():
        raise FileNotFoundError(f"{path.name} is missing: from the project folder run `uv run python -m src.agent_variants.agent`")
    return pd.read_csv(path)


# ---------------------------------------------------------------- hand classification and agreement

MANUAL_FIELDS = ["manual_about", "manual_subtype", "manual_news_direction", "manual_notes"]


def make_manual_sample(s: Settings, n: int = 40, seed: int = 0) -> pd.DataFrame:
    """Blind sample for the hand classification: n signals with at least one news item that is not a list, spread
    over the pairs, one row per news item, without any agent column. The group fills in the manual_* columns."""
    if AGENT_MANUAL.exists():
        raise SystemExit(f"{AGENT_MANUAL.name} already exists and may contain hand classifications: move or delete it yourself, then run again.")
    signals = load_trades()
    rows = []
    for sig in signals.itertuples():
        for item in search_news(sig.ticker_A, sig.ticker_B, sig.t_signal, s.hours):
            if item["n_symbols"] <= MAX_SYMBOLS_LIST:
                rows.append(dict(signal_id=sig.signal_id, pair=sig.pair, ticker_A=sig.ticker_A, ticker_B=sig.ticker_B, t_signal=sig.t_signal,
                                 direction=sig.direction, most_moved_leg=sig.most_moved_leg, news_id=item["news_id"], news_ts=item["ts"],
                                 minutes_before=item["minutes_before"], n_symbols=item["n_symbols"],
                                 tagged="+".join(t for t, m in ((sig.ticker_A, item["mentions_A"]), (sig.ticker_B, item["mentions_B"])) if m),
                                 headline=item["headline"], summary=item["summary"], url=item["url"]))
    pool = pd.DataFrame(rows)
    rng = np.random.default_rng(seed)
    per_pair = {p: list(rng.permutation(g.signal_id.unique())) for p, g in pool.groupby("pair")}
    chosen = []
    while len(chosen) < n and any(per_pair.values()):   # in turn across the pairs, so each pair has 2-3 signals
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
    """Agreement beyond chance between two classifications: 1 perfect agreement, 0 like drawing lots with the same frequencies."""
    x, y = x.astype(str).reset_index(drop=True), y.astype(str).reset_index(drop=True)
    po = (x == y).mean()
    pe = sum(x.eq(k).mean() * y.eq(k).mean() for k in set(x) | set(y))
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def agreement(s: Settings) -> pd.DataFrame:
    """Compares the sample filled in by the group with the agent: share of agreement and kappa per news item (what it is about,
    kind, subtype, direction) and per signal (B and C decision, with the same rule applied to the group's labels)."""
    if not AGENT_MANUAL.exists():
        raise SystemExit(f"{AGENT_MANUAL.name} is missing: create it with `uv run python -m src.agent_variants.agent --sample 40` and have the group fill it in")
    m = pd.read_csv(AGENT_MANUAL, dtype={c: str for c in MANUAL_FIELDS}).fillna({c: "" for c in MANUAL_FIELDS})
    for c in MANUAL_FIELDS[:3]:
        m[c] = m[c].str.strip()
    m = m[m.manual_subtype != ""]
    if m.empty:
        raise SystemExit(f"{AGENT_MANUAL.name} has no filled-in rows yet (column manual_subtype)")
    m["manual_about"] = [{"A": r.ticker_A, "B": r.ticker_B}.get(r.manual_about, r.manual_about) for r in m.itertuples()]
    for c, allowed in (("manual_subtype", SUBTYPES), ("manual_news_direction", NEWS_DIRECTIONS)):
        bad = m[~m[c].isin(allowed)]
        if len(bad):
            raise SystemExit(f"{c}: invalid values {sorted(set(bad[c]))} (rows {list(bad.index[:5] + 2)}); allowed: {', '.join(allowed)}")
    bad = m[[r.manual_about not in (r.ticker_A, r.ticker_B, "both", "none") for r in m.itertuples()]]
    if len(bad):
        raise SystemExit(f"manual_about: invalid values {sorted(set(bad.manual_about))}; allowed: A, B, the ticker, both, none")
    m["manual_kind"] = np.where(m.manual_subtype.isin(STRUCTURAL), "structural", "noise")

    ids = sorted(m.signal_id.unique())
    decisions, labels = run(s, ids, verbose=False)
    model_labels = labels[labels.source == "model"]
    news = m.merge(model_labels, on=["signal_id", "news_id"], how="inner", suffixes=("", "_agent"))
    lines = [dict(level="news", field=c, n=len(news), agreement=(news[f"manual_{c}"] == news[c]).mean(), kappa=cohen_kappa(news[f"manual_{c}"], news[c]))
             for c in ("about", "kind", "subtype", "news_direction") if len(news)]

    trades = load_trades().set_index("signal_id")
    human = []
    for sid in ids:
        sig = _signal_dict(trades.loc[sid].copy()) | dict(signal_id=sid)
        own = [dict(news_id=r.news_id, minutes_before=r.minutes_before, source="manual", valid=True, outcome="manual", about=r.manual_about,
                    subtype=r.manual_subtype, kind=r.manual_kind, news_direction=r.manual_news_direction, rationale=r.manual_notes or "hand classification")
               for r in news[news.signal_id == sid].itertuples()]
        rule = [lab for lab in labels[(labels.signal_id == sid) & (labels.source == "rule")].to_dict("records")]
        human.append(dict(signal_id=sid) | {f"manual_{k}": v for k, v in apply_rule(sig, own + rule).items() if k in ("decision", "decision_C", "category")})
    sig_cmp = pd.DataFrame(human).merge(decisions, on="signal_id")
    lines += [dict(level="signal", field=c, n=len(sig_cmp), agreement=(sig_cmp[f"manual_{c}"] == sig_cmp[c]).mean(), kappa=cohen_kappa(sig_cmp[f"manual_{c}"], sig_cmp[c]))
              for c in ("decision", "decision_C", "category")]
    table = pd.DataFrame(lines)

    s.run_dir.mkdir(parents=True, exist_ok=True)
    keep = ["signal_id", "pair", "news_id", "headline", "manual_about", "about", "manual_subtype", "subtype", "manual_news_direction", "news_direction",
            "rationale", "manual_notes"]
    news[(news.manual_kind != news.kind) | (news.manual_about != news.about)][keep].to_csv(s.run_dir / "news_disagreements.csv", index=False)
    sig_cmp.to_csv(s.run_dir / "signal_agreement.csv", index=False)
    table.to_csv(s.run_dir / "agreement.csv", index=False)
    return table


# ---------------------------------------------------------------- terminal

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", default=env("AGENT_MODEL"), help="name of the model on the server (default: AGENT_MODEL in .env)")
    ap.add_argument("--base-url", default=env("AGENT_BASE_URL", BASE_URL), help=f"server address (default: AGENT_BASE_URL in .env, otherwise {BASE_URL})")
    ap.add_argument("--hours", type=int, default=WINDOW_H, help="hours of news before the signal")
    ap.add_argument("--reasoning", choices=["on", "off"], default="off", help="on: the model reasons before answering (about 70 s per news item); off: it answers at once (about 4 s)")
    ap.add_argument("--real-names", action="store_true", help="lookahead check: the model sees the real names of the companies")
    ap.add_argument("--signals", help="only these signal_ids, comma separated: trial, does not write the table")
    ap.add_argument("--sample", type=int, metavar="N", help="draws N signals to classify by hand and stops")
    ap.add_argument("--agreement", action="store_true", help="agreement between the hand classification and the agent")
    a = ap.parse_args()
    if not a.model and not a.sample:
        raise SystemExit("The model name is missing: write AGENT_MODEL in .env or use --model")
    s = Settings(model=a.model, base_url=normalize_url(a.base_url), hours=a.hours, reasoning=a.reasoning == "on", anonymize=not a.real_names)

    if a.sample:
        sample = make_manual_sample(s, a.sample)
        print(f"saved data/processed/{AGENT_MANUAL.name}: {sample.signal_id.nunique()} signals, {len(sample)} news items (lists excluded).\n"
              f"For each row fill in manual_about (A, B, both, none), manual_subtype ({', '.join(SUBTYPES)}),\n"
              f"manual_news_direction ({', '.join(NEWS_DIRECTIONS)}) and, if needed, manual_notes. Then: uv run python -m src.agent_variants.agent --agreement")
        raise SystemExit
    if a.agreement:
        print(agreement(s).to_string(index=False, float_format=lambda x: f"{x:.2f}"))
        print(f"details in {s.run_dir.relative_to(AGENT_RAW.parents[2])}/: agreement.csv, signal_agreement.csv, news_disagreements.csv")
        raise SystemExit

    ids = [int(x) for x in a.signals.split(",")] if a.signals else None
    out, labels = run(s, ids)
    print(f"\n{len(out)} signals | B: " + ", ".join(f"{k} {v}" for k, v in out.decision.value_counts().items())
          + " | C: " + ", ".join(f"{k} {v}" for k, v in out.decision_C.value_counts().items())
          + " | " + ", ".join(f"{k} {v}" for k, v in out.outcome.value_counts().items()))
    if ids is not None:
        print(out[["signal_id", "decision", "decision_C", "size", "ticker", "category", "news_direction", "n_news", "outcome", "reason"]].to_string(index=False))
    else:
        s.run_dir.mkdir(parents=True, exist_ok=True)
        out.to_csv(s.run_dir / "decisions.csv", index=False)
        labels.to_csv(s.run_dir / "classifications.csv", index=False)
        print(f"saved {s.run_dir.relative_to(AGENT_RAW.parents[2])}/decisions.csv and classifications.csv")
        if s.is_main():
            out.to_csv(AGENT_DECISIONS, index=False)
            print(f"saved data/processed/{AGENT_DECISIONS.name}")
        else:
            print("variant: the main table was not touched")
        n_err = int((out.outcome == "error").sum())
        if n_err:
            print(f"WARNING: {n_err} signals blocked because the server did not answer. Run the same command again: it repeats only those calls.")
