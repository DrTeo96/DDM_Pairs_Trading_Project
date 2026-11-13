"""Variante 11 (punto 1): trova le notizie di M&A e, con regole sul testo, la fase (definitiva, trattativa, completata, approvazione)
e il ruolo di ogni titolo dei 30 (bersaglio, compratore, citata). Le regole sono quelle scritte in registro_varianti.md.

Non prende decisioni sui segnali: scrive la lista per controllarla e per la classificazione a mano (colonne mano_fase, mano_ruolo, mano_note).
Uscita: Results/varianti_agente/ma_regole/notizie_ma.csv. Uso: uv run python -m src.varianti_agente.ma_regole
"""
import re
import pandas as pd

from src.config import NEWS, RESULTS, VARIANTI

OUT = VARIANTI / "ma_regole/notizie_ma.csv"
MAX_SYMBOLS = 3

# nomi con cui le aziende compaiono nei titoli (oltre al ticker)
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
        return "bersaglio"
    if re.search(buyer, text, re.I):
        return "compratore"
    return "citata"


def stage(text: str) -> str:
    if COMPLETED_RE.search(text):
        return "completata"
    if APPROVAL_RE.search(text) and not DEFINITIVE_RE.search(text):
        return "approvazione"
    if TALKS_RE.search(text):
        return "trattativa"          # se compaiono sia parole definitive sia di incertezza vale trattativa
    if DEFINITIVE_RE.search(text):
        return "definitiva"
    return "non chiara"


news = pd.read_parquet(NEWS)
tickers = [c.removeprefix("mentions_") for c in news.columns if c.startswith("mentions_")]
news["text"] = (news.headline.fillna("") + ". " + news.summary.fillna("")).str.strip()
cand = news[(news.n_symbols <= MAX_SYMBOLS) & news[[f"mentions_{t}" for t in tickers]].any(axis=1) & news.text.str.contains(MA_RE)].copy()

rows = []
for r in cand.itertuples():
    mentioned = [t for t in tickers if getattr(r, f"mentions_{t}")]
    roles = {t: role(t, r.text) for t in mentioned}
    rows.append(dict(id=r.id, ts=r.ts, titoli=",".join(mentioned), fase=stage(r.text), ruoli="; ".join(f"{t}={v}" for t, v in roles.items()),
                     bersaglio=",".join(t for t, v in roles.items() if v == "bersaglio"), headline=r.headline, summary=(r.summary or "")[:300],
                     mano_fase="", mano_ruolo="", mano_note=""))
out = pd.DataFrame(rows).sort_values("ts").reset_index(drop=True)
OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT, index=False)
print(f"{len(news)} notizie | mirate su uno dei 30 titoli (al massimo {MAX_SYMBOLS} ticker) con parole di M&A: {len(out)}")
print("fase:", out.fase.value_counts().to_dict())
print("con un bersaglio tra i 30 titoli:", (out.bersaglio != "").sum(), "| definitive con bersaglio:", ((out.fase == "definitiva") & (out.bersaglio != "")).sum())
print(f"salvato {OUT.relative_to(RESULTS.parent)}")
