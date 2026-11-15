"""Sentiment FinBERT delle notizie del test, con lo stesso modello e lo stesso testo del train (varianti_agente/score_finbert.py).

    uv run --with torch --with transformers python -m src.test_finbert

Legge NEWS_TEST (python -m src.test_dati) e scrive FINBERT_SCORES_TEST (Results/test/news_finbert_test.parquet, su git) con
id, p_pos, p_neg, p_neu, score = p_pos - p_neg. Il modello vede solo titolo e sommario: niente date, prezzi o risultati.
Prima di calcolare il test, rifà i punteggi di alcune notizie del train e controlla che coincidano con quelli salvati.
"""
import numpy as np
import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.config import FINBERT_SCORES, FINBERT_SCORES_TEST, NEWS, NEWS_TEST

MODEL = "ProsusAI/finbert"   # come score_finbert.py
BATCH = 16
MAX_LEN = 256
N_CHECK = 64                 # notizie del train ricalcolate per controllo

tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForSequenceClassification.from_pretrained(MODEL).eval()
labels = {v.lower(): k for k, v in model.config.id2label.items()}   # positive, negative, neutral


def score(news: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """Punteggi FinBERT di titolo + sommario, come in score_finbert.py."""
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


# controllo: lo stesso calcolo sul train deve ridare i punteggi salvati (stesso modello, stesso testo). Gruppi di BATCH notizie come
# in score_finbert.py, perché il riempimento (padding) dipende dalle altre notizie del gruppo
train = pd.read_parquet(NEWS, columns=["id", "headline", "summary"])
check = score(train.iloc[:N_CHECK], verbose=False).merge(pd.read_parquet(FINBERT_SCORES), on="id", suffixes=("", "_salvato"))
diff = np.abs(check.score - check.score_salvato).max()
print(f"controllo sul train: {len(check)} notizie, differenza massima del punteggio {diff:.2e}")
assert diff < 1e-3, "FinBERT non ridà i punteggi del train: modello o librerie diversi"

news = pd.read_parquet(NEWS_TEST, columns=["id", "headline", "summary"])
out = score(news)
assert len(out) == len(news) and out.id.is_unique
FINBERT_SCORES_TEST.parent.mkdir(parents=True, exist_ok=True)
out.to_parquet(FINBERT_SCORES_TEST, index=False)
print("salvato", FINBERT_SCORES_TEST.name, len(out), "notizie;", out[["p_pos", "p_neg", "p_neu"]].idxmax(axis=1).value_counts().to_dict())
