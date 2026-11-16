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
| 1 | Frequenza delle barre di prezzo | 1 minuto; 5 o 15 minuti; 1 ora | **Deciso: 1 minuto come base**; file a 5, 15 e 60 minuti pronti per il confronto di robustezza (vedi Passaggio 2) | 2 nov |
| 2 | Fonte delle notizie con orario | API di notizie finanziarie con storico; GDELT; archivio Bloomberg | Verificare lo storico con timestamp di 2 o 3 fonti e sceglierne una. **Provvisorio: Alpaca (Benzinga), provata sulle 10 coppie, vedi Passaggio 3, dove ci sono anche le altre fonti possibili** | 2 nov |
| 3 | Periodo dei dati e divisione train/test | Dipende dai punti 1 e 2 | Primi due terzi per addestramento, ultimo terzo per test, usato una volta sola. Ora sappiamo che i giorni sono 96 (91 per 4 coppie): circa 64 e 32. **Applicato: train fino al 16 settembre, test dal 17 settembre, uguali per tutte le 10 coppie (60-64 giorni di train, 31-32 di test)** | 6 nov |
| 4 | Settori e coppie | Esempi: bevande (KO-PEP), pagamenti (V-MA), energia (XOM-CVX), retail (HD-LOW) | Partire da 4 settori candidati e tenere i 3 con più coppie che passano i test | 6 nov |
| 5 | Come si calcola lo spread | Differenza di prezzi con hedge ratio; differenza di log-prezzi; rapporto A/B | Prezzi con hedge ratio stimato nel periodo di addestramento, scelta dichiarata nel report. **Provvisorio sulle 10 coppie: log-prezzi con β = 1 (importi uguali), vedi Passaggio 4** | 7 nov |
| 6 | Parametri del segnale | Finestra EMA, soglia di ingresso, soglia di uscita, stop-loss, tempo massimo | Ingresso a z-score 2, uscita a 0.5, stop a 3.5, tempo massimo di 4 ore; da ottimizzare solo sul periodo di addestramento. **Provvisorio sulle 10 coppie, uguali per tutte (solo train): emivita 60 minuti, ingresso 2.0, uscita 0, stop 3.5, tempo massimo 90 minuti. I parametri si possono scegliere anche coppia per coppia, vedi Passaggio 4** | 8 nov |
| 7 | Orari di operatività | Tutta la seduta; senza primi e ultimi 15-30 minuti | Escludere i primi 30 minuti (prezzi molto instabili) e chiudere tutto 15 minuti prima della chiusura | 8 nov |
| 8 | Costi di trading | Zero; costo fisso per gamba; costo variabile | Test con 0, 2, 5 e 10 basis points per gamba (1 basis point = 0.01%). Risultato principale: scenario realistico | 8 nov |
| 9 | Dimensione delle posizioni | Importo fisso; proporzionale al segnale | Importo fisso per trade, uguale sulle due gambe, senza leva | 8 nov |
| 10 | Short selling | Assumere sempre possibile; modellare costi di prestito | Assumere possibile e dichiarare l'assunzione nel report | 8 nov |
| 11 | Progetto dell'agente | Modello usato, finestra delle notizie, formato della risposta, strumenti | Un LLM con due strumenti (cerca notizie fino a un certo orario, classifica), risposta in formato fisso | 9 nov |
| 12 | Versioni da confrontare | Solo agente completo; tre versioni | A: senza agente. B: l'agente può solo bloccare. C: l'agente decide | 9 nov |
| 13 | Benchmark | Solo S&P 500; più confronti | SPY buy and hold, liquidità (T-bill), e la versione A come confronto più importante | 9 nov |
| 14 | Cosa consegnare se l'agente non è pronto | Versione minima | Versione A completa più agente testato su un campione di segnali | 6 nov |

## Come rilanciare il lavoro sul proprio computer

Le istruzioni, passo per passo e con i comandi da eseguire, sono in [src/README.md](../src/README.md): ambiente, dati Bloomberg, chiavi di Alpaca, ordine dei passi, tempo e memoria di ciascuno.

La pipeline in `src/` è quella delle 15 coppie. I notebook delle prime 10 coppie, le prime prove su MA-V e la versione 2 del segnale sono in `Old files/`, con la struttura di cartelle che avevano: i link di questo documento puntano lì.

## Chi ha fatto cosa

Registro del lavoro dei passaggi 3 e 4, scritto perché tutto il gruppo sappia cosa è stato fatto, da chi e come ripeterlo. Il codice e i notebook sono stati scritti con **Claude Code** (assistente AI di Anthropic) su richiesta e con le decisioni di Bea; Claude Code ha anche eseguito i notebook e scritto la documentazione di questo file. Le decisioni, le credenziali e i comandi lanciati da Bea sono segnati sotto.

| Cosa | Chi | Note |
| --- | --- | --- |
| Scegliere di provare prima una sola coppia, **MA-V**, e di dividere i dati intraday in train e test | **Bea** | Il taglio (64 giorni di train, 32 di test) è stato proposto da Claude Code e accettato da Bea |
| Scegliere la **EMA continua** per lo z-score (con confronto con quella azzerata ogni giorno) | **Bea** | |
| Chiedere di documentare tutto in modo che il gruppo possa seguire e rilanciare | **Bea** | Notebook con spiegazioni e motivazioni; questo file |
| Passaggio 4 su MA-V: codice, notebook, scelta dei parametri | Claude Code | Regola di scelta dei parametri scritta prima di guardare i risultati |
| Creare l'account Alpaca e generare le chiavi API | **Bea** | Le chiavi sono solo sul suo computer, nel file `.env`: non sono nel repository e non vanno condivise |
| Creare il file `.env` con le chiavi | **Bea** | Dal modello `.env.example` |
| Chiamata di prova all'API (`--probe`) | **Bea** | Dal terminale. Esito: chiavi accettate, storico di giugno-settembre accessibile |
| Scaricare le notizie di MA e V (`python -m src.news`) | **Bea** | Dal terminale: 174 notizie |
| Scrivere il codice di scaricamento (`src/news.py`) e i notebook delle notizie | Claude Code | |
| Estendere segnali e notizie alle altre 9 coppie, **con parametri uguali per tutte** | Decisione di **Bea** | Claude Code ha scritto il codice ed eseguito i notebook |
| Scaricare le notizie dei 20 titoli (`--pair ALL10`) | Claude Code, con le chiavi di Bea | Su richiesta di Bea ("estendi alle altre coppie"): 1250 notizie |
| Chiedere di segnare che i parametri possono essere scelti anche coppia per coppia, e di elencare altre fonti di notizie | **Bea** | Nei passaggi 3 e 4 |
| Controllo a mano degli orari delle notizie | **Da fare** | Vedi Passaggio 3, decisione 1 |

## La pipeline passo per passo

**Versioni delle coppie.** Il lavoro ha ora due versioni separate. La **versione 1** sono le prime 10 coppie (selezione, dati intraday, notizie e segnali sono descritti nei passaggi 1-4). La **versione 2** è una nuova selezione di 15 coppie, fatta ripartendo dall'inizio con criteri diversi, e ha i suoi file e le sue sezioni ("Passaggio 1, versione 2" e "Passaggio 2, versione 2"). Quando si dice "versione 2" si intendono sempre queste coppie. Le due versioni non si mescolano: i file della versione 2 hanno suffisso `_2` o `_v2`.

La pipeline ha nove passaggi, dal passaggio 0 al passaggio 8. Ognuno produce un risultato concreto che il passaggio successivo usa. È la stessa struttura in cinque fasi del tutorial della Lezione 5 (prezzi, notizie, segnali, metriche, report), allargata con la selezione delle coppie e l'agente.

### Passaggio 0. Verifiche preliminari (1-2 novembre)

Perché: due risposte decidono frequenza dei dati, periodo del test e fattibilità dell'agente.

- Scaricare da Bloomberg un solo titolo con barre da 1, 5, 15 e 60 minuti e annotare quanto indietro arriva ciascuna.
- Cercare 2 o 3 fonti di notizie e verificare per ciascuna: storico disponibile, presenza dell'orario di pubblicazione, filtro per azienda e per data e ora, limiti del piano gratuito.
- Scrivere al professore: numero minimo di coppie, se l'agente deve basarsi su un LLM.

Risultato: una pagina con le due risposte, che chiude le decisioni 1 e 2.

### Passaggio 1. Selezione delle coppie

> Questa sezione descrive la **versione 1** (10 coppie). La **versione 2** (selezione separata, 15 coppie) è descritta in "Passaggio 1, versione 2", subito prima del Passaggio 2.

Stato: **fatto in gran parte** (restano tre controlli, vedi più sotto). Il lavoro è nel notebook [Old files/src/01_selezione_coppie/coppie.ipynb](../Old%20files/src/01_selezione_coppie/coppie.ipynb), che contiene il codice, le motivazioni di ogni scelta e il testo dei risultati. La lista finale è salvata in `data/processed/selected_pairs.csv` (cartella ignorata da git: chi la vuole rilancia il notebook).

Perché: una coppia scelta male è come due persone che camminano nella stessa direzione senza elastico. Lo spread non torna indietro e la strategia perde.

#### Cosa prevedeva il programma

- Per ogni settore elencare titoli USA grandi e molto scambiati (liquidi), così si può comprare e vendere senza muovere il prezzo.
- Scaricare prezzi giornalieri aggiustati, solo del periodo di addestramento.
- Calcolare la correlazione (i prezzi si muovono insieme) e poi il test di cointegrazione di Engle-Granger, in Python `statsmodels.tsa.stattools.coint`. Si tengono le coppie con p-value sotto 0.05: la distanza tra i due prezzi non si allarga all'infinito.
- Stimare l'hedge ratio (quante azioni di B servono per bilanciare una di A) con una regressione.
- Calcolare l'half-life: il tempo che lo spread impiega a tornare a metà strada verso la media.

Risultato atteso: tabella con correlazione, p-value, hedge ratio e half-life, e una lista finale di 6-9 coppie.

Attenzione: la scelta usa solo il periodo di addestramento. Scegliere le coppie guardando anche il periodo di test è data snooping (Lezione 2) e invalida i risultati.

#### Cosa abbiamo fatto

1. **Periodo di selezione: dal 16 giugno 2021 al 15 giugno 2026** (5 anni, circa 1.255 giorni di borsa). Finisce il giorno prima dell'inizio dei dati intraday (16 giugno 2026): così la scelta non vede il periodo di test. Parte dopo lo shock del Covid di marzo 2020, che muove tutti i titoli insieme e falsa le distanze.
2. **Titoli liquidi e con dati completi.** Si tengono i titoli con valore scambiato mediano (prezzo per volume) di almeno 50 milioni di dollari al giorno, e con prezzi in tutto il periodo: da 501 titoli restano **307**. Il prezzo usato è `PX_LAST`, già aggiustato per split e dividendi (senza aggiustamento un frazionamento sembrerebbe un crollo).
3. **Solo coppie nello stesso gruppo industriale GICS.** Dal file Bloomberg `data/gics.csv` usiamo `industry_group` (25 gruppi). Aziende dello stesso gruppo hanno clienti, costi e normativa simili e sono esposte agli stessi fattori: è la ragione economica per cui il loro prezzo relativo dovrebbe tornare normale. Le coppie possibili passano da **46.971** a **2.390**.
4. **Metodo della distanza** (Gatev, Goetzmann e Rouwenhorst, 2006). Ogni prezzo viene diviso per il suo primo valore (indice di 1 dollaro investito all'inizio) e per ogni coppia si somma, su tutti i giorni, il quadrato della differenza tra i due indici (SSD). Più è bassa, più i due titoli sono rimasti vicini. Equivale a investire lo stesso capitale sui due titoli, come abbiamo deciso per le posizioni (importo uguale sulle due gambe, senza leva).
5. **Regole di selezione**, fissate prima di guardare i risultati:
   - si toglie GOOG-GOOGL (correlazione dei rendimenti sopra 0.97, sono due classi di azioni della stessa società: lo spread è troppo piccolo e i costi lo cancellano) → 2.389 coppie;
   - si tengono le coppie con correlazione dei rendimenti giornalieri di almeno 0.6 → **467** coppie;
   - si ordina per SSD crescente e si prendono le prime **9**, con un solo titolo per coppia e al massimo 3 coppie per gruppo.
6. **Una coppia aggiunta per scelta**: KO-PEP, fuori dalla regola (vedi sotto). In totale **10 coppie**.
7. **Diagnostiche su ogni coppia**: p-value di cointegrazione (Engle-Granger sui log-prezzi, in entrambi i sensi, tenendo il peggiore), hedge ratio, half-life, attraversamenti della media all'anno, ampiezza dello spread e stabilità nelle due metà del periodo. Servono a conoscere le coppie e a segnalare le più rischiose, non a scartarle.
8. **Confronti**: l'imbuto della cointegrazione sulle stesse coppie del gruppo (con correzione FDR di Benjamini-Hochberg), le 14 coppie "da manuale" indicate in anticipo (KO-PEP, V-MA, HD-LOW, XOM-CVX, BAC-WFC, GS-MS, UPS-FDX, LMT-NOC, PG-CL, MCD-YUM, DUK-SO, MRK-PFE, T-VZ, CME-ICE) e la stessa regola rifatta su 10, 15 e 20 anni.

#### Cosa abbiamo fatto in modo diverso dal programma

| Tema | Programma | Cosa abbiamo fatto | Perché |
| --- | --- | --- | --- |
| Metodo principale | Correlazione, poi cointegrazione con p-value sotto 0.01 come filtro | Metodo della distanza come metodo principale; la cointegrazione resta come confronto e diagnostica | Sul giornaliero e su 5 anni la cointegrazione è troppo severa: solo 11 coppie su 173 testate hanno p-value sotto 0.05 e nessuna supera l'intero imbuto (half-life, stabilità nelle due metà, FDR). Misura inoltre un orizzonte di mesi, mentre i nostri trade durano ore. La distanza è il metodo di riferimento della letteratura (Gatev et al., 2006) e non richiede di assumere un modello |
| Periodo di selezione | Circa 2 anni prima dell'intraday | 5 anni, fino al 15 giugno 2026 | Con 2 anni la classifica è troppo sensibile al caso. Più anni vorrebbero dire più titoli esclusi e più regimi di mercato (vedi controllo di robustezza) |
| Correlazione minima | 0.7-0.8 | 0.6, solo come pavimento | Con la distanza è la distanza a scegliere: la correlazione serve a evitare coppie che hanno solo fatto percorsi simili senza muoversi insieme giorno per giorno |
| p-value di cointegrazione | Sotto 0.01 | Sotto 0.05, solo come diagnostica | Il test non è un filtro del metodo principale; la severità la dà la correzione FDR |
| Half-life | Da 1 a circa 20 giorni | Da 1 a 30 giorni, solo come diagnostica | È il tempo in giorni, mentre i trade durano ore: va ricalcolata sulle barre intraday. Il programma stesso la considera "solo un filtro" |
| Settori | Circa 3 settori, 2-3 coppie per settore | 7 gruppi industriali, al massimo 3 coppie per gruppo | La regola evita di forzare un settore senza coppie valide e di dipendere da uno solo; il numero di settori non è vincolante |
| Numero di coppie | 6-9 | 10 (9 dalla regola, 1 aggiunta per scelta) | Il numero lo decidiamo noi: non è vincolante |
| Un titolo per coppia | Non previsto | Ogni titolo compare in una sola coppia | Rende i trade delle coppie più indipendenti tra loro |

Tutte le soglie "nostre" sono scelte ragionevoli e dichiarate prima dei risultati, ma non hanno una fonte accademica e non sono ottimizzate. Alcune regole (correlazione minima, tetto per gruppo) sono state definite dopo aver visto i primi risultati sul periodo giornaliero: il test intraday resta pulito perché non è stato usato per scegliere nulla.

#### Le 10 coppie scelte

| Coppia | Origine | Gruppo GICS | Posto SSD (su 2.390) | Correlazione | Ampiezza spread | p-value cointegrazione | Half-life (giorni) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MA-V | regola | Servizi finanziari | 1 | 0.88 | 3.3% | 0.081 | 32 |
| TFC-USB | regola | Banche | 3 | 0.83 | 6.6% | 0.370 | 49 |
| BAC-PNC | regola | Banche | 4 | 0.79 | 5.9% | 0.066 | 40 |
| CSX-UNP | regola | Trasporto | 5 | 0.72 | 6.3% | 0.505 | 56 |
| PYPL-XYZ | regola | Servizi finanziari | 6 | 0.61 | 17.7% | 0.557 | 62 |
| BNY-GS | regola | Servizi finanziari | 7 | 0.67 | 6.4% | 0.037 | 31 |
| HD-LOW | regola | Beni discrezionali (distribuzione) | 8 | 0.87 | 5.2% | 0.144 | 52 |
| ITW-OTIS | regola | Beni strumentali | 10 | 0.61 | 7.9% | 0.923 | 110 |
| MCD-YUM | regola | Servizi al consumatore | 11 | 0.61 | 5.8% | 0.122 | 44 |
| KO-PEP | aggiunta per scelta | Alimenti, bevande e tabacco | 240 | 0.68 | 15.4% | 0.946 | infinita |

Il posto in classifica è quello tra tutte le 2.390 coppie dello stesso gruppo: i posti mancanti sono coppie scartate dalle regole (quasi identiche, correlazione bassa, titolo già usato in un'altra coppia).

**Perché queste coppie** (le descrizioni dei business sono dalla conoscenza generale: da verificare prima di metterle nel report):

- **MA-V**: le due grandi reti di pagamento con carta. Stesso modello di business, stessi clienti, ricavi legati ai volumi di spesa dei consumatori. È la più vicina in assoluto nel periodo.
- **TFC-USB**: banche commerciali USA di dimensione simile, stessa esposizione ai tassi d'interesse e al credito retail.
- **BAC-PNC**: banche commerciali USA (BAC più grande, PNC regionale): stessi fattori di tassi e credito, ma il mix di attività non è identico.
- **CSX-UNP**: due ferrovie merci USA, con gli stessi volumi di carico, la stessa regolamentazione e gli stessi costi (carburante, lavoro).
- **PYPL-XYZ**: pagamenti digitali per consumatori e commercianti (XYZ è Block). Settore comune, ma ampiezza dello spread molto alta (17.7%) e correlazione bassa: coppia più rischiosa.
- **BNY-GS**: servizi finanziari, ma BNY fa custodia e gestione e GS investment banking. Legame economico più debole; è l'unica coppia con p-value di cointegrazione sotto 0.05.
- **HD-LOW**: i due grandi distributori USA per la casa e il fai-da-te. Stessi clienti, stessa stagionalità, stessa sensibilità al mercato immobiliare.
- **ITW-OTIS**: stesso gruppo GICS ("beni strumentali", molto ampio) ma business diversi, componenti industriali contro ascensori. Legame debole e half-life lunga (110 giorni): coppia più rischiosa.
- **MCD-YUM**: ristorazione rapida in franchising, con la stessa struttura dei ricavi e la stessa sensibilità alla spesa dei consumatori.
- **KO-PEP**: Coca-Cola e Pepsi, stesso mercato delle bevande analcoliche, stessi clienti e canali di vendita; è l'esempio classico di pair trading. **È un'eccezione**: l'abbiamo aggiunta per scelta del gruppo, fuori dalla regola. Nei dati non è tra le coppie più vicine (posto 240), non risulta cointegrata e l'half-life giornaliera è infinita. Nel report va presentata come scelta nostra e i risultati vanno mostrati anche senza di lei.

**Cosa emerge dai controlli**

- Delle 14 coppie "da manuale", la regola ne seleziona 3 (V-MA, HD-LOW, MCD-YUM). Le altre sono più in basso in classifica o hanno correlazione troppo bassa (per esempio KO-PEP è al posto 240).
- Nessuna coppia passa tutti i test sul giornaliero. Il legame statistico su 5 anni è debole: i prezzi si sono mossi vicini, ma non c'è una forte prova di ritorno alla media. La lista è quindi un elenco di candidate: la prova che funzionano arriva solo dall'addestramento e dal test sui dati intraday, usato una sola volta.
- **Robustezza al periodo.** Rifacendo la stessa regola su 10, 15 e 20 anni, solo TFC-USB, BAC-PNC e MCD-YUM restano tra le 9 scelte in almeno 2 finestre su 4. Con più anni i titoli con storia completa scendono da 307 a 226, 143 e 104 (più survivorship bias). Altre coppie più "pulite" dei periodi lunghi (per esempio HAL-SLB, in 3 finestre) non sono state aggiunte: farlo ora, dopo aver visto i risultati, sarebbe adattare la scelta ai dati.

#### Non ancora fatto

- Controllo della **copertura delle notizie** sui 20 titoli delle coppie (l'agente ne ha bisogno).
- Controllo di **eventi strutturali** nel periodo (acquisizioni, indagini, scissioni) sui 20 titoli.
- Confronto numerico tra **ampiezza dello spread e costi** di trading (4 operazioni per trade).

#### Limiti da dichiarare nel report

- **Survivorship bias**: l'universo sono i titoli dell'S&P 500 di oggi.
- **GICS attuale**, non storico: la riclassificazione del 2018 ha spostato alcune aziende.
- **Un solo periodo di selezione**: le coppie sono scelte sul passato e il legame può cambiare.
- **Soglie nostre**, senza fonte accademica, e alcune fissate dopo aver visto i primi risultati giornalieri.
- **Diagnostiche giornaliere** (half-life, cointegrazione): misurano giorni e mesi, mentre i trade durano ore; vanno ricalcolate sull'intraday.
- **Test multipli**: la distanza classifica migliaia di coppie, quindi alcune sono "vicine per caso". Le coppie testate sono 2.390.
- **KO-PEP** è una coppia aggiunta per scelta, non selezionata dai dati.

Riferimenti (da verificare prima di citarli): Gatev, Goetzmann e Rouwenhorst (2006), Review of Financial Studies 19(3); Engle e Granger (1987), Econometrica 55(2); Benjamini e Hochberg (1995), Journal of the Royal Statistical Society B 57(1); Vidyamurthy (2004), Pairs Trading, Wiley.

### Passaggio 1, versione 2. Selezione separata delle coppie

Stato: **fatto**. Le coppie sono 15 e il gruppo ha deciso di **tenerle tutte** (il programma ne prevede 6-9). Il lavoro è nel notebook [src/01_coppie.ipynb](../src/01_coppie.ipynb), che contiene il codice, le motivazioni di ogni scelta e il testo dei risultati generato dai dati. La lista è salvata in `data/processed/selected_pairs_2.csv` (cartella ignorata da git: chi la vuole rilancia il notebook). La versione 1 (`coppie.ipynb`, `selected_pairs.csv`) non è stata toccata.

Perché una seconda versione: la versione 1 sceglieva per distanza dei prezzi dentro gruppi industriali ampi, e alcune coppie hanno un legame economico debole (per esempio BNY-GS, ITW-OTIS). Abbiamo deciso di ripartire dall'inizio con criteri più vicini all'obiettivo del progetto: **stesso settore e legame forte**, con titoli davvero scambiati.

#### Criteri scelti dal gruppo e come diventano regole

| Criterio | Regola nel notebook |
| --- | --- |
| Stesso settore, legame economico riconoscibile | Stessa **sotto-industria GICS** (più stretta del gruppo industriale usato nella versione 1) |
| Legame forte | Correlazione dei rendimenti giornalieri tra 0.6 e 0.95, poi classifica per distanza dei prezzi (SSD, Gatev et al., 2006) |
| Titoli realmente scambiati | Valore scambiato giornaliero mediano (prezzo per volume) di almeno 100 milioni di dollari per entrambi i titoli |
| Non sono filtri | **Costi** (il professore ha detto di non considerarli), **notizie** (sono il Passaggio 3), **eventi strutturali** noti (le coppie che li hanno restano e vanno segnalate nel report) |

Non si usano i dati intraday in questa parte: la selezione usa solo dati giornalieri fino al 15 giugno 2026, il giorno prima dell'inizio dei dati intraday, come nella versione 1.

#### Cosa abbiamo fatto

1. **Periodo di selezione**: dal 16 giugno 2021 al 15 giugno 2026 (5 anni, 1.255 giorni di borsa), come nella versione 1, per poter confrontare le due.
2. **Titoli**: da 501 titoli, **166** hanno valore scambiato giornaliero mediano di almeno 100 milioni di dollari e **154** hanno anche dati quasi completi (al massimo l'1% di giorni mancanti). I 20 titoli della versione 1 non sono esclusi: se la regola li sceglie di nuovo, restano.
3. **Stessa sotto-industria**: i 154 titoli sono in 64 sotto-industrie, di cui 38 con almeno 2 titoli. Le coppie possibili sono **249**.
4. **Filtro di correlazione**: si toglie GOOG-GOOGL (correlazione 0.996, sono due classi di azioni della stessa società), si scartano 176 coppie con correlazione sotto 0.6 e restano **72** coppie.
5. **Metodo della distanza**: le 72 si ordinano per SSD crescente. Dall'alto si prende una coppia se nessuno dei due titoli è già usato e se il gruppo industriale non ha già 3 coppie, fino a 15. Nessuna coppia è stata aggiunta, tolta o sostituita a mano.
6. **Diagnostiche** (cointegrazione, hedge ratio, half-life, attraversamenti, stabilità nelle due metà): servono a descrivere le coppie, **non** a sceglierle né a scartarle.

#### Cosa abbiamo fatto in modo diverso dalla versione 1

| Tema | Versione 1 | Versione 2 | Perché |
| --- | --- | --- | --- |
| Settore | Gruppo industriale GICS (25 gruppi) | Sotto-industria GICS (più stretta) | Legame economico più riconoscibile |
| Liquidità | Almeno 50 milioni di dollari al giorno | Almeno 100 milioni di dollari al giorno | Si vogliono titoli davvero scambiati; soglia nostra, senza fonte |
| Correlazione | Almeno 0.6 | Tra 0.6 e 0.95 | Sopra 0.95 i due titoli sono quasi la stessa azione |
| Titoli della versione 1 | Non applicabile | Non esclusi | Se sono coppie valide per l'obiettivo, restano |
| Coppie aggiunte per scelta | KO-PEP | Nessuna | Tutte le coppie sono scelte dalla regola |
| Numero di coppie | 10 | 15, tutte tenute | Decisione del gruppo; supera le 6-9 del programma, da dichiarare nel report |
| Costi, notizie, eventi | Non filtri (costi in parte) | Non filtri, per scelta del gruppo | Vedi tabella dei criteri |

#### Le 15 coppie scelte

| Coppia | Sotto-industria | Posto SSD (su 249) | Correlazione | Ampiezza spread | p-value cointegrazione | Half-life (giorni) | Evento noto (da verificare) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MA-V | Servizi di elaborazione transazioni | 1 | 0.88 | 3.3% | 0.081 | 32 | nessuno |
| CSX-UNP | Trasporto ferroviario | 3 | 0.72 | 6.3% | 0.505 | 56 | UNP ha annunciato la fusione con Norfolk Southern (2025) |
| PYPL-XYZ | Servizi di elaborazione transazioni | 4 | 0.61 | 17.7% | 0.557 | 62 | nessuno |
| HD-LOW | Vendita al dettaglio per la casa | 5 | 0.87 | 5.2% | 0.144 | 52 | HD ha acquisito SRS (2024), LOW FBM (2025) |
| DHR-TMO | Strumenti e servizi per le scienze della vita | 6 | 0.81 | 7.1% | 0.286 | 62 | DHR ha scorporato Veralto (2023) |
| CRM-WDAY | Software applicativi | 7 | 0.65 | 13.6% | 0.401 | 68 | CRM ha acquisito Informatica (2025) |
| JPM-WFC | Altre banche | 8 | 0.76 | 10.6% | 0.172 | 110 | WFC: tetto agli attivi tolto (2025) |
| NXPI-TXN | Semiconduttori | 9 | 0.76 | 11.3% | 0.790 | 66 | nessuno |
| ELV-UNH | Cure mediche | 10 | 0.63 | 11.3% | 0.114 | 60 | nessuno |
| CL-PG | Prodotti per la casa | 17 | 0.72 | 6.1% | 0.065 | 62 | nessuno |
| GS-MS | Banche d'investimento e broker | 24 | 0.84 | 10.2% | 0.048 | 157 | nessuno |
| ISRG-SYK | Attrezzatura sanitaria | 25 | 0.63 | 14.2% | 0.084 | 110 | nessuno |
| KO-PEP | Bibite analcoliche | 27 | 0.68 | 15.4% | 0.946 | infinita | nessuno |
| BAC-C | Altre banche | 29 | 0.81 | 16.5% | 0.587 | infinita | C: vendita di Banamex in corso |
| COP-EOG | Esplorazione e produzione di petrolio | 40 | 0.87 | 7.0% | 0.218 | 55 | COP ha acquisito Marathon Oil (2024) |

Gli eventi noti sono scritti a memoria e **vanno verificati** prima di metterli nel report. Il notebook riporta per ogni coppia anche una descrizione economica breve.

#### Cosa emerge

- **Sovrapposizione con la versione 1**: 5 coppie su 15 sono le stesse (MA-V, CSX-UNP, PYPL-XYZ, HD-LOW, KO-PEP); 10 sono nuove. Cinque coppie della versione 1 non ci sono più (BAC-PNC, BNY-GS, ITW-OTIS, MCD-YUM, TFC-USB), per la soglia di liquidità più alta, per la sotto-industria più stretta o per il tetto per gruppo (per esempio GS è ora con MS e BAC con C). Il motivo esatto per ogni singola coppia non è stato verificato. KO-PEP, che nella versione 1 era stata aggiunta a mano, qui è scelta dalla regola (posto 27 su 249).
- **Il legame statistico sul giornaliero è debole**: una sola coppia ha p-value di cointegrazione sotto 0.05 (GS-MS, 0.048), quattro sotto 0.10 (con MA-V, ISRG-SYK e CL-PG). KO-PEP e BAC-C hanno half-life non definita nel periodo. Come per la versione 1, la lista è un elenco di candidate: la prova che funzionano arriva dall'intraday.
- **Stabilità**: molte coppie hanno una distanza molto diversa nelle due metà del periodo (per esempio GS-MS, NXPI-TXN, CRM-WDAY): il legame non è costante.
- **Coppie esaminate**: 249 (test multipli: alcune sono vicine per caso).

#### Non ancora fatto

- Nessuna rifinitura della lista: si lavora su tutte le 15 coppie (decisione del gruppo). Più coppie vuol dire più chiamate all'agente di notizie e più test multipli.
- Verifica degli eventi strutturali e delle descrizioni economiche.

#### Limiti da dichiarare nel report

- **Survivorship bias** e **GICS attuale**, come nella versione 1.
- **Soglie nostre** (100 milioni di dollari, correlazione 0.6-0.95, tetto 3 per gruppo, 15 coppie), senza fonte accademica. Prima di scrivere il notebook abbiamo guardato una volta la distribuzione di liquidità dei titoli e una lista provvisoria; il gruppo ha poi tolto i filtri su notizie, costi, eventi e sui titoli già usati dopo aver visto le prime esecuzioni. Le soglie non sono ottimizzate sulla lista finale, ma non sono indipendenti dai dati.
- **Eventi strutturali non esclusi**: alcune coppie hanno fusioni, acquisizioni o scorpori nel periodo; per quelle il legame può essere cambiato.
- **Costi non considerati** (indicazione del docente).
- **Test multipli**: 249 coppie esaminate.
- **Legame statistico debole** sul giornaliero (una sola coppia con p-value sotto 0.05).

### Passaggio 2. Dati di prezzo intraday

> Questa sezione descrive la **versione 1** (10 coppie). La **versione 2** (15 coppie) è descritta in "Passaggio 2, versione 2", subito prima del Passaggio 3.

Stato: **fatto** per la parte di pulizia; restano tre decisioni collegate (vedi "Decisioni ancora da prendere"). Il lavoro è nel notebook [Old files/src/02_dati_intraday/intraday_pulizia.ipynb](../Old%20files/src/02_dati_intraday/intraday_pulizia.ipynb), che contiene il codice, le motivazioni e i controlli. I risultati sono in `data/processed/pairs_intraday/` (cartella ignorata da git: chi li vuole rilancia il notebook).

Perché: sono il materiale di base del segnale e della simulazione.

#### Cosa prevedeva il programma

- Scaricare da Bloomberg apertura, massimo, minimo, chiusura e volume di ogni barra per i titoli delle coppie scelte.
- Usare un solo fuso orario (l'ora di New York) e tenere solo la seduta regolare, dalle 9:30 alle 16:00.
- Allineare i due titoli di ogni coppia sullo stesso orario.
- Riempire le barre mancanti solo copiando in avanti il prezzo precedente, mai usando prezzi futuri (Lezione 5).
- Usare prezzi aggiustati per split e dividendi.
- Controllare i dati: un grafico per coppia, il numero di barre per giorno, i giorni a orario ridotto.

Risultato atteso: un file pulito per ogni coppia.

#### Cosa abbiamo fatto

1. **Dati già presenti.** Abbiamo usato i file al minuto in `data/raw/intraday_1m/` per i 20 titoli delle 10 coppie, senza nuovo scaricamento. Orario di New York, seduta regolare 9:30-15:59 (390 barre al giorno).
2. **Controllo degli split.** I prezzi intraday non sono aggiustati. Abbiamo cercato i gap notturni sopra il 15% e confrontato l'ultima chiusura di ogni giorno con `PX_LAST` giornaliero (che è aggiustato): nessuno split nei 20 titoli (differenza massima circa 2%). Resta un solo gap sopra il 15%, PYPL il 15 luglio 2026 (+15.8%): è un movimento vero, perché giornaliero e intraday restano allineati.
3. **Giorni in comune.** Per ogni coppia si tengono solo i giorni in cui entrambi i titoli hanno dati. Mancano l'11, 14, 15, 16 e 17 settembre per CSX, GS, LOW e USB: le coppie CSX-UNP, BNY-GS, HD-LOW e TFC-USB hanno **91 giorni**, le altre sei **96**. Nessun giorno a orario ridotto.
4. **Griglia completa e riempimento solo dentro la giornata.** Ogni giorno ha 390 minuti. Se un titolo non ha scambi in un minuto, prende l'ultimo prezzo dello stesso giorno (apertura = massimo = minimo = chiusura, volume 0) e la barra è segnata `filled = True`. Non si copia mai il prezzo del giorno prima: l'inizio di ogni giornata resta vuoto finché c'è il primo scambio vero.
5. **Minuti iniziali senza prezzo.** Se un titolo fa il primo scambio dopo le 9:30, quei minuti sono tolti a entrambi i titoli della coppia, per non inventare prezzi. Totale: PYPL-XYZ 74 minuti, HD-LOW 24, MCD-YUM 13, BNY-GS 9, KO-PEP 4, BAC-PNC 1, le altre 0.
6. **Quattro frequenze.** Per ogni coppia 1, 5, 15 e 60 minuti (40 file parquet) più `quality_summary.csv`. Le barre più lunghe sono costruite dal minuto (apertura della prima, massimo, minimo, chiusura dell'ultima, volume sommato) e hanno la colonna `filled_share`, la quota di minuti riempiti nella barra. La funzione `load_pair("KO-PEP", 15)` restituisce i prezzi di una coppia con una colonna per titolo.
7. **Controlli di qualità.** Un grafico per coppia (prezzi normalizzati e spread a 15 minuti) e nessun salto sopra il 5% in un minuto dopo la pulizia.

#### Cosa abbiamo fatto in modo diverso dal programma

| Tema | Programma | Cosa abbiamo fatto | Perché |
| --- | --- | --- | --- |
| Prezzi aggiustati | Prezzi aggiustati per split e dividendi | Prezzi non aggiustati, con controllo degli split | Bloomberg intraday non li fornisce. Split assenti nei 20 titoli; i dividendi in 96 giorni sono pochi e piccoli, ma restano un limite |
| Scaricamento | Scaricare i dati dei titoli scelti | Usati i file già presenti | I dati sono già in `data/raw/` |
| Giorni disponibili | 140 giorni | 96 giorni (91 per 4 coppie) | È la lunghezza reale dei dati: dal 16 giugno al 30 ottobre 2026 |
| Barre mancanti | Copiare il prezzo precedente | Copia solo dentro la giornata, con flag `filled` | Il flag permette di sapere quando il prezzo non è un prezzo di scambio vero (vedi decisione B) |
| Giorni mancanti | Non previsto | Scartati i giorni in cui manca uno dei due titoli | Uno spread con una sola gamba non esiste; non si inventano 5 giorni di prezzi |
| Frequenze | Una da scegliere | Salvate 1, 5, 15 e 60 minuti | Il programma stesso chiede di confrontare le frequenze (sezione "Come scegliere la frequenza") |

#### Decisioni prese

- **Frequenza di base: 1 minuto** (decisione 1 della tabella). Resta una nota: il programma suggeriva 5 o 15 minuti e avverte che al minuto parte dell'oscillazione è rimbalzo tra acquisto e vendita, non sfruttabile, e che i segnali sono molto più numerosi (più chiamate all'agente). I file a 5, 15 e 60 minuti sono già pronti come confronto di robustezza: se i risultati al minuto fossero molto migliori, il programma invita a diffidare.
- **Trattamento dei dati** (punti 3, 4 e 5 sopra): giorni in comune, riempimento solo dentro la giornata, niente prezzi inventati ai minuti iniziali.

#### Decisioni ancora da prendere

**A. Periodo dei dati e divisione train/test (decisione 3 della tabella).** Ora sappiamo che i giorni sono 96, non 140. La proposta del programma (due terzi per l'addestramento, un terzo per il test) dà circa 64 e 32 giorni. Va deciso: la data di taglio (ordine cronologico, mai casuale), e se le quattro coppie con 91 giorni si dividono nello stesso punto delle altre. Regola già fissata: i parametri si scelgono solo sul primo periodo e il test si usa una volta sola. Con circa 3 mesi di dati il mercato è sempre dello stesso tipo, e va scritto nel report.

**B. Come trattare le barre riempite nel segnale.** Una barra riempita è un minuto in cui quel titolo non ha avuto nessuno scambio: il suo prezzo è quello dell'ultimo scambio, quindi "vecchio". Il problema: se uno dei due titoli ha il prezzo vecchio e l'altro si muove, lo spread si allarga solo perché una gamba è ferma. Quando il titolo fermo scambia di nuovo, lo spread rientra da solo. Il segnale sembra un'occasione ma non lo è, e comprare o vendere il titolo fermo a quel prezzo non è nemmeno possibile.

Quanto pesa: dipende dalla frequenza e dal titolo.

| Titolo | Minuti riempiti a 1 min | Barre senza nessuno scambio a 5 min | a 15 min |
| --- | --- | --- | --- |
| UNP (in CSX-UNP) | 41.4% | 3.2% | 0% |
| YUM (in MCD-YUM) | 40.3% | 2.6% | 0% |
| PNC (in BAC-PNC) | 40.0% | 2.2% | 0% |
| ITW (in ITW-OTIS) | 34.8% | non misurato | non misurato |
| LOW (in HD-LOW) | 31.9% | non misurato | non misurato |
| BNY (in BNY-GS) | 29.5% | 0.9% | 0% |
| KO e PEP | sotto il 2% | 0% | 0% |

Questo non rende le coppie inutilizzabili: sono state scelte con la liquidità giornaliera (almeno 50 milioni di dollari al giorno), che è alta; è solo che un titolo meno attivo non scambia ogni minuto. Il problema si concentra al minuto, ed è uno dei motivi per cui il programma propone 5 o 15 minuti. Le opzioni sono tre:

1. **Usare i dati così come sono**, dichiarando il limite. È l'opzione più semplice ma rischia segnali falsi sulle coppie con titoli poco scambiati.
2. **Non aprire un trade se una delle due gambe ha la barra riempita** (o se l'ultimo scambio vero è più vecchio di N minuti). Elimina i segnali falsi, e il costo è che si perdono alcune occasioni. Si può applicare solo ai segnali di ingresso.
3. **Calcolare il segnale su barre più lunghe** (5 minuti) e usare il minuto solo per l'esecuzione.

Proposta: partire dall'opzione 2, perché mantiene la scelta del minuto e vale solo dove serve, e confrontare con le barre a 5 minuti nella robustezza. Va decisa prima di costruire il segnale (Passaggio 4), e il numero di segnali scartati va riportato nel report.

**C. Dividendi e prezzi non aggiustati.** Il giorno ex-dividendo il prezzo scende dell'importo del dividendo senza che sia una perdita vera. In 96 giorni sono pochi eventi e piccoli, ma sullo spread di una coppia un dividendo di un solo titolo può sembrare un'anomalia. Da decidere: accettare e dichiarare il limite (proposta), oppure controllare le date ex-dividendo dei 20 titoli ed escludere i segnali di quel giorno.

#### Limiti da dichiarare nel report

- Prezzi non aggiustati per dividendi.
- Il volume intraday è solo una parte del volume totale (in quota diversa per borsa): va usato come indicatore, non come volume reale.
- Per i titoli meno scambiati una quota alta dei minuti è riempita (fino al 41% al minuto).
- Quattro coppie hanno 91 giorni invece di 96, perché per uno dei due titoli mancano cinque giorni di settembre.
- Circa 3 mesi di dati: un solo tipo di mercato.

Risultato: 40 file puliti (10 coppie × 4 frequenze) più una tabella di qualità.

### Passaggio 2, versione 2. Dati di prezzo intraday delle coppie della versione 2

Stato: **fatto** per la pulizia, con lo stesso metodo della versione 1. Il lavoro è nel notebook [src/02_intraday.ipynb](../src/02_intraday.ipynb), che legge `selected_pairs_2.csv` e scrive in una cartella **separata**, `data/processed/pairs_intraday_v2/` (cartella ignorata da git: chi la vuole rilancia il notebook). I file della versione 1 in `data/processed/pairs_intraday/` non sono stati toccati.

Perché: sono il materiale di base del segnale e della simulazione sulle coppie della versione 2.

#### Cosa abbiamo fatto

Gli stessi passi della versione 1 (vedi "Passaggio 2" sopra), applicati ai **30 titoli** delle 15 coppie:

1. **Dati già presenti**: file al minuto in `data/raw/intraday_1m/`, orario di New York, seduta regolare 9:30-15:59 (390 barre al giorno). Periodo: dal 16 giugno al 30 ottobre 2026, 96 giorni di borsa, nessun giorno a orario ridotto.
2. **Controllo degli split**: nessuno split. La chiusura intraday di ogni giorno differisce dal `PX_LAST` giornaliero (aggiustato) al massimo dell'1.5%. Due gap notturni sopra il 15% sono movimenti veri, perché giornaliero e intraday restano allineati: DHR il 21 luglio (-16.5%) e PYPL il 15 luglio (+15.8%).
3. **Giorni in comune**: si tengono solo i giorni in cui entrambi i titoli hanno dati. A COP, CSX, GS, LOW, SYK e TMO mancano gli stessi cinque giorni (11, 14, 15, 16 e 17 settembre 2026): le coppie COP-EOG, CSX-UNP, GS-MS, HD-LOW, ISRG-SYK e DHR-TMO hanno **91 giorni**, le altre nove **96**.
4. **Riempimento solo dentro la giornata**: un minuto senza scambi prende l'ultimo prezzo dello stesso giorno (barra segnata `filled = True`); mai prezzi del giorno prima, mai prezzi futuri.
5. **Minuti iniziali senza prezzo**: se un titolo fa il primo scambio dopo le 9:30, quei minuti sono tolti a entrambi i titoli. Totale in tutto il periodo: BAC-C 124 minuti, JPM-WFC 109, PYPL-XYZ 74, GS-MS 59, CL-PG 56, ISRG-SYK 35, HD-LOW 24, DHR-TMO 11, KO-PEP 4, CRM-WDAY 3, ELV-UNH 1; le altre 0.
6. **Quattro frequenze**: 1, 5, 15 e 60 minuti per ognuna delle 15 coppie (60 file parquet) più `quality_summary.csv`. La funzione `load_pair("KO-PEP", 15)` restituisce i prezzi di una coppia con una colonna per titolo.
7. **Controlli di qualità**: un grafico per coppia e il conteggio dei salti sopra il 5% in un minuto dopo la pulizia.

#### Risultati e cosa vuol dire

- **Barre riempite al minuto**: la quota è alta per alcuni titoli, cioè hanno molti minuti senza scambi. Titoli più colpiti: UNP 41%, ELV 36%, LOW 32%, DHR 25%, EOG 24%; anche NXPI 23% e TMO 22%. Per KO, PEP, MA, JPM, WFC, BAC e C è sotto il 10%. Questo è il problema descritto nella **decisione B** della versione 1 (barre riempite nel segnale): resta da decidere prima del Passaggio 4 e vale per entrambe le versioni.
- **Salti sopra il 5% in un minuto**: 3, tutti di WDAY il 13 agosto 2026 tra le 14:32 e le 14:44 (da +5% a +10% al minuto, circa +25% in 12 minuti). È un movimento di prezzo molto grande sul titolo di una sola coppia (CRM-WDAY): da guardare prima del Passaggio 4 (probabile notizia o risultati, da verificare), perché sposterebbe lo spread di quel giorno.
- **Giorni per coppia**: 91 per sei coppie, 96 per nove. Meno giorni = meno dati per addestramento e test.
- Le **decisioni A** (divisione train/test) e **C** (dividendi) sono le stesse della versione 1 e non sono ancora prese; la frequenza di base resta 1 minuto (decisione 1), con i file a 5, 15 e 60 minuti come confronto.

#### Limiti da dichiarare nel report

- Prezzi non aggiustati per dividendi.
- Il volume intraday è solo una parte del volume totale (in quota diversa per borsa).
- Per i titoli meno scambiati una quota alta dei minuti è riempita (fino al 41% al minuto).
- Sei coppie hanno 91 giorni invece di 96, perché per uno dei due titoli mancano cinque giorni di settembre.
- Circa 3 mesi di dati: un solo tipo di mercato.

Risultato: 60 file puliti (15 coppie × 4 frequenze) più una tabella di qualità, in `data/processed/pairs_intraday_v2/`.

### Passaggio 3. Archivio delle notizie

> Questa sezione descrive la **versione 1** (10 coppie). La **versione 2** (15 coppie) è descritta in "Passaggio 3, versione 2", subito prima del Passaggio 4.

Stato: **fatto in via sperimentale con Alpaca (fonte Benzinga), sul periodo di addestramento, per le 10 coppie**. Il lavoro è nel modulo [src/news.py](../src/news.py) (scaricamento e archivio locale) e in due notebook, con codice, motivazioni e controlli: [Old files/src/03_notizie/notizie_mav.ipynb](../Old%20files/src/03_notizie/notizie_mav.ipynb) (prima prova su MA-V) e [Old files/src/03_notizie/notizie_coppie.ipynb](../Old%20files/src/03_notizie/notizie_coppie.ipynb) (le 10 coppie). Le risposte grezze sono in `data/raw/news/alpaca/` e le tabelle in `data/processed/` (cartelle ignorate da git: chi le vuole rilancia `python -m src.news --pair ALL10` e i notebook). Servono le chiavi API di Alpaca nel file `.env`, che git ignora: **ognuno crea le sue** e non le condivide. I passi per crearle e per rilanciare tutto sono nella sezione [Come rilanciare il lavoro sul proprio computer](#come-rilanciare-il-lavoro-sul-proprio-computer); chi ha fatto cosa è nel [registro](#chi-ha-fatto-cosa).

Perché: l'agente deve poter leggere solo le notizie uscite prima di ogni segnale, altrimenti vede il futuro.

#### Cosa prevedeva il programma

- Scaricare i titoli delle notizie per le aziende scelte, con data e ora esatte.
- Salvare in una tabella: orario, titolo, fonte, azienda, link, nello stesso fuso orario dei prezzi.
- Tenere l'archivio in locale, così il backtest legge sempre gli stessi dati e il risultato è riproducibile.

Risultato: una tabella di notizie con orario.

Attenzione: se per un segnale non si trova nessuna notizia, non significa che non ne siano uscite. Le fonti hanno copertura incompleta. Va scritto nel report.

#### Cosa abbiamo fatto

1. **Fonte: API delle notizie di Alpaca** (Benzinga). **Bea** ha creato l'account e le chiavi e ha lanciato una chiamata di prova, con la quale abbiamo verificato che le chiavi funzionano e che lo storico di giugno-settembre 2026 è accessibile col piano gratuito; ha orario di pubblicazione preciso, filtro per ticker e per data e ora, 50 notizie per pagina. Non abbiamo confrontato altre fonti.
2. **Scaricamento dei 20 titoli delle 10 coppie, dal 1 giugno al 16 settembre 2026**: 1250 notizie uniche (di cui 174 su MA e V). Le notizie di MA e V le ha scaricate **Bea** dal terminale; quelle dei 20 titoli sono state scaricate da Claude Code con le chiavi di Bea, su sua richiesta. Si parte due settimane prima del train perché l'agente guarda indietro dal segnale. Il test (dal 17 settembre) **non è stato scaricato**. Ogni pagina grezza è salvata, così il risultato è riproducibile.
3. **Tabella pulita**: una riga per notizia con orario di pubblicazione (`created_at`) in ora di New York senza indicazione del fuso, come i prezzi, titolo, sommario, fonte, link, tutti i ticker citati e una colonna per ogni titolo delle coppie.
4. **Niente lookahead**: si usa `created_at` e non `updated_at` (l'ultimo aggiornamento può essere molto più tardi; in pratica solo l'1% delle notizie è aggiornato più di un'ora dopo). Per un segnale alla barra *t* si usano solo le notizie con orario fino a *t*.
5. **Notizie "mirate"**: una notizia è mirata se cita al massimo 3 ticker; le altre sono elenchi generici (fino a 128 ticker), che restano nella tabella ma sono segnate.
6. **Tabella notizie-segnali**: per ognuno dei 624 segnali del Passaggio 4 si salvano le notizie delle ultime 24 ore che citano uno dei due titoli della coppia, con quanti minuti prima sono uscite (`data/processed/news_for_signals_10pairs_train.csv`). Sarà l'input del Passaggio 5.

#### Risultati sul train

| | |
|---|---|
| Notizie uniche sui 20 titoli | **1250**, tutte Benzinga; 67% mirate; 48% a mercato aperto; 34 titoli duplicati |
| Copertura per titolo | da 9 notizie (OTIS) e 11 (ITW) a 222 (GS); per coppia da **0.19 notizie al giorno (ITW-OTIS)** a 2.5 (BNY-GS) |
| Segnali con almeno una notizia nelle ultime 24 ore | **347 su 624 (56%)** |
| Segnali con una notizia **mirata** nelle ultime 2 / 6 / 24 ore | 13% / 24% / 42% (circa 84 / 150 / 261 segnali) |
| Orari casuali alla stessa ora del giorno, per confronto | 15% / 25% / 43% |
| Guadagno lordo dei trade con una notizia mirata nelle ultime 6 ore | 13.6 bps (150 trade, errore 5.9) contro 4.6 bps (474 trade, errore 2.0) senza |

#### Cosa abbiamo fatto in modo diverso dal programma

| Tema | Programma | Cosa abbiamo fatto | Perché |
| --- | --- | --- | --- |
| Fonti | Verificare 2 o 3 fonti e sceglierne una (Passaggio 0) | Provata solo Alpaca | È gratuita, ha orario preciso e l'accesso è immediato; le altre sono elencate sotto, da provare se la copertura non basta |
| Contenuto | Titolo | Titolo e sommario, senza il testo completo | Il programma parte dal titolo; il testo completo è molto più pesante |
| Periodo | Notizie fino a ogni segnale | Dal 1 giugno al 16 settembre | Le due settimane prima del train servono alla finestra all'indietro |

#### Cosa ci dicono i risultati

- **Le notizie sono poche e distribuite male.** Una sola fonte, in media circa 1.2 notizie al giorno per coppia (1.6 per MA-V). ITW-OTIS ha 20 notizie in tre mesi e mezzo: per quella coppia l'agente non avrà quasi mai niente da leggere.
- **I segnali non coincidono con le notizie.** La quota di segnali con una notizia è uguale a quella di orari casuali alla stessa ora del giorno (per esempio 24% contro 25% a 6 ore con notizie mirate). Non si vede una relazione tra una notizia e un movimento anomalo dello spread. Attenzione: confrontare con orari di tutta la giornata, e non della stessa ora, fa sembrare i segnali poveri di notizie solo perché il 43% dei segnali è subito dopo l'apertura, quando le ultime ore includono la notte.
- **Le notizie vere sono rare.** Quelle che l'agente leggerebbe sono per lo più cambi di target price e giudizi degli analisti, annunci di prodotto ed elenchi di titoli; i fatti strutturali su una sola azienda sono pochi (un esempio: la vendita di Pizza Hut da parte di Yum!, 171 minuti prima di un segnale su MCD-YUM).
- **Con le 10 coppie il Passaggio 5 diventa fattibile**: circa 150 segnali con notizie mirate nelle ultime 6 ore (circa 15 su MA-V da sola), 260-350 con 24 ore, cioè poche centinaia di chiamate al modello. Il confronto tra le versioni A, B e C resta comunque incerto (errori standard di 6-10 bps).
- **Descrittivo, non una prova**: i trade con una notizia mirata guadagnano di più (13.6 contro 4.6 bps a 6 ore), cioè il contrario di quello che direbbe l'ipotesi del progetto, ma la differenza è di 1.3-1.8 errori standard, e una notizia qualsiasi non è un fatto strutturale. Per saperlo serve la classificazione del Passaggio 5.

#### Decisioni ancora da prendere

1. **Orario vero di pubblicazione.** Non si può controllare dai dati: il gruppo apre a mano i link di 10 notizie (tabella nel notebook, parte 4), confronta l'orario con la pagina originale e scrive l'esito.
2. **Aggiungere altre fonti?** Vedi sotto. Conviene decidere dopo aver visto, nel Passaggio 5, se la copertura basta; la seconda fonte serve soprattutto alle coppie con poche notizie.
3. **Finestra di ricerca**: 2, 6 o 24 ore. Il programma lascia da decidere la lunghezza; si può partire da 6 ore e confrontare.
4. **Duplicati e notizie con molti ticker**: raggruppare i titoli simili e decidere se l'agente vede anche gli elenchi generici.
5. **Classificazione a mano** di 30-50 segnali con notizia (programma, Passaggio 5), per misurare l'accordo con l'agente.

#### Altre fonti che possiamo aggiungere

Le informazioni vengono da guide e confronti di terzi che spesso si contraddicono su limiti e piani gratuiti: **nessuna è stata provata**. Per ognuna va fatta la stessa verifica fatta su Alpaca, con una chiamata di prova: storico di giugno-settembre 2026, orario di pubblicazione, filtro per ticker e per data e ora, limiti del piano gratuito, condizioni d'uso.

| Fonte | Cosa offre | Dubbi da verificare |
| --- | --- | --- |
| **Marketaux** | Notizie per ticker con sentiment; piano gratuito indicato a 100 richieste al giorno | Profondità dello storico e numero di articoli per richiesta |
| **Finnhub** | Notizie per azienda; 60 chiamate al minuto nel piano gratuito | Le fonti discordano su cosa sia gratuito; licenza per uso personale |
| **Alpha Vantage** | Notizie con sentiment e filtro per ticker | Limiti gratuiti discordanti (5 o 25 richieste al giorno) |
| **GDELT** | Gratuita, senza chiave, ricerca dal 2017 | Non è finanziaria: la ricerca per nome è ambigua (con "Visa" si trovano anche i visti di viaggio); l'orario è quello in cui GDELT vede l'articolo, non quello di pubblicazione; massimo 250 articoli per richiesta |
| **Bloomberg** | Già nel progetto: sentiment e numero di notizie *giornalieri* (`sentiment_all.parquet`, vedi [bloomberg-api.md](../Old%20files/docs/bloomberg-api.md)) | Senza orario: per un segnale di giornata rischia di includere notizie successive; si può usare solo il valore del giorno prima |

Ordine consigliato: **Marketaux e Finnhub** per prime (notizie per ticker con orario); GDELT come fonte generale, ma richiede filtri per non raccogliere rumore; Bloomberg è un tipo di dato diverso (un indicatore giornaliero, non titoli con orario). Una seconda fonte di titoli porta duplicati con Benzinga, da raggruppare.

#### Limiti da dichiarare nel report

- Una sola fonte (Benzinga via Alpaca) e copertura incompleta: "nessuna notizia trovata" non vuol dire "non è successo niente".
- I ticker sono assegnati da Benzinga: una notizia associata a un titolo non è per forza su quell'azienda.
- Orari non ancora verificati a mano.
- Solo titolo e sommario, non il testo completo.
- Segnali non indipendenti tra coppie: il 25% dei trade ha un segnale di un'altra coppia nello stesso minuto, quindi gli errori standard sono sottostimati.

Risultato: una tabella di 1250 notizie con orario (`news_ALL10_train.parquet`) e una tabella notizie-segnali per i 624 segnali del train.

### Passaggio 3, versione 2. Archivio delle notizie per le 15 coppie

Stato: **fatto** per l'archivio e la copertura, sul periodo di addestramento. Il lavoro è nel modulo [src/news.py](../src/news.py) (esteso con `--pair ALL15_V2`; la versione 1 non cambia) e nel notebook [src/04_notizie.ipynb](../src/04_notizie.ipynb), con codice, motivazioni e testo dei risultati generato dai dati. Le risposte grezze sono in `data/raw/news/alpaca/ALL15_V2_2026-06-01_2026-09-16/` e la tabella in `data/processed/news_ALL15_V2_train.parquet` (cartelle ignorate da git: chi le vuole rilancia `python -m src.news --pair ALL15_V2` e il notebook). Servono le chiavi API di Alpaca nel file `.env`, come per la versione 1.

Perché: l'agente deve poter leggere solo le notizie uscite prima di ogni segnale, altrimenti vede il futuro.

#### Cosa abbiamo fatto

Lo stesso metodo della versione 1, sui **30 titoli** delle 15 coppie:

1. **Fonte**: API delle notizie di Alpaca (fonte Benzinga). Lo scaricamento è stato lanciato da Claude Code con le chiavi nel `.env` del progetto, su richiesta del gruppo.
2. **Periodo**: dal 1 giugno al 16 settembre 2026 (si parte due settimane prima del train perché l'agente guarda indietro dal segnale). Il test (dal 17 settembre) **non è stato scaricato**.
3. **Tabella pulita**: una riga per notizia con orario di pubblicazione (`created_at`) in ora di New York, titolo, sommario, fonte, link, tutti i ticker citati e una colonna `mentions_<ticker>` per ogni titolo. Una notizia con più ticker compare una volta sola.
4. **Niente lookahead**: si usa `created_at` e non `updated_at`; per un segnale alla barra *t* si useranno solo le notizie con orario fino a *t*.
5. **Notizie "mirate"**: al massimo 3 ticker citati; le altre sono elenchi generici e restano segnate.
6. **Cosa non è stato fatto**: la tabella notizie-segnali, perché i segnali della versione 2 (Passaggio 4) non esistono ancora.

#### Risultati sul train

| | |
|---|---|
| Notizie uniche sui 30 titoli | **2.106**, tutte Benzinga; 68% mirate; 49% a mercato aperto; 4.4% nel weekend; 66 titoli duplicati |
| Copertura per titolo | da 20 notizie (CL) e 26 (EOG, SYK) a 268 (JPM) e 222 (GS) |
| Copertura per coppia (notizie al giorno) | da **0.48 (CL-PG)** a **3.06 (GS-MS)**; meno coperte: CL-PG 0.48, DHR-TMO 0.63, COP-EOG 0.75, CSX-UNP 0.80; più coperte: GS-MS 3.06, JPM-WFC 2.86, CRM-WDAY 2.51 |
| Coppie sotto 0.3 notizie al giorno | 0 su 15 (nella versione 1 ITW-OTIS aveva 0.19) |
| Orari | solo l'1% delle notizie è aggiornato più di un'ora dopo la pubblicazione: si tiene `created_at` |
| Coerenza con la versione 1 | per i 12 titoli in comune (BAC, CSX, GS, HD, KO, LOW, MA, PEP, PYPL, UNP, V, XYZ) le notizie sono esattamente le stesse (981) |

#### Cosa ci dicono i risultati

- **Copertura più omogenea della versione 1**: nessuna coppia ha così poche notizie da lasciare l'agente senza niente da leggere (il minimo è 0.48 al giorno, circa una notizia ogni due giorni). Le coppie più coperte sono quelle di banche e software; le meno coperte, beni di consumo (CL-PG), strumenti scientifici (DHR-TMO) e petrolio (COP-EOG).
- **Una sola fonte**: "nessuna notizia trovata" non vuol dire che non sia successo niente.
- Il numero di **segnali con una notizia nelle ultime ore** e il confronto con orari casuali si potranno misurare solo dopo il Passaggio 4 per la versione 2.

#### Decisioni ancora da prendere

Le stesse della versione 1 (orario vero di pubblicazione da verificare a mano su 10 notizie, altre fonti, finestra di ricerca di 2, 6 o 24 ore, trattamento di duplicati ed elenchi, classificazione a mano), che restano aperte anche per la versione 2. Il notebook estrae le 10 notizie a caso con il link per il controllo a mano.

#### Limiti da dichiarare nel report

- Una sola fonte (Benzinga via Alpaca) e copertura incompleta.
- I ticker sono assegnati da Benzinga: una notizia associata a un titolo non è per forza su quell'azienda.
- Orari non ancora verificati a mano.
- Solo titolo e sommario, non il testo completo.
- Notizie solo fino al 16 settembre 2026 (test non scaricato).

Risultato: una tabella di 2.106 notizie con orario (`news_ALL15_V2_train.parquet`).

### Passaggio 4. Spread e segnale

> Questa sezione descrive la **versione 1** (10 coppie). La **versione 2** (15 coppie) è descritta in "Passaggio 4, versione 2", subito prima del Passaggio 5.

Stato: **fatto in via sperimentale, solo sul periodo di addestramento**, su richiesta e con le scelte di Bea (vedi il [registro](#chi-ha-fatto-cosa)): prima su MA-V ([Old files/src/04_segnali/segnale_mav.ipynb](../Old%20files/src/04_segnali/segnale_mav.ipynb), con codice, motivazioni e controlli), poi esteso alle 10 coppie con parametri uguali per tutte ([Old files/src/04_segnali/segnali_coppie.ipynb](../Old%20files/src/04_segnali/segnali_coppie.ipynb); le regole sono nel modulo [src/signals.py](../src/signals.py)). I segnali sono in `data/processed/signals_MA-V_train.csv` e `data/processed/signals_10pairs_train.csv` (cartella ignorata da git: chi li vuole rilancia i notebook). Il periodo di test non è stato calcolato.

Perché: è il cuore matematico della strategia, indipendente dall'agente.

#### Cosa prevedeva il programma

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

#### Cosa abbiamo fatto (prima prova su MA-V)

1. **Coppia e divisione dei dati.** MA-V, la prima per distanza (Passaggio 1). Taglio cronologico per giorni interi: **train = primi 64 giorni (16 giugno - 16 settembre), test = ultimi 32 (17 settembre - 30 ottobre)**. Il test non è stato calcolato.
2. **Spread in logaritmi con β = 1**: $S_t = \ln P^{MA}_t - \ln P^{V}_t$. Con importi uguali sulle due gambe (decisione 9) il guadagno della posizione è la differenza dei due rendimenti, che è esattamente la variazione di questo spread. Confronto con β stimato dalla regressione sul train: β = 1.37, ma significherebbe importi diversi sulle due gambe.
3. **Z-score con EMA continua** sull'intera serie, giorno dopo giorno (la notte conta come una barra). Nel notebook c'è il confronto con l'EMA azzerata ogni mattina. Verificato che lo z-score di una barra non usa dati futuri.
4. **Regole.** Ingresso a $|z| \ge$ soglia alla chiusura della barra t, esecuzione all'apertura della barra t+1. Una posizione alla volta. Uscita al primo tra: rientro, stop-loss, tempo massimo, fine giornata (all'ultima barra). Niente ingressi nei primi 15 e negli ultimi 30 minuti. **Decisione B del Passaggio 2 applicata (opzione 2):** non si apre se una delle due gambe ha la barra del segnale riempita.
5. **Parametri provati solo sul train**: emivita 30, 60, 120, 240 minuti; ingresso 1.5, 2.0, 2.5, 3.0; uscita 0 o 0.5 (32 combinazioni per tipo di EMA). Regola di scelta scritta prima di guardare i risultati: tra le combinazioni con almeno 30 trade, quella con il guadagno lordo medio più alto, poi controllo che le combinazioni vicine siano positive.
6. **Parametri scelti:** emivita 120 minuti, ingresso 2.0, uscita 0, stop a 3.5 (ingresso + 1.5), tempo massimo 90 minuti.

#### Risultati sul train (MA-V)

| | |
|---|---|
| Trade | **56** (0.9 al giorno, in 46 giorni su 64) |
| Guadagno **lordo** medio per trade | **10.3 bps** (mediano 9.3; errore standard 3.2; 68% in positivo) |
| Combinazioni vicine con guadagno positivo | 8 su 8 |
| Uscite | rientro 20 (+28.2 bps), tempo 31 (-1.9), fine giornata 4 (+21.3), stop 1 (-12.9) |
| Barre candidate scartate per gamba riempita | 2 |

Con la EMA azzerata ogni giorno il risultato è peggiore: migliore combinazione 5.7 bps (39 trade).

#### Cosa abbiamo fatto in modo diverso dal programma

| Tema | Programma | Cosa abbiamo fatto | Perché |
| --- | --- | --- | --- |
| Spread | Prezzi con hedge ratio stimato (decisione 5) | Log-prezzi con β = 1 | Coerente con importi uguali sulle gambe (decisione 9) |
| Uscita | z = 0.5 | z = 0 (0.5 dà risultati simili, vedi notebook) | Scelta con la regola sul train |
| Tempo massimo | 4 ore | 90 minuti | Assunzione nostra, non ottimizzata. Solo 36% dei trade rientra entro 90 minuti: da rivedere |
| Orari | Escludere i primi 30 minuti (decisione 7) | Primi 15 minuti esclusi | Con l'EMA continua metà dei segnali nasce subito dopo, sul gap della notte (vedi sotto) |
| Trigger secondario | Da decidere | Non implementato | Si salva solo `leg_piu_mosso`, descrittivo |

#### Cosa ci dicono i risultati su MA-V

- **Lo spread di MA-V rientra lentamente**: emivita di circa 5 giorni di seduta, il livello cambia da un giorno all'altro di circa 190 punti base contro circa 18 dentro la giornata. Sullo spread con β = 1 il test ADF non rifiuta la camminata casuale (p = 0.44); Engle-Granger dà p = 0.03. La cointegrazione del Passaggio 1 (dati giornalieri) non è confermata con forza sull'intraday.
- **Il segnale c'è ma è piccolo**: 10 bps lordi, circa 3 errori standard. I costi (4 operazioni per trade) non sono inclusi: non sappiamo ancora se il guadagno netto resta positivo.
- **Gap della notte**: 29 trade su 56 entrano tra i minuti 15 e 30. È in parte una strategia di rientro del gap della notte, diversa dall'anomalia dentro la giornata. Il guadagno medio di questi trade è simile al totale, ma va dichiarato.
- **Il massimo della griglia inganna**: la combinazione col guadagno più alto (38.7 bps) ha 4 trade, per questo la regola chiede almeno 30 trade.

#### Estensione alle 10 coppie (parametri uguali per tutte, scelta di Bea)

Notebook: [Old files/src/04_segnali/segnali_coppie.ipynb](../Old%20files/src/04_segnali/segnali_coppie.ipynb). Segnali: `data/processed/signals_10pairs_train.csv`.

**Cosa abbiamo fatto**

1. **Stesse regole di MA-V**, spostate in funzioni ([src/signals.py](../src/signals.py)). Controllo: su MA-V il nuovo codice riproduce esattamente i 56 trade della prima prova (stessi orari, stessi guadagni). Controllo anche che lo z-score non usi dati futuri, su ogni coppia.
2. **Stesso taglio per tutte le coppie**, in date di calendario: train fino al 16 settembre (64 giorni; 60 per CSX-UNP, BNY-GS, HD-LOW, TFC-USB, a cui mancano 4 giorni di settembre), test dal 17 settembre, non calcolato.
3. **Prova della griglia** (4 emivite × 4 soglie di ingresso × 2 di uscita) su **tutte le coppie insieme**, solo sul train. Regola di scelta scritta prima di guardare i risultati: tra le combinazioni con almeno 300 trade (in media 30 per coppia), il guadagno lordo medio più alto; poi si controlla che le combinazioni vicine siano positive e in quante coppie su 10 il guadagno è positivo.
4. **Parametri scelti, uguali per tutte:** emivita 60 minuti, ingresso 2.0, uscita 0, stop 3.5, tempo massimo 90 minuti, nessun ingresso nei primi 15 e negli ultimi 30 minuti. (Per MA-V da sola era 120; con 60 MA-V fa 7.5 bps su 75 trade, contro 10.3 su 56.)
5. **Confronti nel notebook**: EMA azzerata ogni giorno; parametri scelti coppia per coppia (solo informativo).

**Parametri uguali o scelti coppia per coppia.** **[SCELTA provvisoria]** Per ora **uguali per tutte le coppie**, scelti sui trade di tutte insieme. **Si possono scegliere anche coppia per coppia**: si ripete la griglia per ogni coppia con una regola di scelta (nel notebook, parte 6: almeno 20 trade, guadagno medio più alto). Il codice è già pronto e il risultato è nella tabella del notebook. Pro: ogni coppia ha la sua velocità di rientro. Contro: con circa 60 giorni di train per coppia, 32 combinazioni per coppia moltiplicano il rischio di test multipli, e il guadagno "migliore" è misurato sugli stessi dati su cui è scelto, quindi è ottimistico. Nel train i parametri migliori cambiano da coppia a coppia senza un andamento chiaro (emivita 30-120, ingresso 1.5-2.5), con guadagni molto più alti ma su 20-30 trade (per esempio MCD-YUM da 9.7 a 31.2 bps). **Per ora non conviene**; da riconsiderare con più dati, oppure valutando la scelta per coppia sul test con i parametri bloccati.

#### Risultati sul train (10 coppie)

| | |
|---|---|
| Trade | **624** (circa 1 al giorno per coppia, 10 al giorno in tutto) |
| Guadagno **lordo** medio per trade | **6.8 bps** (errore standard 2.1; mediano 10.4; 59% in positivo) |
| Senza PYPL-XYZ (la coppia col guadagno più alto, 29.6 bps) | 564 trade, **4.3 bps** (errore 1.8), 7 coppie su 9 positive |
| Coppie con guadagno medio positivo | 8 su 10 (MA-V 7.5, TFC-USB -1.6, BAC-PNC -3.8, CSX-UNP 6.8, PYPL-XYZ 29.6, BNY-GS 9.6, HD-LOW 4.4, ITW-OTIS 3.2, MCD-YUM 9.7, KO-PEP 3.5) |
| Combinazioni vicine con guadagno positivo | 8 su 8 |
| Uscite | rientro 301 trade (+37.1 bps), tempo 267 (-21.5), fine giornata 42 (-16.1), stop 14 (-38.1) |
| Entrate nei minuti 15-30 dall'apertura | 271 trade (43%), **80% del guadagno lordo totale** (12.4 bps in media); dopo i 30 minuti 2.4 bps (errore 2.1) |
| Con EMA azzerata ogni giorno | 1.5 bps (792 trade) |
| Barre candidate scartate per gamba ferma | 183; 111 trade (18%) eseguiti a un prezzo vecchio |

#### Cosa ci dicono i risultati sulle 10 coppie

- **Il segnale c'è anche sulle altre coppie ma è piccolo e fragile.** Circa 7 bps lordi per trade, 4 senza la coppia migliore, con errori standard di 4-8 bps su quasi tutte le coppie prese da sole. I costi (4 operazioni per trade) non sono ancora inclusi: il margine è stretto.
- **Il guadagno viene quasi tutto dalle entrate subito dopo l'apertura**, cioè dal rientro del gap della notte reso visibile dalla EMA continua. Con la EMA azzerata il guadagno è vicino a zero.
- **Rientra solo la metà dei trade** (48%); chi non rientra entro 90 minuti perde in media 21 bps. Il tempo massimo non è ottimizzato.
- **La cointegrazione intraday non si conferma** nel train: il test di Engle-Granger è sotto 0.05 solo per MA-V, il test ADF per nessuna coppia. L'emivita dello spread va da 3 a 10 giorni. La selezione del Passaggio 1 era fatta sui dati giornalieri di 20 anni; questo controllo è su 3 mesi, quindi non c'è contraddizione, ma la relazione non è abbastanza forte sull'orizzonte di una giornata.
- **Il minuto è troppo corto per 5 coppie**: nel 42-49% dei minuti uno dei due titoli non scambia (BAC-PNC, CSX-UNP, BNY-GS, ITW-OTIS, MCD-YUM; HD-LOW 36%). KO-PEP è la più pulita (3%).
- **Segnali non indipendenti**: il 25% dei trade ha un segnale di un'altra coppia nello stesso minuto (spesso movimenti di tutto il mercato), quindi gli errori standard sono sottostimati.

#### Decisioni ancora da prendere

1. **Parametri uguali o scelti coppia per coppia** (vedi sopra): per ora uguali.
2. **Gap della notte**: tenere i trade del mattino (sono la fonte quasi unica del guadagno) o alzare l'esclusione dei primi minuti (decisione 7). Se si tengono, vanno descritti come strategia di rientro del gap della notte.
3. **Coppie con la gamba ferma** (decisione B del Passaggio 2): segnale su barre da 5 minuti per quelle coppie, oppure tenerle al minuto dichiarando il limite.
4. **Parametri non ottimizzati**: tempo massimo (90 minuti), stop, orari di esclusione.
5. **Trigger secondario** (un solo titolo che si muove in modo anomalo): non implementato.
6. **Cointegrazione intraday debole**: rivedere la selezione delle coppie o accettare il limite.
7. **Costi** (Passaggio 6): sono la prova decisiva per sapere se 4-7 bps lordi sopravvivono. Uso del test (dal 17 settembre) una sola volta, con i parametri bloccati.

#### Limiti da dichiarare nel report

- Circa 3 mesi di dati, un solo tipo di mercato; 10 coppie.
- 32 combinazioni provate: rischio di test multipli, mitigato da minimo di trade, controllo dei vicini e test finale.
- Gli errori standard assumono trade indipendenti: i trade non lo sono (stessi giorni, coppie dello stesso settore).
- Guadagni lordi: niente costi, impatto sul prezzo, costo di prestito dei titoli.
- Prezzi di esecuzione vecchi nel 18% dei trade; prezzi non aggiustati per i dividendi (Passaggio 2).

Risultato: una tabella di 624 segnali del train per le 10 coppie con orario, direzione, z, prezzi, motivo di uscita e guadagno lordo (e una di 56 segnali per MA-V con i parametri della prima prova).

#### Versione 2 del segnale: provata e scartata

Stato: **fatta sul train, scartata**. Codice in [Old files/src/signals_v2.py](../Old%20files/src/signals_v2.py), notebook con regole, risultati e conclusioni in [Old files/src/04_segnali/segnali_v2.ipynb](../Old%20files/src/04_segnali/segnali_v2.ipynb). I file della versione 1 (`signals.py`, `segnali_coppie.ipynb`, `backtest.py`) non sono stati modificati. Il file `data/processed/signals_v2_train.csv` contiene la combinazione scelta dalla regola, ma non ha superato il controllo e **non va usato come input del Passaggio 5** senza dichiararlo.

**Perché.** Il backtest con costi (Passaggio 6) ha mostrato che con le regole sopra il guadagno lordo, 6.77 bps per trade, non copre i costi: costo di pareggio 1.69 bps per operazione, mentre lo scenario realistico è 5. Prima di costruire l'agente abbiamo provato se qualche modifica semplice delle regole potesse portare il segnale in guadagno netto, **solo sul train**.

**Cosa abbiamo provato** (griglia di 18 combinazioni, scritta prima di guardare i risultati):

| Leva | Valori | Idea |
| --- | --- | --- |
| Scostamento minimo in punti base, oltre a z ≥ 2 | 0, 8, 20 | Scartare i trade in cui lo spread si è mosso troppo poco per coprire i costi. 0 = regole di prima; 8 e 20 bps sono il costo di un trade a 2 e a 5 bps per operazione |
| Tempo massimo | 90, 180 minuti, solo fine giornata | Le uscite per tempo perdono: forse si chiude prima del rientro |
| Barre del segnale | 1 e 5 minuti | Meno rumore e meno prezzi vecchi. Con 5 minuti lo z-score è calcolato sulle barre da 5 (emivita 60 minuti = 12 barre), si decide alla chiusura della barra e si esegue all'apertura del minuto dopo |

Rimasti uguali: emivita 60 minuti, ingresso z 2.0, uscita 0, stop 3.5, niente ingressi nei primi 15 e negli ultimi 30 minuti, EMA continua, non si apre con una gamba ferma.

**Regola di scelta, scritta prima.** Controllo di coerenza: la combinazione di prima deve riprodurre i 624 trade (fatto: stessi trade, stessi orari, stessi guadagni). Il train si divide in due metà di 32 giorni (fino al 31 luglio e dal 3 agosto). Si sceglie sulla prima metà la combinazione con il guadagno netto più alto a 2 bps per operazione, con almeno 150 trade; è valida solo se il netto a 2 bps è positivo anche nella seconda metà, e se non lo è non se ne sceglie un'altra a posteriori. Il test non è stato letto.

**Risultati**

| | Versione 1 (Passaggio 4) | Combinazione scelta dalla v2 (1 minuto, 20 bps, solo fine giornata) |
| --- | --- | --- |
| Trade | 624 | 604 |
| Guadagno lordo per trade | 6.77 bps | 6.01 bps |
| Netto a 2 bps per operazione | -1.2 bps | -2.0 bps |
| Netto a 5 bps per operazione | -13.2 bps | -14.0 bps |
| Costo di pareggio | 1.69 bps | 1.5 bps |
| Netto a 2 bps, prima metà / seconda metà | +3.1 / -5.8 bps | +3.4 / **-7.9 bps** |

- **Nessuna combinazione è valida.** Tutte le 18 sono negative a 2 e a 5 bps sull'intero train, e tutte negative nella seconda metà. La scelta della regola è **non valida** e la v2 è scartata: si resta alle regole del Passaggio 4, più semplici e senza una scelta in più da giustificare.
- **Il problema è il periodo, non i parametri.** Con le regole di prima il lordo è 11.1 bps nei primi 32 giorni e 2.2 negli ultimi 32; con le barre da 5 minuti 9.1 e 3.9. Nessuna combinazione supera 4 bps lordi nella seconda metà, quindi nessuna copre nemmeno il costo più basso (8 bps per trade a 2 bps per operazione). Con 64 giorni di train non si distingue un segnale che si è spento da un risultato dovuto al caso.
- **La soglia in bps non serve ai valori provati.** Con 8 bps i trade sono identici a quelli senza soglia; con 20 bps ne cadono solo 14 su 624: a z = 2 lo scostamento è quasi sempre già sopra 20 bps.
- **Allungare il tempo massimo peggiora.** Con 180 minuti il lordo scende a 5.9 bps; con "solo fine giornata" i 69 trade chiusi a fine giornata perdono 58 bps in media.
- **Barre da 5 minuti:** dimezzano i trade (309), ma il lordo non migliora (6.4 bps con 90 minuti, dentro l'incertezza).
- **Gap della notte:** resta la stessa struttura. Nella combinazione scelta, 11.4 bps lordi per gli ingressi nei minuti 15-30 e 1.7 dopo i 30 minuti.

**Da dichiarare nel report.** Le combinazioni provate sono 18, in più delle 32 del Passaggio 4. La v2 non migliora la v1 e non ha superato il controllo sulla seconda metà; il train è lo stesso su cui erano stati scelti i parametri della v1. La conclusione è che a costi realistici la strategia di base non rende e che la differenza tra "funziona" e "non funziona" dipende dal periodo.

### Passaggio 4, versione 2. Spread e segnale per le 15 coppie

Stato: **fatto sul periodo di addestramento**, con le stesse regole e gli stessi parametri della versione 1. Il lavoro è nel notebook [src/03_segnali.ipynb](../src/03_segnali.ipynb), con codice, motivazioni e testo dei risultati generato dai dati. Le regole sono nel modulo [src/signals.py](../src/signals.py), esteso con un parametro `version` (con `version=2` legge le 15 coppie e i file puliti della versione 2; il default resta la versione 1). I segnali sono in `data/processed/signals_15pairs_v2_train.csv` (cartella ignorata da git: chi li vuole rilancia il notebook). Il periodo di test **non è stato calcolato**.

Perché: è il cuore matematico della strategia, indipendente dall'agente. Si usano gli stessi parametri della versione 1 perché il confronto tra le due versioni riguardi le coppie e non il segnale, e per non cercare parametri sui dati della versione 2.

#### Scelte del gruppo per la versione 2

| Tema | Scelta |
| --- | --- |
| Divisione train/test | Uguale per tutte le coppie: train fino al 16 settembre 2026, test dal 17 settembre. Le sei coppie con 91 giorni hanno 4 giorni di train in meno e 1 di test in meno |
| Spread | Logaritmo del rapporto tra i prezzi, β = 1 (importi uguali sulle due gambe, senza leva) |
| Parametri | **Quelli della versione 1**, uguali per tutte: emivita 60 minuti, ingresso a \|z\| ≥ 2.0, uscita a \|z\| ≤ 0, stop a 3.5, tempo massimo 90 minuti. Nessuna ricerca nuova |
| Orari | Nessun ingresso nei primi 15 e negli ultimi 30 minuti; tutto chiuso a fine giornata |
| Barre riempite (decisione B) | Non si apre se una delle due gambe ha la barra del segnale riempita |
| Salto di WDAY del 13 agosto | Lasciato: nessun dato escluso |
| Dividendi (decisione C) | Prezzi non aggiustati: limite da dichiarare |
| Costi | **Non considerati** (indicazione del docente): guadagno lordo |
| Frequenza | Barre da 1 minuto (file a 5, 15 e 60 minuti disponibili per la robustezza) |
| Versione per il report | Da decidere alla fine |

#### Cosa abbiamo fatto

1. **Dati**: i file puliti a 1 minuto della versione 2 (Passaggio 2, `data/processed/pairs_intraday_v2/`).
2. **Spread** $S_t = \ln P^A_t - \ln P^B_t$ e **z-score** con media e deviazione standard esponenziali (EMA continua su tutta la serie, la notte conta come una barra).
3. **Regole**: ingresso alla chiusura della barra *t* se \|z\| ≥ 2.0, esecuzione all'apertura della barra *t+1* (niente lookahead); uscita al primo tra rientro, stop, tempo massimo e fine giornata; una posizione alla volta per coppia.
4. **Controlli**: lo z-score di ogni barra non dipende dalle barre successive (verificato su tutte le coppie); sulle 5 coppie in comune con la versione 1 (MA-V, CSX-UNP, PYPL-XYZ, HD-LOW, KO-PEP) i trade sono **identici** a quelli della versione 1 (stessi orari, stessi guadagni).

#### Risultati sul train (15 coppie)

| | |
|---|---|
| Trade | **973** (circa 1 al giorno per coppia) |
| Guadagno **lordo** medio per trade | **7.4 bps** (errore standard 2.0; mediano 10.8; 60% in positivo) |
| Coppie con guadagno medio positivo | 12 su 15 |
| Senza PYPL-XYZ (la coppia migliore) | 913 trade, 6.0 bps (errore 2.0) |
| Confronto con la versione 1 (stessi parametri) | 624 trade, 6.8 bps (errore 2.1) |
| Barre riempite | 129 trade (13%) eseguiti a un prezzo vecchio; 233 occasioni scartate per gamba ferma |
| Segnali sovrapposti | il 30% dei trade ha un segnale di un'altra coppia nello stesso minuto |

| Coppia | Trade | Lordo medio (bps) | Errore standard | In positivo | Uscita per tempo |
| --- | --- | --- | --- | --- | --- |
| PYPL-XYZ | 60 | 29.6 | 14.0 | 63% | 47% |
| CRM-WDAY | 60 | 28.2 | 19.1 | 60% | 48% |
| ELV-UNH | 59 | 10.8 | 7.4 | 58% | 58% |
| GS-MS | 72 | 9.6 | 4.1 | 65% | 36% |
| MA-V | 75 | 7.5 | 2.5 | 64% | 36% |
| CSX-UNP | 61 | 6.8 | 4.2 | 56% | 41% |
| CL-PG | 63 | 6.6 | 4.7 | 60% | 40% |
| DHR-TMO | 62 | 6.6 | 6.5 | 58% | 44% |
| HD-LOW | 65 | 4.4 | 4.1 | 68% | 31% |
| JPM-WFC | 65 | 4.3 | 5.9 | 62% | 38% |
| KO-PEP | 68 | 3.5 | 4.9 | 60% | 49% |
| BAC-C | 71 | 3.4 | 6.2 | 65% | 41% |
| COP-EOG | 61 | -1.0 | 5.3 | 59% | 48% |
| NXPI-TXN | 68 | -2.2 | 7.3 | 50% | 44% |
| ISRG-SYK | 63 | -3.2 | 9.6 | 54% | 56% |

**Come escono i trade**: il rientro è 464 trade e guadagna in media 39 bps; il tempo massimo è 422 trade e perde 23 bps; lo stop 31 trade e perde 32 bps; la fine giornata 56 trade, circa 0. Solo il 48% dei trade rientra.

**Orario**: le entrate nei minuti 15-30 sono 457 trade (47%) e producono il **72% del guadagno lordo** (11.4 bps in media); dopo i primi 30 minuti 516 trade fanno 3.9 bps (errore 2.6), vicino a zero. Come nella versione 1, gran parte del guadagno è il rientro del gap della notte, non un movimento dentro la giornata.

**Stazionarietà sul train** (descrittiva): Engle-Granger sotto 0.05 solo per 1 coppia su 15 e ADF per nessuna; l'emivita dello spread va da 2.9 a 17.6 giorni. Il legame statistico del Passaggio 1 (giornaliero, 5 anni) non si conferma sull'orizzonte di una giornata, come nella versione 1.

#### Il giorno del salto di WDAY (13 agosto)

Per scelta del gruppo il giorno non è escluso. Quel giorno CRM-WDAY ha 5 trade: -2, +7, +72, -42 e **+985 bps** (quest'ultimo chiuso a fine giornata). Quel solo trade vale il **14% del guadagno lordo totale** delle 15 coppie: senza di esso la media scenderebbe da 7.4 a 6.4 bps e quella di CRM-WDAY da 28.2 a 12.0 bps. È il dato che pesa di più sul risultato della coppia e va dichiarato nel report; la decisione di tenerlo o toglierlo si può riaprire.

#### Cosa ci dicono i risultati

- **Il segnale della versione 1 funziona in modo simile sulle nuove coppie**: 7.4 bps lordi contro 6.8, con più trade. Ma è un guadagno piccolo, con errore standard di circa 2 bps, e senza costi.
- **Il risultato dipende da poche coppie e da pochi trade**: PYPL-XYZ (29.6 bps, errore 14.0) e CRM-WDAY (28.2, errore 19.1, di cui buona parte dal trade del 13 agosto) tirano su la media; le altre coppie sono tra -3 e +11 bps, con errori standard di diversi punti base (colonna "Errore standard" della tabella): per la maggior parte indistinguibili da zero. Tre coppie sono negative (ISRG-SYK, NXPI-TXN, COP-EOG, tutte vicine a zero).
- **Concentrazione nei primi 30 minuti**: da dichiarare, come nella versione 1.
- **Barre riempite**: le coppie con la gamba ferma più spesso (CSX-UNP 42%, DHR-TMO 41%, ELV-UNH 37%, HD-LOW 37%) hanno guadagni al minuto meno credibili come guadagni realizzabili.

#### Decisioni ancora da prendere

- Tenere o togliere il giorno del salto di WDAY (decisione presa per ora: tenerlo).
- Le decisioni sul gap della notte (se è una strategia che vogliamo) e sul tempo massimo di 90 minuti, che nella versione 1 sono ancora aperte.
- La versione da usare nel report (alla fine).

#### Limiti da dichiarare nel report

- Guadagno lordo: i costi non sono considerati (indicazione del docente).
- Solo periodo di addestramento; il test non è stato calcolato.
- Parametri della versione 1 non ottimizzati sulla versione 2: scelta voluta, ma potrebbero non essere i migliori per queste coppie.
- Un trade (CRM-WDAY, 13 agosto) pesa per il 14% del guadagno totale.
- Prezzi non aggiustati per dividendi; barre riempite e prezzi di esecuzione vecchi per alcuni titoli.
- Segnali non indipendenti tra coppie (30% nello stesso minuto): gli errori standard sono sottostimati.
- Circa 3 mesi di dati: un solo tipo di mercato.

Risultato: una tabella di 973 segnali del train (`signals_15pairs_v2_train.csv`).

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

**Stato al 15 novembre.** Fatto sulle 15 coppie, sul train, per tutte le 21 varianti dell'agente: [src/06_backtest.ipynb](../src/06_backtest.ipynb), commento in [Results/RESOCONTO.md](../Results/RESOCONTO.md). Variante scelta per il test: `finbert_episodio`. Il paragrafo "Stato" qui sotto è quello delle prime 10 coppie, lasciato com'era.

Stato: **versione A fatta sul train, con costi**; B e C non ancora (aspettano l'agente). Motore in [src/backtest.py](../src/backtest.py), notebook con spiegazioni e risultati in [Old files/src/06_backtest/backtest_A.ipynb](../Old%20files/src/06_backtest/backtest_A.ipynb). Scelte di Bea: 10.000 dollari per gamba, scenario realistico 5 bps per operazione. Il test non è stato letto (il motore rifiuta trade dopo il 16 settembre).

**Risultato sul train (624 trade): la versione A perde con i costi.** Il costo di pareggio è 1.69 bps per operazione (6.77 bps per trade). Guadagno netto per trade: 0 bps = +6.8, 2 bps = -1.2, 5 bps = -13.2, 10 bps = -33.2. Rendimento sul capitale in 64 giorni a 5 bps: -4.1%. Rientrano e guadagnano solo i trade che rientrano (301, +37 bps lordi); tempo massimo, fine giornata e stop perdono. Le entrate subito dopo l'apertura (gap della notte) hanno 12.4 bps lordi, quelle dopo i 30 minuti 2.4 bps. A 5 bps solo PYPL-XYZ è netta positiva (errore standard 14 bps). Versioni B e C: il motore le accetta (B con decisioni finte, solo prova tecnica; C da implementare con la direzione scelta dall'agente).

Conseguenza: abbiamo provato a rivedere le regole del segnale sul train (soglia minima in bps, tempo massimo, barre da 5 minuti; vedi "Versione 2 del segnale" nel Passaggio 4) e nessuna combinazione è valida. Resta da confrontare A, B e C al lordo e a costi bassi dichiarando il limite, oppure da provare altre leve dichiarandole.

Perché: ricostruire che cosa sarebbe successo seguendo le regole, barra per barra, in ordine cronologico.

- Tre versioni su identici dati: A senza agente, B con agente che può solo bloccare, C con agente che decide.
- Costi per ogni gamba: un trade ha due titoli e quindi quattro operazioni (apertura e chiusura di entrambi). Si simulano più livelli di costo.
- Importo fisso e uguale sulle due gambe, nessuna leva, tutto chiuso a fine giornata.
- Registro di ogni trade: coppia, orari, prezzo, motivo di uscita (rientro, stop, tempo, fine giornata), guadagno lordo e netto.

Il motore si scrive subito su dati finti, così è pronto quando arrivano quelli veri.

Risultato: un registro di trade per ciascuna versione.

### Passaggio 7. Metriche e controlli di robustezza

**Stato al 15 novembre.** Fatto sul train per tutte le varianti (bootstrap, beta e alpha rispetto a SPY, costi, coppie, settori, periodo): [src/07_robustezza.ipynb](../src/07_robustezza.ipynb). Sul test, per `finbert_episodio`: [src/07_test_robustezza.ipynb](../src/07_test_robustezza.ipynb).

Perché: dimostrare che un risultato non è fortuna.

- Win rate netto dei costi, profit factor, Sharpe ratio, massimo drawdown, numero di trade, durata media, guadagno medio per trade in basis points.
- Beta e alpha rispetto a SPY (Lezione 5): con il pairs trading il beta dovrebbe essere vicino a zero.
- Risultati per coppia e per settore, per capire se il risultato dipende da una sola coppia.
- Sensibilità ai costi e ai parametri vicini (se funziona solo con un valore esatto, è un campanello d'allarme).
- Bootstrap: intervallo di confidenza al 95% sulla differenza tra versione C e versione A. È il controllo che il progetto dell'anno scorso non aveva.
- Tabella finale con colonna Delta rispetto al benchmark, come nel report dell'anno scorso.

Attenzione: con pochi mesi di dati il numero di trade può essere basso. Conviene sapere presto quanti trade ci sono, perché con poche decine nessuna metrica è affidabile.

Risultato: tabelle e grafici delle curve di capitale.

### Il test: `finbert_episodio` dal 17 settembre al 30 ottobre

Perché: vedere se la variante scelta sul train funziona su dati che nessuno aveva guardato.

#### Cosa prevedeva il programma

Il test si usa una volta sola, alla fine, con regole e parametri bloccati (decisione 3).

#### Decisioni prese (14 novembre, Bea con il gruppo)

- Variante: `finbert_episodio`, con le versioni A, B e C. Nessun'altra variante va sul test.
- Criterio principale: la differenza in dollari tra B e A, e tra C e A, a costo 0 (lo stesso usato per scegliere la variante sul train). Costo 5 per confronto.
- Controlli: gli stessi del train (bootstrap, blocchi contro caso, Fisher sul rientro, notizia giusta nella C, metriche, per coppia e per settore, senza PYPL-XYZ, beta e alpha) più la coerenza con il train. Non le due metà del periodo.
- Regola per i casi a zero: se l'agente non blocca o non segue niente, il test non dice nulla su quella versione.
- Notizie scaricate solo dal 17 settembre, script nuovi separati da quelli del train, nessun secondo giro.

Le regole complete sono in [docs/Test.md](Test.md).

#### Cosa abbiamo fatto

Claude Code ha scritto gli script e i notebook e li ha eseguiti, con le chiavi Alpaca di Bea, su richiesta di Bea:
- [src/test_dati.py](../src/test_dati.py): 2.725 notizie del test e SPY;
- [src/test_finbert.py](../src/test_finbert.py): FinBERT sulle notizie del test, dopo aver controllato che ridà i punteggi del train;
- [src/test_finale.py](../src/test_finale.py): prima ha rifatto il train e ha ritrovato esattamente i 973 segnali e le decisioni e i trade di `finbert_episodio`, poi ha calcolato il test (500 segnali in 32 giorni);
- [src/06_test_backtest.ipynb](../src/06_test_backtest.ipynb) e [src/07_test_robustezza.ipynb](../src/07_test_robustezza.ipynb): risultati, confronto con il train e commento. Tabelle in `Results/test/`.

#### Risultati sul test (costo 0)

| | Test | Train |
| --- | --- | --- |
| A, senza agente | +2.472 $ (4,9 bps per trade, 500 trade) | +7.239 $ (7,4 bps, 973 trade) |
| B rispetto alla A | **-189 $**, intervallo al 95% da -527 a +135 | -285 $ |
| C rispetto alla A | **-1.242 $**, intervallo al 95% da -2.183 a -374 | -651 $ |

- B: 7 blocchi. I trade bloccati avrebbero guadagnato +27 bps in media contro +4,6 dei tenuti; blocco a caso p = 0,90; rientro 43% contro 49% (p Fisher 1,00).
- C: 21 trade nel verso opposto alla A, notizia giusta nel 24% dei casi (train 55%).
- A costo 5: B -49 $, C -1.142 $ rispetto alla A; la A perde 7.528 $.
- Beta di A, B e C rispetto a SPY: -0,04.

#### Cosa ci dicono i risultati

- Il segno è lo stesso del train: né bloccare né seguire le notizie con `finbert_episodio` migliora la strategia. La B non si distingue dalla A, la C è peggiore della A con una certa sicurezza.
- I blocchi scattano su notizie che non sono fatti strutturali: comunicati di studi legali che "indagano", acquisizioni fatte dall'azienda stessa.
- La A guadagna ancora a costo 0, ma meno che sul train (pareggio a 1,24 bps per operazione invece di 1,86); il vantaggio degli ingressi nel gap della notte sparisce.
- Sul train la perdita della B veniva da PYPL-XYZ; sul test no: è distribuita su più coppie.

#### Limiti da dichiarare nel report

- 32 giorni, 7 blocchi, 21 trade seguiti: pochi casi.
- Molte più notizie al giorno che nel train (2.725 in 44 giorni di calendario contro 2.106 in 108), probabilmente per la stagione dei risultati di ottobre.
- Le regole in `docs/Test.md` sono state scritte prima del giro ma messe su git dopo: su git non c'è la prova dell'ordine.
- Le regole e la variante sono state scelte sul train, il criterio di scelta è stato precisato dopo aver visto il train (ma prima del test).

### Il segnale +1 / 0 / -1 per titolo

Perché: le istruzioni del professore chiedono che il sistema dia, per ogni titolo e in ogni momento, un segnale +1 (long), 0 (fuori) o -1 (short), e che il rendimento di ogni periodo sia il rendimento del titolo moltiplicato per il segnale, con le ipotesi dichiarate. La strategia lavora per coppie e il backtest salva trade: l'informazione c'era, ma non in questa forma.

#### Decisioni prese (15 novembre, Bea)

- Un notebook dedicato, [src/08_segnale.ipynb](../src/08_segnale.ipynb), per train e test, invece di una sezione nel notebook del test.
- I numeri principali restano quelli dei trade; il calcolo dal segnale è la formula del professore, mostrata accanto.
- Se due trade della stessa coppia sono aperti insieme, le posizioni si sommano (il segnale potrebbe valere +2 o -2).

#### Cosa abbiamo fatto

Claude Code ha scritto ed eseguito il notebook, su richiesta di Bea. Per le versioni A, B e C di `finbert_episodio`, su train e test:
- dai trade salvati, il segnale per ciascuno dei 30 titoli e per ogni minuto: +1 sul titolo comprato e -1 su quello venduto, dalla barra d'ingresso a quella d'uscita; 0 altrove e di notte;
- il guadagno con la formula del professore: segnale x rendimento semplice del titolo, dall'apertura di una barra all'apertura della successiva (alla chiusura nell'ultima barra della giornata), x 10.000 dollari;
- il confronto con il guadagno dei trade, e il rendimento giornaliero dal segnale sul capitale di 300.000 dollari, salvato per la curva di capitale e le metriche annualizzate.

Le ipotesi sono scritte all'inizio del notebook: decisione alla chiusura della barra ed esecuzione all'apertura della successiva, niente posizioni di notte, 10.000 dollari per titolo senza leva, vendita allo scoperto sempre possibile e gratuita, costo 0.

#### Risultati

- Il segnale vale sempre -1, 0 o +1: nessun trade di `finbert_episodio` si sovrappone a un altro della stessa coppia, né sul train né sul test.
- La formula del professore dà quasi lo stesso guadagno dei trade: da +2 a +9 dollari di differenza su tutto il periodo, meno dello 0,3% (A del test: 2.472 dollari dai trade, 2.477 dal segnale).
- Le differenze dalla A non cambiano: test B -188 $ (trade -189), C -1.245 $ (trade -1.242); train B -288 $ (trade -285), C -648 $ (trade -651).

File: `Results/segnale_A.parquet`, `Results/varianti_agente/finbert_episodio/segnale_B.parquet` e `segnale_C.parquet` (train), `Results/test/segnale_*.parquet` (test); `Results/rendimenti_segnale.csv` e `Results/test/rendimenti_segnale.csv` (rendimenti giornalieri); `Results/confronto_segnale_trade.csv`.

#### Limiti da dichiarare nel report

- Calcolo dal segnale solo a costo 0.
- Le ipotesi del backtest restano: vendita allo scoperto gratuita, nessun effetto degli ordini sul prezzo, prezzi intraday non aggiustati per i dividendi.

### Curve di capitale e metriche, train e test

Perché: le istruzioni del professore chiedono metriche adatte su train e test, confrontate con un benchmark di cui si giustifica la scelta, tra cui la curva di capitale da 100 con il benchmark sullo stesso grafico, rendimento e volatilità annualizzati, Sharpe con il tasso privo di rischio dichiarato, massimo drawdown e profit factor.

#### Decisioni prese (15 novembre, Bea)

- Rendimenti dal **segnale** +1/0/-1 ([src/08_segnale.ipynb](../src/08_segnale.ipynb)), cioè con la formula del professore; l'analisi dell'agente (notebook 06 e 07) resta sui trade.
- Benchmark: **SPY comprato e tenuto** (il mercato da cui vengono le azioni, suggerito dal professore) e **la versione A** (per giudicare l'agente). Non i 30 titoli comprati e tenuti: la strategia è quasi sempre fuori dal mercato.
- Curva della strategia con capitale fisso di 300.000 dollari, senza reinvestimento; SPY capitalizzato. Tutte partono da 100 alla chiusura del giorno prima del periodo.
- Rendimento annualizzato composto per tutti; tasso privo di rischio 0, dichiarato; costo 0 e 5 punti base.
- Anche i controlli per il punto bonus "market-neutral": beta, correlazione con SPY, rendimento nei giorni in cui SPY scende.
- E per il punto bonus "rendimento corretto per il rischio superiore": sul test Sharpe più alto e drawdown più basso di SPY, con la differenza di Sharpe sostenuta da un test statistico.

#### Cosa abbiamo fatto

Claude Code ha scritto ed eseguito [src/09_curve_metriche.ipynb](../src/09_curve_metriche.ipynb), su richiesta di Bea. Legge solo file salvati. Per i costi conta le operazioni dal segnale (ogni variazione di 1 del segnale di un titolo): sono esattamente 4 per trade, come nel backtest.

#### Risultati (costo 0)

| | A | B | C | SPY |
| --- | --- | --- | --- | --- |
| **Train:** rendimento cumulato | +2,42% | +2,32% | +2,20% | +0,15% |
| rendimento annualizzato | +9,9% | +9,5% | +8,9% | +0,6% |
| volatilità annualizzata | 1,2% | 1,1% | 1,2% | 11,7% |
| Sharpe | 8,2 | 8,2 | 7,5 | 0,1 |
| massimo drawdown | -0,14% | -0,14% | -0,14% | -3,4% |
| profit factor (giorni) | 3,9 | 3,9 | 3,5 | 1,0 |
| **Test:** rendimento cumulato | +0,83% | +0,76% | +0,41% | +0,47% |
| rendimento annualizzato | +6,7% | +6,2% | +3,3% | +3,8% |
| volatilità annualizzata | 1,3% | 1,3% | 1,2% | 11,4% |
| Sharpe | 4,9 | 4,7 | 2,8 | 0,4 |
| massimo drawdown | -0,17% | -0,19% | -0,21% | -3,0% |
| profit factor (giorni) | 2,5 | 2,3 | 1,6 | 1,1 |

- A costo 5 tutte le versioni perdono: test A -2,5%, B -2,5%, C -2,9%; train A -4,1%, B -4,1%, C -4,3%.

Dipendenza dal mercato sul test:

| | A | B | C |
| --- | --- | --- | --- |
| beta rispetto a SPY (t) | -0,04 (-2,2) | -0,04 (-2,1) | -0,04 (-2,3) |
| correlazione con SPY | -0,37 | -0,36 | -0,39 |
| guadagno medio nei 16 giorni in cui SPY scende (-55 bps in media) | +4,0 bps | +3,6 bps | +2,8 bps |
| quota di quei giorni in positivo | 62% | 62% | 56% |

Sul train il beta è 0,01 e la correlazione 0,07-0,08 per tutte e tre.

Test statistico sullo Sharpe (sezione 5 del notebook). Scelte di Bea, prese prima di calcolare: bootstrap della differenza di Sharpe tra strategia e SPY, solo sul test, costo 0, A, B e C. Si estraggono 32 giorni del test con reinserimento, gli stessi per la strategia e per SPY, 10.000 volte con seed 0. Regola scritta prima: la differenza è sostenuta se l'intervallo al 95% non contiene lo zero.

| | A | B | C |
| --- | --- | --- | --- |
| Sharpe strategia meno Sharpe SPY | +4,6 | +4,4 | +2,4 |
| intervallo al 95% | da -4,6 a +12,5 | da -4,8 a +12,4 | da -7,3 a +10,6 |
| quota di estrazioni con strategia sotto SPY | 15% | 16% | 31% |
| massimo drawdown (SPY -3,0%) | -0,17% | -0,19% | -0,21% |

File: `Results/curva_capitale_100.png` (train), `Results/test/curva_capitale_100.png` (test), `Results/metriche_train_test.csv`, `Results/neutralita_mercato.csv`, `Results/test/sharpe_contro_spy.csv`.

#### Cosa ci dicono i risultati

- L'agente non migliora la strategia nemmeno con queste metriche: la B sta poco sotto la A (blocca solo 7 trade sul test), la C più sotto. Sul test la C rende meno anche di SPY (+0,41% contro +0,47%), pur con molto meno rischio.
- A costo 0 tutte e tre hanno molto meno rischio di SPY (volatilità 1,1-1,3% contro 11-12%, drawdown sotto lo 0,25% contro il 3%); con costi realistici perdono. La volatilità è bassissima perché il capitale è investito solo di giorno e in pochi trade: lo Sharpe alto non è confrontabile con quello di un fondo.
- Beta vicino a zero e guadagni medi positivi nei giorni in cui SPY scende vanno a favore del bonus "market-neutral"; la correlazione negativa sul test e i rendimenti piccoli in assoluto no.
- Bonus "rendimento corretto per il rischio superiore": il drawdown è più basso di SPY per tutte e tre, ma la differenza di Sharpe non è sostenuta dal test (l'intervallo contiene lo zero), quindi il bonus non si può reclamare. In 32 giorni lo Sharpe di SPY è molto incerto; il professore chiede un test lungo e impegnativo, e il nostro non lo è.

#### Limiti da dichiarare nel report

- Periodi brevi (64 e 32 giorni) e un solo tipo di mercato: SPY quasi fermo in tutti e due.
- Annualizzare poche settimane è poco affidabile.
- Tasso privo di rischio 0.
- Il bootstrap sullo Sharpe estrae i giorni uno per uno: non tiene conto che giorni vicini possono somigliarsi.
- Rendimenti piccoli in assoluto (+0,8% in sei settimane sul test).

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

Bloomberg dà dati intraday per gli ultimi 140 giorni di borsa (nei nostri file sono 96, dal 16 giugno al 30 ottobre 2026; le tabelle seguenti sono indicative). La frequenza non si sceglie a intuito: si prova la stessa pipeline sulla stessa coppia a frequenze diverse e si confrontano i risultati. Si scarica una sola volta il dato al minuto e si creano da soli le barre da 5, 15 e 60 minuti con `resample` in pandas.

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
- Notizie: la copertura delle fonti è incompleta (finora una sola, Benzinga via Alpaca, circa 1 notizia al giorno per coppia), l'agente legge solo il titolo e il sommario, e nessuna notizia trovata non vuol dire nessuna notizia uscita.
- LLM: il modello può già conoscere gli eventi del periodo testato, e questo falsa il test.
- Coppie: scelte sul passato. Il legame tra due aziende può rompersi in futuro, ed è proprio il rischio che l'agente deve intercettare.
- Win rate: da solo non basta a dire che la strategia guadagna. Contano anche l'importo medio di vincite e perdite (profit factor).
