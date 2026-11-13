# Varianti dell'agente di notizie

Qui c'è il codice di tutte le varianti dell'agente provate dal gruppo: quelle di Giulio, di Orfeo e di Beatrice. Ogni variante ha una cartella di risultati in [Results/varianti_agente/](../../Results/varianti_agente/), su git. Tutte le varianti si confrontano **solo sul train**: il backtest e il confronto sono in [06_backtest.ipynb](../06_backtest.ipynb) (tabella in [Results/confronto_versioni.csv](../../Results/confronto_versioni.csv)), i controlli di robustezza in [07_robustezza.ipynb](../07_robustezza.ipynb). Le funzioni che usano tutti e due i notebook sono in [confronto.py](confronto.py): caricano ogni variante con il suo riferimento (la A, oppure la A ritardata) e ne calcolano le differenze.

Il test (dal 17 settembre) non è mai stato letto. Si usa una volta sola, alla fine, per la variante che il gruppo sceglierà con un criterio scritto prima, con regole e soglie bloccate.

Le regole di Beatrice, scritte prima di ogni prova con i loro esiti, sono in [REGISTRO.md](REGISTRO.md). La colonna "Registro" dà il numero della variante lì.

## Le varianti

**Set di decisioni.** Per ogni segnale `entra`, `blocca` o `segui`. Si confrontano in `06_backtest.ipynb` con `VERSIONS` di [backtest.py](../backtest.py).

| Variante (cartella) | Chi | Registro | Versioni | Cosa fa | Codice |
|---|---|---|---|---|---|
| `spark_24h` | Giulio | 1, 2 | B, C | Spark X2.6 4B, notizie delle 24 ore prima, nomi nascosti, ragionamento spento (versione principale) | `agent.py` |
| `spark_6h` | Giulio | 3, 4 | B, C | Come `spark_24h`, con le notizie delle 6 ore prima | `agent.py --hours 6` |
| `lessico` | Giulio | 5, 6 | B, C | Baseline senza modello: parole positive e negative del lessico Loughran-McDonald | non nel repo (solo le decisioni) |
| `spark_24h_ragiona` | Giulio | 7 | B | Come `spark_24h` con il ragionamento acceso, solo sui 40 segnali del campione | `agent.py --agreement --reasoning on` |
| `mano` | Giulio (gruppo) | 7 | B | Classificazione a mano del gruppo sui 40 segnali, con la regola dell'agente | `agent.py --sample 40`, poi `--agreement` |
| `3b_6h` | Beatrice | 8 | B | Llama 3.2 3B con Ollama, 6 ore, prompt completo; ogni blocco richiede una parola dell'evento nel testo | `agent_3b.py` |
| `finbert_seduta` | Beatrice | 9, 10 | B, C | FinBERT sulle notizie mirate (una sola azienda, al massimo 3 ticker). Finestra legata alla seduta: dall'ultima chiusura per il gap della notte, dalle 9:30 per il resto | `score_finbert.py`, `agent_finbert.py` |
| `c_fresca` | Beatrice | 13 | C | Segue solo notizie della seduta uscite nei 60 minuti prima, con un evento, sentiment forte e direzione uguale al movimento | `c_fresca.py` |
| `finbert_episodio` | Beatrice | 14, 15 | B, C | Regole di `finbert_seduta`, con le notizie uscite mentre lo spread si allontanava dalla media | `episodio.py` |

**Varianti che cambiano il backtest stesso.** Hanno un loro script, che salva i trade; il notebook 06 li legge da `Results/varianti_agente/`.

| Variante (cartella) | Chi | Registro | Cosa fa | Codice |
|---|---|---|---|---|
| `ma_regole` | Beatrice | 11, 11b | Regole sul testo per le notizie di M&A: blocca solo un'acquisizione definitiva in cui un titolo della coppia è il bersaglio. Sul train non trova casi: coincide con la A, quindi niente trade, solo la lista delle notizie | `ma_regole.py` |
| `dimensione` | Beatrice | 12a-12d | Ridurre a metà invece di bloccare, con le decisioni di `spark_24h`, `3b_6h` e `finbert_seduta` | `backtest_size.py` |
| `ritardo` | Beatrice | 16, 17 | Decisione e ingresso 5 o 15 minuti dopo il segnale, contro una A ritardata dello stesso tempo | `ritardo.py` |
| `post_train` | Orfeo | — | `B_esagerazione`: entra quando la notizia conferma il movimento. Scelta **dopo** aver visto i risultati del train: i numeri sono ottimistici | `post_train.py` |

Se l'agente sceglie bene (i trade bloccati rientrano meno? quando la C segue la notizia, la notizia ha ragione?) si vede nella sezione 4 di `06_backtest.ipynb`.

## Come si rifanno

Dalla cartella del progetto, con l'ambiente di `uv sync`. Tutti gli script leggono solo il train.

```bash
uv run python -m src.varianti_agente.agent              # Giulio: serve il server del modello, vedi src/README.md (passo 5)
uv run python -m src.varianti_agente.agent_3b           # serve Ollama con llama3.2:3b; ore di calcolo
uv run --with torch --with transformers python -m src.varianti_agente.score_finbert   # solo se cambiano le notizie
uv run python -m src.varianti_agente.agent_finbert
uv run python -m src.varianti_agente.c_fresca
uv run python -m src.varianti_agente.ma_regole
uv run python -m src.varianti_agente.episodio           # prima di ritardo: ritardo usa l'inizio dell'episodio
uv run python -m src.varianti_agente.ritardo
uv run python -m src.varianti_agente.backtest_size
uv run python -m src.varianti_agente.post_train
```

Poi si rieseguono `06_backtest.ipynb`, che confronta tutto e salva i trade dei set di decisioni nelle loro cartelle, e `07_robustezza.ipynb`.

Non serve far girare i modelli: le decisioni e i punteggi FinBERT sono su git. Gli script di FinBERT, delle regole e dei backtest girano in pochi secondi o minuti.

## Dove sono i file

- **Decisioni.** Le nostre e quelle di Orfeo sono in `Results/varianti_agente/<variante>/`: `decisioni.csv`, oppure `agent_decisions_15pairs_v2_train.csv` per `spark_24h`. Le risposte grezze di Giulio (`data/raw/agent/`) stanno solo sul suo computer. Per questo `backtest.py` usa la copia su git quando l'originale manca.
- **Copie di `spark_6h` e `lessico`.** Sono state ricostruite dai loro trade salvati. Il controllo: con le copie, il backtest rifà esattamente gli stessi trade.
- **`spark_24h_ragiona` e `mano`.** Non hanno una copia: senza i file di Giulio il notebook mostra la tabella del campione già salvata (`Results/confronto_campione_40.csv`).
- **Trade.** `trades_B.csv` e `trades_C.csv` per i set di decisioni, scritti dal notebook 06; i file `trades_*.csv` delle altre varianti sono scritti dai loro script. Tutti a costo 0: i costi si aggiungono con `backtest.add_costs`.
