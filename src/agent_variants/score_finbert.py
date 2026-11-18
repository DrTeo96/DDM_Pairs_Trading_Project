"""FinBERT sentiment of every news item (headline + summary), computed once and saved.

Model: ProsusAI/finbert (positive / negative / neutral). The model sees no dates, no company names searched by us and no prices: only the text.
Output: Results/agent_variants/finbert_session/news_finbert.parquet (FINBERT_SCORES in config.py) with id, p_pos, p_neg, p_neu, score = p_pos - p_neg.
The file is on git: this script needs to be run again only if the news change. torch and transformers are not in the project environment:
    uv run --with torch --with transformers python -m src.agent_variants.score_finbert
"""
import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.config import FINBERT_SCORES, NEWS

OUT = FINBERT_SCORES
MODEL = "ProsusAI/finbert"
BATCH = 16
MAX_LEN = 256   # headline + summary almost always stay below this length

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
print("saved", OUT.name, len(out), "news items;", out[["p_pos", "p_neg", "p_neu"]].idxmax(axis=1).value_counts().to_dict())
