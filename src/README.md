# La pipeline, dall'inizio alla fine

Questa cartella contiene tutto il codice della strategia, nell'ordine in cui va eseguito: dai file Bloomberg ai segnali, alle decisioni dell'agente di notizie, al backtest. Seguendo i passi qui sotto si ottengono sul proprio computer gli stessi file e gli stessi numeri del gruppo.

La pipeline lavora sulle 15 coppie scelte in `01_coppie.ipynb` e solo sul periodo di addestramento (train), che finisce il 16 settembre 2026. Le decisioni del gruppo e i risultati commentati sono in [docs/Programma.md](../docs/Programma.md).

## Prima di iniziare

1. **Ambiente.** Installa uv seguendo [docs/setup.md](../docs/setup.md), poi dalla cartella del progetto:

   ```bash
   uv sync
   ```
2. **Dati Bloomberg.** Non sono su git: vanno copiati in `data/` da chi li ha scaricati.

   | Dove                      | Contenuto                                                                                                              |
   | ------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
   | `data/raw/daily/`       | un file per titolo (`AAPL_UW_Equity.parquet`): `PX_LAST`, `PX_VOLUME`, `TOT_RETURN_INDEX_GROSS_DVDS`, dal 2006 |
   | `data/raw/intraday_1m/` | un file per titolo: barre da 1 minuto in UTC, dal 16 giugno al 30 ottobre 2026                                         |
   | `data/raw/sentiment/`   | numero di notizie e sentiment giornaliero per titolo, dal 2006                                                         |
   | `data/gics.csv`         | classificazione GICS dei titoli                                                                                        |
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

| Passo          | Cosa si esegue                                                           | Legge                                                                                    | Scrive in `data/processed/`                                                               | Tempo                  | Memoria    |
| -------------- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ---------------------- | ---------- |
| 0              | `uv run python -m src.data`                                            | `data/raw/daily`, `intraday_1m`, `sentiment`                                       | `daily_all.parquet`, `intraday_1m_all.parquet`, `sentiment_all.parquet`               | 15 s                   | 4,0 GB     |
| 0, facoltativo | `00_esplorazione.ipynb`                                                | i tre file del passo 0                                                                   | niente (grafici)                                                                            | 5 s                    | 4,1 GB     |
| 1              | `01_coppie.ipynb`                                                      | `daily_all.parquet`, `data/gics.csv`                                                 | `selected_pairs_2.csv`                                                                    | 3 s                    | 0,9 GB     |
| 2              | `02_intraday.ipynb`                                                    | `selected_pairs_2.csv`, `intraday_1m_all.parquet`, `daily_all.parquet`             | `pairs_intraday_v2/` (60 file e `quality_summary.csv`)                                  | 6 s                    | 0,9 GB     |
| 3              | `03_segnali.ipynb`                                                     | `selected_pairs_2.csv`, `pairs_intraday_v2/`                                         | `signals_15pairs_v2_train.csv`                                                            | 4 s                    | 0,3 GB     |
| 4              | `uv run python -m src.news --probe`, poi `uv run python -m src.news` | Alpaca (chiavi in `.env`), `selected_pairs_2.csv`                                    | `news_ALL15_V2_train.parquet`; pagine grezze in `data/raw/news/alpaca/`                 | circa 1 minuto (stima) | 0,1 GB     |
| 4              | `04_notizie.ipynb`                                                     | `news_ALL15_V2_train.parquet`, `signals_15pairs_v2_train.csv`                        | `news_for_signals_15pairs_v2_train.csv`                                                   | 1 s                    | 0,2 GB     |
| 5              | `uv run python -m src.agent`                                           | `signals_15pairs_v2_train.csv`, `news_ALL15_V2_train.parquet`, il server del modello | `agent_decisions_15pairs_v2_train.csv`; risposte grezze e registri in `data/raw/agent/` | vedi sotto             | vedi sotto |
| 6              | `06_backtest.ipynb`                                                    | `signals_15pairs_v2_train.csv`, `pairs_intraday_v2/`, le decisioni di ogni versione (vedi passo 6) | `Results/` (su git): tabelle, trade di ogni versione, `curve_capitale.png`               | 10 s                   | 0,3 GB     |

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

L'agente è un grafo [LangGraph](https://langchain-ai.github.io/langgraph/) a passi fissi, uguale per ogni segnale: **cerca** le notizie sui due titoli nelle 24 ore prima del segnale, **classifica** ogni notizia, **verifica** i fatti strutturali, **decide** con una regola scritta nel codice e **registra** tutto. Il modello linguistico classifica e basta: non decide, non vede le soglie del segnale, non vede la data. Le regole complete sono nella docstring di [agent.py](agent.py).

- Nessuna notizia: `entra`, senza chiamare il modello.
- Elenchi con più di 5 ticker: rumore per regola, senza chiamare il modello.
- Fatto strutturale (acquisizione, indagine, frode, cambio del management) su uno solo dei due titoli: `blocca`. Per la versione C, `segui` se la direzione della notizia coincide con il movimento dei 30 minuti prima.
- Verifica: quando il modello trova un fatto strutturale su un solo titolo, il codice controlla prima che titolo e sommario nominino davvero quell'azienda, poi il modello risponde a una seconda domanda: l'azienda è il compratore, il venditore, il bersaglio, l'indagato o quella che cambia capo? Se no, la notizia diventa rumore. Serve perché il modello confonde l'azienda a cui la notizia è collegata con quella di cui parla: sui casi provati ha corretto Yum! che vende Pizza Hut (collegata a PEP), Nvidia che compra Hugging Face (collegata a CRM), un'indagine del DOJ su tutte le banche USA e un'IPO in cui JPMorgan fa da consulente.
- Solo rumore (risultati, analisti, accordi, prodotti, settore) o fatti su entrambi: `entra`, con una dimensione suggerita di 0,5 nella colonna `size`, che il backtest per ora non usa.
- Ricerca fallita, server che non risponde, risposta non valida: `blocca`.

**Anonimizzazione.** Prima di arrivare al modello, nomi, ticker, marchi e dirigenti delle due aziende diventano "Company A" e "Company B". Serve a ridurre il lookahead del modello, cioè il rischio che riconosca l'azienda e sappia già come è andata a finire. Non lo elimina: cifre, altre aziende citate e sotto-industria possono ancora far riconoscere il caso. Va dichiarato nel report. Sulle 958 notizie del train che arrivano al modello non resta visibile nessuno dei nomi della tabella `ALIASES`. Le istruzioni dicono al modello che ogni azienda nominata con il suo nome è un'altra azienda, non A o B. Due controlli: `--real-names` (stesso modello, nomi in chiaro) e un modello con data di addestramento lontana (`--model google/gemma-3-4b`).

Il modello gira in locale dietro un server che parla il protocollo dell'API di OpenAI. In `.env` si scrivono l'indirizzo del server e il nome del modello; se l'indirizzo non finisce con `/v1`, il codice lo aggiunge:

```
AGENT_BASE_URL=http://127.0.0.1:1234/v1
AGENT_MODEL=spark-x2.6-4b
```

| Server                                 | Come si avvia                                                                                                              | `AGENT_BASE_URL`                | Provato con questo codice                                |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | -------------------------------------------------------- |
| LM Studio                              | scheda Developer, Start Server (oppure `lms server start`); nome del modello da `curl http://127.0.0.1:1234/v1/models` | `http://127.0.0.1:1234/v1`      | sì, con Spark X2.6 4B (GGUF Q4_K_M)                     |
| Ollama                                 | `ollama serve`; nome del modello da `ollama list`                                                                      | `http://localhost:11434/v1`     | no                                                       |
| mlx-lm (solo Mac con processore Apple) | `uv run --no-project --python 3.12 --with mlx-lm python -m mlx_lm.server --model <cartella del modello> --port 8089`     | `http://localhost:8089/v1`      | sì, con Gemma 3 4B e la versione precedente di agent.py |
| un altro computer                      | uno dei server qui sopra, avviato là                                                                                      | `http://<indirizzo>:<porta>/v1` | no                                                       |

```bash
uv run python -m src.agent --signals 0,1,2,3          # prova su pochi segnali: stampa le decisioni, non scrive la tabella
uv run python -m src.agent                            # tutti i 973 segnali: 586 hanno notizie, 958 notizie da classificare
uv run python -m src.agent --sample 40                # crea data/processed/agent_manual_15pairs_v2_train.csv da compilare a mano
uv run python -m src.agent --agreement                # accordo tra il gruppo e l'agente (aggiungi --reasoning on per l'altra modalità)
uv run python -m src.agent --hours 6                  # variante: finestra di 6 ore
```

- **Ragionamento.** Spark X2.6 4B è un modello che ragiona prima di rispondere. Misurato su questo Mac: circa 70 s a notizia con il ragionamento acceso (una risposta su tre supera il tetto di 2000 token e va richiesta senza ragionamento), circa 4 s con il ragionamento spento. Un giro completo dura circa un'ora senza ragionamento e circa 20 ore con il ragionamento acceso, quindi il default è spento. Le due modalità danno risposte diverse sulla stessa notizia: si sceglie con l'accordo sul campione classificato a mano.
- **Classificazione a mano.** `--sample 40` estrae 40 segnali con notizie, distribuiti sulle coppie, senza le risposte dell'agente: il gruppo non le vede prima di classificare. Per ogni notizia si compilano `mano_riguarda` (A, B, entrambi, nessuno), `mano_sottotipo`, `mano_direzione` e, se serve, `mano_note`. `--agreement` calcola la quota di accordo e il kappa di Cohen, per notizia e per decisione. La decisione del gruppo si ricava dalle sue etichette con la stessa regola dell'agente. Il comando rifiuta di sovrascrivere un campione già esistente.
- **Quale modello.** Un modello addestrato dopo giugno 2026 può conoscere già gli eventi del periodo. La data di fine addestramento di Spark X2.6 4B va verificata e dichiarata nel report. Gemma 3 dichiara agosto 2024: è il controllo.
- **Rieseguire è gratis.** Ogni risposta del modello è salvata in `data/raw/agent/<modello>/notizie/` con orario, richiesta e risposta grezza. Se la stessa domanda è già stata fatta, la risposta viene riletta senza chiamare il server; cambiare finestra non richiede le notizie già classificate. Gli errori di rete o del server non si salvano: alla esecuzione successiva la chiamata si ripete.
- **Registri.** Ogni giro scrive in `data/raw/agent/<modello>/<impostazioni>/` un JSON per segnale (notizie trovate, testo mostrato al modello, classificazioni, decisione), più `decisions.csv` e `classifications.csv`.
- **Stesse decisioni per tutto il gruppo.** Basta che una persona faccia il giro completo e passi agli altri la cartella `data/raw/agent/`: con quella, e con lo stesso nome del modello in `.env`, il comando ricrea la tabella senza server.

### Passo 6. Backtest

Applica costi e capitale ai trade del passo 3 e confronta tre versioni:

- **A**: tutti i segnali entrano, senza agente;
- **B**: l'agente può bloccare (colonna `decision`);
- **C**: l'agente può anche seguire la notizia (colonna `decision_C` = `segui`, direzione in `follow_side`). Il trade che segue la notizia apre alla stessa barra della A, nella direzione opposta, e si rifà barra per barra sui prezzi di `pairs_intraday_v2/`: esce al primo tra rientro dello spread (z torna a 0), 90 minuti e fine giornata, senza stop.

Le versioni girano su ogni **set di decisioni** elencato in `VERSIONS` ([backtest.py](backtest.py)); i percorsi sono in [config.py](config.py):

| Nome            | File                                                              | Segnali |
| --------------- | ----------------------------------------------------------------- | ------- |
| `spark_24h`         | `data/raw/agent/spark-x2.6-4b/h24_diretto_anonimo/decisions.csv` (principale, uguale a `agent_decisions_15pairs_v2_train.csv`) | 973 |
| `spark_6h`          | `data/raw/agent/spark-x2.6-4b/h6_diretto_anonimo/decisions.csv` (`--hours 6`) | 973 |
| `lessico`           | `data/processed/baseline_lexicon_decisions_15pairs_v2_train.csv`: baseline senza modello, lessico Loughran-McDonald. Il codice che lo produce non è nel repo | 973 |
| `spark_24h_ragiona` | `data/raw/agent/spark-x2.6-4b/h24_ragiona_anonimo/accordo_segnali.csv` (`--agreement --reasoning on`) | 40 |
| `mano`              | colonne `mano_*` di `h24_diretto_anonimo/accordo_segnali.csv` (`--agreement`): solo B, perché manca la direzione da seguire | 40 |

I set da 40 segnali si confrontano solo sui segnali del campione classificato a mano. Per il lessico, `flat` vuol dire bloccare e `solo_A`/`solo_B` con `long`/`short` vuol dire seguire: la C si simula con la coppia coperta, come per l'agente.

```python
from src.backtest import load_trades, trading_days, load_version, apply_version, compare_versions

trades = load_trades()
B = apply_version(trades, "B", load_version("spark_24h"))
C = apply_version(trades, "C", load_version("spark_24h"))
cmp = compare_versions(trades, trading_days(), ["spark_24h", "spark_6h", "lessico"])
```

Il notebook salva tabelle, trade e grafico in `Results/`, che è su git, così i risultati si leggono anche senza i dati. Il commento dei numeri per chi non conosce la finanza è in [Results/RESOCONTO.md](../Results/RESOCONTO.md). Per aggiungere un nuovo set di decisioni: il percorso in `config.py`, una riga in `VERSIONS`, poi si riesegue il notebook.

## Regole da non rompere

- **Il taglio train/test.** Il train finisce il 16 settembre 2026 e la data è scritta in un posto solo, `TRAIN_END` in [config.py](config.py). Il test, dal 17 settembre, si usa una volta sola, alla fine, con regole e parametri bloccati. Segnali, notizie e decisioni dell'agente non contengono giorni di test: `load_trades` rifiuta una tabella che ne contiene e `news.py` rifiuta di scaricarli.
- **I nomi dei file in `data/`.** Ogni collega ha la sua copia di `data/`: rinominare un file di uscita rompe le copie degli altri. I nomi sono in `config.py`.
- **Niente percorsi nei notebook.** Percorsi e date si importano da `config.py`.

## Se qualcosa si rompe

| Messaggio                                                          | Cosa fare                                                                                                                          |
| ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| `No module named 'src'` dal terminale                            | Il terminale non è nella cartella del progetto: entra lì con `cd`                                                              |
| `No module named 'src'` in un notebook                           | Il notebook è stato spostato fuori dal progetto, oppure la prima cella non è stata eseguita                                      |
| `No module named ...` (un'altra libreria)                        | Il kernel non è `.venv`, oppure manca `uv sync`                                                                               |
| `manca selected_pairs_2.csv`                                     | Esegui prima `01_coppie.ipynb`                                                                                                   |
| `Mancano ALPACA_API_KEY_ID ...`                                  | Manca `.env` o è vuoto: vedi il passo 4                                                                                         |
| `Alpaca ha risposto 401`                                         | Chiavi sbagliate: rigenerale sul sito di Alpaca                                                                                    |
| `manca news_for_signals_15pairs_v2_train.csv`                    | Esegui prima `04_notizie.ipynb`                                                                                                  |
| `Nessun server risponde a ...`                                   | Il server del modello è spento o `AGENT_BASE_URL` è sbagliato                                                                  |
| `ServerError: Unexpected endpoint or method`                     | L'indirizzo del server è sbagliato: per LM Studio è `http://127.0.0.1:1234/v1`                                                 |
| Da Claude Code l'agente non raggiunge il server, dal terminale sì | La sandbox di Claude Code blocca le connessioni locali: lancia il comando dal terminale                                            |
| Molte righe `risposta non valida` nell'agente                    | Il modello non rispetta il formato: usa un server che impone lo schema della risposta (LM Studio, Ollama) o un modello più grande |
| Il computer rallenta molto al passo 0                              | Chiudi le altre applicazioni: servono circa 4 GB liberi                                                                            |

## I moduli

| File                      | Cosa contiene                                                             |
| ------------------------- | ------------------------------------------------------------------------- |
| [config.py](config.py)     | Percorsi, `TRAIN_END`, nomi dei file, lettura di `.env` e dei parquet |
| [data.py](data.py)         | Passo 0: costruzione dei dataset, `load()`, controlli di qualità       |
| [signals.py](signals.py)   | Spread, z-score e regole di ingresso e uscita                             |
| [news.py](news.py)         | Scaricamento e archivio delle notizie, notizie prima di ogni segnale      |
| [agent.py](agent.py)       | Agente di notizie                                                         |
| [backtest.py](backtest.py) | Costi, versioni A, B e C, set di decisioni da confrontare, metriche, salvataggio in `Results/` |

Ciò che non fa più parte della pipeline è in `Old files/`, nella struttura di cartelle che aveva: i notebook delle prime 10 coppie, le prime prove su una coppia sola, la versione 2 del segnale (scartata) e i documenti del piano iniziale. Sono conservati come erano e non vengono aggiornati: usano percorsi e funzioni di allora.
