# Sintesi: la domanda di ricerca, i risultati e le richieste del professore

Questo documento riassume in un posto solo che cosa volevamo sapere, che cosa abbiamo trovato e come il progetto risponde alle istruzioni del corso ([resources/instructions.pdf](../resources/instructions.pdf)). I dettagli sono nei notebook di [src/](../src/README.md), nel diario [docs/Programma.md](Programma.md) e nel [resoconto](../Results/RESOCONTO.md), scritto per chi non conosce la finanza.

## 1. La domanda e la risposta in breve

**Ipotesi.** Aziende con business simili hanno prezzi legati nel tempo. Quando, durante la giornata, i loro prezzi si allontanano per rumore, la distanza (lo spread) rientra; quando si allontanano per un fatto vero su una sola azienda (acquisizione, indagine, cambio del management), può non rientrare. Un agente che legge le notizie uscite prima del segnale può distinguere i due casi e migliorare la strategia.

**Risposta.**
- **Lo spread rientra, ma il guadagno è piccolo.** La strategia senza agente (A) guadagna +7,4 punti base lordi per trade sul train e +4,9 sul test; con un costo realistico di 5 punti base per operazione perde.
- **L'agente non migliora la strategia.** Sul test, dove è stato provato una volta sola, bloccare i trade (B) fa guadagnare 189 dollari meno della A, e la differenza non si distingue da zero; seguire la notizia (C) fa guadagnare 1.242 dollari meno, con un intervallo di confidenza tutto sotto zero. Sul train succedeva lo stesso.
- **I trade bloccati per una notizia non sono quelli che non rientrano**: in media guadagnavano più degli altri (+27 punti base contro +4,6 sul test).
- **La strategia non dipende dalla borsa**: beta vicino a zero, e nei giorni in cui l'S&P 500 scende guadagna in media un po'.

## 2. Dati e strategia

| | |
|---|---|
| **Titoli** | 15 coppie di azioni dell'S&P 500 della stessa sotto-industria (30 titoli), scelte con il metodo della distanza sui prezzi giornalieri fino al 15 giugno 2026 ([01_coppie.ipynb](../src/01_coppie.ipynb)) |
| **Prezzi** | Bloomberg, barre da 1 minuto dal 16 giugno al 30 ottobre 2026 (96 giorni di borsa); giornalieri dal 2006 per la selezione |
| **Notizie** | Alpaca (fonte Benzinga), con l'orario di pubblicazione: 2.106 sul train, 2.725 sul test |
| **Segnale** | Spread = differenza dei logaritmi dei prezzi; z-score con media e deviazione standard esponenziali (emivita 60 minuti). Si entra a \|z\| ≥ 2, si esce a 0, stop a 3,5, al massimo 90 minuti, tutto chiuso a fine giornata ([signals.py](../src/signals.py)) |
| **Agente (AI)** | `finbert_episodio`: FinBERT dà a ogni notizia un punteggio positivo o negativo; l'agente legge le notizie uscite mentre lo spread si allontanava e blocca il trade se trova una notizia forte su una sola azienda con una parola dell'evento; nella C segue la notizia se va nella stessa direzione del movimento ([varianti_agente/episodio.py](../src/varianti_agente/episodio.py)) |
| **Versioni** | A: entra sempre. B: l'agente può bloccare. C: l'agente può bloccare o seguire la notizia |
| **Train e test** | Train dal 16 giugno al 16 settembre (64 giorni), test dal 17 settembre al 30 ottobre (32 giorni), usato una volta sola il 14 novembre con le regole di [docs/Test.md](Test.md) |
| **Backtest** | 10.000 dollari per titolo, senza leva, 300.000 di capitale; costo 0 (indicazione del docente) e 5 punti base per operazione |

Sul train il gruppo ha confrontato 21 varianti dell'agente (modelli linguistici, FinBERT, lessico, regole sul testo) e ha scelto `finbert_episodio` per il test ([06_backtest.ipynb](../src/06_backtest.ipynb), sezione 7).

## 3. I risultati

**L'agente rispetto alla A** (differenza in dollari, costo 0, dai trade):

| | Train | Test | Intervallo al 95% sul test |
|---|---|---|---|
| B meno A | -285 $ | **-189 $** | da -527 a +135 |
| C meno A | -651 $ | **-1.242 $** | da -2.183 a -374 |

Fonti: [06_test_backtest.ipynb](../src/06_test_backtest.ipynb) e [07_test_robustezza.ipynb](../src/07_test_robustezza.ipynb).

**Le metriche richieste dal professore** (rendimenti dal segnale +1/0/-1, costo 0, [09_curve_metriche.ipynb](../src/09_curve_metriche.ipynb)):

| | A | B | C | SPY |
|---|---|---|---|---|
| **Train:** rendimento cumulato | +2,42% | +2,32% | +2,20% | +0,15% |
| rendimento annualizzato | +9,9% | +9,5% | +8,9% | +0,6% |
| volatilità annualizzata | 1,2% | 1,1% | 1,2% | 11,7% |
| Sharpe (tasso privo di rischio 0) | 8,2 | 8,2 | 7,5 | 0,1 |
| massimo drawdown | -0,14% | -0,14% | -0,14% | -3,4% |
| profit factor (giorni) | 3,9 | 3,9 | 3,5 | 1,0 |
| **Test:** rendimento cumulato | +0,83% | +0,76% | +0,41% | +0,47% |
| rendimento annualizzato | +6,7% | +6,2% | +3,3% | +3,8% |
| volatilità annualizzata | 1,3% | 1,3% | 1,2% | 11,4% |
| Sharpe (tasso privo di rischio 0) | 4,9 | 4,7 | 2,8 | 0,4 |
| massimo drawdown | -0,17% | -0,19% | -0,21% | -3,0% |
| profit factor (giorni) | 2,5 | 2,3 | 1,6 | 1,1 |

Con 5 punti base di costo tutte le versioni perdono (test: A -2,5%, B -2,5%, C -2,9%). La volatilità è così bassa perché il capitale è investito solo di giorno e in pochi trade alla volta: lo Sharpe alto non è confrontabile con quello di un fondo.

**Dipendenza dal mercato sul test:** beta -0,04 per A, B e C; correlazione con SPY da -0,36 a -0,39; nei 16 giorni in cui SPY scende (-55 punti base in media) A, B e C guadagnano in media +4,0, +3,6 e +2,8 punti base.

## 4. L'ipotesi, parte per parte

| Parte dell'ipotesi | Risposta | Prova |
|---|---|---|
| I prezzi delle coppie sono legati e lo spread rientra | **Sì, ma con un guadagno piccolo** | +7,4 bps (train) e +4,9 bps (test) lordi per trade; i trade che rientrano guadagnano, quelli chiusi dopo 90 minuti perdono |
| Gli allargamenti dovuti a notizie vere non rientrano | **Non lo troviamo** | I trade bloccati rientrano quasi come gli altri (43% contro 49% sul test) e guadagnavano di più. Sul train nessuna variante con regole scritte prima blocca meglio di un blocco a caso (p da 0,58 a 1,00); solo `b_esagerazione`, costruita dopo aver visto i risultati, ci riesce (p = 0,04) |
| L'agente distingue i due casi e migliora la strategia | **No** | Sul test B -189 $ e C -1.242 $ rispetto alla A; stesso segno del train |
| Seguire la notizia (C) rende | **No** | La notizia seguita ha ragione nel 24% dei casi sul test (55% sul train) |

Perché, secondo i dati: i blocchi nascono spesso da notizie che non sono fatti strutturali (comunicati di studi legali che "indagano", acquisizioni fatte dall'azienda stessa), e negli allargamenti più grandi anche le notizie vere sono rientrate nella giornata.

## 5. Le richieste del professore, una per una

| Richiesta | Cosa abbiamo fatto | Dove |
|---|---|---|
| Idea | Pairs trading intraday con un agente di notizie, ipotesi esplicita | Sezione 1, [Programma](Programma.md) |
| Raccolta dati | Bloomberg (giornaliero, intraday, sentiment), Alpaca (notizie, SPY) | [data.py](../src/data.py), [news.py](../src/news.py), [test_dati.py](../src/test_dati.py) |
| Validazione dei dati, prezzi aggiustati | Giornalieri aggiustati; intraday non aggiustati da Bloomberg: controllati gli split (nessuno), dividendi non aggiustati (limite, sezione 8) | [02_intraday.ipynb](../src/02_intraday.ipynb) |
| Feature engineering | Spread e z-score; punteggi FinBERT; finestra dell'episodio | [03_segnali.ipynb](../src/03_segnali.ipynb), [episodio.py](../src/varianti_agente/episodio.py) |
| Costruzione della strategia | Regole del segnale e dell'agente | [signals.py](../src/signals.py), [varianti_agente/](../src/varianti_agente/README.md) |
| Backtest | Trade barra per barra, versioni A, B, C | [backtest.py](../src/backtest.py), [06_backtest.ipynb](../src/06_backtest.ipynb) |
| Validazione fuori campione | Test usato una volta, regole scritte prima | [Test.md](Test.md), [06_test_backtest.ipynb](../src/06_test_backtest.ipynb) |
| Valutazione | Metriche su train e test, robustezza, bootstrap | [07_robustezza.ipynb](../src/07_robustezza.ipynb), [07_test_robustezza.ipynb](../src/07_test_robustezza.ipynb), [09_curve_metriche.ipynb](../src/09_curve_metriche.ipynb) |
| Segnale +1 / 0 / -1 per titolo, rendimento = segnale x rendimento del titolo, ipotesi dichiarate | Segnale per 30 titoli e ogni minuto; il guadagno coincide con quello dei trade a meno dello 0,3% | [08_segnale.ipynb](../src/08_segnale.ipynb) |
| Almeno 2 titoli | 30 | [01_coppie.ipynb](../src/01_coppie.ipynb) |
| Frequenza almeno settimanale; lunghezza giustificata | 1 minuto; giustificazione nella sezione 7 | Sezione 7 |
| Almeno una tecnica di AI o di ottimizzazione | FinBERT nell'agente scelto; modelli linguistici nelle altre varianti; griglia dei parametri del segnale | [episodio.py](../src/varianti_agente/episodio.py), Programma, Passaggio 4 |
| Momento di esecuzione senza lookahead | Decisione alla chiusura della barra, esecuzione all'apertura della successiva | [signals.py](../src/signals.py), [08_segnale.ipynb](../src/08_segnale.ipynb) |
| Costi | 0 e 5 punti base per operazione, 4 operazioni per trade | [backtest.py](../src/backtest.py) |
| Dimensione delle posizioni e leva | 10.000 dollari per titolo, 20.000 per coppia, nessuna leva | [backtest.py](../src/backtest.py) |
| Divisione train / test; selezione del modello su una validazione dentro il train | Train e test separati, test usato una volta. La variante è stata scelta su tutto il train, non su una parte separata (sezione 6) | [Test.md](Test.md) |
| Metriche su train e test con un benchmark giustificato | Curva da 100 con SPY, rendimento cumulato e annualizzato, volatilità, Sharpe (tasso 0), drawdown, profit factor; benchmark SPY e A | [09_curve_metriche.ipynb](../src/09_curve_metriche.ipynb) |
| Analisi dei pitfall | Sezione 6 | Sezione 6 |
| Codice in script e notebook, codice condiviso in moduli | Notebook e script numerati in `src/`, moduli importati. Gli script del test ripetono alcune regole del train (controllato che coincidano) | [src/README.md](../src/README.md) |
| Dati e output di ogni passo nel progetto, riproducibili senza scaricare | Risultati su git; i dati in `data/` vanno inclusi nello zip; gli output del modello linguistico e di FinBERT sono salvati | [src/README.md](../src/README.md) |
| Impostazioni in un solo file di configurazione | Date e percorsi in `config.py`; le soglie del segnale e dell'agente sono negli script e nei notebook | [config.py](../src/config.py) |
| Seed fissi, percorsi relativi, nessuna chiave nel codice | Seed fissi nei ricampionamenti; percorsi da `config.py`; chiavi solo in `.env`, che git ignora | [config.py](../src/config.py), [.env.example](../.env.example) |
| Ambiente e versione di Python | `pyproject.toml`, `uv.lock`, `.python-version` | [docs/setup.md](setup.md) |
| README con i comandi in ordine | Sì | [README.md](../README.md), [src/README.md](../src/README.md) |
| Presentazione e zip | A cura del gruppo | |
| Punto bonus "market-neutral" (facoltativo) | Beta vicino a zero e guadagno medio positivo nei giorni in cui SPY scende; correlazione -0,37 sul test e rendimenti piccoli | [09_curve_metriche.ipynb](../src/09_curve_metriche.ipynb), sezione 4 |
| Punto bonus "rendimento corretto per il rischio superiore" (facoltativo) | Drawdown più basso di SPY per A, B e C; la differenza di Sharpe (+4,6 per la A) non è sostenuta dal bootstrap: intervallo al 95% da -4,6 a +12,5, contiene lo zero. Bonus non reclamabile | [09_curve_metriche.ipynb](../src/09_curve_metriche.ipynb), sezione 5 |

## 6. Analisi dei pitfall

Il professore chiede di mostrare come il metodo affronta cinque errori tipici del backtest.

**Overfitting** (regole adattate ai dati su cui si misurano).
- I parametri del segnale sono stati scelti una volta, con una griglia di 32 combinazioni sul train delle prime 10 coppie e una regola di scelta scritta prima (almeno 300 trade); per le 15 coppie sono stati tenuti uguali, senza nuova ricerca, e uguali per tutte le coppie.
- Le soglie dell'agente (forte da 0,8, segui da 0,5, al massimo 3 ticker) sono state fissate prima di guardare i risultati e sono le stesse sul test.
- Il test è stato usato una volta sola, con regole bloccate; prima del test il codice ha rifatto il train e ritrovato esattamente segnali, decisioni e trade.
- Resta: sul train sono state confrontate 21 varianti, quindi la migliore lo è anche per caso. Sul test il risultato ha lo stesso segno del train.

**Lookahead bias** (usare informazioni non ancora disponibili).
- Il segnale si calcola con i prezzi fino alla chiusura della barra e si esegue all'apertura della barra dopo; un controllo in [03_segnali.ipynb](../src/03_segnali.ipynb) verifica che lo z-score di una barra non cambi togliendo le barre successive.
- Le notizie si filtrano con l'orario di pubblicazione (`created_at`), mai con quello dell'ultimo aggiornamento; l'agente vede solo notizie uscite prima della decisione.
- Le coppie sono scelte con i prezzi giornalieri fino al 15 giugno, prima dell'inizio dei dati intraday.
- Resta: la classificazione GICS usata per le sotto-industrie è quella di oggi.

**Survivorship bias** (studiare solo chi è sopravvissuto).
- L'universo sono i titoli dell'S&P 500 di oggi: chi è uscito dall'indice manca. Su quattro mesi e mezzo l'effetto è piccolo, ma le coppie sono scelte tra aziende che sappiamo essere rimaste nell'indice. È dichiarato.

**Data snooping** (provare molte cose sugli stessi dati finché una funziona).
- Sul train sono state provate 21 varianti dell'agente, una seconda versione del segnale (scartata) e più selezioni di coppie: è il rischio principale del progetto.
- Le varianti con regole costruite dopo aver visto i risultati (`b_esagerazione`) sono state escluse dalla scelta; il criterio di scelta è stato precisato dopo aver visto il train, ma prima del test (dichiarato).
- Le regole del test sono in [Test.md](Test.md), scritte prima del giro; sono state messe su git solo dopo (dichiarato).
- Per capire se una differenza è fortuna: bootstrap sui giorni, confronto con blocchi a caso, test di Fisher, controlli per coppia e per settore.

**Pretrained model leakage** (un modello pre-addestrato che conosce già il futuro).
- La variante portata sul test usa **FinBERT** (`ProsusAI/finbert`), pubblicato tra il 2019 e il 2020 e addestrato su testi finanziari di quegli anni o precedenti: non può conoscere gli eventi del 2026. Vede solo titolo e sommario delle notizie, mai date, prezzi o risultati.
- I modelli linguistici delle altre varianti (Spark X2.6 4B, Llama 3.2 3B) sono stati usati solo sul train. Per ridurre il rischio i nomi delle aziende erano nascosti ("Company A" e "Company B"); la data di fine addestramento di Spark X2.6 4B non è nota e va dichiarata come limite di quelle varianti.

## 7. Lunghezza del campione e regimi di mercato

- **Perché 96 giorni.** Bloomberg fornisce le barre da 1 minuto solo per gli ultimi mesi: i nostri file vanno dal 16 giugno al 30 ottobre 2026. È tutta la storia intraday disponibile.
- **Perché bastano per stimare la strategia.** A 1 minuto ogni coppia ha circa 37.000 barre; i trade sono 973 sul train e 500 sul test, abbastanza per misurare il guadagno medio con un errore di circa 2 punti base. La strategia apre e chiude in giornata: conta il numero di trade più del numero di anni.
- **Perché non bastano per tutto.** Il professore chiede che train e test contengano regimi di mercato diversi. Non è così: in tutti e due i periodi l'S&P 500 è quasi fermo (+0,15% e +0,47%) con volatilità simile (11,7% e 11,4% annua). I risultati valgono per questo tipo di mercato; non sappiamo come andrebbe in un mercato in forte calo o molto volatile.
- **La divisione** (due terzi train, un terzo test, 64 e 32 giorni) è stata decisa prima di costruire il segnale, uguale per tutte le coppie.

## 8. Limiti

- Periodo breve, un solo regime di mercato (sezione 7).
- Prezzi intraday non aggiustati per i dividendi: lo stacco di un dividendo può spostare lo spread all'apertura.
- La variante è stata scelta su tutto il train, non su una validazione separata dentro il train.
- Costi stimati, non misurati; vendita allo scoperto sempre possibile e senza costi di prestito; ordini eseguiti senza effetto sul prezzo.
- Copertura delle notizie incompleta (una sola fonte); sul test molte più notizie al giorno che sul train.
- Pochi casi per l'agente: 7 blocchi e 21 notizie seguite sul test.
- Tasso privo di rischio 0 nello Sharpe. Lo Sharpe più alto di SPY non è sostenuto dal test statistico: in 32 giorni quello di SPY è troppo incerto.
- Impostazioni non tutte in un file; alcune regole ripetute negli script del test.
