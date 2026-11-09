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

4. Apri [src/00_esplorazione/plots.ipynb](src/00_esplorazione/plots.ipynb) in VS Code e scegli come kernel l'ambiente del progetto:
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
| [src/00_esplorazione/plots.ipynb](src/00_esplorazione/plots.ipynb) | Grafici: panoramica dei dati, confronto dei prezzi, esploratore di una coppia con lo z-score dello spread, correlazioni, notizie e movimenti di prezzo |
| [src/01_selezione_coppie/coppie.ipynb](src/01_selezione_coppie/coppie.ipynb) | Passaggio 1 (versione 1): selezione delle prime 10 coppie (crea `data/processed/selected_pairs.csv`) |
| [src/01_selezione_coppie/coppie_2.ipynb](src/01_selezione_coppie/coppie_2.ipynb) | Passaggio 1 (versione 2): nuova selezione separata di 15 coppie, stesso settore e legame forte (crea `data/processed/selected_pairs_2.csv`) |
| [src/02_dati_intraday/intraday_pulizia.ipynb](src/02_dati_intraday/intraday_pulizia.ipynb) | Passaggio 2 (versione 1): prezzi intraday puliti per coppia (crea `data/processed/pairs_intraday/`) |
| [src/02_dati_intraday/intraday_pulizia_v2.ipynb](src/02_dati_intraday/intraday_pulizia_v2.ipynb) | Passaggio 2 (versione 2): prezzi intraday puliti per le 15 coppie della versione 2 (crea `data/processed/pairs_intraday_v2/`) |
| [src/signals.py](src/signals.py) | Regole dei segnali di pairs trading (spread, z-score con EMA, ingresso e uscita) |
| [src/04_segnali/segnale_mav.ipynb](src/04_segnali/segnale_mav.ipynb), [src/04_segnali/segnali_coppie.ipynb](src/04_segnali/segnali_coppie.ipynb) | Passaggio 4 (versione 1): segnali, prima su MA-V e poi sulle 10 coppie |
| [src/04_segnali/segnali_coppie_v2.ipynb](src/04_segnali/segnali_coppie_v2.ipynb) | Passaggio 4 (versione 2): segnali sulle 15 coppie della versione 2, stessi parametri della versione 1 (crea `data/processed/signals_15pairs_v2_train.csv`) |
| [src/news.py](src/news.py) | Passaggio 3 (versioni 1 e 2): scarica e archivia le notizie di Alpaca (servono le chiavi nel file `.env`, vedi `.env.example`) |
| [src/03_notizie/notizie_mav.ipynb](src/03_notizie/notizie_mav.ipynb), [src/03_notizie/notizie_coppie.ipynb](src/03_notizie/notizie_coppie.ipynb) | Passaggio 3 (versione 1): qualità e copertura delle notizie, tabella notizie-segnali |
| [src/03_notizie/notizie_v2.ipynb](src/03_notizie/notizie_v2.ipynb) | Passaggio 3 (versione 2): qualità e copertura delle notizie dei 30 titoli delle 15 coppie (`python -m src.news --pair ALL15_V2`) |
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
