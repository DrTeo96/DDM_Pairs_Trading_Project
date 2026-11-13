"""Sentiment FinBERT di ogni notizia (titolo + sommario), calcolato una sola volta e salvato.

Modello: ProsusAI/finbert (positivo / negativo / neutro). Il modello non vede date, nomi di aziende cercati da noi né prezzi: solo il testo.
Uscita: Results/varianti_agente/finbert_seduta/news_finbert.parquet (FINBERT_SCORES in config.py) con id, p_pos, p_neg, p_neu, score = p_pos - p_neg.
Il file è su git: serve rilanciare questo script solo se cambiano le notizie. torch e transformers non sono nell'ambiente del progetto:
    uv run --with torch --with transformers python -m src.varianti_agente.score_finbert
"""
import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.config import FINBERT_SCORES, NEWS

OUT = FINBERT_SCORES
MODEL = "ProsusAI/finbert"
BATCH = 16
MAX_LEN = 256   # titolo + sommario stanno quasi sempre sotto questa lunghezza

news = pd.read_parquet(NEWS, columns=["id", "headline", "summary"])
text = (news.headline.fillna("") + ". " + news.summary.fillna("")).str.strip()

tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForSequenceClassification.from_pretrained(MODEL).eval()
labels = {v.lower(): k for k, v in model.config.id2label.items()}   # positive, negative, neutral

rows = []
with torch.no_grad():
    for i in range(0, len(text), BATCH):
        enc = tok(list(text.iloc[i:i + BATCH]), padding=True, truncation=True, max_length=MAX_LEN, return_tensors="pt")
        p = torch.softmax(model(**enc).logits, dim=-1).numpy()
        rows.append(pd.DataFrame({"p_pos": p[:, labels["positive"]], "p_neg": p[:, labels["negative"]], "p_neu": p[:, labels["neutral"]]}))
        if (i // BATCH) % 20 == 0:
            print(f"{i}/{len(text)}", flush=True)

out = pd.concat([news[["id"]].reset_index(drop=True), pd.concat(rows, ignore_index=True)], axis=1)
out["score"] = out.p_pos - out.p_neg
out.to_parquet(OUT, index=False)
print("salvato", OUT.name, len(out), "notizie;", out[["p_pos", "p_neg", "p_neu"]].idxmax(axis=1).value_counts().to_dict())
