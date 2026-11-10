# La pipeline, dall'inizio alla fine

Questa cartella contiene tutto il codice della strategia, nell'ordine in cui va eseguito: dai file Bloomberg ai segnali, alle decisioni dell'agente di notizie, al backtest. Seguendo i passi qui sotto si ottengono sul proprio computer gli stessi file e gli stessi numeri del gruppo.

La pipeline lavora sulle 15 coppie scelte in `01_coppie.ipynb` e solo sul periodo di addestramento (train), che finisce il 16 settembre 2026. Le decisioni del gruppo e i risultati commentati sono in [docs/Programma.md](../docs/Programma.md).

## Prima di iniziare

1. **Ambiente.** Installa uv seguendo [docs/setup.md](../docs/setup.md), poi dalla cartella del progetto:

   ```bash
   uv sync
   ```

2. **Dati Bloomberg.** Non sono su git: vanno copiati in `data/` da chi li ha scaricati.

   | Dove | Contenuto |
   |---|---|
   | `data/raw/daily/` | un file per titolo (`AAPL_UW_Equity.parquet`): `PX_LAST`, `PX_VOLUME`, `TOT_RETURN_INDEX_GROSS_DVDS`, dal 2006 |
   | `data/raw/intraday_1m/` | un file per titolo: barre da 1 minuto in UTC, dal 16 giugno al 30 ottobre 2026 |
   | `data/raw/sentiment/` | numero di notizie e sentiment giornaliero per titolo, dal 2006 |
   | `data/gics.csv` | classificazione GICS dei titoli |

3. **File `.env`.** Serve dal passo 4. Copia il modello e compila i valori, senza spazi e senza virgolette:

   ```bash
   cp .env.example .env
   ```

   Il file `.env` resta sul tuo computer: git lo ignora. Le chiavi non si condividono e non si incollano in chat, nei notebook o nei commit.

## Come si esegue un passo

Tutti i comandi si lanciano **dalla cartella del progetto** (quella che contiene `pyproject.toml`). Se compare `No module named 'src'`, il terminale è in un'altra cartella.

Un notebook si esegue in uno di questi due modi:

- in VS Code: aprilo, scegli il kernel del progetto (*Select Kernel → Python Environments → .venv*) e premi *Run All*;
- dal terminale, per esempio per il passo 1:

  ```bash
  uv run --with nbconvert jupyter nbconvert --to notebook --execute --inplace src/01_coppie.ipynb
  ```

## I passi

Tempo e memoria sono misurati su un Mac con 16 GB (processore M4). La memoria è il picco del passo: è quanta RAM libera serve perché giri senza rallentare.

| Passo | Cosa si esegue | Legge | Scrive in `data/processed/` | Tempo | Memoria |
|---|---|---|---|---|---|
| 0 | `uv run python -m src.data` | `data/raw/daily`, `intraday_1m`, `sentiment` | `daily_all.parquet`, `intraday_1m_all.parquet`, `sentiment_all.parquet` | 15 s | 4,0 GB |
| 0, facoltativo | `00_esplorazione.ipynb` | i tre file del passo 0 | niente (grafici) | 5 s | 4,1 GB |
| 1 | `01_coppie.ipynb` | `daily_all.parquet`, `data/gics.csv` | `selected_pairs_2.csv` | 3 s | 0,9 GB |
| 2 | `02_intraday.ipynb` | `selected_pairs_2.csv`, `intraday_1m_all.parquet`, `daily_all.parquet` | `pairs_intraday_v2/` (60 file e `quality_summary.csv`) | 6 s | 0,9 GB |
| 3 | `03_segnali.ipynb` | `selected_pairs_2.csv`, `pairs_intraday_v2/` | `signals_15pairs_v2_train.csv` | 4 s | 0,3 GB |
| 4 | `uv run python -m src.news --probe`, poi `uv run python -m src.news` | Alpaca (chiavi in `.env`), `selected_pairs_2.csv` | `news_ALL15_V2_train.parquet`; pagine grezze in `data/raw/news/alpaca/` | circa 1 minuto (stima) | 0,1 GB |
| 4 | `04_notizie.ipynb` | `news_ALL15_V2_train.parquet`, `signals_15pairs_v2_train.csv` | `news_for_signals_15pairs_v2_train.csv` | 1 s | 0,2 GB |
| 5 | `uv run python -m src.agent` | `signals_15pairs_v2_train.csv`, `news_for_signals_15pairs_v2_train.csv`, il server del modello | `agent_decisions_15pairs_v2_train.csv`; risposte grezze in `data/raw/agent/` | vedi sotto | vedi sotto |
| 6 | `06_backtest.ipynb` | `signals_15pairs_v2_train.csv`, `pairs_intraday_v2/` | niente (tabelle e grafici) | 1 s | 0,2 GB |

Un passo si rifà solo quando cambiano i file che legge. Nel Programma i passi hanno un'altra numerazione: lì le notizie sono il Passaggio 3 e i segnali il Passaggio 4. Qui i segnali vengono prima, perché la tabella notizie-segnali ha bisogno dei segnali.

### Passo 0. Dai file Bloomberg ai dataset

Unisce i file grezzi in tre tabelle, converte gli orari dell'intraday all'ora di New York e stampa i controlli di qualità. Da sapere prima di usare i dati:

- l'universo sono i titoli dell'indice di oggi: chi è uscito dall'indice manca (survivorship bias);
- nel giornaliero `PX_LAST` è aggiustato per split e dividendi; alcune serie hanno buchi di anni, quindi per i rendimenti si usa la colonna `ret` di `load("daily")`;
- nell'intraday i prezzi **non** sono aggiustati: uno split compare come un salto;
- nel sentiment il valore -134217.7 è il segnaposto di Bloomberg per "dato mancante": `load("sentiment")` lo trasforma in NaN.

### Passo 1. Selezione delle coppie

Sceglie 15 coppie della stessa sotto-industria con il metodo della distanza, usando solo prezzi giornalieri fino al 15 giugno 2026, il giorno prima dell'inizio dei dati intraday.

### Passo 2. Prezzi intraday per coppia

Per ogni coppia allinea i due titoli sugli stessi minuti (seduta 09:30-15:59), tiene i giorni in cui ci sono entrambi e riempie i minuti senza scambi con l'ultimo prezzo dello stesso giorno, segnandoli con `filled`. I file arrivano al 30 ottobre: contengono anche i prezzi del periodo di test, che i passi successivi non usano.

### Passo 3. Segnali

Calcola spread e z-score e applica le regole di ingresso e uscita di [signals.py](signals.py), solo sul train. Ogni riga del file è un trade con orari, prezzi, motivo di uscita e guadagno lordo.

### Passo 4. Notizie

Le notizie vengono dall'API gratuita di Alpaca (fonte Benzinga). Ognuno crea le proprie chiavi:

1. crea un account gratuito su [alpaca.markets](https://alpaca.markets); basta il conto Paper Trading;
2. nella dashboard, in Paper Trading, riquadro API Keys, premi Generate New Keys: compaiono il Key ID e il Secret Key, che viene mostrato una volta sola;
3. scrivi i due valori in `.env`, dopo `ALPACA_API_KEY_ID=` e `ALPACA_API_SECRET_KEY=`.

```bash
uv run python -m src.news --probe    # una sola chiamata: dice se le chiavi funzionano, non salva niente
uv run python -m src.news            # scarica le notizie dei 30 titoli, dal 1 giugno al 16 settembre 2026
```

Lo scaricamento sostituisce l'archivio solo quando è finito: se si interrompe, quello di prima resta intero. Una data di fine successiva al 16 settembre viene rifiutata. Poi `04_notizie.ipynb` controlla la copertura e crea, per ogni segnale, l'elenco delle notizie uscite nelle 24 ore prima.

### Passo 5. Agente di notizie

Per ogni segnale l'agente decide `entra` o `blocca`. Se nelle 24 ore prima non ci sono notizie la decisione è `entra` e il modello non viene chiamato; altrimenti il modello legge le notizie e risponde in un formato fisso, che il codice controlla. Una risposta non valida, un errore o un timeout danno `blocca`. Le regole sono nella docstring di [agent.py](agent.py).

Il modello linguistico gira in locale, su questo computer o su un altro, dietro un server che parla il protocollo dell'API di OpenAI. In `.env` si scrivono l'indirizzo del server e il nome del modello:

```
AGENT_BASE_URL=http://localhost:1234/v1
AGENT_MODEL=nome-del-modello
```

| Server | Come si avvia | `AGENT_BASE_URL` | Provato con questo codice |
|---|---|---|---|
| LM Studio | scheda Developer, Start Server (oppure `lms server start`); nome del modello da `lms ls` | `http://localhost:1234/v1` | no |
| Ollama | `ollama serve`; nome del modello da `ollama list` | `http://localhost:11434/v1` | no |
| mlx-lm (solo Mac con processore Apple) | `uv run --no-project --python 3.12 --with mlx-lm python -m mlx_lm.server --model <cartella del modello> --port 8089` | `http://localhost:8089/v1` | sì, con Gemma 3 da 4 miliardi di parametri |
| un altro computer | uno dei server qui sopra, avviato là | `http://<indirizzo>:<porta>/v1` | no |

```bash
uv run python -m src.agent --signals 0,1,2,3,4,5    # prova su sei segnali: stampa le decisioni, non scrive la tabella
uv run python -m src.agent                          # tutti i 973 segnali: 586 hanno notizie e richiedono una chiamata
```

- **Quale modello.** Un modello addestrato dopo giugno 2026 può conoscere già gli eventi del periodo e "sapere" come è andata a finire. Va scelto un modello con data di fine addestramento precedente al 1 giugno 2026, e va dichiarato nel report. Gemma 3 dichiara agosto 2024.
- **Tempo e memoria.** Il programma in sé usa meno di 0,2 GB. Il modello pesa sul computer dove gira il server: Gemma 3 da 4 miliardi di parametri ha occupato 4,0 GB e ha risposto in circa 4 secondi a domanda, quindi un giro completo dura circa 40 minuti (stima, da cinque chiamate misurate). Un modello più grande è più lento e chiede più memoria.
- **Rieseguire è gratis.** Ogni risposta è salvata in `data/raw/agent/<modello>/` con orario e nome del modello. Se la risposta a una domanda c'è già viene riletta, senza chiamare il server. Le chiamate rimaste senza risposta vengono ripetute alla esecuzione successiva.
- **Stesse decisioni per tutto il gruppo.** Basta che una persona faccia il giro completo e passi agli altri la cartella `data/raw/agent/`: con quella, e con lo stesso nome del modello in `.env`, il comando ricrea la tabella senza server.

### Passo 6. Backtest

Applica costi e capitale ai trade del passo 3 e confronta le versioni: A senza agente, B con l'agente che può bloccare. Per la versione B:

```python
from src.agent import load_decisions
from src.backtest import load_trades, apply_version

B = apply_version(load_trades(), "B", load_decisions())
```

La versione C, in cui l'agente sceglie anche la direzione, non è simulata.

## Regole da non rompere

- **Il taglio train/test.** Il train finisce il 16 settembre 2026 e la data è scritta in un posto solo, `TRAIN_END` in [config.py](config.py). Il test, dal 17 settembre, si usa una volta sola, alla fine, con regole e parametri bloccati. Segnali, notizie e decisioni dell'agente non contengono giorni di test: `load_trades` rifiuta una tabella che ne contiene e `news.py` rifiuta di scaricarli.
- **I nomi dei file in `data/`.** Ogni collega ha la sua copia di `data/`: rinominare un file di uscita rompe le copie degli altri. I nomi sono in `config.py`.
- **Niente percorsi nei notebook.** Percorsi e date si importano da `config.py`.

## Se qualcosa si rompe

| Messaggio | Cosa fare |
|---|---|
| `No module named 'src'` dal terminale | Il terminale non è nella cartella del progetto: entra lì con `cd` |
| `No module named 'src'` in un notebook | Il notebook è stato spostato fuori dal progetto, oppure la prima cella non è stata eseguita |
| `No module named ...` (un'altra libreria) | Il kernel non è `.venv`, oppure manca `uv sync` |
| `manca selected_pairs_2.csv` | Esegui prima `01_coppie.ipynb` |
| `Mancano ALPACA_API_KEY_ID ...` | Manca `.env` o è vuoto: vedi il passo 4 |
| `Alpaca ha risposto 401` | Chiavi sbagliate: rigenerale sul sito di Alpaca |
| `manca news_for_signals_15pairs_v2_train.csv` | Esegui prima `04_notizie.ipynb` |
| `Nessun server risponde a ...` | Il server del modello è spento o `AGENT_BASE_URL` è sbagliato |
| Molte righe `risposta non valida` nell'agente | Il modello non rispetta il formato: usa un server che impone lo schema della risposta (LM Studio, Ollama) o un modello più grande |
| Il computer rallenta molto al passo 0 | Chiudi le altre applicazioni: servono circa 4 GB liberi |

## I moduli

| File | Cosa contiene |
|---|---|
| [config.py](config.py) | Percorsi, `TRAIN_END`, nomi dei file, lettura di `.env` e dei parquet |
| [data.py](data.py) | Passo 0: costruzione dei dataset, `load()`, controlli di qualità |
| [signals.py](signals.py) | Spread, z-score e regole di ingresso e uscita |
| [news.py](news.py) | Scaricamento e archivio delle notizie, notizie prima di ogni segnale |
| [agent.py](agent.py) | Agente di notizie |
| [backtest.py](backtest.py) | Costi, versioni A e B, metriche |

Ciò che non fa più parte della pipeline è in `Old files/`, nella struttura di cartelle che aveva: i notebook delle prime 10 coppie, le prime prove su una coppia sola, la versione 2 del segnale (scartata) e i documenti del piano iniziale. Sono conservati come erano e non vengono aggiornati: usano percorsi e funzioni di allora.
