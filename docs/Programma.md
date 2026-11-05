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
| 2 | Fonte delle notizie con orario | API di notizie finanziarie con storico; GDELT; archivio Bloomberg | Verificare lo storico con timestamp di 2 o 3 fonti e sceglierne una | 2 nov |
| 3 | Periodo dei dati e divisione train/test | Dipende dai punti 1 e 2 | Primi due terzi per addestramento, ultimo terzo per test, usato una volta sola. Ora sappiamo che i giorni sono 96 (91 per 4 coppie): circa 64 e 32 | 6 nov |
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

Stato: **fatto in gran parte** (restano tre controlli, vedi più sotto). Il lavoro è nel notebook [src/coppie.ipynb](../src/coppie.ipynb), che contiene il codice, le motivazioni di ogni scelta e il testo dei risultati. La lista finale è salvata in `data/processed/selected_pairs.csv` (cartella ignorata da git: chi la vuole rilancia il notebook).

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

### Passaggio 2. Dati di prezzo intraday

Stato: **fatto** per la parte di pulizia; restano tre decisioni collegate (vedi "Decisioni ancora da prendere"). Il lavoro è nel notebook [src/intraday_pulizia.ipynb](../src/intraday_pulizia.ipynb), che contiene il codice, le motivazioni e i controlli. I risultati sono in `data/processed/pairs_intraday/` (cartella ignorata da git: chi li vuole rilancia il notebook).

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
- Notizie: la copertura delle fonti è incompleta, l'agente legge solo il titolo, e nessuna notizia trovata non vuol dire nessuna notizia uscita.
- LLM: il modello può già conoscere gli eventi del periodo testato, e questo falsa il test.
- Coppie: scelte sul passato. Il legame tra due aziende può rompersi in futuro, ed è proprio il rischio che l'agente deve intercettare.
- Win rate: da solo non basta a dire che la strategia guadagna. Contano anche l'importo medio di vincite e perdite (profit factor).
