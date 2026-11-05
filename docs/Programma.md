# Pairs Trading intraday con agente di notizie: piano di progetto

Il progetto confronta tre versioni di una strategia di pairs trading intraday (senza agente, con agente che blocca, con agente che decide) e va consegnato il 16 novembre alle 23:59. Entro il 2 novembre vanno chiariti due punti che condizionano tutto il resto: profondità dei dati Bloomberg e fonte delle notizie con orario.

## Cosa è già deciso

L'idea di base è chiara e coerente con il corso: si cercano due aziende simili, si aspetta che i loro prezzi si allontanino più del normale e si scommette sul ritorno alla normalità.

| Tema | Scelta fatta | Cosa significa in pratica |
| --- | --- | --- |
| Strategia | Pairs trading su aziende con business comparabili e andamento storicamente correlato | Si compra il titolo che è rimasto indietro e si vende allo scoperto quello andato troppo avanti |
| Universo | Circa 3 settori, 2-3 coppie per settore | Totale indicativo: 6-9 coppie |
| Anomalia | Lo spread si allontana dalla sua media, calcolata con media mobile esponenziale (EMA) | Il segnale nasce dalla matematica, non da un'opinione |
| Dati | Prezzi intraday (dentro la giornata), da Bloomberg | Frequenza (minuto, 15 minuti, ora) ancora da decidere |
| Agente | Un solo agente che cerca notizie, le legge dal titolo e giudica | Si parte dal titolo, non dall'articolo completo |
| Regola "nessuna notizia" | Movimento senza motivo apparente: si assume che lo spread rientri | Si scommette sul rientro |
| Regola "notizia trovata" | L'agente analizza il tipo di notizia e consiglia long, short, su quale titolo, oppure di restare fermi | È la parte più ambiziosa e va validata con confronti |
| Durata dei trade | Operazioni veloci, chiuse a fine giornata | Nessuna posizione tenuta di notte |
| Obiettivo | Piccoli guadagni percentuali su molte operazioni | I costi di trading diventano decisivi |
| Benchmark | S&P 500 (SPY) | Da affiancare ad altri confronti, vedi la sezione successiva |
| Divisione dei dati | Addestramento e test decisi dopo aver visto quanti dati abbiamo | Regola fissa: parametri solo sul primo periodo, test usato una volta sola |

## Cosa va ancora deciso

Le prime quattro decisioni bloccano il lavoro degli altri e vanno chiuse entro il 2 novembre. Per ciascuna c'è una proposta di partenza, così nessuno resta fermo in attesa.

| # | Decisione | Opzioni | Proposta di partenza | Entro |
| --- | --- | --- | --- | --- |
| 1 | Frequenza delle barre di prezzo | 1 minuto; 5 o 15 minuti; 1 ora | Test su Bloomberg: 15 minuti se la storia copre almeno 5-6 mesi, altrimenti 1 ora | 2 nov |
| 2 | Fonte delle notizie con orario | API di notizie finanziarie con storico; GDELT; archivio Bloomberg | Verificare lo storico con timestamp di 2 o 3 fonti e sceglierne una | 2 nov |
| 3 | Periodo dei dati e divisione train/test | Dipende dai punti 1 e 2 | Primi due terzi per addestramento, ultimo terzo per test, usato una volta sola | 6 nov |
| 4 | Settori e coppie | Esempi: bevande (KO-PEP), pagamenti (V-MA), energia (XOM-CVX), retail (HD-LOW) | Partire da 4 settori candidati e tenere i 3 con più coppie che passano i test | 6 nov |
| 5 | Come si calcola lo spread | Differenza di prezzi con hedge ratio; differenza di log-prezzi; rapporto A/B | Prezzi con hedge ratio stimato nel periodo di addestramento, scelta dichiarata nel report | 7 nov |
| 6 | Parametri del segnale | Finestra EMA, soglia di ingresso, soglia di uscita, stop-loss, tempo massimo | Ingresso a z-score 2, uscita a 0.5, stop a 3.5, tempo massimo di 4 ore; da ottimizzare solo sul periodo di addestramento | 8 nov |
| 7 | Orari di operatività | Tutta la seduta; senza primi e ultimi 15-30 minuti | Escludere i primi 30 minuti (prezzi molto instabili) e chiudere tutto 15 minuti prima della chiusura | 8 nov |
| 8 | Costi di trading | Zero; costo fisso per gamba; costo variabile | Test con 0, 2, 5 e 10 basis points per gamba (1 basis point = 0.01%). Risultato principale: scenario realistico | 8 nov |
| 9 | Dimensione delle posizioni | Importo fisso; proporzionale al segnale | Importo fisso per trade, uguale sulle due gambe, senza leva | 8 nov |
| 10 | Short selling | Assumere sempre possibile; modellare costi di prestito | Assumere possibile e dichiarare l'assunzione nel report | 8 nov |
| 11 | Progetto dell'agente | Modello usato, finestra delle notizie, formato della risposta, strumenti | Un LLM con due strumenti (cerca notizie fino a un certo orario, classifica), risposta in formato fisso | 9 nov |
| 12 | Versioni da confrontare | Solo agente completo; tre versioni | A: senza agente. B: l'agente può solo bloccare. C: l'agente decide | 9 nov |
| 13 | Benchmark | Solo S&P 500; più confronti | SPY buy and hold, liquidità (T-bill), e la versione A come confronto più importante | 9 nov |
| 14 | Cosa consegnare se l'agente non è pronto | Versione minima | Versione A completa più agente testato su un campione di segnali | 6 nov |

## La pipeline passo per passo

La pipeline ha nove passaggi, dal passaggio 0 al passaggio 8. Ognuno produce un risultato concreto che il passaggio successivo usa. È la stessa struttura in cinque fasi del tutorial della Lezione 5 (prezzi, notizie, segnali, metriche, report), allargata con la selezione delle coppie e l'agente.

### Passaggio 0. Verifiche preliminari (1-2 novembre)

Perché: due risposte decidono frequenza dei dati, periodo del test e fattibilità dell'agente.

- Scaricare da Bloomberg un solo titolo con barre da 1, 5, 15 e 60 minuti e annotare quanto indietro arriva ciascuna.
- Cercare 2 o 3 fonti di notizie e verificare per ciascuna: storico disponibile, presenza dell'orario di pubblicazione, filtro per azienda e per data e ora, limiti del piano gratuito.
- Scrivere al professore: numero minimo di coppie, se l'agente deve basarsi su un LLM.

Risultato: una pagina con le due risposte, che chiude le decisioni 1 e 2.

### Passaggio 1. Selezione delle coppie

Perché: una coppia scelta male è come due persone che camminano nella stessa direzione senza elastico. Lo spread non torna indietro e la strategia perde.

L'imbuto completo e i test sono nella sezione "Selezione delle coppie nell'S&P 500", più sotto.

- Per ogni settore elencare titoli USA grandi e molto scambiati (liquidi), così si può comprare e vendere senza muovere il prezzo.
- Scaricare prezzi giornalieri aggiustati, solo del periodo di addestramento.
- Calcolare la correlazione (i prezzi si muovono insieme) e poi il test di cointegrazione di Engle-Granger, in Python `statsmodels.tsa.stattools.coint`. Si tengono le coppie con p-value sotto 0.05: la distanza tra i due prezzi non si allarga all'infinito.
- Stimare l'hedge ratio (quante azioni di B servono per bilanciare una di A) con una regressione.
- Calcolare l'half-life: il tempo che lo spread impiega a tornare a metà strada verso la media. Per operazioni veloci serve un rientro rapido, in ore o pochi giorni. Si ricalcola sulle barre intraday appena sono disponibili.

Risultato: tabella con correlazione, p-value, hedge ratio e half-life, e una lista finale di 6-9 coppie.

Attenzione: la scelta usa solo il periodo di addestramento. Scegliere le coppie guardando anche il periodo di test è data snooping (Lezione 2) e invalida i risultati.

### Passaggio 2. Dati di prezzo intraday

Perché: sono il materiale di base del segnale e della simulazione.

- Scaricare da Bloomberg apertura, massimo, minimo, chiusura e volume di ogni barra per i titoli delle coppie scelte.
- Usare un solo fuso orario (l'ora di New York) e tenere solo la seduta regolare, dalle 9:30 alle 16:00.
- Allineare i due titoli di ogni coppia sullo stesso orario.
- Riempire le barre mancanti solo copiando in avanti il prezzo precedente, mai usando prezzi futuri (Lezione 5).
- Usare prezzi aggiustati per split e dividendi.
- Controllare i dati: un grafico per coppia, il numero di barre per giorno, i giorni a orario ridotto.

Risultato: un file pulito per ogni coppia.

### Passaggio 3. Archivio delle notizie

Perché: l'agente deve poter leggere solo le notizie uscite prima di ogni segnale, altrimenti vede il futuro.

- Scaricare i titoli delle notizie per le aziende scelte, con data e ora esatte.
- Salvare in una tabella: orario, titolo, fonte, azienda, link, nello stesso fuso orario dei prezzi.
- Tenere l'archivio in locale, così il backtest legge sempre gli stessi dati e il risultato è riproducibile.

Risultato: una tabella di notizie con orario.

Attenzione: se per un segnale non si trova nessuna notizia, non significa che non ne siano uscite. Le fonti hanno copertura incompleta. Va scritto nel report.

### Passaggio 4. Spread e segnale

Perché: è il cuore matematico della strategia, indipendente dall'agente.

Prima si costruisce lo spread, cioè la distanza tra i due prezzi, dove A e B sono i due titoli della coppia e β è l'hedge ratio:

```latex
S_t = P^{A}_t - \beta \, P^{B}_t
```

Poi si misura quanto lo spread è lontano dal suo valore normale, in unità di variabilità (z-score). La media e la deviazione standard sono esponenziali (EMA), cioè danno più peso alle barre recenti:

```latex
z_t = \frac{S_t - \mathrm{EMA}(S)_t}{\sigma_t}
```

Regole proposte, tutte da testare:

- z oltre +soglia: spread troppo alto. Short su A, long su B.
- z sotto -soglia: spread troppo basso. Long su A, short su B.
- Uscita quando z torna vicino a 0 (soglia di uscita).
- Stop-loss se z peggiora ancora oltre una soglia. Nel file Week 4 mancava ed era una debolezza.
- Tempo massimo di permanenza e chiusura di tutto a fine giornata.
- Trigger secondario, da decidere: un singolo titolo che si muove in modo anomalo in poche barre, come avete descritto.

Risultato: per ogni coppia, una serie di segnali con orario e direzione.

Attenzione: il segnale si calcola con i dati fino alla chiusura della barra t e l'ordine si esegue alla barra t+1. Eseguire alla stessa barra è lookahead bias (Lezione 2).

### Passaggio 5. Agente di notizie

Perché: distinguere un allargamento dello spread dovuto a rumore (rientra) da uno dovuto a un fatto vero (può non rientrare).

Per ogni segnale l'agente riceve coppia, titolo che si è mosso, orario e direzione, e ha due strumenti:

- ricerca delle notizie sui due titoli in una finestra di tempo che termina all'orario del segnale (la lunghezza va decisa);
- classificazione di ogni titolo di notizia: riguarda entrambe le aziende o una sola, è rumore (risultati, commenti di analisti) o fatto strutturale (acquisizione, indagine, frode, cambio del management), con quale direzione.

La risposta ha formato fisso: decisione, titolo coinvolto, categoria, motivo in una frase. Le decisioni possibili:

- nessuna notizia trovata: si entra scommettendo sul rientro;
- notizia su entrambi i titoli o rumore: si entra sul rientro, eventualmente con dimensione ridotta;
- notizia strutturale su un solo titolo: si blocca il trade, oppure (solo versione C) si entra nella direzione indicata dalla notizia.

Regole di sicurezza: l'agente non cambia le soglie, ogni sua risposta viene salvata con orario e motivo, e se la ricerca fallisce la decisione di default è bloccare.

Controlli:

- il gruppo classifica a mano 30-50 segnali e si confronta con l'agente: la quota di accordo è un risultato da riportare;
- un LLM può già conoscere gli eventi del periodo testato perché li ha visti in addestramento (lookahead bias del modello, Lezione 6). Va dichiarato nel report, e se possibile si testa su un periodo successivo alla sua data di aggiornamento.

Risultato: un file con la decisione dell'agente per ogni segnale.

### Passaggio 6. Simulazione (backtest)

Perché: ricostruire che cosa sarebbe successo seguendo le regole, barra per barra, in ordine cronologico.

- Tre versioni su identici dati: A senza agente, B con agente che può solo bloccare, C con agente che decide.
- Costi per ogni gamba: un trade ha due titoli e quindi quattro operazioni (apertura e chiusura di entrambi). Si simulano più livelli di costo.
- Importo fisso e uguale sulle due gambe, nessuna leva, tutto chiuso a fine giornata.
- Registro di ogni trade: coppia, orari, prezzo, motivo di uscita (rientro, stop, tempo, fine giornata), guadagno lordo e netto.

Il motore si scrive subito su dati finti, così è pronto quando arrivano quelli veri.

Risultato: un registro di trade per ciascuna versione.

### Passaggio 7. Metriche e controlli di robustezza

Perché: dimostrare che un risultato non è fortuna.

- Win rate netto dei costi, profit factor, Sharpe ratio, massimo drawdown, numero di trade, durata media, guadagno medio per trade in basis points.
- Beta e alpha rispetto a SPY (Lezione 5): con il pairs trading il beta dovrebbe essere vicino a zero.
- Risultati per coppia e per settore, per capire se il risultato dipende da una sola coppia.
- Sensibilità ai costi e ai parametri vicini (se funziona solo con un valore esatto, è un campanello d'allarme).
- Bootstrap: intervallo di confidenza al 95% sulla differenza tra versione C e versione A. È il controllo che il progetto dell'anno scorso non aveva.
- Tabella finale con colonna Delta rispetto al benchmark, come nel report dell'anno scorso.

Attenzione: con pochi mesi di dati il numero di trade può essere basso. Conviene sapere presto quanti trade ci sono, perché con poche decine nessuna metrica è affidabile.

Risultato: tabelle e grafici delle curve di capitale.

### Passaggio 8. Report e presentazione

Perché: il voto dipende anche da come si racconta il lavoro.

- Struttura come il progetto più votato dell'anno scorso: ipotesi esplicita, dati ed elaborazione, metodologia con formule, risultati con Delta, curve di capitale, conclusioni divise in punti di forza, debolezze e sviluppi futuri.
- Ogni assunzione dichiarata: short selling, costi, orari, copertura delle notizie, limiti dell'LLM.
- Ipotesi proposta: "Aziende con business simili hanno prezzi legati nel tempo. Gli allargamenti dello spread dovuti a rumore rientrano, quelli dovuti a fatti strutturali no. Un agente che legge le notizie può distinguere i due casi e migliorare i risultati."
- Presentazione il 17 o 19 novembre: ognuno deve saper spiegare tutta la pipeline, non solo la propria parte.

## Il flusso decisionale di ogni trade

&#91;embedded content: flusso decisionale · 1 decisione, 3 esiti\]

Il segnale matematico apre la verifica: l'agente cerca e legge i titoli, poi decide se entrare sul rientro, entrare con dimensione ridotta o bloccare. Nella versione A questo passaggio non esiste. In B l'agente può solo bloccare, in C può anche seguire la notizia.

## Come scegliere la frequenza dei dati

Bloomberg dà dati intraday per gli ultimi 140 giorni di borsa. La frequenza non si sceglie a intuito: si prova la stessa pipeline sulla stessa coppia a frequenze diverse e si confrontano i risultati. Si scarica una sola volta il dato al minuto e si creano da soli le barre da 5, 15 e 60 minuti con `resample` in pandas.

| Frequenza | Barre al giorno | Barre in 140 giorni |
| --- | --- | --- |
| 1 minuto | 390 | circa 54.600 |
| 5 minuti | 78 | circa 10.900 |
| 15 minuti | 26 | circa 3.600 |
| 1 ora | circa 7 | circa 900 |

Per ogni frequenza si confrontano cinque numeri:

1. Half-life dello spread in barre. Se a 1 minuto è di 2 barre, il segnale è quasi tutto rumore. Se è di 10-30 barre, c'è tempo per entrare e uscire.
2. Guadagno medio lordo per trade contro il costo. Ogni trade ha 4 operazioni: se il guadagno è di 3 basis points e i costi di 4, la strategia perde.
3. Numero di trade: almeno 100-200 in totale e 30-50 nel periodo di test.
4. Rumore del prezzo. Sul minuto parte dell'oscillazione è solo il prezzo che rimbalza tra acquisto e vendita, e non è sfruttabile. Se i risultati al minuto sono molto migliori di quelli a 5 minuti, diffidate.
5. Numero di chiamate all'agente: ogni segnale richiede una ricerca e una classificazione, e con migliaia di segnali costi e tempi non reggono.

Punto di partenza: 5 o 15 minuti. La decisione finale spetta al confronto sui vostri dati. Divisione indicativa dei 140 giorni: circa 90 per scegliere regole e parametri, circa 50 per il test, usato una sola volta. Con circa 7 mesi di dati il mercato è sempre dello stesso tipo, e va scritto nel report.

## Selezione delle coppie nell'S&P 500

Le coppie si cercano con un filtro statistico applicato a molti titoli, invece di sceglierle a mano. Le coppie classiche servono solo da controllo: se l'algoritmo le trova, funziona come previsto.

### L'imbuto in 6 passaggi

1. Elenco dei componenti dell'S&P 500 con la classificazione GICS (settore, industria, sotto-industria). Su Bloomberg si esporta dall'indice `SPX Index`.
2. Solo coppie nella stessa industria o sotto-industria: è la parte economica (business comparabili) e riduce molto le coppie da testare. Nel settore "Financials" ci sono banche, assicurazioni e società di pagamenti, che hanno poco in comune.
3. Prezzi giornalieri aggiustati dei 2 anni precedenti all'inizio dei dati intraday. Il periodo di selezione deve finire prima dei 140 giorni, altrimenti la scelta vede il periodo di test (data snooping).
4. Test statistici sul giornaliero (tabella sotto).
5. Filtri pratici: titoli molto liquidi, buona copertura di notizie (le aziende poco note ne hanno poche), nessun evento strutturale nel periodo (acquisizioni, indagini, scissioni).
6. Dati intraday solo per le coppie finaliste, circa 12-18 titoli.

Non si scaricano dati intraday per tutti i 500 titoli: a 1 minuto sarebbero circa 27 milioni di barre, probabilmente oltre i limiti di Bloomberg. Il giornaliero di 500 titoli per 2 anni è circa 250.000 valori, poca roba.

### I test sui dati giornalieri, in ordine

Le soglie sono proposte di partenza e vanno scritte prima di lanciare lo script, senza cambiarle dopo aver visto i risultati.

| # | Test | Che cosa verifica | Soglia proposta | In Python |
| --- | --- | --- | --- | --- |
| 0 | Filtri sul singolo titolo | Il titolo è scambiato abbastanza e ha dati completi | Volume medio alto, nessun buco, quotato da almeno 2 anni | `pandas` |
| 1 | Stessa industria GICS | Le due aziende fanno lo stesso mestiere | Stessa industria o sotto-industria | Colonna GICS |
| 2 | Correlazione dei rendimenti | I due titoli salgono e scendono insieme | Sopra 0.7-0.8 | `DataFrame.corr()` |
| 3 | Cointegrazione (Engle-Granger) | La distanza tra i due prezzi resta stabile | p-value sotto 0.01 | `statsmodels.tsa.stattools.coint` |
| 4 | Hedge ratio e spread | Quante azioni di B bilanciano una di A | Tra 0.5 e 2 | Regressione `OLS` |
| 5 | Half-life | Tempo per tornare a metà strada verso la media | Da 1 a circa 20 giorni | Regressione semplice |
| 6 | Attraversamenti della media | Quante volte l'anno lo spread torna alla media | Almeno 12 all'anno | Conteggio |
| 7 | Ampiezza dello spread | Lo spread oscilla abbastanza da coprire i costi | Molto più grande dei costi | `std()` |
| 8 | Stabilità | La coppia passa i test 3-6 in entrambe le metà del periodo | p-value sotto 0.05 in entrambe, hedge ratio simile | Ripetere i test |
| 9 | Correzione per test multipli | Meno falsi positivi su migliaia di coppie | Controllo FDR (Benjamini-Hochberg) | `statsmodels.stats.multitest.multipletests` |

Punti meno ovvi:

- La correlazione (test 2) si calcola sui rendimenti giornalieri, non sui prezzi. Due prezzi che crescono nel tempo risultano quasi sempre correlati anche se non c'entrano nulla.
- La cointegrazione (test 3) si calcola sui logaritmi dei prezzi, lanciando il test in entrambi i sensi (A su B e B su A) e tenendo il p-value peggiore, per prudenza.
- Lo spread (test 4) si ottiene regredendo il logaritmo del prezzo di A su quello di B. Il coefficiente è l'hedge ratio β.

```latex
S_t = \ln P^{A}_t - \beta \, \ln P^{B}_t
```

- L'half-life (test 5) si ottiene regredendo la variazione giornaliera dello spread sul suo valore del giorno prima. Il coefficiente λ deve essere negativo: se è positivo o vicino a zero, lo spread non rientra e la coppia va scartata.

```latex
S_t - S_{t-1} = \lambda \, S_{t-1} + \varepsilon_t
\qquad
\text{half-life} = -\frac{\ln 2}{\lambda}
```

- L'half-life giornaliera è solo un filtro. Va ricalcolata sulle barre intraday appena disponibili.
- Una coppia può essere cointegrata e inutile se lo spread è quasi immobile (non copre i costi, test 7) o se attraversa la media una volta l'anno (pochi trade, test 6).

### Il rischio dei test multipli

Nelle stesse industrie ci sono circa 12.000-13.000 coppie (stima approssimativa da verificare). Con un test al 5%, circa il 5% risulta cointegrato per caso, cioè centinaia di falsi positivi. Per ridurre il problema: restringere alle sotto-industrie, usare una soglia severa (p-value sotto 0.01), richiedere la stabilità nelle due metà del periodo, applicare la correzione FDR e verificare il buon senso economico. Il test vero sono i 140 giorni intraday: se le coppie scelte non funzionano lì, il filtro era troppo permissivo, e va scritto nel report.

Nel report si può mostrare l'imbuto con i numeri a ogni passaggio (ad esempio: 500 titoli, circa 12.000 coppie nelle stesse industrie, poche centinaia dopo la correlazione, poche decine dopo la cointegrazione, 6-9 finali).

### Quante coppie tenere

Regola proposta da fissare in anticipo: le migliori 6-9 coppie complessive, con al massimo 3 per industria. Così non si forza un settore senza coppie valide e non si dipende da una sola industria. Se il professore chiede esplicitamente 3 settori, si applica il tetto per settore e si prendono le migliori in ciascuno. Dopo i test, classifica semplice: p-value basso, half-life breve, molti attraversamenti, ampiezza alta, poi i controlli su liquidità, notizie ed eventi.

### Coppie classiche da usare come controllo

| Settore | Coppie classiche |
| --- | --- |
| Bevande e consumo | KO-PEP, PG-CL |
| Pagamenti | V-MA |
| Banche USA | JPM-BAC, GS-MS, C-WFC |
| Energia | XOM-CVX, COP-OXY, SLB-HAL |
| Casa e fai da te | HD-LOW |
| Grande distribuzione | WMT-TGT, COST-WMT |
| Altri | T-VZ, PFE-MRK, DAL-UAL, UNP-CSX, UPS-FDX, DUK-SO |

Sono ricavate dalla conoscenza generale e vanno verificate con i dati. Sono da evitare titoli quasi identici (come SPY-VOO o GLD-IAU: lo spread è troppo piccolo e i costi lo cancellano) e titoli quotati in borse diverse.

## Suddivisione del lavoro

La proposta divide il lavoro in due coppie e un lavoro individuale. Le due coppie corrispondono ai due filoni del progetto: i prezzi e il segnale da un lato, le notizie e l'agente dall'altro. La quinta persona costruisce il motore di simulazione su dati finti e li unisce. Le persone sono indicate con numeri: assegnatele in base alle competenze, mettendo chi ha più pratica con Python su prezzi e segnale (persone 1 e 2) e sulla simulazione (persona 5).

| Persona | Ruolo | Passaggi | Come lavora | Risultato |
| --- | --- | --- | --- | --- |
| 1 | Coppie e dati di prezzo | 0 (test Bloomberg), 1, 2 | In coppia con la persona 2 | File di prezzi puliti e tabella delle coppie scelte |
| 2 | Spread e segnale | 4 | In coppia con la persona 1; nei primi giorni prova il codice su 1 o 2 coppie note | Segnali con orario per ogni coppia |
| 3 | Archivio notizie | 0 (fonti), 3 | In coppia con la persona 4 | Tabella di notizie con orario |
| 4 | Agente | 5 | In coppia con la persona 3; nei primi giorni lo costruisce su 20 notizie scritte a mano | Decisione dell'agente per ogni segnale e prova di accordo con la classificazione manuale |
| 5 | Simulazione, metriche, robustezza e regia del report | 6, 7, 8 | Da sola; costruisce il motore su dati finti e lo collega agli altri | Registro dei trade, tabelle finali e report integrato |

Tutti: leggono la sezione della pipeline prima del 2 novembre, scrivono la parte di report del proprio passaggio e preparano la presentazione. Ognuno deve saper spiegare ogni passaggio, perché il professore può chiedere a chiunque.

### Come si collegano le parti

Le parti lavorano in parallelo solo se si accordano subito sul formato dei file che si scambiano. Proposta di formato, da fissare il 2 novembre:

| Da | A | File | Colonne minime |
| --- | --- | --- | --- |
| Persona 1 | Persone 2 e 5 | Prezzi puliti per coppia | orario, titolo, apertura, massimo, minimo, chiusura, volume |
| Persona 2 | Persone 4 e 5 | Segnali | identificativo, orario, coppia, direzione, z-score |
| Persona 3 | Persona 4 | Notizie | orario, titolo, azienda, fonte, link |
| Persona 4 | Persona 5 | Decisioni dell'agente | identificativo del segnale, decisione, categoria, motivo |

### Che cosa fare se qualcuno resta indietro

La persona 5 è la più esposta perché dipende da tutti. Per questo parte subito con dati finti e con segnali casuali, e collega i dati veri uno alla volta. Se la parte notizie non arriva in tempo, si consegna la versione A completa, con l'agente valutato su un campione di segnali (decisione 14).

## Calendario fino al 16 novembre

Mancano 16 giorni alla consegna. Il calendario prevede quattro riunioni di tutto il gruppo, una a ogni scadenza, e lascia i due ultimi giorni prima della consegna per il report.

| Date | Fase | Cosa deve essere pronto | Riunione di gruppo |
| --- | --- | --- | --- |
| 31 ott - 2 nov | Verifiche e decisioni | Test Bloomberg, fonti di notizie valutate, email al professore, formato dei file, ruoli assegnati. Decisioni 1-2 chiuse | 2 nov: confermare frequenza, fonte e ruoli |
| 3 - 6 nov | Dati | Coppie scelte, prezzi intraday puliti, archivio notizie almeno per una coppia, motore di simulazione su dati finti | 6 nov: dati pronti? Decidere il periodo di test |
| 7 - 10 nov | Costruzione | Segnali su tutte le coppie, agente funzionante su un campione, simulazione della versione A con dati veri | 10 nov: pipeline completa su un campione |
| 11 - 13 nov | Risultati | Versioni A, B e C, scenari di costo, controlli di robustezza, bootstrap, grafici | 13 nov: risultati e storia da raccontare |
| 14 - 15 nov | Report | Bozza completa, revisione incrociata, prova di presentazione | 15 nov: prova generale |
| 16 nov | Consegna | Invio entro le 23:59, meglio entro le 18:00 |  |
| 17 o 19 nov | Presentazione | Tutti sanno spiegare tutta la pipeline |  |

Punto di verifica per decidere se tagliare: il 10 novembre, se la versione A non gira ancora su dati veri, si rinuncia alla versione C e si lavora su A e B.

## Limiti da dichiarare nel report

Dichiarare i limiti in modo esplicito è un punto di forza, come nel report dell'anno scorso. Questi sono quelli che già conosciamo.

- Periodo breve: con dati intraday la storia disponibile è di pochi mesi, quindi un solo tipo di mercato. I risultati hanno molta incertezza e il numero di trade va riportato sempre.
- Costi: commissioni, spread tra prezzo di acquisto e di vendita e slippage (differenza tra prezzo atteso e ottenuto) sono stimati, non misurati.
- Short selling: si assume che sia sempre possibile, senza costi di prestito.
- Esecuzione ideale: gli ordini si eseguono al prezzo della barra successiva, senza effetto sul mercato.
- Notizie: la copertura delle fonti è incompleta, l'agente legge solo il titolo, e nessuna notizia trovata non vuol dire nessuna notizia uscita.
- LLM: il modello può già conoscere gli eventi del periodo testato, e questo falsa il test.
- Coppie: scelte sul passato. Il legame tra due aziende può rompersi in futuro, ed è proprio il rischio che l'agente deve intercettare.
- Win rate: da solo non basta a dire che la strategia guadagna. Contano anche l'importo medio di vincite e perdite (profit factor).
