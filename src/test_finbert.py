"""FinBERT sentiment of the test news, with the same model and the same text as the train (agent_variants/score_finbert.py).

    uv run --with torch --with transformers python -m src.test_finbert

It reads NEWS_TEST (python -m src.test_data) and writes FINBERT_SCORES_TEST (Results/test/news_finbert_test.parquet, on git) with
id, p_pos, p_neg, p_neu, score = p_pos - p_neg. The model sees only headline and summary: no dates, prices or results.
Before scoring the test, it redoes the scores of some train news and checks that they match the saved ones.
"""
import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.config import FINBERT_SCORES, FINBERT_SCORES_TEST, NEWS, NEWS_TEST

MODEL = "ProsusAI/finbert"   # as in score_finbert.py
BATCH = 16
MAX_LEN = 256
N_CHECK = 64                 # train news scored again as a check

tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForSequenceClassification.from_pretrained(MODEL).eval()
labels = {v.lower(): k for k, v in model.config.id2label.items()}   # positive, negative, neutral


def score(news: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """FinBERT scores of headline + summary, as in score_finbert.py."""
    text = (news.headline.fillna("") + ". " + news.summary.fillna("")).str.strip()
    rows = []
    with torch.no_grad():
        for i in range(0, len(text), BATCH):
            enc = tok(list(text.iloc[i:i + BATCH]), padding=True, truncation=True, max_length=MAX_LEN, return_tensors="pt")
            p = torch.softmax(model(**enc).logits, dim=-1).numpy()
            rows.append(pd.DataFrame({"p_pos": p[:, labels["positive"]], "p_neg": p[:, labels["negative"]], "p_neu": p[:, labels["neutral"]]}))
            if verbose and (i // BATCH) % 20 == 0:
                print(f"{i}/{len(text)}", flush=True)
    out = pd.concat([news[["id"]].reset_index(drop=True), pd.concat(rows, ignore_index=True)], axis=1)
    out["score"] = out.p_pos - out.p_neg
    return out


# check: the same computation on the train must give back the saved scores (same model, same text). Batches of BATCH news as
# in score_finbert.py, because the padding depends on the other news of the batch
train = pd.read_parquet(NEWS, columns=["id", "headline", "summary"])
check = score(train.iloc[:N_CHECK], verbose=False).merge(pd.read_parquet(FINBERT_SCORES), on="id", suffixes=("", "_saved"))
diff = np.abs(check.score - check.score_saved).max()
print(f"check on the train: {len(check)} news items, maximum score difference {diff:.2e}")
assert diff < 1e-3, "FinBERT does not give back the train scores: different model or libraries"

news = pd.read_parquet(NEWS_TEST, columns=["id", "headline", "summary"])
out = score(news)
assert len(out) == len(news) and out.id.is_unique
FINBERT_SCORES_TEST.parent.mkdir(parents=True, exist_ok=True)
out.to_parquet(FINBERT_SCORES_TEST, index=False)
print("saved", FINBERT_SCORES_TEST.name, len(out), "news items;", out[["p_pos", "p_neg", "p_neu"]].idxmax(axis=1).value_counts().to_dict())
