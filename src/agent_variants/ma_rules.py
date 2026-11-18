"""Variant 11 (point 1): finds the M&A news and, with text rules, the stage (definitive, talks, completed, approval)
and the role of each of the 30 stocks (target, buyer, mentioned). The rules are those written in LOG.md.

It takes no decisions on the signals: it writes the list to check it and for the hand classification (columns manual_stage, manual_role, manual_notes).
Output: Results/agent_variants/ma_rules/ma_news.csv. Usage: uv run python -m src.agent_variants.ma_rules
"""
import re
import pandas as pd

from src.config import NEWS, RESULTS, VARIANTS

OUT = VARIANTS / "ma_rules/ma_news.csv"
MAX_SYMBOLS = 3

# names with which the companies appear in the headlines (besides the ticker)
ALIASES = {
    "MA": ["Mastercard"], "V": ["Visa"], "CSX": ["CSX"], "UNP": ["Union Pacific"], "PYPL": ["PayPal"], "XYZ": ["Block", "Square"],
    "HD": ["Home Depot"], "LOW": ["Lowe's", "Lowes"], "DHR": ["Danaher"], "TMO": ["Thermo Fisher"], "CRM": ["Salesforce"], "WDAY": ["Workday"],
    "JPM": ["JPMorgan", "JP Morgan", "Chase"], "WFC": ["Wells Fargo"], "NXPI": ["NXP"], "TXN": ["Texas Instruments"], "ELV": ["Elevance"],
    "UNH": ["UnitedHealth", "Optum"], "CL": ["Colgate"], "PG": ["Procter", "P&G"], "GS": ["Goldman"], "MS": ["Morgan Stanley"],
    "ISRG": ["Intuitive Surgical", "Intuitive"], "SYK": ["Stryker"], "KO": ["Coca-Cola", "Coke"], "PEP": ["PepsiCo", "Pepsi"],
    "BAC": ["Bank of America", "BofA"], "C": ["Citigroup", "Citi"], "COP": ["ConocoPhillips", "Conoco"], "EOG": ["EOG"],
}

MA_RE = re.compile(r"\b(acqui(re|res|red|ring|sition|sitions)|merg(er|ers|e|es|ing)|takeover|take-over|buyout|buy-out|deal to buy|bid for|"
                   r"offer for|tender offer|go(es|ing)? private|take private|to be (acquired|bought)|sells? .{0,40} to|sale of)\b", re.I)
DEFINITIVE_RE = re.compile(r"\b(definitive (agreement|deal)|agree[ds]? to (acquire|buy|be acquired|be bought|merge|sell)|to be acquired by|"
                           r"per share|all-cash|all-stock|cash-and-stock|signs? (a )?deal|announce[ds]? (a )?deal)\b", re.I)
TALKS_RE = re.compile(r"\b(in talks|talks (to|with)|exploring|explores?|considering|considers?|weigh(s|ing)?|reportedly|report(s|ed)?\b|"
                      r"people familiar|sources|approach(ed|es)?|bid|offer|interest(ed)? in|could|may|might|potential|rumou?r\w*|proposal|propos(e|ed|es))\b", re.I)
COMPLETED_RE = re.compile(r"\b(complete[sd]?|completion|close[sd]? (the |its )?(acquisition|deal|merger|sale)|closing of)\b", re.I)
APPROVAL_RE = re.compile(r"\b(approv(al|es|ed)|clearance|clears?|cleared|antitrust|regulator\w*|commission)\b", re.I)


def alias_re(t: str) -> str:
    names = [re.escape(n) for n in ALIASES[t]] + [rf"\({re.escape(t)}\)", rf"\$?{re.escape(t)}\b(?=[^a-z])"] if len(t) > 1 else [re.escape(n) for n in ALIASES[t]]
    return "(" + "|".join(names) + ")"


def role(t: str, text: str) -> str:
    n = alias_re(t)
    target = (rf"\b(acquire[sd]?|acquiring|buy(s|ing)?|purchase[sd]?|takeover of|bid for|offer for|deal for|acquisition of|take)\s+(the\s+)?(\w+\s+){{0,3}}{n}"
              rf"|{n}[^.]{{0,40}}\b(to be acquired|agrees? to be acquired|to be bought|sold to|to sell itself|explores? (a )?sale|go(es|ing)? private|takeover target)")
    buyer = rf"{n}[^.]{{0,40}}\b(to acquire|acquires|acquired|agrees? to (acquire|buy)|will acquire|buys|to buy|bought|makes? (an? )?(offer|bid)|bids|completes? (the |its )?acquisition)"
    if re.search(target, text, re.I):
        return "target"
    if re.search(buyer, text, re.I):
        return "buyer"
    return "mentioned"


def stage(text: str) -> str:
    if COMPLETED_RE.search(text):
        return "completed"
    if APPROVAL_RE.search(text) and not DEFINITIVE_RE.search(text):
        return "approval"
    if TALKS_RE.search(text):
        return "talks"               # if both definitive and uncertain words appear, it counts as talks
    if DEFINITIVE_RE.search(text):
        return "definitive"
    return "unclear"


news = pd.read_parquet(NEWS)
tickers = [c.removeprefix("mentions_") for c in news.columns if c.startswith("mentions_")]
news["text"] = (news.headline.fillna("") + ". " + news.summary.fillna("")).str.strip()
cand = news[(news.n_symbols <= MAX_SYMBOLS) & news[[f"mentions_{t}" for t in tickers]].any(axis=1) & news.text.str.contains(MA_RE)].copy()

rows = []
for r in cand.itertuples():
    mentioned = [t for t in tickers if getattr(r, f"mentions_{t}")]
    roles = {t: role(t, r.text) for t in mentioned}
    rows.append(dict(id=r.id, ts=r.ts, tickers=",".join(mentioned), stage=stage(r.text), roles="; ".join(f"{t}={v}" for t, v in roles.items()),
                     target=",".join(t for t, v in roles.items() if v == "target"), headline=r.headline, summary=(r.summary or "")[:300],
                     manual_stage="", manual_role="", manual_notes=""))
out = pd.DataFrame(rows).sort_values("ts").reset_index(drop=True)
OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT, index=False)
print(f"{len(news)} news items | targeted on one of the 30 stocks (at most {MAX_SYMBOLS} tickers) with M&A words: {len(out)}")
print("stage:", out.stage.value_counts().to_dict())
print("with a target among the 30 stocks:", (out.target != "").sum(), "| definitive with a target:", ((out.stage == "definitive") & (out.target != "")).sum())
print(f"saved {OUT.relative_to(RESULTS.parent)}")
