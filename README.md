# Pairs trading intraday sull'S&P 500 con un agente di notizie

Progetto d'esame (LUISS). Il testo del progetto è in [resources/instructions.pdf](resources/instructions.pdf).

Il pairs trading scommette su due aziende simili: quando i loro prezzi si allontanano più del solito, si compra il titolo rimasto indietro e si vende quello andato avanti, aspettando che la distanza rientri. Qui la distanza (lo spread) si misura minuto per minuto su 15 coppie di titoli dell'S&P 500, con dati Bloomberg. Un agente legge le notizie uscite prima di ogni segnale e blocca il trade quando l'allontanamento ha una causa vera in una sola delle due aziende. Il progetto confronta tre versioni: A senza agente, B con l'agente che può bloccare, C con l'agente che può anche seguire la notizia. Le decisioni sulle notizie vengono da più fonti messe a confronto: l'agente con due finestre di notizie (24 e 6 ore), una baseline a lessico senza modello e, su un campione, il ragionamento acceso e la classificazione a mano del gruppo.

Sul periodo di addestramento (train) il gruppo ha confrontato 21 varianti dell'agente e ha scelto `finbert_episodio`. Il periodo di test (17 settembre - 30 ottobre 2026) è stato usato una volta sola, il 14 novembre, per quella variante, con le regole scritte prima in [docs/Test.md](docs/Test.md): la B (l'agente blocca) guadagna 189 dollari meno della A, la C (l'agente segue la notizia) 1.242 dollari meno. Le notizie, con questo agente, non migliorano la strategia.

La sintesi della domanda di ricerca, dei risultati e di come il progetto risponde alle istruzioni del corso (compresa l'analisi dei pitfall) è in [docs/Sintesi.md](docs/Sintesi.md). I risultati di train e test, spiegati anche per chi non conosce la finanza, sono in [Results/RESOCONTO.md](Results/RESOCONTO.md).

## Per iniziare

1. Installa [uv](https://docs.astral.sh/uv/) seguendo [docs/setup.md](docs/setup.md). Non serve installare Python: ci pensa uv.
2. Dalla cartella del progetto crea l'ambiente:

   ```bash
   uv sync    # crea .venv/ con Python e le versioni delle librerie scritte in uv.lock
   ```

3. Segui [src/README.md](src/README.md): dice quali dati servono e, passo per passo, cosa eseguire, cosa legge, cosa scrive e quanto tempo e memoria richiede.

## Dove sono le cose

| Dove | Cosa c'è |
|---|---|
| [src/](src/README.md) | Il codice della pipeline, nell'ordine di esecuzione |
| [Results/](Results/RESOCONTO.md) | Risultati del backtest, su git: tabelle, trade di ogni versione, decisioni dell'agente, curve di capitale e il resoconto |
| [Results/test/](Results/test/confronto_versioni.csv) | Risultati del test di `finbert_episodio`: segnali, decisioni, trade di A, B e C, tabelle dei criteri e della robustezza |
| [src/varianti_agente/](src/varianti_agente/README.md) | Tutte le varianti dell'agente di notizie (Giulio, Orfeo, Beatrice): codice, comandi e regole; i loro risultati sono in `Results/varianti_agente/` |
| [docs/Programma.md](docs/Programma.md) | Il diario del gruppo: decisioni, risultati e limiti di ogni passaggio |
| [docs/Sintesi.md](docs/Sintesi.md) | La sintesi: domanda di ricerca e risposta, risultati, richieste del professore una per una, pitfall, limiti |
| [docs/Test.md](docs/Test.md) | Le regole del test, scritte prima di guardarlo: variante, criterio principale, controlli |
| [docs/setup.md](docs/setup.md) | Uso di uv: installare, eseguire, aggiungere librerie |
| `data/` | Dati grezzi e file prodotti dalla pipeline. Non è su git: ognuno tiene la sua copia |
| `resources/` | Testo del progetto, modello della presentazione, nomi dei titoli |
| `Old files/` | Ciò che non fa più parte della pipeline, conservato com'era |
| `.env.example` | Modello del file `.env` con chiavi e indirizzi personali, che git ignora |
