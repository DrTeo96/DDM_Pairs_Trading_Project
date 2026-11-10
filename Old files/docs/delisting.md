# Titoli che escono dal mercato con una posizione aperta

Nota di ricerca per il progetto di pair trading sull'S&P 500 (dati giornalieri, 2000 - settembre 2026, universo point-in-time). Consultazione delle fonti: 30 ottobre 2026.

**Domanda.** Come tratta la letteratura i titoli che escono dal mercato mentre una posizione è aperta, e quanto è grande l'errore se si chiude all'ultimo prezzo disponibile?

**Questa nota non decide.** Presenta opzioni ed evidenze; la scelta spetta al team.

**Legenda.** Ogni affermazione porta una di queste etichette:

- **[V]** verificata leggendo il testo della fonte; il codice rimanda all'[elenco delle fonti](#fonti-lette).
- **[P]** verificata solo in parte: abstract, pagina di catalogo o estratto restituito da un motore di ricerca.
- **[C]** calcolo o ragionamento dell'autore di questa nota, non presente nelle fonti.

Ciò che non è stato possibile verificare è raccolto nella [sezione 6](#6-cosa-non-è-stato-possibile-verificare).

## 1. Sintesi

1. Chiudere all'ultimo prezzo equivale a imporre un delisting return pari a zero. Shumway osserva che un rendimento così calcolato è ottenibile solo vendendo l'ultimo giorno di negoziazione, cosa che l'investitore in genere non può sapere in anticipo. [V: S97, p. 328]
2. L'errore dipende molto dalla causa. Fusioni: circa +2% in media. Delisting per performance su NYSE/AMEX: circa -30%. Su Nasdaq: -55% come rendimento corretto, inclusi i costi di liquidità. [V: S97, Tab. I e V; SW99, p. 2370]
3. Queste stime vengono da campioni 1962-1995 dominati da titoli piccoli. Nel decile di capitalizzazione più alto Shumway non trova alcun effetto, nemmeno con -100%. [V: S97, Tab. VII] Nessuna fonte letta misura l'errore sui componenti dell'S&P 500 dopo il 2000.
4. L'unico dato trovato su un pair trading: Gatev et al. portano a -100% solo le gambe long delistate e il top-20 resta a 1,32% al mese, contro 1,44% del caso base. [V: GGR, nota 5 e sez. 3.1]
5. L'uscita dall'indice è un evento diverso: di norma il titolo continua a essere scambiato e un prezzo esiste. La riga attuale di `SPEC.md`, sezione 6, tratta insieme i due casi. Nessun paper di pair trading letto affronta questo evento, perché quelli letti lavorano sull'universo CRSP e non su un indice.
6. **Do e Faff (2010, 2012) restano non verificati:** il testo integrale non era raggiungibile, quindi la loro scelta sul delisting non è nota (dettagli nella [sezione 4](#4-le-scelte-nei-paper-di-pair-trading)).

## 2. Delisting return mancanti e correzioni

### 2.1 Che cosa fornisce CRSP

CRSP calcola il delisting return confrontando il valore dopo il delisting (prezzo fuori borsa, quotazione o somma delle distribuzioni) con il prezzo dell'ultimo giorno di negoziazione. [V: DDG, p. 29]

Il primo numero del codice di delisting dà la categoria. [V: DDG, p. 27 e sezione III, pp. 117-118]

| Codici | Categoria | Esempi |
|---|---|---|
| 1xx | ancora negoziato | 100 |
| 2xx | fusione | 233 fusione in contanti; 231 fusione in azioni |
| 3xx | scambio di titoli | 331 |
| 4xx | liquidazione | 400 |
| 5xx | rimosso dal listino | 574 bancarotta; 552 prezzo troppo basso; 573 uscita volontaria (going private); 520 passaggio all'OTC |

**Attenzione ai valori sentinella.** Nel campo del delisting return alcuni valori sono codici di dato mancante, non rendimenti. [V: DDG, p. 30]

| Valore | Significato |
|---|---|
| -55,0 | nessuna fonte per stabilire il valore dopo il delisting, oppure ricerca ancora in corso |
| -66,0 | più di 10 periodi tra l'ultimo prezzo e il primo prezzo sul nuovo mercato |
| -88,0 | titolo ancora attivo |
| -99,0 | il titolo tratta su un nuovo mercato, ma CRSP non ha fonti di prezzo |

Il codice -55,0 non ha nulla a che vedere con la correzione del -55% di Shumway e Warther: la coincidenza numerica può generare errori. [C] Un valore di -1 invece è un vero rendimento: il titolo è considerato senza valore. [V: DDG, pp. 29-30]

### 2.2 Il problema: Shumway (1997)

Dati CRSP 1993, NYSE/AMEX 1962-1993. [V: S97, Tab. I]

| Causa | Codici | Titoli | Con delisting return | Media |
|---|---|---|---|---|
| Fusione | 200-240 | 2.171 | 98,9% | +1,94% |
| Scambio | 300-390 | 332 | 98,2% | -0,74% |
| Liquidazione | 400 | 134 | 31,3% | +1,00% |
| Cambio di mercato | 501-519 | 84 | 82,1% | -2,09% |
| Performance | 500, 520-584 | 1.029 | 11,7% | -41,56% |

Nel file Nasdaq nessuno dei 3.750 titoli delistati per performance aveva un delisting return. [V: S97, Tab. I, Panel B]

Altri risultati, tutti [V: S97]:

- **Effetto sorpresa.** Circa due terzi dei delisting per performance non sono annunciati: 68 preannunciati su 226 trovati, 1984-1993 (p. 331). Spesso coincidono con sospensioni delle negoziazioni, quindi vendere prima non era possibile (pp. 331-332).
- **Stima centrale.** Con i prezzi OTC delle Pink Sheets e 84 titoli divenuti senza valore, la media è -29,9% e la mediana -31,3%, con il 71,3% dei casi coperti e deviazione standard 48,9 (Tab. V).
- **Annunciati.** Chi annuncia perde in media il 14% entro un giorno dall'annuncio; i delisting CRSP classificati come preannunciati con prezzo OTC disponibile mostrano comunque -9,66% (Tab. IV e III).
- **Limiti dei dati OTC.** Sono quotazioni, non scambi, e i dealer non sono obbligati a rispettarle. Esempio: Careercom, denaro $0,01 e lettera $0,10 (pp. 334-335).
- **Dipendenza dalla dimensione.** Decile più piccolo: da 21,28% annuo a 19,83% con i dati OTC e a 16,07% con -100%. Decile più grande: 11,71% in tutti e tre i casi. Penultimo decile: da 12,45% a 12,40%. Pesi uguali, 1962-1992 (Tab. VII, p. 339).
- **Sensibilità al metodo.** L'effetto è maggiore con pesi uguali che con pesi di mercato, e maggiore con CAR che con buy-and-hold (p. 337).
- **Prescrizione.** I ricercatori dovrebbero dichiarare come trattano i delisting return, possono usare -0,3 al posto dei valori mancanti e possono calcolare un limite superiore con -1 (p. 340).

### 2.3 Nasdaq: Shumway e Warther (1999)

Dati Nasdaq 1972-1995. Tutti [V: SW99]:

- Sono delistati per performance ogni anno l'1,2% dei titoli NYSE/AMEX e il 5,6% di quelli Nasdaq (p. 2361).
- Rendimenti trovati per il 63% dei casi (2.107 su 3.330): media -26,3%, mediana -30,0%, con massa a -100% e coda destra spessa (p. 2368).
- Metà dei casi senza prezzo viene assunta a -100%: il calo medio di prezzo diventa -40% (p. 2369, eq. 1). L'assunzione è dichiarata come ragionevole, non osservata.
- Lo spread relativo medio passa da 0,41 a 0,82 con il delisting (p. 2370).
- Il -55% combina calo di prezzo e peggioramento della liquidità: (0,354P - 0,795P) / 0,795P (p. 2370, eq. 3).

**Implicazione.** Il -55% incorpora uno spread pre-delisting del 41%, tipico di microcap. Trasferirlo a un componente dell'S&P 500 è un'estrapolazione. Il -30% di Shumway è invece una media di rendimenti su quote medie e non include esplicitamente quel costo. [C]

### 2.4 Varianti usate dopo

La regola non è unica. L'insieme dei codici cambia da fonte a fonte:

| Fonte | Regola | Stato |
|---|---|---|
| SAFE, dataset CRSP preprocessato | `dlret` se disponibile; altrimenti -30% NYSE/Amex e -55% Nasdaq sui "codici rilevanti", non elencati | [V: SAFE, p. 2] |
| Schwarz, Walter e Weiss (2026), descrivendo Shumway | -30% se il valore manca e il codice è tra 400 e 591 | [V: SWW, p. 16] |
| Shumway e Warther, definizione di "performance" su Nasdaq | codici 500 e 505-588 | [V: SW99, sez. I.A] |
| *Long-Term Shareholder Returns*, FAJ (2023) | -30% per i codici 500, 520, 551-573, 574, 580, 584 | [P: estratto di ricerca, FAJ] |
| Shumway stesso | -0,3 per i delisting per performance mancanti (500, 520-584) | [V: S97, pp. 329, 340] |

Il dataset SAFE compone poi il rendimento ordinario con il delisting return e usa quello disponibile se ne esiste uno solo. [V: SAFE, p. 2]

### 2.5 Il nuovo formato CRSP (CIZ)

Per il 2000-2026 conta anche il formato dei dati, se si usasse CRSP come backup.

- CRSP ha interrotto il vecchio tape nel gennaio 2025. Nei rendimenti mensili del nuovo tape il delisting è incluso "se appropriato". [V: SWW, abstract e p. 10]
- Il nuovo tape **non** imposta -30% sui valori mancanti e pone il rendimento a zero se il pagamento dista più di 30 giorni dal delisting: così gli autori spiegano le differenze rispetto al vecchio tape. È una ricostruzione degli autori, non una dichiarazione di CRSP. [V: SWW, pp. 16-17]
- Nel nuovo formato il delisting return entra nella serie giornaliera come riga con `DlyDelFlg = Y`. [V: WRDS, slide 14] La copia del DDG letta è del 2012 e non copre CIZ.

**Esempio: Lehman Brothers (codice 574).** [V per i dati: WRDS, slide 14-15; C per i calcoli]

| Data | Prezzo | Rendimento |
|---|---|---|
| 29/8/2008 | 16,09 | fine mese precedente |
| 17/9/2008 | 0,13 | ultimo prezzo: -56,67% nel giorno |
| 18/9/2008 | 0,052 | delisting return: -60% |

Il -60% sembra enorme, ma si applica a un valore residuo. Rispetto al prezzo di fine agosto, l'errore da ultimo prezzo vale (0,13 - 0,052) / 16,09 = **0,48%**; quasi tutta la perdita era già nei prezzi di borsa. Il delisting return va quindi applicato al valore corrente della gamba, non al capitale iniziale. Un caso solo non è una stima dell'errore medio.

## 3. Bancarotta, acquisizione, uscita dall'indice

### 3.1 Confronto per causa e per gamba

Con "ultimo prezzo" il delisting return viene posto a zero. Il segno dell'errore è un ragionamento [C]; le grandezze sono delle fonti indicate.

| Evento | Il titolo esiste ancora? | Rendimento omesso | Gamba long | Gamba short | Evidenza |
|---|---|---|---|---|---|
| Bancarotta o delisting per performance | Spesso OTC o senza valore | -30% NYSE/AMEX; -55% corretto Nasdaq; fino a -100% | Profitto **sovrastimato** | Profitto **sottostimato** sulla carta; realizzabilità non verificata | [V: S97, SW99] |
| Acquisizione completata | No, si riceve il corrispettivo | Circa +2% in media | Profitto leggermente sottostimato | Profitto leggermente sovrastimato | [V: S97, Tab. I] |
| Uscita dall'indice senza delisting | Sì | Nessuno: il prezzo esiste | Nessun errore da dato mancante | Nessun errore da dato mancante | [C] |

### 3.2 Bancarotta

- **Long.** È il caso in cui l'ultimo prezzo inganna di più: spesso il titolo è sospeso prima che il mercato reagisca. [V: S97, pp. 331-332]
- **Short.** Applicare lo stesso -30% alla gamba short **aumenta** il profitto simulato. Questo guadagno può non essere incassabile con le stesse modalità: quotazioni OTC non vincolanti e spread molto ampi. [V per spread e quote: S97, SW99; C per l'applicazione allo short]
- **Asimmetria nel paper di riferimento.** Gatev et al. applicano lo stress solo al long, proprio perché è la direzione che penalizza il profitto. [V: GGR, nota 5] Discutono anche che il titolo long possa avere un rischio di fallimento temporaneamente più alto, ma ritengono improbabile che i rendimenti siano una remunerazione di questo rischio, perché gran parte dell'alfa viene dallo short. [V: GGR, sez. 1.5 e 3.7]
- **Recall.** Gatev et al. simulano recall dello short nei giorni di volume elevato: i profitti calano di 4-13 pb al mese e il top-20 scende a 85 pb. Il test riguarda la chiusura forzata in generale, non il delisting. [V: GGR, sez. 3.9]

### 3.3 Acquisizione

- **Delisting return.** È quasi sempre disponibile e piccolo: 98,9% dei casi e +1,94% su NYSE/AMEX; 95,7% e +2,31% su Nasdaq. [V: S97, Tab. I]
- **Prezzi prima della chiusura.** Nelle operazioni riuscite lo spread si riduce avvicinandosi alla conclusione e si azzera al completamento. [V: MP, pp. 2139-2140] Questo spiega perché l'ultimo prezzo sia già vicino al valore finale. [C]
- **Il rischio vero sta prima del delisting.** Il salto all'annuncio è già nei prezzi di borsa, quindi non è un errore da ultimo prezzo: colpisce una gamba short sul target indipendentemente da questa scelta. [C] L'entità del premio non è stata verificata ([sezione 6](#6-cosa-non-è-stato-possibile-verificare)).
- **Operazione fallita.** Non c'è delisting, ma lo spread mediano passa da circa 15% a oltre 30% il giorno dell'annuncio. [V: MP, pp. 2139-2140] La gamba long sul target può subire un calo che resta visibile nei prezzi. [C]
- **Corrispettivo in azioni.** I codici CRSP distinguono contanti e azioni (233, 231). [V: DDG, p. 117] La gestione operativa di uno short su un target pagato in azioni non è stata verificata.

### 3.4 Uscita dall'indice

- **Titolo ancora negoziato.** La distorsione di Shumway non si applica, perché il prezzo esiste. [C] Molte uscite sono migrazioni verso l'S&P MidCap, con una quota in crescita. [V: GS, p. 4]
- **Effetto di prezzo.** Rendimento cumulato corretto per il mercato, dall'ultimo giorno prima dell'annuncio al primo dopo l'implementazione: -12,3% negli anni 2000, -0,6% negli anni 2010. L'intervallo medio tra annuncio e data effettiva è di 5,8 giorni. Per gran parte del campione il rendimento si concentra all'annuncio. [V: GS, p. 10 e nota 8] I valori della versione pubblicata possono differire leggermente: vedi [sezione 6](#6-cosa-non-è-stato-possibile-verificare).
- **Filtri del campione.** Il campione principale di GS esclude alcuni casi vicini ad acquisizioni o delisting; gli autori affermano che le conclusioni sui rendimenti non dipendono dal campione. Quindi non è una stima diretta per le uscite dovute a fusione o fallimento. [V: GS, pp. 6-7]
- **Convenzione di S&P.** Nel 2017 S&P DJI ha stabilito che un titolo passato all'OTC usa i prezzi OTC fino alla rimozione; se non tratta sull'OTC prima della data di rimozione, esce a prezzo zero. [V: SP17] È una convenzione di calcolo dell'indice, non un rendimento realizzabile da un investitore.
- **Sovrapposizione.** Uscita dall'indice e delisting possono essere lo stesso evento (fusione) oppure distanti nel tempo (migrazione, fallimento dopo l'uscita). Un titolo uscito dall'indice può quindi fallire dopo: se la posizione resta aperta, il problema del delisting torna. [C]

## 4. Le scelte nei paper di pair trading

| Paper | Universo | Regola sul delisting | Stato |
|---|---|---|---|
| Gatev, Goetzmann e Rouwenhorst (2006) | CRSP giornaliero, 1962-2002; esclusi i titoli con giorni senza scambi in formazione | Si chiude la coppia usando il delisting return **oppure** l'ultimo prezzo disponibile. Stress: -100% solo sulle gambe long delistate | [V: GGR, p. 12, nota 5] |
| Do e Faff (2010) | Non verificato direttamente | **Non verificata** | Solo pagina di sintesi [P: DF10] |
| Do e Faff (2012) | USA, 1963-2009 | **Non verificata** | Solo abstract [P: DF12] |
| Bowen e Hutchinson (Regno Unito) | Datastream, 1979-2012 | Falliti e acquisiti restano nel campione fino alla data di delisting. Nessun delisting return dichiarato | [V: BH, sez. dati] |
| Zhu (2024, working paper) | CRSP, 2003-2023 | La posizione si chiude se un titolo è delistato e il prezzo diventa mancante | [V: Z, sez. metodologia] |
| Rad, Low e Faff (2016) | Non approfondito | Nel testo estratto dal manoscritto non compare la parola "delist"; l'estrazione ha segnalato un errore del PDF | [V: RLF, ricerca nel testo] |

### Il dato di Gatev et al.

Il top-20 passa da 1,44% a 1,32% al mese, cioè -12 pb al mese (-8,3%). [V per i valori: GGR; C per la differenza]

Tre cautele nell'uso di questo confronto, tutte [C]:

1. L'1,44% è il rendimento fully invested (sez. 3.1); la nota 5 non specifica la base dell'1,32%, che qui si presume uguale. Il rendimento su capitale impegnato, la base prevista da `SPEC.md`, è 0,81%: se la perdita assoluta fosse la stessa, il peso relativo sarebbe circa il 15%.
2. È un limite estremo sulle sole gambe long, che non testa le gambe short.
3. Il campione è 1962-2002 su CRSP intero e non sull'S&P 500, anche se il 74% dei titoli del top-20 sta nei tre decili maggiori. [V per il 74%: GGR, sez. 3.2]

### Falso riscontro da evitare

Un risultato di ricerca attribuiva a Do e Faff il test "-100% for delisted long stocks". Nella pagina Quantpedia quella frase si riferisce a **Gatev et al.** (p. 12, 1,32%). [V: pagina Quantpedia e GGR] Non va citata come scelta di Do e Faff.

## 5. Opzioni per il team

Le opzioni A-E riguardano il delisting, F-H l'uscita dall'indice: sono due scelte separate. L'ordine non è una preferenza.

### 5.1 Delisting con posizione aperta

| Opzione | Regola | A favore | Contro | Dati richiesti |
|---|---|---|---|---|
| **A. Ultimo prezzo** | Delisting return = 0 per tutti (regola attuale in `SPEC.md`, sez. 6) | Semplice; basta il prezzo. L'errore può essere piccolo su large cap (S97, Tab. VII) | Non realizzabile sui delisting a sorpresa (S97, p. 328); sovrastima i long | Prezzi |
| **B. Regola Gatev** | Delisting return se c'è, altrimenti ultimo prezzo | Allineata al paper di riferimento | Il dato manca soprattutto nei casi negativi (S97, Tab. I) | Delisting return per titolo |
| **C. Imputazione per causa** | Delisting return se c'è; altrimenti -30% per performance, eventualmente -55% su Nasdaq; 0 per le altre cause | Standard di Shumway; distingue le cause | Stime 1962-1995 su titoli piccoli; insieme di codici non univoco (sez. 2.4) | Rendimento e motivo del delisting |
| **D. Come C, ma asimmetrica** | Imputazione solo sui long; short a 0 | Non accredita guadagni forse non incassabili | Non è uno standard citato: deriva dalla logica di GGR, nota 5 [C] | Come C |
| **E. Stress -100% long** | Da affiancare a qualsiasi opzione come limite | Precedenti: GGR e S97 (p. 340). Non richiede dati sul motivo | È un limite, non una stima | Elenco dei delisting |

**Escludere le coppie a posteriori** non è un'opzione valida: togliere dal backtest le coppie con un delisting futuro usa informazione non disponibile al momento. [C] Zhu filtra i titoli poco liquidi nella selezione, che è una cosa diversa, e ottiene una varianza minore. [V: Z]

### 5.2 Uscita dall'indice con posizione aperta

Nessuna fonte letta di pair trading sostiene una di queste opzioni. Le evidenze disponibili sono indirette.

| Opzione | Regola | A favore | Contro |
|---|---|---|---|
| **F. Chiusura alla data effettiva** | Si chiude alla chiusura del giorno di uscita | Regola semplice; coerente con un universo legato all'indice | Chiude per un motivo estraneo al segnale; il rendimento attorno all'evento resta nella posizione |
| **G. Mantenere fino all'uscita naturale** | Il titolo resta tradabile e la coppia segue le sue regole | Non interrompe il segnale; sfrutta prezzi che esistono | Servono prezzi dopo l'uscita; il titolo può poi fallire (torna la 5.1) |
| **H. Chiusura all'annuncio** | Si chiude quando l'uscita è annunciata, al giorno successivo | Evita il tratto tra annuncio e data effettiva, ma non la reazione all'annuncio, dove si concentra gran parte del rendimento (GS, nota 8) | Richiede date di annuncio per tutto il periodo; non verificata in letteratura |

### 5.3 Ordine di grandezza per il progetto

Illustrazione, non stima. [C] Con $N$ coppie, capitale uguale e gamba ancora al valore iniziale, l'errore su un evento vale $r / N$ del capitale impegnato:

| Caso, con $N = 20$ | $r$ | Errore sul portafoglio |
|---|---|---|
| Fusione | +1,94% | 0,10% |
| Performance NYSE/AMEX | -30% | 1,5% |
| Performance Nasdaq corretto | -55% | 2,75% |
| Azzeramento | -100% | 5% |

L'errore si riduce se il prezzo è già crollato (Lehman) e l'impatto totale dipende dal numero di eventi, oggi ignoto.

### 5.4 Misure che possono ridurre l'incertezza

Sono verifiche possibili, non raccomandazioni su quale regola adottare:

1. Contare nell'universo point-in-time i delisting e le uscite con una posizione aperta nel backtest, per causa e per gamba.
2. Eseguire lo stesso backtest con A, B/C ed E: la differenza misura direttamente l'errore per questa strategia.
3. Se la LUISS ha accesso a WRDS, confrontare i delisting return CRSP con ciò che fornisce Bloomberg su un campione di eventi.

## 6. Cosa non è stato possibile verificare

**Do e Faff (2010, 2012)**

- Il trattamento del delisting non è stato letto. Tentativi falliti: CFA Institute (contenuto riservato), Strathprints (nessun testo integrale), ResearchGate, SSRN e Wiley (HTTP 403), working paper FMA (404), Web Archive (non raggiungibile).
- Che seguano Gatev et al. è solo un'ipotesi, non un dato.
- Il filtro su ultimo decile e prezzo sotto $5 attribuito al paper del 2012 è stato visto solo in un estratto di ricerca.
- **Per chiudere il punto:** recuperare i PDF tramite la biblioteca LUISS e leggere le sezioni su dati e metodologia.

**Copertura dei dati**

- Nessuna fonte letta misura la copertura dei delisting return CRSP dopo il 2000: i dati di S97 finiscono nel 1993, quelli di SW99 nel 1995.
- Nessuna fonte misura il delisting return specifico sui componenti o ex componenti dell'S&P 500.
- Quindi non si può dire quanto valga l'errore nel periodo 2000-2026, solo che i dati storici lo indicano piccolo sui titoli grandi.

**Bloomberg, fonte primaria prevista dal progetto**

- Nessuna documentazione trovata sul comportamento di `PX_LAST` dopo il delisting, sull'inclusione dei prezzi OTC o su un campo equivalente al delisting return. Le guide di biblioteca confermano solo che sul terminale si trovano aziende delistate e il filtro per delisting in `CACT`. [P]
- Va verificato sul terminale. Senza un campo di delisting return, le opzioni B, C e D richiedono un'altra fonte.

**Gamba short**

- Come si chiude uno short su un titolo in bancarotta (cancellazione delle azioni, restituzione del collaterale, tempi): trovate solo fonti di bassa autorità (Tickeron, forum), non usate qui. Nessun documento SEC o FINRA.
- Conversione di uno short su un target in fusione in contanti o in azioni: nessuna fonte.

**Altra letteratura non letta**

- Beaver, McNichols e Price (2007), *Delisting returns and their effect on accounting-based market anomalies*, JAE: confermati solo titolo e riferimenti; testo non accessibile.
- La convenzione "-100% sui codici non di performance" attribuita a Hou, Xue e Zhang: non trovata in una fonte, non va citata senza controllo.
- Premi nelle acquisizioni (Andrade, Mitchell e Stafford 2001): non letto.
- Chen, Noronha e Singal (2004): nessun calo permanente dopo l'uscita. Kumar et al. (2023): calo permanente. Solo estratti di ricerca, **in disaccordo tra loro**. [P]
- Quota di uscite dovuta a fusioni e bancarotte ("quasi 3/4"): solo un paper terzo in un estratto. [P]
- Greenwood e Sammon, versione pubblicata (JF 2025) e bozza 2024: un estratto riporta -16,1% e -12,4% per anni 90 e 2000, contro -16,6% e -12,3% della versione NBER letta. [P]

**Metodologia S&P**

- *Equity Indices Policies & Practices* (agosto 2026) e *S&P U.S. Indices Methodology*: download bloccato (403). Un estratto di ricerca indica che il target di una fusione è rimosso intorno alla data effettiva, di solito al prezzo di chiusura. [P]
- Verificato solo il comunicato del 2017. La regola potrebbe essere cambiata in seguito.

**Versioni delle fonti**

- GGR è il working paper Yale ICF 08-03 (febbraio 2006) su un host di terzi; non è stato confrontato con la versione pubblicata su RFS. Pagine e sezioni citate sono quelle del working paper.
- La guida CRSP letta è del 29 marzo 2012 e ospitata dall'Università di Toronto; i codici correnti vanno confermati su WRDS.
- SWW è una bozza del 24 febbraio 2026; GS è il working paper NBER.

**Disallineamento da segnalare**

- Questa ricerca considera il periodo 2000 - settembre 2026; `SPEC.md` parla ancora di 2000-2024.
- `SPEC.md` è stato solo letto, non modificato. La sua regola sul delisting è marcata [PROPOSTA] e resta aperta.

## Fonti lette

| Codice | Fonte | Accesso |
|---|---|---|
| S97 | Shumway, T. (1997), *The Delisting Bias in CRSP Data*, Journal of Finance 52(1), 327-340 | [PDF dal sito dell'autore](https://www.tylergshumway.org/Shumway-DelistingBiasCRSP-1997.pdf) |
| SW99 | Shumway, T. e Warther, V. (1999), *The Delisting Bias in CRSP's Nasdaq Data and Its Implications for the Size Effect*, Journal of Finance 54(6), 2361-2379 | [PDF dal sito dell'autore](https://www.tylergshumway.org/Shumway-DelistingBiasCRSPs-1999.pdf) |
| GGR | Gatev, E., Goetzmann, W. e Rouwenhorst, K.G., *Pairs Trading: Performance of a Relative Value Arbitrage Rule*, Yale ICF WP 08-03 (feb. 2006); poi Review of Financial Studies (2006) | [Copia del working paper](https://c.mql5.com/forextsd/forum/208/Pairs%20Trading%20-%20Performance%20of%20a%20Relative%20Value%20Arbitrage%20Rule.pdf) |
| DDG | CRSP, *Data Descriptions Guide* (agg. 29 marzo 2012) | [Copia Università di Toronto](https://clouddc.chass.utoronto.ca/ds/crsp/en/manuals/data_descriptions_guide.pdf) |
| WRDS | WRDS, webinar sulla transizione da SIZ a CIZ | [PDF](https://wrds-www.wharton.upenn.edu/documents/2084/Webinar.pdf) |
| SWW | Schwarz, P., Walter, D. e Weiss, P. (24 feb. 2026), *Rewriting CRSP's History* | [PDF](https://jfqa.org/wp-content/uploads/2026/02/26501_Rewriting_CRSP_History.pdf) |
| SAFE | Hillert, A. (2025), *Information on the preprocessed CRSP data set*, SAFE Research Datacenter | [PDF](https://datacenter.safe-frankfurt.de/documents/Data_Description_CRSP_Shumway_20250317.pdf) |
| MP | Mitchell, M. e Pulvino, T. (2001), *Characteristics of Risk and Return in Risk Arbitrage*, Journal of Finance 56(6), 2135-2175 | [PDF](https://www.johnhcochrane.com/s/mitchell-pulvino-characteristics-of-risk-and-return-JF.pdf) |
| GS | Greenwood, R. e Sammon, M., *The Disappearing Index Effect*, NBER WP 30748; poi Journal of Finance (2025) | [PDF](https://www.nber.org/system/files/working_papers/w30748/w30748.pdf) |
| SP17 | S&P Dow Jones Indices, comunicato del 31 luglio 2017 sui titoli in bancarotta | [Comunicato](https://press.spglobal.com/2017-07-31-S-P-Dow-Jones-Indices-Announces-Changes-to-the-S-P-U-S-Indices-Methodology-and-to-the-Pricing-of-Bankrupt-U-S-Listed-Securities) |
| BH | Bowen, D. e Hutchinson, M., *Pairs Trading in the UK Equity Market: Risk and Return* | [PDF](https://www.ucc.ie/en/media/research/centreforinvestmentresearch/wp/PT2.5.pdf) |
| Z | Zhu, X. (3 aprile 2024), *Examining Pairs Trading Profitability* | [PDF](https://economics.yale.edu/sites/default/files/2024-05/Zhu_Pairs_Trading.pdf) |
| RLF | Rad, H., Low, R. e Faff, R. (2016), *The profitability of pairs trading strategies*, Quantitative Finance | [Manoscritto](https://pure.bond.edu.au/ws/portalfiles/portal/36339487/AM_The_profitability_of_pairs_trading_strategies.pdf) |

**Solo in parte**

| Codice | Fonte | Che cosa è stato visto |
|---|---|---|
| DF10 | Do, B. e Faff, R. (2010), *Does Simple Pairs Trading Still Work?*, Financial Analysts Journal 66(4) | [Pagina di sintesi CFA](https://rpc.cfainstitute.org/research/financial-analysts-journal/2010/does-simple-pairs-trading-still-work) |
| DF12 | Do, B. e Faff, R. (2012), *Are Pairs Trading Profits Robust to Trading Costs?*, Journal of Financial Research 35(2) | [Abstract su Strathprints](https://strathprints.strath.ac.uk/41722/) |
| - | Quantpedia, *Pairs Trading with Stocks* (fonte secondaria, usata solo per il falso riscontro) | [Pagina](https://quantpedia.com/strategies/pairs-trading-with-stocks) |
| FAJ | *Long-Term Shareholder Returns: Evidence from 64,000 Global Stocks*, Financial Analysts Journal (2023) | [Estratto di ricerca](https://www.tandfonline.com/doi/abs/10.1080/0015198X.2023.2188870); pagina non accessibile |
