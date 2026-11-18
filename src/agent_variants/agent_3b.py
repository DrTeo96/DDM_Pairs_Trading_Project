"""News agent, version B (can only block), for the 15 pairs of version 2. Step 5 of the plan.

For each signal Python looks up the news of the two stocks published BEFORE the signal, in a window of hours; a local LLM (Llama 3.2 3B by default, via Ollama)
classifies them by filling in only the facts (category, stock involved, whether the news explains the widening, permanence...); the decision is computed by
the code with a fixed table and, for every block, a keyword check on the text. The model sees no prices, returns or trade results.
Ollama must be running with the model downloaded (`ollama pull llama3.2:3b`). No new libraries are needed: requests use the standard library.
From the terminal, in the project folder:
    uv run python -m src.agent_variants.agent_3b --dry-run --limit 5      prints the prompts of 5 signals without calling the model
    uv run python -m src.agent_variants.agent_3b --limit 20               calls the model on 20 signals (trial)
    uv run python -m src.agent_variants.agent_3b                          all the 973 train signals, 6-hour window, full prompt
    uv run python -m src.agent_variants.agent_3b --hours 24               robustness check with 24 hours
    uv run python -m src.agent_variants.agent_3b --prompt simple          the first prompt (simple categories), for the comparison
    uv run python -m src.agent_variants.agent_3b --model llama3.1:8b      another model (separate answer file)
The answers are saved one at a time: with the default settings (6 hours, llama3.2:3b, full prompt) in
Results/agent_variants/3b_6h/decisions.csv (DEC_3B_6H in config.py), with the others in data/processed/agent_decisions_v2_<hours>h_<model>_<prompt>.csv.
If it stops, launching it again restarts from where it had arrived.
The file has the columns signal_id and decision ('enter' or 'block'), those expected by backtest.apply_version("B", ...).

The prompts below are the ones the recorded decisions were produced with, and are kept exactly as they were: they ask the model
for a `reason` in Italian, so that column holds the model's own Italian sentence.

Rules (plan, Step 5):
- no news in the window: 'enter', without calling the model;
- it blocks only with a structural news item that explains the widening of the spread (table in decide_full); 'enter_reduced' is saved in decision_full but in version B counts as 'enter';
- every block also needs an event word in the text of the news: if it is missing, the block falls;
- if the model or the answer fail: 'block' (safety rule), with the error written in the `error` column;
- the agent does not change direction, thresholds, size or exit.
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
MODEL = "llama3.2:3b"           # Llama 3.1 8B (4.9 GB) does not fit in the 8 GB of the Mac: it swaps and takes minutes per signal. Another model: --model
PROMPT = "full"
WINDOW_HOURS = 6              # the group's decision: 6 hours, with 24 hours as a robustness check declared in advance
GENERIC_MIN_TICKERS = 6       # the group's decision: a news item with 6 tickers or more is "generic" (lists of stocks); it stays visible, with the flag
MAX_HEADLINES = 15            # cap on the news in the prompt (the most recent ones), so as not to exceed the model context
MAX_SUMMARY = 300             # characters of the summary of each news item
MAX_PROMPT_CHARS = 4500       # cap on the user message (about 1300 tokens): with the instructions and the answer it fits in the 4096 tokens of the context
NUM_CTX = 4096
LAST_TRAIN_DAY = pd.Timestamp("2026-09-16 23:59:59")   # the test (from 17 September) is not read
TIMEOUT = 180                 # seconds for an answer (the first call loads the model in memory)
RETRIES = 2

# signal fields the agent can see. The other columns (exit, exit prices, 30-minute returns, profit) are the future: never in the prompt
SIGNAL_FIELDS = ["signal_id", "pair", "ticker_A", "ticker_B", "t_signal", "direction", "most_moved_leg", "z_signal"]

# the model was trained before 2024: we give it the names, because it would not know tickers like XYZ (Block)
NAMES = {
    "MA": "Mastercard", "V": "Visa", "CSX": "CSX Corp", "UNP": "Union Pacific", "PYPL": "PayPal", "XYZ": "Block Inc (ex Square)",
    "HD": "Home Depot", "LOW": "Lowe's", "DHR": "Danaher", "TMO": "Thermo Fisher Scientific", "CRM": "Salesforce", "WDAY": "Workday",
    "JPM": "JPMorgan Chase", "WFC": "Wells Fargo", "NXPI": "NXP Semiconductors", "TXN": "Texas Instruments", "ELV": "Elevance Health",
    "UNH": "UnitedHealth Group", "CL": "Colgate-Palmolive", "PG": "Procter & Gamble", "GS": "Goldman Sachs", "MS": "Morgan Stanley",
    "ISRG": "Intuitive Surgical", "SYK": "Stryker", "KO": "Coca-Cola", "PEP": "PepsiCo", "BAC": "Bank of America", "C": "Citigroup",
    "COP": "ConocoPhillips", "EOG": "EOG Resources",
}

# columns of the decision file: if an existing file has others (previous version of the code) it refuses to append rows
COLUMNS = ["signal_id", "pair", "t_signal", "window_hours", "model", "prompt", "n_news", "news_ids", "decision", "decision_full", "category", "affected_ticker",
           "explains_divergence", "permanence", "confidence", "flags", "relevant_news_id", "keyword_ok", "evidence", "evidence_ok", "reason", "error"]

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------
# Simple prompt: simple categories (structural_one, both, noise, none). It blocks with structural_one. Kept for the comparison (--prompt simple).
CATEGORIES_SIMPLE = ["structural_one", "both", "noise", "none"]
SYSTEM_SIMPLE = """You are a careful financial news analyst helping a pairs-trading strategy.
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
# Full prompt: adapted from a prompt proposed by the group. The model fills in only the facts; the decision table is in the code (decide_full).
CATEGORIES_FULL = ["no_news", "noise", "common_factor", "company_temporary", "structural", "earnings", "uncertain"]
FLAGS = ["headline_only", "generic_only", "earnings_today", "rumor", "stale_news", "conflicting_news", "guidance_change"]
SYSTEM_FULL = """ROLE
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

# words that must appear in the text of a news item for a block to stand (deterministic check on top of the model's judgement)
EVENT_RE = re.compile(r"\b(acqui\w*|merg\w*|takeover|buyout|divest\w*|spin-?off|investigat\w*|probe|subpoena\w*|lawsuit|sues|sued|settle\w*|fraud\w*|recall\w*|bankrupt\w*|"
                      r"chapter 11|resign\w*|steps? down|ousted|fired|retire\w*|new (ceo|cfo)|appoint\w*|names? (a )?(new )?(ceo|cfo)|delist\w*|going private)\b", re.I)
_UP_DOWN = r"(cut|cuts|lower\w*|slash\w*|rais\w*|boost\w*|hike\w*|increas\w*|reduc\w*|withdr\w*|suspend\w*)"
GUIDANCE_RE = re.compile(rf"\b(guidance|outlook|forecast)\b.*\b{_UP_DOWN}\b|\b{_UP_DOWN}\b.*\b(guidance|outlook|forecast)\b", re.I | re.S)


def company(t: str) -> str:
    return f"{NAMES[t]} ({t})"


def select_news(sig: pd.Series, news: pd.DataFrame, hours: float) -> pd.DataFrame:
    """News of the two stocks published in the window that ENDS at the signal time: ts <= t_signal and ts > t_signal - hours.
    It uses `ts` (created_at), never updated_at_ny, which can be much later (lookahead). At most MAX_HEADLINES, the most recent ones."""
    t = pd.Timestamp(sig["t_signal"])
    if t > LAST_TRAIN_DAY:
        raise ValueError(f"signal {sig['signal_id']} after 16 September: the test is not used")
    m = news[f"mentions_{sig['ticker_A']}"] | news[f"mentions_{sig['ticker_B']}"]
    w = news[m & (news.ts <= t) & (news.ts > t - pd.Timedelta(hours=hours))]
    return w.sort_values("ts").tail(MAX_HEADLINES)


def build_prompt_simple(sig: pd.Series, window: pd.DataFrame) -> str:
    a, b, mover = sig["ticker_A"], sig["ticker_B"], sig["most_moved_leg"]
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
    """'long COP / short EOG' -> long_a_short_b (A is the first stock of the pair)."""
    return "long_a_short_b" if str(sig["direction"]).startswith(f"long {sig['ticker_A']}") else "short_a_long_b"


def build_prompt_full(sig: pd.Series, window: pd.DataFrame) -> str:
    """Input in JSON. decision_time = signal_bar_close = t_signal: no news after the signal."""
    t = pd.Timestamp(sig["t_signal"])
    items = []
    for i, (_, r) in enumerate(window.iterrows()):
        items.append({"index": i, "time": f"{r['ts']:%Y-%m-%d %H:%M}", "minutes_before": int((t - r["ts"]).total_seconds() // 60), "headline": r["headline"],
                      "summary": (r["summary"] or "")[:MAX_SUMMARY].replace("\n", " "), "source": r["source"], "symbols": r["symbols"],
                      "generic": bool(r["n_symbols"] >= GENERIC_MIN_TICKERS)})
    a, b = sig["ticker_A"], sig["ticker_B"]
    return json.dumps({"signal_id": int(sig["signal_id"]), "ticker_a": a, "name_a": NAMES[a], "ticker_b": b, "name_b": NAMES[b], "direction": direction_ab(sig),
                       "z": round(float(sig["z_signal"]), 2), "signal_bar_close": f"{t:%Y-%m-%d %H:%M}", "decision_time": f"{t:%Y-%m-%d %H:%M}", "news": items}, ensure_ascii=False)


def schema_simple(a: str, b: str) -> dict:
    return {"type": "object", "required": ["category", "company", "evidence", "reason"], "additionalProperties": False,
            "properties": {"category": {"type": "string", "enum": CATEGORIES_SIMPLE}, "company": {"type": "string", "enum": [a, b, "none"]}, "evidence": {"type": "string"}, "reason": {"type": "string"}}}


def schema_full() -> dict:
    s = lambda *vals: {"type": "string", "enum": list(vals)}   # noqa: E731
    props = {"news_category": s(*CATEGORIES_FULL), "relevant_news_index": {"type": "integer"}, "affected_ticker": s("A", "B", "both", "none"),
             "explains_divergence": s("yes", "partly", "no", "unknown"), "permanence": s("temporary", "permanent", "unclear"), "confidence": s("low", "medium", "high"),
             "flags": {"type": "array", "items": s(*FLAGS)}, "evidence": {"type": "string"}, "reason": {"type": "string"}}
    return {"type": "object", "required": list(props), "additionalProperties": False, "properties": props}


def chat(model: str, system: str, user: str, fmt: dict) -> dict:
    """One call to Ollama, with a JSON answer constrained by the schema, temperature 0 and fixed seed (repeatable answers)."""
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


def decide_simple(category: str) -> str:
    """Simple prompt: it blocks only with a structural news item on a single stock."""
    return "block" if category == "structural_one" else "enter"


def decide_full(out: dict, window: pd.DataFrame) -> tuple[str, object]:
    """Decision table (the group's decision). Returns (decision_full, keyword_ok): decision_full is enter, enter_reduced or block;
    keyword_ok is None if there is no block to check, otherwise True/False. A block without event words in the text falls."""
    cat, flags = out["news_category"], set(out["flags"])
    explains = out["explains_divergence"] in ("yes", "partly")
    i = out["relevant_news_index"]
    rel = window.iloc[[i]] if 0 <= i < len(window) else window                    # if the index is not valid the whole window is checked
    text = " ".join(rel["headline"] + " " + rel["summary"].fillna(""))
    if cat in ("no_news", "noise", "common_factor"):
        return "enter", None
    if cat == "company_temporary":
        return ("enter_reduced" if explains else "enter"), None
    if cat == "structural":
        full, regex = ("block" if explains else "enter_reduced"), EVENT_RE
    elif cat == "earnings":
        full, regex = ("block" if "guidance_change" in flags else "enter_reduced"), GUIDANCE_RE
    else:                                                                          # uncertain: only a rumour on acquisition, investigation or bankruptcy is blocked
        full, regex = ("block" if "rumor" in flags else "enter_reduced"), EVENT_RE
    if full != "block":
        return full, None
    ok = bool(regex.search(text))
    return ("block" if ok else "enter"), ok


def run_signal(sig: pd.Series, news: pd.DataFrame, hours: float, dry_run: bool = False, model: str = MODEL, prompt_version: str = PROMPT) -> dict:
    window = select_news(sig, news, hours)
    rec = {c: "" for c in COLUMNS}
    rec.update(signal_id=sig["signal_id"], pair=sig["pair"], t_signal=sig["t_signal"], window_hours=hours, model=model, prompt=prompt_version, n_news=len(window),
              news_ids=",".join(str(i) for i in window["id"]), decision="enter", decision_full="enter", category="no_news", evidence_ok=True)
    if window.empty:
        return rec
    build = build_prompt_full if prompt_version == "full" else build_prompt_simple
    prompt = build(sig, window)
    while len(prompt) > MAX_PROMPT_CHARS and len(window) > 1:     # the oldest news are dropped, never the instructions
        window = window.iloc[1:]
        prompt = build(sig, window)
    rec.update(n_news=len(window), news_ids=",".join(str(i) for i in window["id"]))
    if dry_run:
        print(f"\n===== signal {sig['signal_id']} =====\n{prompt}")
        rec["category"] = "dry_run"
        return rec
    a, b = sig["ticker_A"], sig["ticker_B"]
    try:
        if prompt_version == "simple":
            out = chat(model, SYSTEM_SIMPLE, prompt, schema_simple(a, b))
            if out["category"] not in CATEGORIES_SIMPLE:
                raise RuntimeError(f"unknown category: {out['category']}")
            rec.update(category=out["category"], evidence=out["evidence"], reason=out["reason"], decision=decide_simple(out["category"]))
            rec["decision_full"] = "block" if rec["decision"] == "block" else "enter"
            rec["affected_ticker"] = out["company"]
        else:
            out = chat(model, SYSTEM_FULL, prompt, schema_full())
            full, kw = decide_full(out, window)
            i = out["relevant_news_index"]
            rec.update(category=out["news_category"], affected_ticker=out["affected_ticker"], explains_divergence=out["explains_divergence"], permanence=out["permanence"],
                       confidence=out["confidence"], flags=",".join(out["flags"]), relevant_news_id=int(window.iloc[i]["id"]) if 0 <= i < len(window) else "",
                       keyword_ok=("" if kw is None else kw), evidence=out["evidence"], reason=out["reason"], decision_full=full, decision=("block" if full == "block" else "enter"))
        text = " ".join(window["headline"] + " " + window["summary"].fillna("")).lower()
        rec["evidence_ok"] = bool(rec["evidence"] in ("none", "") or rec["evidence"].strip().lower() in text)   # does the quotation really exist among the news?
    except (RuntimeError, KeyError, ValueError, TypeError) as e:
        rec.update(decision="block", decision_full="block", category="error", error=str(e)[:200])   # safety rule: if something fails, block
    return rec


def run(hours: float = WINDOW_HOURS, limit: int | None = None, dry_run: bool = False, model: str = MODEL, prompt_version: str = PROMPT) -> pd.DataFrame:
    sigs = pd.read_csv(SIGNALS)[SIGNAL_FIELDS]       # only the allowed fields: the rest of the file never reaches the model
    news = load_news(NEWS_PAIR)
    if (hours, model, prompt_version) == (WINDOW_HOURS, MODEL, PROMPT):
        out_path = DEC_3B_6H                                                       # the 3b_6h variant, on git
    else:                                                                          # one file per model and prompt: they are not mixed
        out_path = PROCESSED / f"agent_decisions_v2_{hours:g}h_{model.replace(':', '-')}_{prompt_version}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = pd.read_csv(out_path) if out_path.exists() and not dry_run else pd.DataFrame()
    if len(done) and list(done.columns) != COLUMNS:
        raise SystemExit(f"{out_path.name} has columns different from the current ones (it is from a previous version of the code): move or delete it and relaunch")
    if len(done) and (done.category == "error").any():
        # the rows in error (timeout, invalid answer) are a failure, not a judgement of the model: they are removed and redone
        print(f"{(done.category == 'error').sum()} signals in error from the previous run: redoing them")
        done = done[done.category != "error"]
        done.to_csv(out_path, index=False)
    todo = sigs[~sigs.signal_id.isin(done.get("signal_id", []))]
    if limit:
        todo = todo.head(limit)
    print(f"{len(sigs)} signals, {len(done)} already done, doing {len(todo)} (window {hours:g} hours, model {model}, prompt {prompt_version})")
    t0 = time.time()
    for i, (_, sig) in enumerate(todo.iterrows(), 1):
        rec = run_signal(sig, news, hours, dry_run, model, prompt_version)
        if not dry_run:
            pd.DataFrame([rec])[COLUMNS].to_csv(out_path, mode="a", header=not out_path.exists(), index=False)
            print(f"{i}/{len(todo)} signal {rec['signal_id']} {rec['pair']}: {rec['decision']} ({rec['category']}, {rec['n_news']} news) {time.time() - t0:.0f}s")
    return pd.read_csv(out_path) if out_path.exists() and not dry_run else pd.DataFrame()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hours", type=float, default=WINDOW_HOURS, help="news window in hours before the signal")
    ap.add_argument("--limit", type=int, help="at most N signals (for trials)")
    ap.add_argument("--model", default=MODEL, help="Ollama model (default: llama3.2:3b)")
    ap.add_argument("--prompt", default=PROMPT, choices=["simple", "full"], help="which prompt to use (default: full)")
    ap.add_argument("--dry-run", action="store_true", help="prints the prompts without calling the model and without saving")
    a = ap.parse_args()
    res = run(a.hours, a.limit, a.dry_run, a.model, a.prompt)
    if len(res):
        print(res.groupby(["category", "decision_full", "decision"]).size())
