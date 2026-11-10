# Bloomberg Desktop API: cosa scaricare e cosa verificare

Ricerca su documentazione pubblica per il progetto di pair trading sull'S&P 500 (dati giornalieri, 2000 - settembre 2026). Fonti consultate il 30 ottobre 2026. Nessun dato è stato provato su un terminale.

La documentazione ufficiale di Bloomberg (`FLDS`, `WAPI`, `DAPI`) è quasi tutta dietro il terminale. Questa nota si appoggia quindi a poche pagine Bloomberg pubbliche e a fonti terze. Il livello di ogni affermazione è indicato così:

| Etichetta | Significato |
|---|---|
| **[BBG]** | Testo Bloomberg: paper, pagina pubblica o schermata di terminale riprodotta da terzi |
| **[TERZI]** | Documentazione di terzi affidabili (MathWorks, biblioteche universitarie, manuali di librerie) |
| **[DEBOLE]** | Un solo progetto, un forum o un caso d'uso isolato |
| **[INFERENZA]** | Deduzione mia, non scritta in nessuna fonte |
| **[NON CONFERMATO]** | Nessuna fonte trovata: si decide al terminale |

Gran parte delle fonti è datata, comprese le due più utili: il paper sul sentiment è del 2016, il testo sui limiti è in un PDF del 2018. Vanno considerate come ipotesi forti, non come stato attuale del servizio.

## 1. Sintesi

1. **Tre risposte cambiano il progetto.**
   - Il sentiment giornaliero, secondo Bloomberg, esce circa 10 minuti **prima dell'apertura**, non dopo la chiusura.
   - Nessuna fonte conferma che la serie storica sia davvero point-in-time.
   - Più guide universitarie, che rimandano alle Desktop API Guidelines, dicono che i dati **non devono lasciare il PC del terminale**. Questo è in conflitto con il piano Parquet e con l'agente LLM (sezione 7).
2. **Nomi di campo trovati.** I candidati sono `NEWS_SENTIMENT_DAILY_AVG` e, per la heat, `NEWS_HEAT_PUB_DAVG` o `NEWS_HEAT_PUB_DMAX`. La corrispondenza con le etichette "Daily News Sentiment Score" e "Daily News Publication Heat" è una mia inferenza.
3. **Override della composizione.** Circolano due nomi: `END_DATE_OVERRIDE` e `END_DT`. Il test decisivo è controllare che la lista cambi davvero tra date diverse.
4. **Nessuna fonte risolve** la mappatura dei ticker delistati, l'esistenza del GICS storico su Bloomberg e la definizione ufficiale di `TOT_RETURN_INDEX_GROSS_DVDS`.
5. **Rischio volumi.** Il limite mensile (non pubblicato, per terminale) è il più pericoloso. Il testo Bloomberg del 2018 fa pensare che il volume sia gestibile, ma resta da chiarire come vengono conteggiati gli hit di `BDH` (sezione 6).

## 2. Composizione storica dell'S&P 500

| Punto | Esito | Livello |
|---|---|---|
| `=BDS("SPX Index","INDX_MWEIGHT_HIST","END_DATE_OVERRIDE=20020207")`, data `YYYYMMDD` | Sintassi documentata [1] | [TERZI] |
| Stesso campo e override via Python su `DAX Index`; output `Index Member` e `Percent Weight` [2] | Confermato | [TERZI] |
| Override alternativo `END_DT`: `{'INDX_MWEIGHT_HIST'},{'END_DT'},{'20070506'}` su `SPX Index` [3]; stesso nome in un caso reale con Rblpapi [4] | Confermato che è in uso, ma non quale dei due sia quello attuale | [TERZI] |
| `INDX_MEMBERS` con `END_DATE_OVERRIDE=20190501`: restituisce solo i ticker [5] | Alternativa senza pesi | [TERZI] |
| "A different ticker could be used for historical members": controllare con `DES` sull'indice [1] | Possibile ticker diverso per lo storico | [TERZI] |
| I ticker vanno completati con `" Equity"`: output `1COV GY` [2], formula `A1 & " Equity"` [5] | Confermato | [TERZI] |
| Il campo include i membri poi delistati | Affermato solo per indici brasiliani [6] | [DEBOLE] |
| Pesi affidabili | Nell'esempio di [2] tutti i pesi valgono `-2.42e-14`, senza spiegazione. Non fare affidamento sui pesi finché non sono verificati | [DEBOLE] |
| Copertura dal gennaio 2000 per `SPX Index` | L'esempio più vecchio è del 2002 [1] | [NON CONFERMATO] |
| Rischio di dati incompleti | Il maintainer di Rblpapi parla di ritorni di dati incompleti e chiede controlli propri [4] | [TERZI] |

**Frequenza di download.** IESE consiglia snapshot a ogni fine mese: usando solo le date estreme si perdono i titoli entrati e usciti nel frattempo [7]. Da gennaio 2000 a settembre 2026 sono 321 chiamate. La schermata `CHNG` funziona solo per alcuni indici e non si esporta [7].

**Trappola da testare [INFERENZA]:** se un override non viene riconosciuto, la risposta potrebbe essere la composizione corrente senza alcun errore. Sarebbe survivorship bias silenzioso.

## 3. Sentiment e news heat

### 3.1 Nomi di campo

Bloomberg usa proprio le due etichette della bozza, ma non pubblica il mnemonico: "Daily News Publication Heat" è un punteggio sul volume del flusso di notizie, "Daily News Sentiment Score" una misura del sentiment medio del flusso [8] **[BBG]**.

La lista dei campi "news heat" arriva da una schermata di terminale del 29 gennaio 2016, riprodotta nell'Internet Appendix di Ben-Rephael, Carlin, Da e Israelsen (*Journal of Finance*) [9, Fig. IA.1] **[BBG, via terzi]**:

| Descrizione nel terminale | ID | Mnemonico | Rilevanza |
|---|---|---|---|
| News Heat - Daily Average Story Flow | `NW013` | `NEWS_HEAT_PUB_DAVG` | **Candidato principale** per la publication heat |
| News Heat - Max Story Flow | `NW012` | `NEWS_HEAT_PUB_DMAX` | **Candidato** |
| News Publication - Daily Number of Stories | `NW014` | `NEWS_HEAT_PUB_DNUMSTORIE...` (troncato nella schermata) | Conteggio storie, nome completo da verificare |
| News Heat - Daily Max Readership | `NW016` | `NEWS_HEAT_READ_DMAX` | Lettura, non pubblicazione |
| News Heat - Average Readership | `NW015` | `NEWS_HEAT_READ_DAVG` | Lettura, non pubblicazione |
| News Heat - Story Flow (Realtime) | `RQ368` | `NEWS_HEAT_STORY_FLOW_RT` | Solo tempo reale, non per lo storico |
| News Heat - User Activity (Realtime) | `RQ369` | `NEWS_HEAT_USER_ACTIVITY_R...` (troncato; `_RT` nel testo) | Solo tempo reale, non per lo storico |

La stessa appendice riporta che le misure di attenzione esistono solo nei giorni di borsa e raccomanda di **non** attivare "carry over last value" [9] **[TERZI]**. `RQ369` è una scala 0-4 relativa ai 30 giorni precedenti [9, Fig. IA.2]; che le varianti `PUB` usino la stessa scala è **[NON CONFERMATO]**.

**Sentiment:** l'unica attestazione letta di `NEWS_SENTIMENT_DAILY_AVG` è un progetto GitHub che dice di averlo scaricato con `BDH` per 30 titoli, 2018-2026 [10] **[DEBOLE]**. Lo stesso progetto riferisce che `NUM_NEWS_STORIES_24HR` restituisce `#N/A Field Not Applicable` e lo attribuisce al livello della licenza. Quindi la disponibilità può dipendere dal terminale. Il progetto indica `TREN NSENT` come punto d'accesso recente.

**[INFERENZA]** La corrispondenza tra `NEWS_SENTIMENT_DAILY_AVG` e "Daily News Sentiment Score", e tra `NEWS_HEAT_PUB_*` e "Daily News Publication Heat", non è scritta in nessuna fonte letta.

### 3.2 Costruzione e tempistica del sentiment

Fonte: Cui, Lam e Verma, *Embedded Value in Bloomberg News & Social Sentiment Data*, Bloomberg, 2016 [11] **[BBG]**. Autori dalla citazione in [12].

- Il sentiment **per storia** viene generato in tempo reale all'arrivo della notizia: punteggio in {1, 0, -1} e confidenza da 0 a 100.
- Il punteggio **giornaliero per azienda** è la media pesata per confidenza delle storie delle 24 ore precedenti, con valori da -1 a 1.
- Viene pubblicato "every morning about 10 minutes before market open". Il backtest parla esplicitamente di "observing the sentiment score at 9:20 AM".
- Il paper lo definisce un indicatore "lagging".

**Risposta sulla chiusura USA.** Nessuna fonte dice che il punteggio venga finalizzato rispetto alla chiusura. La tempistica documentata è prima dell'apertura. Il backtest confronta il punteggio con il rendimento open-to-close "on the same day as the sentiment score", dopo averlo osservato alle 9:20. Da qui due letture:

- **[INFERENZA]** Il valore con data T copre circa dalle 9:20 di T-1 alle 9:20 di T, ed è già noto alla chiusura di T. Sarebbe utilizzabile per un segnale calcolato sulla chiusura di T, senza contenere le notizie del pomeriggio di T.
- **[NON CONFERMATO]** La data assegnata da `BDH`, il fuso orario, il trattamento di weekend e festivi e l'attualità del dato del 2016. Un paper del 2026 scrive solo la finestra (t-1, t], senza orari [12].

Per la **heat** nessuna fonte dà l'orario. Se i campi giornalieri si chiudono a fine giornata, la heat di T potrebbe non essere nota quando serve, o incorporare notizie successive al segnale. **[NON CONFERMATO]**

Nei giorni senza notizie il valore manca: 0,76%-24,56% di mancanti su 34 titoli tecnologici [12] **[TERZI]**. Su titoli piccoli la quota può essere più alta **[INFERENZA]**.

### 3.3 È point-in-time?

**Non è confermato.** La frase di `SPEC.md` (sezione 9.1), "interamente backtestabile e point-in-time, perché Bloomberg calcola il sentiment al momento della pubblicazione", è vera per il calcolo della singola storia secondo [11], ma non basta per la serie storica. Non ho trovato nulla su:

- ricalcolo dello storico quando il modello viene riaddestrato;
- se la parte iniziale della serie sia stata calcolata in diretta o ricostruita dopo;
- versioni storiche del valore "come era noto allora".

Inoltre non ho potuto verificare l'inizio nel 2010: la pagina Bloomberg citata in `SPEC.md` restituisce 403 a un accesso automatico.

## 4. Prezzi aggiustati e total return

### 4.1 Opzioni della richiesta storica

Definizioni dalla documentazione MathWorks per la connessione Desktop [13] **[TERZI]**, che rimanda alla guida ufficiale in `WAPI <GO>`:

| Opzione | Cosa copre |
|---|---|
| `adjustmentSplit` | Prezzo **o volume**: spin-off, split e raggruppamenti, stock dividend, rights offering |
| `adjustmentNormal` | Dividendi ordinari: regular cash, interim, income, final, distribution e simili |
| `adjustmentAbnormal` | Dividendi straordinari: special cash, liquidation, capital gains, return of capital e altri |
| `adjustmentFollowDPDF` | Segue l'impostazione `DPDF <GO>` del terminale. Default MathWorks: `true` |

Quindi, senza impostare nulla, il risultato può **dipendere dalle preferenze `DPDF` del terminale**. Un blog del 2015 conferma l'uso delle tre opzioni a `true` e dice che per i prezzi originali vanno messe esplicitamente a `false` [14] **[DEBOLE]**.

Configurazione proposta **[INFERENZA, da provare]**:

```text
adjustmentFollowDPDF = false
adjustmentNormal     = true
adjustmentAbnormal   = true
adjustmentSplit      = true
```

La precedenza tra `adjustmentFollowDPDF` e le altre tre opzioni non è descritta in nessuna fonte letta. **[NON CONFERMATO]**

Una libreria Python riporta i flag `CshAdjNormal`, `CshAdjAbnormal` e `CapChg`, attivi di default **nelle funzioni di quella libreria** [15] **[TERZI]**. L'equivalenza con le opzioni sopra è **[INFERENZA]**.

### 4.2 Differenza con `TOT_RETURN_INDEX_GROSS_DVDS`

**Non ho trovato una definizione pubblica di questo campo.** L'unica traccia è una domanda del 2013, senza risposte, in cui il campo restituisce dati mensili sempre al giorno 28 [16] **[DEBOLE]**. La dicitura compare anche in un altro campo, `day_to_day_tot_return_gross_dvds`, indicato da una biblioteca per il total shareholder return [17] **[TERZI]**; i due campi non vanno confusi.

| Aspetto | `PX_LAST` aggiustato | `TOT_RETURN_INDEX_GROSS_DVDS` |
|---|---|---|
| Natura | Prezzo con opzioni di richiesta [13] | Campo a sé, definizione ufficiale non trovata |
| Dipende da `DPDF`/opzioni | Sì [13] | **[NON CONFERMATO]** |
| Trattamento dei dividendi | Secondo i flag scelti [13] | "Gross" fa pensare a dividendi lordi reinvestiti **[INFERENZA]** |
| Si applica anche a `PX_VOLUME` | Sì per `adjustmentSplit` [13] | No, non è un prezzo **[INFERENZA]** |
| Livello | Lo storico cambia con eventi futuri **[INFERENZA]** | Base e data di reinvestimento **[NON CONFERMATO]** |
| Rendimento di delisting | **[NON CONFERMATO]** | **[NON CONFERMATO]** |

Scaricare entrambi e confrontarli giorno per giorno intorno agli stacchi è più economico che decidere a priori.

## 5. Ticker delistati e GICS storico

### 5.1 Ticker delistati

La documentazione pubblica **non descrive** una procedura. Ciò che esiste:

- Gli autori Bloomberg avvertono che, nel loro stesso studio, membri e prezzi scaricati separatamente possono far perdere le barre di un titolo che ha cambiato ticker [11, nota 1] **[BBG]**. Il problema è quindi reale anche con dati Bloomberg.
- `/cusip/459200101 US` è un modo valido di indicare la stessa security, e il testo Bloomberg cita i prefissi `cusip` e `isin` [18, appendice] **[BBG]**.
- `CACT <GO>` elenca i delisting: Listings, Action Types, solo "Delisting" [19] **[TERZI]**. `SECF <GO>` cerca le security [5].
- `ENRNQ <equity>` citato su un forum (2015) come esempio di titolo fallito con dati conservati; nello stesso thread un altro utente non trova dati, ma forse per il ticker sbagliato [20] **[DEBOLE]**.
- La FIGI è pensata per non cambiare con le corporate action [21] **[TERZI]**. OpenFIGI esclude i titoli delistati per default e li include con `includeUnlistedEquities: true`; limite di 25 richieste al minuto senza chiave, 250 con chiave, con massimo 10 o 100 job per richiesta [22] **[TERZI]**.

**[NON CONFERMATO]:**

- i formati di ticker dei titoli ritirati (ricordo suffissi come `Q` o `D`, ma non ho trovato fonti);
- se la `BDH` su un ticker riutilizzato restituisce la società giusta;
- se i prefissi `/figi/` e `/bbgid/` funzionano in una richiesta storica;
- i campi identificativi da usare: `ID_BB_GLOBAL`, `COMPOSITE_ID_BB_GLOBAL`, `ID_BB_UNIQUE`, `ID_ISIN`, `ID_CUSIP`, `PARSEKYABLE_DES` sono candidati a memoria o da query, non letti in documentazione.

### 5.2 GICS storico

- **Su Bloomberg: [NON CONFERMATO] in entrambi i sensi.** Nessuna fonte dimostra che esista una storia dei campi GICS, e nessuna lo esclude. L'affermazione di `SPEC.md` ("restituisce la classificazione GICS attuale") è plausibile ma senza fonte.
- Gli esempi trovati usano solo `BDP` su `GICS_Sector_Name`, cioè un valore corrente [23] **[TERZI]**. `GICS_INDUSTRY_GROUP_NAME` non compare in nessuna fonte letta.
- `AS_OF_DATE` in BQL è documentato per i fondamentali [24] **[BBG]**. L'estensione alle classificazioni è **[NON CONFERMATO]**.
- **Fuori da Bloomberg:** S&P vende un GICS History dal 1985 con date from/thru. L'ho visto solo come estratto di ricerca: il PDF restituisce 403, quindi va verificato prima di citarlo [25]. Katselas, Sidhu e Yu trovano misure di performance meglio specificate con GICS dinamico che con quello statico [26] **[TERZI]**.

## 6. Limiti di volume

### 6.1 Testo Bloomberg

L'appendice del PDF dell'Università di Zurigo (2018) riproduce le pagine `WAPI` "Extended Rules" e "Managing Your API Data Limits" [18] **[BBG, via terzi]**:

- **Giornaliero:** totale degli hit, dove un hit è una coppia security/campo. 5 campi per 10 titoli fanno 50 hit. Le ripetizioni contano.
- **Mensile:** titoli unici **per categoria** (historical, derived, intraday, pricing, descriptive). Lo stesso titolo in una stessa categoria conta una sola volta nel mese, "no matter what the length of the period requested". Chiederlo in un'altra categoria aumenta il consumo.
- **Tempo reale:** titoli unici monitorati contemporaneamente.
- Bloomberg raccomanda di essere collegati al terminale mentre si scaricano i dati.

Il testo non pubblica le soglie numeriche.

### 6.2 Soglie e conseguenze

| Tema | Cosa dicono le fonti | Stato |
|---|---|---|
| Soglia giornaliera | 500.000 hit [27][28][29], azzerati a mezzanotte [27][30] | Coerente tra le fonti [TERZI]; il fuso orario non è indicato |
| Soglia mensile | "5000-7000 unique identifiers" [29]; secondo altri dipende da titoli e tipo di dato, modello non divulgato [18][28] | **In conflitto** |
| Tempo reale | 3.500 [27][28][29] | Non rilevante per il download storico |
| Ambito | Per terminale, non per utente [18][27][30] | Confermato. Il terminale LUISS è condiviso con chi lo usa nello stesso mese |
| Preavviso | Nessuno: si scopre solo dopo averlo superato [27][28] | Confermato |
| Azzeramento mensile | Inizio del mese successivo [27][28][29] | Confermato. Yale dice che anche dopo il limite giornaliero si riprende "the next month" [31], ma è un'eccezione |
| Deroghe | Bloomberg non azzera i limiti [30] e non li estende per gli abbonamenti educational [28] | Confermato per quelle biblioteche; LUISS da verificare |
| Codici errore | `#N/A Daily Capacity` [27][28], `#N/A Daily` [29], `#N/A Dly Lmt` e `#N/A Mth Lmt` [31], `#N/A Limit` [28][29][31], `#N/A Review` [27][28][29] | **Variano.** `Review` è il limite mensile per [27][28][29], ma per NYU indica un superamento giornaliero o in tempo reale, o una revisione [32]. Non dedurre il tipo di limite dal solo codice |

**Cosa succede in pratica:**

- Se il limite arriva durante una richiesta, si può ricevere l'errore "per each and every downloaded data point", senza alcun dato, secondo la guida di Zurigo [18].
- Una query può anche tornare **incompleta** o vuota [30].
- Questi comportamenti sono descritti per Excel. La forma dell'errore in una risposta `blpapi` o `xbbg` è **[NON CONFERMATO]**.

### 6.3 Stima per questo progetto

**[INFERENZA]** Con 1.200 titoli unici (ipotesi: `SPEC.md` cita 895 dal 2004) e 7 campi storici, più circa 8 campi statici:

| Lettura delle regole | Consumo giornaliero stimato | Esito |
|---|---|---|
| Hit per coppia security/campo (testo Bloomberg) | Circa 18.000 hit, più 321 per la composizione | Ampiamente sotto 500.000 |
| Hit per singolo dato (caso peggiore) | Fino a circa 56 milioni (1.200 x 6.700 giorni x 7) | Oltre il limite: servirebbero molti giorni |

Il testo Bloomberg indica la prima lettura. La guida di Zurigo, però, parla di costo "per data point" [18]: va chiarito con l'help desk.

Sul mensile si consumerebbero circa 1.200 titoli "historical" e 1.200 "descriptive". Sarebbero 2.400 su 5.000-7.000 se valesse la cifra di HKUST, in cui confluisce anche ciò che hanno scaricato gli altri utenti. La categoria di `BDS` è **[NON CONFERMATO]**.

Accorgimenti: prima pochi titoli di prova (la navigazione nel terminale non consuma limiti [18]), download a lotti con salvataggio dopo ogni lotto [18], niente `TODAY()` in Excel [18], `BDH` anziché `BDP` ripetuti [18]; NYU suggerisce anche BQL per ridurre il consumo [30].

## 7. Vincolo non richiesto, ma bloccante: i dati possono uscire dal terminale?

NYU: "Data downloaded using the API should not, under any circumstances, be removed from the Bloomberg terminal (i.e. local PC)" e "Only your analysis of the data can be removed" [30]. Yale lo conferma [31]. Entrambe rimandano alle Desktop API Guidelines in `DAPI <GO>` **[TERZI]**. Non ho letto il testo originale, e la sua applicazione a LUISS va chiarita.

Impatto sul progetto **[INFERENZA]**:

- `data/raw/` in Parquet su laptop o in repo: `data/` oggi non è in `.gitignore`.
- Headline e valori Bloomberg inviati a un provider LLM (`SPEC.md`, sezione 9.1).
- Lavoro di gruppo su macchine diverse dal PC del terminale.

Serve anche capire se sul PC del terminale si può installare Python: NYU indica che non c'è accesso remoto [30]. Se la risposta alle domande sopra è negativa, il backup CRSP via WRDS previsto in `SPEC.md` diventa più rilevante.

## 8. Correzioni suggerite a `SPEC.md`

`SPEC.md` non è stato modificato. Da valutare:

| Sezione | Oggi | Proposta |
|---|---|---|
| 4.4 | Etichette per sentiment e heat | Mnemonici candidati, dopo la verifica in `FLDS` |
| 4.1, 4.4 | Solo `END_DATE_OVERRIDE` | Provare anche `END_DT`; snapshot a fine mese |
| 4.4 | 2000-2024 | 2000 - settembre 2026 |
| 4.2 | "Bloomberg restituisce la classificazione GICS attuale" | Segnarla **[VERIFICARE]** |
| 9.1 | Filtro "interamente backtestabile e point-in-time" | Declassare a ipotesi; indicare la pubblicazione prima dell'apertura |
| 4.4, 9.1 | Parquet e LLM | Subordinati all'esito della sezione 7 |

## 9. Checklist al terminale

Da eseguire nell'ordine. **Per ogni voce annotare data, ora, comando e risultato.** I titoli di prova vengono da conoscenza generale: confermare gli eventi in `CACT` o `DES`.

### Prima di scaricare

- [ ] **Licenza.** `DAPI <GO>`, leggere "Desktop API Guidelines". Chiedere per iscritto a biblioteca LUISS e help desk (`<HELP> <HELP>`) se Parquet su altri PC, GitHub e invio a LLM sono ammessi. Se no, attivare il piano WRDS.
- [ ] **Limiti.** `WAPI <GO>` -> API General Information -> API Data Limits. Annotare regole correnti e codici (`LPHP DAPI:0:1 1489652 <GO>`). Chiedere all'help desk se una `HistoricalDataRequest` conta per coppia security/campo o per dato, e in quale categoria rientra `BDS`.
- [ ] **Ambiente.** Sul PC del terminale: Python installabile? `blpapi`/`xbbg` funzionano? Chiedere alla biblioteca quanti terminali ci sono, chi altro scarica questo mese e quando conviene iniziare.

### Composizione

- [ ] **Override.** `SPX Index`, `FLDS <GO>` su `INDX_MWEIGHT_HIST`: annotare override e definizione.
- [ ] **Test decisivo.** Per 2000-01-31, 2008-09-30 e 2026-09-30, scaricare con `END_DATE_OVERRIDE` e con `END_DT`, più `INDX_MEMBERS`. Le liste devono **differire tra le date** e coincidere con `SPX Index MEMB <GO>` alla data "As of". Numero atteso intorno a 500.
- [ ] **Ticker alternativo.** `SPX Index DES <GO>`: esiste un altro ticker per lo storico?
- [ ] **Titoli usciti.** Enron nella lista di fine ottobre 2001 e Lehman in quella di fine agosto 2008, assenti dopo l'uscita? Annotare la stringa esatta e se i pesi hanno valori sensati.

### Prezzi

- [ ] **Flag.** Su `AAPL US Equity` (split 2020), `MSFT US Equity` (dividendo straordinario 2004), `GE US Equity` (spin-off 2024): scaricare `PX_LAST` e `PX_VOLUME` con (a) nessuna opzione, (b) `adjustmentFollowDPDF=false` e tre flag `true`, (c) `false` e tre flag `false`. Confrontare con `GP <GO>` e controllare `DPDF <GO>`. La configurazione (b) deve dare lo stesso risultato cambiando `DPDF`; se si cambia l'impostazione, ripristinarla alla fine.
- [ ] **Total return.** `FLDS` su `TOT_RETURN_INDEX_GROSS_DVDS`: definizione, override, base. Controllare il rapporto con `PX_LAST` di (b) agli stacchi e la presenza di dati giornalieri effettivi, dal 2000 e su un delistato. Annotare la data di reinvestimento.

### Delistati e GICS

- [ ] **Delistati.** Con 30 uscite storiche: `BDH` su `PX_LAST` e `PX_VOLUME` dalla stringa restituita al passo precedente. Misurare quanti rispondono e confrontare l'ultima data con `CACT <GO>`.
- [ ] **Ticker riusati.** `T US Equity` prima del 2005 (vecchia AT&T o SBC?), più un cambio di nome (`META US Equity` prima del 2022). Provare `/isin/`, `/cusip/`, `/figi/`, `/bbgid/`: la storia coincide?
- [ ] **Identificatori.** In `FLDS` verificare `ID_BB_GLOBAL`, `COMPOSITE_ID_BB_GLOBAL`, `ID_BB_UNIQUE`, `ID_ISIN`, `ID_CUSIP`, `PARSEKYABLE_DES`, e valorizzarli anche su un delistato. Scegliere la chiave stabile del dataset.
- [ ] **GICS.** `FLDS` su `GICS_SECTOR_NAME` e `GICS_INDUSTRY_GROUP_NAME`. Provare `BDH` e BQL con `AS_OF_DATE` su `DIS US Equity` e `GOOGL US Equity` a cavallo di settembre 2018. Se la classificazione non cambia o è vuota, chiedere all'help desk e dichiarare il limite. Controllare che i campi siano valorizzati sui delistati.

### Sentiment e heat

- [ ] **Mnemonici.** `FLDS` con "news sentiment" e "news heat": esistono `NEWS_SENTIMENT_DAILY_AVG`, `NEWS_HEAT_PUB_DAVG`, `NEWS_HEAT_PUB_DMAX` e `NEWS_HEAT_PUB_DNUMSTORIES`? Quali corrispondono alle due etichette? Annotare definizione, scala e `TREN NSENT`.
- [ ] **Copertura.** `BDH` su 20 titoli: prima data disponibile, valori sul 2010, risposta sui delistati, mancanti o zeri nei giorni senza notizie, nessun riempimento con l'ultimo valore. Se un campo restituisce `Field Not Applicable`, chiedere se dipende dalla licenza.
- [ ] **Tempistica.** Stesso giorno di borsa, 20 titoli con notizie, leggere i valori con data T e T-1 prima e dopo le 9:20 ET, dopo le 16:00 ET e il mattino seguente. In Italia di norma 15:20 e 22:00, ma controllare il fuso. Annotare quando appare il valore T e se cambia.
- [ ] **Stessa prova per la heat.** Se il valore T cambia dopo le 9:30 ET, nel backtest usare T-1 per i segnali coinvolti.
- [ ] **Revisioni.** Chiedere per iscritto all'help desk: fuso e finestra della data, ricalcolo dello storico dopo aggiornamenti del modello, inizio reale in diretta. Salvare 5 titoli e riscaricarli a fine progetto per confrontarli. Senza conferma, dichiarare nel report che il point-in-time è un'ipotesi.

### Prova generale

- [ ] **Pilota.** 10 titoli con tutti i campi definitivi, inclusi 3 delistati. Controllare celle vuote, date, registro degli errori. Testare in codice il riconoscimento di `#N/A`, risposte parziali e `securityError`. Non superare i limiti di proposito.
- [ ] **Download a lotti.** Salvare dopo ogni lotto, registrare richieste e hit stimati e fermarsi al primo segnale di limite, senza tentativi ripetuti.

## Fonti

Le fonti non raggiungibili sono indicate esplicitamente in fondo.

1. SMU Libraries, [Members or constituents of an equity index](https://libfaq.smu.edu.sg/faq/134895)
2. M. Gilbert, [blp Quickstart](https://matthewgilbert.github.io/blp/quickstart.html)
3. MathWorks Answers, [Historical weights from Bloomberg](https://www.mathworks.com/matlabcentral/answers/102668-how-can-i-get-the-historical-weights-from-bloomberg-using-the-datafeed-toolbox)
4. Rblpapi, [issue 253](https://github.com/Rblp/Rblpapi/issues/253)
5. IESE Library, [Index members](https://libhowto.iese.edu/faq/184855)
6. PerseveraTools, [PR 15](https://github.com/Persevera-Asset-Mgmt/PerseveraTools/pull/15)
7. IESE Library, [Historical constituents lists](https://libhowto.iese.edu/faq/77765) (aggiornata il 10 ottobre 2023)
8. Bloomberg, [Session 4: News-Related Characteristics and Medium-Term Stock Returns](https://professional.content.cirrus.bloomberg.com/professional2023/?p=59324)
9. Ben-Rephael, Carlin, Da, Israelsen, [Internet Appendix to "Information Consumption and Asset Pricing"](https://academicweb.nd.edu/~zda/EIC_IA.pdf), Fig. IA.1 e IA.2
10. S. Rajhans, [bloomberg-sentiment-finbert](https://github.com/siddhant-rajhans/bloomberg-sentiment-finbert)
11. Cui, Lam, Verma, [Embedded Value in Bloomberg News & Social Sentiment Data](https://developer.twitter.com/content/dam/developer-twitter/pdfs-and-files/Bloomberg-Twitter-Data-Research-Report.pdf), Bloomberg, 2016. L'URL dà 404: letta la [copia in Internet Archive](https://web.archive.org/web/2020/https://developer.twitter.com/content/dam/developer-twitter/pdfs-and-files/Bloomberg-Twitter-Data-Research-Report.pdf)
12. [Do News and Social Media Tell the Same Story?](https://arxiv.org/pdf/2604.26811), arXiv, 2026, sezione 4
13. MathWorks, [history, Bloomberg Desktop connection](https://www.mathworks.com/help/datafeed/bloomberg.history.html)
14. J. Lin, [How to get adjusted stock prices from Bloomberg API](https://lichgo.github.io/2015/11/14/how-to-get-adjusted-stock-price-from-bloomberg-api.html), 2015
15. A. Sepp, [BloombergFetch](https://github.com/ArturSepp/BloombergFetch)
16. MathWorks Answers, [TOT_RETURN_INDEX_GROSS_DVDS](https://www.mathworks.com/matlabcentral/answers/67711-questions-about-bloomberg-history-command-with-the-field-of-tot_return_index_gross_dvds), 2013
17. Harvard Business School, [Total returns](https://www.library.hbs.edu/services/help-center/total-returns-stocks-bonds-indexes)
18. University of Zurich, [How to use the Bloomberg terminals](https://www.df.uzh.ch/dam/jcr:f081029c-6875-44a2-93a2-2d9394efe4cb/How_to_use_the_Bloomberg_terminals_20180309.pdf), 9 marzo 2018, con appendice dai testi `WAPI`
19. Boston University, [Delisted corporations](https://askalibrarian.bu.edu/businessFAQs/faq/87690)
20. Elite Trader, [S&P500 historical EOD data with delisted stocks](https://www.elitetrader.com/et/threads/s-p500-historical-eod-data-with-delisted-stocks-included.290761/), 2015
21. OMG, [FIGI-8](https://issues.omg.org/issues/FIGI-8)
22. OpenFIGI, [API documentation](https://www.openfigi.com/api/documentation)
23. [xbbg](https://github.com/alpha-xone/xbbg)
24. Bloomberg, [BQL Fundamentals Fact Sheet](https://www.wu.ac.at/fileadmin/wu/s/library/databases_info_image/Bloomberg_BQL_Fundamentals_FactSheet.pdf)
25. S&P Global, [GICS History brochure](https://www.spglobal.com/marketintelligence/en/documents/gics-history-brochure.pdf) (non letta: solo estratto di ricerca)
26. Katselas, Sidhu, Yu, [Know your industry](https://openresearch-repository.anu.edu.au/items/23749149-091e-45f8-9ee4-f3a2f8338498), *Accounting and Finance*
27. University of Manchester, [Review or Daily Capacity](https://manchester-uk.libanswers.com/teaching-and-learning/faq/258845) (aggiornata il 25 giugno 2026)
28. IESE Library, [Data Download Limits](https://libhowto.iese.edu/faq/275023)
29. HKUST Library, [Bloomberg Excel Add-in](https://libguides.hkust.edu.hk/c.php?g=208028&p=6948363)
30. NYU Libraries, [Excel API and BQL](https://guides.nyu.edu/bloombergguide/excel-api-bql)
31. Yale Library, [Bloomberg Excel Add-in](https://guides.library.yale.edu/c.php?g=296285&p=1974285)
32. NYU Libraries, [Excel API error codes](https://library.answers.nyu.edu/faq/290548) (aggiornata il 17 maggio 2023)

**Non lette (403 a un accesso automatico), e quindi non usate come prova:** la pagina Bloomberg citata in `SPEC.md` per l'inizio del sentiment nel 2010; [Finding Novel Ways to Trade on Sentiment Data](https://www.bloomberg.com/company/stories/finding-novel-ways-trade-sentiment-data/); il comunicato Bloomberg sul prodotto point-in-time; i due articoli Medium sul sentiment ([1](https://medium.com/@tzjy/alpha-research-analyzing-sentiment-data-using-bloomberg-and-python-6dc55dc1bc3c), [2](https://foreducators.medium.com/analysing-bloombergs-company-news-and-twitter-sentiment-data-fe273481a664)). Questi potrebbero contenere altri mnemonici di campo e sono da leggere da browser.
