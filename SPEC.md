# SPEC: Data Driven Model for Investment

Pair trading sull'S&P 500 con filtro agentico su news e sentiment.

Stato: bozza v0.1 del 30/10/2026, da validare nello step 2 (Wayfinder).

Legenda: **[DECISO]** scelta già fatta dal team. **[PROPOSTA]** raccomandazione da confermare nello step 2. **[VERIFICARE]** dato da controllare sul terminale o presso la fonte.

---

## 1. Obiettivo e domanda di ricerca

Il progetto costruisce una strategia di pair trading statistico sulle azioni dell'S&P 500 e misura se un livello di agenti, che filtra i segnali con news e sentiment, migliora i risultati rispetto alla strategia base.

**Domanda di ricerca:** a parità di segnali, scartare le divergenze "giustificate" da news migliora rendimento corretto per il rischio, drawdown e hit rate?

**Logica economica:** due aziende simili tendono a muoversi insieme. Se lo spread si allarga senza una ragione fondamentale, è probabile che si richiuda. Se si allarga per una ragione vera (acquisizione, earnings surprise, taglio della guidance, causa legale), è probabile che non si richiuda. Queste sono le perdite tipiche del pair trading, e il filtro agentico serve a evitarle.

**Correzione rispetto all'idea iniziale:** la stabilità dello spread tra due aziende dello stesso settore non va data per scontata, va testata. Molte coppie dello stesso settore non sono cointegrate. Il settore serve a restringere i candidati, mentre la stabilità la stabilisce un test statistico.

**Aspettativa realistica:** la letteratura documenta un calo della profittabilità del pair trading semplice dopo i primi anni 2000 (Do e Faff 2010). Il successo del progetto è un'analisi valida, non una strategia per forza profittevole: un risultato negativo misurato bene vale quanto uno positivo.

## 2. Vincoli

- **[DECISO]** Tempo disponibile: circa 2 settimane e mezzo.
- **[DECISO]** Mercato USA, universo S&P 500, periodo 2000-2024.
- **[DECISO]** Accesso al terminale Bloomberg dell'università.
- Bloomberg conserva solo circa 140 giorni di storico intraday (barre e tick). Per il 2000-2024 dal terminale si ottengono quindi solo dati giornalieri.
- Il sentiment news di Bloomberg parte dal 2010. L'API desktop espone campi numerici di sentiment, ma non il testo delle news.
- L'API desktop Bloomberg ha limiti di volume di download che dipendono dall'abbonamento. Il download va pianificato e fatto una volta sola. **[VERIFICARE]** i limiti del terminale LUISS.

## 3. Architettura in due fasi

**Fase 1, strategia base.** Universo point-in-time, selezione delle coppie, spread, segnale z-score, backtest walk-forward con costi. Periodo: 2000-2024.

**Fase 2, strategia agentica.** Stessi segnali della fase 1, filtrati da un agente news/sentiment prima dell'esecuzione. Periodo: 2010-2024, limitato dalla copertura del sentiment Bloomberg.

Il confronto tra fase 1 e fase 2 sullo stesso periodo 2010-2024 è il risultato principale del progetto.

```
dati -> universo -> coppie -> spread e z-score -> segnale -> [filtro agente] -> esecuzione simulata -> metriche -> report
                                                                   ^
                                                              auditor su ogni passaggio
```

## 4. Dati

### 4.1 Universo

- **[DECISO]** S&P 500.
- **[PROPOSTA]** Composizione point-in-time: a ogni data di formazione si usano solo le aziende presenti nell'indice in quella data, comprese quelle uscite o fallite in seguito. Usare la composizione attuale per il 2000-2024 introduce survivorship bias e gonfia i risultati. Su Bloomberg: campo `INDX_MWEIGHT_HIST` su `SPX Index` con override `END_DATE_OVERRIDE`, una chiamata per data di formazione. **[VERIFICARE]**
- I titoli unici passati per l'indice nel periodo sono molti più di 500 (un fornitore ne conta 895 solo dal 2004). La mappatura dei ticker delistati su Bloomberg richiede tempo e va messa in conto nel giorno 1-3.

### 4.2 Categorie

- **[DECISO]** Coppie formate solo all'interno della stessa categoria.
- **[PROPOSTA]** GICS Industry Group (25 gruppi) invece del GICS Sector (11 settori). Gli esempi del team (automotive, food & beverage, banche) corrispondono agli industry group, che producono coppie più omogenee e meno numerose. Campo `GICS_INDUSTRY_GROUP_NAME`. **[VERIFICARE]**
- Limite noto: Bloomberg restituisce la classificazione GICS attuale. La riclassificazione del 2018 (nascita di Communication Services) ha spostato alcune aziende. Va dichiarato come limite nel report.

### 4.3 Frequenza

**[PROPOSTA] Dati giornalieri per l'intero progetto.** I motivi:

1. Bloomberg non ha intraday oltre circa 140 giorni: l'intraday 2000-2024 andrebbe comprato da un altro fornitore.
2. Il giornaliero è lo standard della letteratura sul pair trading. Gatev, Goetzmann e Rouwenhorst (2006) lavorano su dati giornalieri. Venticinque anni danno circa 6.300 osservazioni per titolo, più che sufficienti.
3. Il sentiment Bloomberg è giornaliero: un segnale intraday filtrato con un sentiment giornaliero non guadagna precisione.
4. Il carico dell'intraday sull'intero universo non è gestibile in 2 settimane e mezzo (sezione 8).

**Estensione opzionale [PROPOSTA]:** barre orarie o a 5 minuti solo per le 20 coppie migliori e solo sul 2020-2024, per testare se l'esecuzione intraday migliora i risultati. Fonte a pagamento: FirstRate Data vende barre a 1 minuto dal 2000, incluse le aziende delistate. **[VERIFICARE]** prezzo e licenza. Decisione entro il giorno 3: senza budget o senza tempo, l'estensione salta.

Dati tick: fuori scope.

### 4.4 Download Bloomberg (sessione unica)

Tutti i nomi di campo e ticker sono **[VERIFICARE]** con `FLDS <GO>` prima della sessione.

| Dato | Campo o ticker | Periodo |
|---|---|---|
| Composizione storica | `SPX Index`, `INDX_MWEIGHT_HIST` + `END_DATE_OVERRIDE` | 2000-2024 |
| Classificazione | `GICS_SECTOR_NAME`, `GICS_INDUSTRY_GROUP_NAME` | statico |
| Prezzi aggiustati | `PX_LAST` aggiustato per split e dividendi, `PX_VOLUME` | 2000-2024 |
| Total return titoli | `TOT_RETURN_INDEX_GROSS_DVDS` | 2000-2024 |
| Sentiment | campi Daily News Sentiment Score e Daily News Publication Heat | 2010-2024 |
| Benchmark | `SPXT Index` (S&P 500 total return) | 2000-2024 |
| Risk-free | `USGG3M Index` (T-bill 3 mesi) | 2000-2024 |

Salvataggio in Parquet in `data/raw/`, un file per tipo di dato. I file grezzi non si modificano e non si riscaricano.

**Fonte di backup:** CRSP via WRDS, se LUISS ha l'accesso (da chiedere alla biblioteca). È la fonte accademica standard per prezzi point-in-time con delisting. yfinance è escluso: non contiene le aziende delistate e reintroduce il survivorship bias.

## 5. Selezione delle coppie e segnale

### 5.1 Chiarimento sulle opzioni

Media, deviazione standard, z-score e differenza semplice non sono alternative tra loro: lo z-score usa media e deviazione standard dello spread. La scelta reale avviene su due livelli: come si costruisce lo spread, e quale regola trasforma lo spread in segnale.

La differenza semplice tra prezzi va scartata. Con titoli a prezzi diversi (200 $ contro 20 $), lo spread riflette la scala dei prezzi e non la relazione tra le due aziende.

### 5.2 Spread [PROPOSTA]

Spread sui log-prezzi con hedge ratio stimato in OLS sulla finestra di formazione (metodo Engle-Granger):

```
s_t = ln(P_A,t) - beta * ln(P_B,t) - alpha
```

`alpha` e `beta` si stimano solo sui dati di formazione e restano fissi per tutta la finestra di trading.

Baseline aggiuntiva a costo quasi nullo: il metodo della distanza di Gatev et al. (prezzi normalizzati, coppie con la minima somma degli scarti quadratici). Serve come secondo riferimento.

Estensione solo se avanza tempo: hedge ratio dinamico con filtro di Kalman.

### 5.3 Selezione delle coppie per finestra [PROPOSTA]

1. Tutte le coppie all'interno dello stesso industry group, tra i titoli presenti nell'indice alla data di formazione.
2. Prefiltro: correlazione dei rendimenti giornalieri superiore a 0,7 sulla formazione. Riduce il calcolo.
3. Test di cointegrazione Engle-Granger con p-value inferiore a 0,01.
4. Half-life dello spread (modello Ornstein-Uhlenbeck) tra 2 e 30 giorni di borsa.
5. Si tengono le K = 20 coppie migliori per half-life.

**Rischio di multiple testing:** con 5.000 coppie testate al 5%, ci si aspettano circa 250 falsi positivi anche se nessuna coppia fosse davvero cointegrata. La soglia più severa, il filtro sull'half-life e la verifica out-of-sample nella finestra di trading servono a contenerli.

### 5.4 Regola di segnale [PROPOSTA]

```
z_t = (s_t - mu) / sigma     con mu e sigma stimati sulla finestra di formazione
```

- **Apertura:** |z| > 2. Long sul titolo che ha sottoperformato, short su quello che ha sovraperformato, posizione dollar-neutral.
- **Chiusura:** z torna a 0.
- **Stop-loss:** |z| > 3,5.
- **Time stop:** chiusura dopo 3 volte l'half-life o a fine finestra di trading.

Le soglie si testano in sensitivity (1,5 / 2 / 2,5), senza ottimizzarle sull'intero campione.

## 6. Backtest [PROPOSTA]

- **Walk-forward:** formazione di 12 mesi, trading di 6 mesi, avanzamento di 6 mesi. Sul 2000-2024 si ottengono circa 48 finestre di trading (2001-2024).
- **Nessun look-ahead:** segnale calcolato sulla chiusura del giorno t, esecuzione alla chiusura del giorno t+1.
- **Costi:** 5 bps per lato per gamba nello scenario base, sensitivity a 0, 10 e 20 bps. Costo di prestito sullo short: 50 bps annui, assunzione ragionevole per large cap.
- **Delisting o uscita dall'indice durante il trading:** posizione chiusa all'ultimo prezzo disponibile.
- **Allocazione:** capitale uguale per coppia, rendimento calcolato sul capitale impegnato, come in Gatev et al.
- **Implementazione:** vettoriale in pandas e numpy. I framework event-driven sono lenti e non servono a frequenza giornaliera.
- **Metriche:** rendimento annuo, volatilità, Sharpe sul T-bill, Sortino, max drawdown, Calmar, hit rate, holding medio, numero di trade, turnover, beta e alpha rispetto all'S&P 500.
- **Sotto-periodi:** 2000-2002, 2008-2009, 2020, 2022, oltre al periodo intero.

## 7. Benchmark [PROPOSTA]

L'S&P 500 da solo è il benchmark sbagliato per questa strategia. Il pair trading è dollar-neutral e ha un beta vicino a zero: confrontarlo con un indice long-only misura soprattutto l'andamento del mercato.

Proposta a tre livelli:

1. **Benchmark principale:** la strategia base senza agenti, sullo stesso periodo. È il confronto che risponde alla domanda di ricerca.
2. **Risk-free (T-bill 3 mesi):** riferimento per lo Sharpe e per l'excess return.
3. **S&P 500 total return:** contesto, più beta e alpha della strategia tramite regressione CAPM. L'S&P resta utile come misura dell'esposizione al mercato, non come asticella da battere.

Opzionale: un indice hedge fund equity market neutral (ad esempio HFRX Equity Market Neutral). **[VERIFICARE]** disponibilità su Bloomberg.

## 8. Carico computazionale

**Con dati giornalieri:**

- Prezzi: circa 1.000 titoli per 6.300 giorni, quindi circa 6 milioni di righe. Trascurabile.
- Test di cointegrazione: alcune migliaia di coppie per 48 finestre, quindi qualche centinaio di migliaia di test. Richiedono minuti su un laptop con parallelizzazione (joblib), e il prefiltro sulla correlazione li riduce ancora.
- Chiamate all'agente: solo sui segnali di apertura, non su ogni giorno. Con 20 coppie per finestra sul 2010-2024 si arriva a circa 1.000-2.000 eventi. Il costo API resta contenuto con un modello piccolo.

**Con barre a 1 minuto sull'intero universo, per confronto:**

- 390 barre al giorno per 252 giorni per 25 anni: circa 2,5 milioni di barre per titolo, oltre 1 miliardo di righe per 500 titoli.
- Lo z-score su 13.000 coppie (livello settore) richiede circa 30 miliardi di valori per ogni configurazione di parametri.

**Conclusione:** l'intraday completo non entra in 2 settimane e mezzo. Si usa il giornaliero su tutto il periodo e l'intraday solo come estensione mirata.

## 9. Agenti

### 9.1 Agente news/sentiment (nucleo della fase 2)

- **Trigger:** solo quando la fase 1 genera un segnale di apertura.
- **Input:** coppia, data, z-score, sentiment giornaliero e news heat Bloomberg di entrambe le aziende nei giorni precedenti al segnale.
- **Output JSON:** `{"giustificato": bool, "confidenza": 0-1, "motivo": str}`.
- **Azione:** se la divergenza è giustificata, il trade viene scartato (variante da testare: size ridotta). Altrimenti passa all'esecuzione.

**[PROPOSTA] Due livelli:**

1. **Filtro sistematico** su tutti i segnali 2010-2024, basato sui dati Bloomberg. La divergenza è giustificata se c'è una news heat anomala o un differenziale di sentiment forte tra le due aziende. Il filtro è interamente backtestabile e point-in-time, perché Bloomberg calcola il sentiment al momento della pubblicazione di ogni notizia.
2. **Agente LLM su un campione** di circa 100 eventi. Le headline si raccolgono dal terminale, i nomi delle aziende e le date si anonimizzano, l'LLM classifica la divergenza come giustificata o no e motiva la scelta. Il risultato si confronta con il filtro sistematico e con l'esito reale del trade.

**Rischio critico: look-ahead bias degli LLM.** Un LLM moderno è addestrato su testi che coprono anche il 2000-2024 e può sapere come è andata a finire una notizia. Mitigazione: anonimizzare nomi e date (Glasserman e Lin 2023) e dichiarare il limite nel report. Per questo il risultato principale si basa sul filtro sistematico, mentre l'LLM resta un esperimento sul campione.

### 9.2 Auditor [PROPOSTA]

L'auditor è un modulo di controlli deterministici in codice, non un LLM: i controlli in codice sono affidabili, testabili e gratuiti. Controlli previsti:

- nessun dato con timestamp successivo al momento della decisione;
- universo point-in-time rispettato a ogni finestra;
- costi applicati a ogni trade;
- esposizione dollar-neutral entro una tolleranza;
- assenza di prezzi mancanti, split anomali e spread non finiti.

Ogni controllo è un test automatico, coerente con il TDD previsto nello step 5. Un LLM critico che rivede un campione delle decisioni dell'agente news resta un'estensione opzionale.

### 9.3 Agente report [PROPOSTA: sì, nell'ultimo blocco]

Genera il report finale a partire da un file di metriche e dai grafici. Regola fissa: i numeri arrivano solo dal file di metriche, l'LLM scrive il commento. Rischio basso, impatto alto sulla consegna.

### 9.4 Implementazione degli agenti

**[PROPOSTA]** Python puro con chiamate all'API di un LLM e output JSON strutturato. Nessun framework multi-agente (LangGraph, CrewAI): in 2 settimane e mezzo aggiungono complessità senza valore, salvo richiesta esplicita del corso. Per la classificazione basta un modello piccolo, che contiene i costi.

## 10. Stack e struttura del repo [PROPOSTA]

Python 3.11+, pandas, numpy, statsmodels, pyarrow (Parquet), xbbg o blpapi per Bloomberg, matplotlib, joblib, pytest, SDK del provider LLM scelto.

```
ddinvestment/
  SPEC.md
  data/
    raw/            # Parquet scaricati da Bloomberg, mai modificati
    processed/
  src/
    data/           # download, pulizia, universo point-in-time
    pairs/          # selezione, cointegrazione, half-life
    signals/        # spread, z-score, regole di apertura e chiusura
    backtest/       # engine vettoriale, costi, metriche
    agents/         # news/sentiment, auditor, report
  tests/
  reports/
```

## 11. Piano di massima (circa 17 giorni)

| Giorni | Blocco | Milestone |
|---|---|---|
| 1-3 | Sessione Bloomberg, pulizia, mappatura delisting, universo point-in-time | Dataset congelato. Decisione sull'intraday |
| 4-7 | Selezione coppie, spread, segnali, backtest con costi | M1: backtest base 2000-2024 |
| 8-11 | Filtro sentiment, agente LLM sul campione, auditor | M2: confronto base contro agentico 2010-2024 |
| 12-14 | Sensitivity su soglie, costi e sotto-periodi. Agente report | Report generato |
| 15-17 | Buffer e presentazione | Consegna |

Lo step 4 trasforma questo piano in build phases.

## 12. Criteri di successo

- Backtest base 2000-2024 point-in-time, walk-forward, con costi, riproducibile con un solo comando.
- Variante agentica valutata sugli stessi segnali del 2010-2024, con tabella di confronto tra base e agentico.
- Tutti i controlli dell'auditor passano.
- Report generato in automatico dal file di metriche.

## 13. Fuori scope

Trading live, dati tick, intraday sull'intero universo, filtro di Kalman (salvo tempo avanzato), modelli di machine learning per il segnale, ottimizzazione di portafoglio, modelli di costo non lineari.

## 14. Decisioni da confermare nello step 2

| # | Tema | Proposta |
|---|---|---|
| 1 | Benchmark | Strategia base senza agenti, più T-bill e S&P 500 TR per beta e alpha |
| 2 | Frequenza | Giornaliera. Intraday solo come estensione mirata, decisione entro il giorno 3 |
| 3 | Categorie | GICS Industry Group |
| 4 | Spread | Log-prezzi con hedge ratio OLS (Engle-Granger) |
| 5 | Segnale | Z-score: apertura a 2, chiusura a 0, stop a 3,5 |
| 6 | Backtest | Walk-forward 12 mesi + 6 mesi, esecuzione a t+1, costi 5 bps |
| 7 | Agente news | Filtro sistematico Bloomberg più LLM su campione anonimizzato |
| 8 | Auditor | Controlli deterministici, LLM opzionale |
| 9 | Report | Sì, nell'ultimo blocco, numeri solo dal file di metriche |
| 10 | Fonte dati | Bloomberg giornaliero, WRDS/CRSP come backup, FirstRate solo per l'intraday |
| 11 | Provider LLM | Da decidere |

**Domande aperte per il team:**

- Il corso impone un framework, un linguaggio o un formato di consegna?
- C'è budget per dati a pagamento?
- LUISS ha accesso a WRDS?
- Quante persone lavorano al progetto, e chi ha accesso al terminale e in quali orari?

## Fonti

- Limite di circa 140 giorni sull'intraday Bloomberg: [MathWorks Answers](https://www.mathworks.com/matlabcentral/answers/101509-is-it-possible-to-download-intraday-tick-data-from-bloomberg-using-datafeed-toolbox-3-5-r2010a), [r-sig-finance](https://r-mailing-lists.thecoatlessprofessor.com/lists/r-sig-finance/threads/thread-af8d32f8272e)
- Sentiment Bloomberg dal 2010: [Bloomberg Professional](https://www.bloomberg.com/company/wp-json/wp/v2/posts/20717)
- Assenza del testo delle news nell'API: [MathWorks Answers](https://www.mathworks.com/matlabcentral/answers/498783-how-to-read-import-the-news-feed-data-from-bloomberg-with-datafeed-toolbox-in-r2019b)
- Dati intraday storici con delisting: [FirstRate Data](https://firstratedata.com/), [Datarade, S&P 500 Components](https://datarade.ai/data-products/s-p-500-components-historical-intraday-dataset-firstrate-data)
- Look-ahead bias negli LLM: Glasserman e Lin (2023), [arXiv:2309.17322](https://arxiv.org/abs/2309.17322)
- Gatev, Goetzmann e Rouwenhorst (2006), "Pairs Trading: Performance of a Relative-Value Arbitrage Rule", Review of Financial Studies
- Do e Faff (2010), "Does Simple Pairs Trading Still Work?", Financial Analysts Journal
