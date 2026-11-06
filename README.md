# Pair trading sull'S&P 500

Progetto d'esame: una strategia di pair trading sui titoli dell'S&P 500, costruita su dati Bloomberg giornalieri, intraday e di sentiment delle notizie.
Il testo del progetto è in [resources/instructions.pdf](resources/instructions.pdf).

## Per iniziare

1. Installa [uv](https://docs.astral.sh/uv/) seguendo [docs/setup.md](docs/setup.md). Non serve installare Python: ci pensa uv.
2. Dalla cartella del progetto crea l'ambiente:

   ```bash
   uv sync    # crea .venv/ con Python 3.14 e le versioni esatte delle librerie scritte in uv.lock
   ```

3. Copia i file Bloomberg in `data/raw/` (vedi [Dati](#dati)) e costruisci i dataset puliti:

   ```bash
   uv run python -m src.data    # da data/raw/ a data/processed/, poi stampa i controlli di qualità
   ```

4. Apri [src/plots.ipynb](src/plots.ipynb) in VS Code e scegli come kernel l'ambiente del progetto:
   *Select Kernel → Python Environments → .venv*. Senza VS Code: `uv run --with jupyter jupyter lab`.

## Dati

I dati non sono nella repo: ognuno tiene la sua copia in `data/`. Il passo 3 si ripete solo quando cambiano i file grezzi.

| Cartella | Contenuto | Periodo |
|---|---|---|
| `data/raw/daily/` | un file per ticker (`AAPL_UW_Equity.parquet`): `PX_LAST`, `PX_VOLUME`, `TOT_RETURN_INDEX_GROSS_DVDS` | nov 2006 - nov 2026 |
| `data/raw/intraday_1m/` | un file per ticker: barre da 1 minuto (`open`, `high`, `low`, `close`, `volume`, `n_events`) in UTC | giu - ott 2026 |
| `data/raw/sentiment/` | numero di notizie e sentiment giornaliero, con il ticker come colonna | 2006 - 2026 |

[src/data.py](src/data.py) unisce i file di ogni cartella in `data/processed/<nome>_all.parquet`.
Da un notebook dentro `src/` si caricano così:

```python
from data import load

daily = load("daily")    # oppure "intraday_1m", "sentiment"
```

### Da sapere prima di usarli

- **Survivorship bias**: l'universo sono i 503 titoli dell'indice di oggi, quindi chi è entrato dopo il 2006 non ha la storia completa
  e chi è uscito dall'indice manca del tutto.
- **daily**: `PX_LAST` è già aggiustato per split e dividendi. Alcune serie hanno buchi di anni (es. FITB): per i rendimenti usare la
  colonna `ret` aggiunta da `load()`, calcolata solo tra giorni di borsa consecutivi.
- **intraday_1m**: dopo `load()` gli orari sono di New York. I prezzi **non** sono aggiustati (gli split compaiono come gap: APH, CRWD, DD, MNST)
  e il volume è solo una parte di `PX_VOLUME`, in quota diversa per borsa.
- **sentiment**: `load()` trasforma in NaN il valore -134217.7 che Bloomberg usa per i dati mancanti. La copertura cresce da circa il 10%
  dei giorni nel 2007 a circa il 60% dal 2022.

## File principali

| File | Contenuto |
|---|---|
| [src/data.py](src/data.py) | Dai file grezzi ai dataset puliti, la funzione `load()` e i controlli di qualità |
| [src/plots.ipynb](src/plots.ipynb) | Grafici: panoramica dei dati, confronto dei prezzi, esploratore di una coppia con lo z-score dello spread, correlazioni, notizie e movimenti di prezzo |
| [src/coppie.ipynb](src/coppie.ipynb) | Passaggio 1: selezione delle coppie (crea `data/processed/selected_pairs.csv`) |
| [src/intraday_pulizia.ipynb](src/intraday_pulizia.ipynb) | Passaggio 2: prezzi intraday puliti per coppia (crea `data/processed/pairs_intraday/`) |
| [src/signals.py](src/signals.py) | Regole dei segnali di pairs trading (spread, z-score con EMA, ingresso e uscita) |
| [src/segnale_mav.ipynb](src/segnale_mav.ipynb), [src/segnali_coppie.ipynb](src/segnali_coppie.ipynb) | Passaggio 4: segnali, prima su MA-V e poi sulle 10 coppie |
| [src/news.py](src/news.py) | Passaggio 3: scarica e archivia le notizie di Alpaca (servono le chiavi nel file `.env`, vedi `.env.example`) |
| [src/notizie_mav.ipynb](src/notizie_mav.ipynb), [src/notizie_coppie.ipynb](src/notizie_coppie.ipynb) | Passaggio 3: qualità e copertura delle notizie, tabella notizie-segnali |
| `.env.example` | Modello del file `.env` con le chiavi di Alpaca (il file `.env` è privato e git lo ignora) |
| `pyproject.toml`, `uv.lock`, `.python-version` | Librerie e versioni dell'ambiente: si modificano solo con uv (vedi [docs/setup.md](docs/setup.md)) |

## Documentazione

| File | Contenuto |
|---|---|
| [docs/Programma.md](docs/Programma.md) | Piano del progetto, stato di ogni passaggio, **come rilanciare tutto sul proprio computer** (anche le chiavi di Alpaca) e chi ha fatto cosa |
| [docs/setup.md](docs/setup.md) | Installare uv, eseguire il codice, aggiungere librerie, cosa fare se qualcosa non funziona |
| [docs/metrics.md](docs/metrics.md) | Rendimenti della strategia senza lookahead bias, divisione In-Sample / Out-of-Sample, metriche di valutazione |
| [docs/bloomberg-api.md](docs/bloomberg-api.md) | Bloomberg Desktop API: cosa scaricare e cosa verificare |
| [docs/delisting.md](docs/delisting.md) | Come trattare i titoli che escono dal mercato con una posizione aperta |
| [resources/instructions.pdf](resources/instructions.pdf) | Testo del progetto d'esame |
| [resources/presentation.pptx](resources/presentation.pptx) | Template della presentazione |
