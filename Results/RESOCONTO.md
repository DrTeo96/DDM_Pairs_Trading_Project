# Resoconto: la strategia e l'agente di notizie alla prova del backtest

Questo resoconto spiega che cosa abbiamo provato e che cosa è uscito, senza dare per scontata nessuna conoscenza di finanza. I numeri vengono da [src/06_backtest.ipynb](../src/06_backtest.ipynb) e sono salvati nelle tabelle di questa cartella. Riguardano solo il **periodo di addestramento** (train, dal 16 giugno al 16 settembre 2026, 64 giorni di borsa).

## In breve

- La strategia di base (versione A) fa 973 operazioni e guadagna in media 7,4 punti base per operazione, cioè lo 0,074%. Su un capitale di 300.000 dollari sono 7.239 dollari in tre mesi (+2,4%).
- Il guadagno è così piccolo che i costi di compravendita lo cancellano: basta un costo di 1,9 punti base per operazione per azzerarlo. Con un costo realistico di 5 punti base la strategia perde 12.221 dollari (-4,1%).
- L'agente di notizie doveva evitare le operazioni sbagliate. Invece blocca operazioni che in media guadagnavano **più** delle altre: 27,8 punti base contro 7,4. Ha fatto peggio di un blocco a caso.
- Seguire la notizia (versione C) peggiora ancora: le 13 operazioni in cui l'agente segue la notizia perdono in media 155 punti base.
- Una versione più semplice senza intelligenza artificiale, che conta le parole positive e negative delle notizie, blocca in modo indistinguibile dal caso.
- Questi risultati dipendono da pochissime operazioni, soprattutto da un giorno (13 agosto). Sono un'indicazione, non una prova.

## 1. L'idea, in parole semplici

Due aziende che fanno lo stesso mestiere, per esempio Coca-Cola e Pepsi, hanno prezzi di borsa che si muovono insieme: se il mercato delle bibite va bene, salgono entrambe. Ogni tanto, durante la giornata, una delle due si muove più dell'altra senza un motivo vero, magari solo perché qualcuno ha comprato o venduto molto in quel momento. Di solito la distanza rientra dopo poco.

La strategia scommette proprio su questo rientro. Quando la distanza tra le due è insolitamente grande:

- **compra** l'azione rimasta indietro (guadagna se sale);
- **vende allo scoperto** l'azione andata avanti (guadagna se scende). Vendere allo scoperto vuol dire prendere in prestito un'azione, venderla subito e ricomprarla dopo: se nel frattempo il prezzo è sceso, si guadagna la differenza.

Le due operazioni hanno lo stesso importo, 10.000 dollari ciascuna. Se tutto il mercato sale o scende, quello che si guadagna da una parte si perde dall'altra: conta solo come si muovono le due azioni **una rispetto all'altra**. Si guadagna se la distanza rientra, si perde se si allarga ancora. Tutto si chiude entro la fine della giornata.

**Il problema.** A volte la distanza si allarga per un motivo vero: una delle due aziende viene comprata da un'altra, riceve un'indagine, cambia l'amministratore delegato. In quel caso la distanza può non rientrare mai, e la scommessa perde. L'**agente di notizie** è un programma con un modello di intelligenza artificiale che legge le notizie uscite nelle ore prima di ogni segnale e, se trova un fatto del genere su una sola delle due aziende, dice di non entrare.

## 2. Le parole da sapere

| Parola | Cosa vuol dire |
|---|---|
| Coppia | Due aziende dello stesso settore, per esempio Visa e Mastercard. Ne usiamo 15. |
| Spread | La distanza tra i prezzi delle due azioni (precisamente: la differenza dei loro logaritmi). È quello su cui si scommette. |
| z-score | Quanto è insolito lo spread in questo momento, misurato in "deviazioni standard" rispetto alla sua media recente. Si entra quando supera 2 (molto insolito), si esce quando torna a 0 (normale). |
| Segnale | Il momento in cui lo z-score supera la soglia: la strategia vorrebbe entrare. Nel train ce ne sono 973. |
| Trade | Un'operazione completa: apertura delle due posizioni e loro chiusura. |
| Punto base (bps) | Un centesimo di punto percentuale: 1 bps = 0,01%. Su 10.000 dollari, 1 bps = 1 dollaro. |
| Lordo e netto | Lordo: guadagno prima dei costi. Netto: dopo i costi. |
| Costo per operazione | Quanto costa comprare o vendere (commissioni e differenza tra prezzo di acquisto e di vendita). Un trade ha 4 operazioni: aprire e chiudere due azioni. Con 5 bps per operazione il trade costa 20 bps. |
| Costo di pareggio | Il costo per operazione a cui il guadagno medio diventa zero. |
| Uscita | Come finisce un trade: **rientro** (lo spread è tornato normale: di solito si guadagna), **stop** (lo spread si è allargato troppo: si chiude in perdita), **tempo** (dopo 90 minuti si chiude comunque), **fine giornata**. |
| Win rate | La quota di trade chiusi in guadagno. |
| Profit factor | Quanto si è guadagnato nei trade vincenti diviso quanto si è perso in quelli perdenti. Sopra 1: si guadagna in totale. |
| Errore standard | Quanto è incerta una media. Se la media è 7,4 e l'errore standard 2,0, la media vera sta grosso modo tra 3,4 e 11,4. |
| Sharpe ratio | Guadagno diviso per quanto oscillano i guadagni giorno per giorno, riportato a un anno. Più è alto, più il guadagno è regolare. Su 64 giorni e con guadagni giornalieri minuscoli viene gonfiato: un valore come 8 non va confrontato con quello di un fondo. |
| Drawdown | La perdita massima dal punto più alto raggiunto. |
| Train e test | Il periodo di borsa è diviso in due. Sul train (fino al 16 settembre) si costruisce e si prova la strategia; il test (dal 17 settembre) si usa una volta sola alla fine, con le regole bloccate, per vedere se funziona su dati mai visti. **Il test non è ancora stato letto.** |
| p-value | Qui: la probabilità che un blocco fatto a caso dia un risultato altrettanto buono o migliore di quello dell'agente. Piccolo (sotto 0,05) = l'agente sceglie meglio del caso. Vicino a 1 = l'agente sceglie peggio del caso. |

## 3. Come abbiamo messo alla prova la strategia

Un **backtest** rifà sul passato, minuto per minuto, quello che la strategia avrebbe fatto, con le regole decise prima di guardare i risultati:

- 10.000 dollari su ciascuna delle due azioni, senza prestiti per aumentare l'importo;
- capitale totale di 300.000 dollari (20.000 per ognuna delle 15 coppie): ogni coppia ha al massimo un trade aperto alla volta;
- tutto chiuso entro la fine della giornata;
- costi: scenario principale **0** (indicazione del docente per queste 15 coppie), poi 2, 5 e 10 bps per operazione per vedere quanto pesano. 5 è lo scenario realistico.

## 4. Le tre versioni e i cinque set di decisioni

Le **versioni** sono tre modi di usare le notizie:

| Versione | Cosa fa |
|---|---|
| **A**, senza agente | Entra a ogni segnale. È il termine di confronto. |
| **B**, l'agente blocca | Se l'agente trova un fatto vero su una sola azienda, non entra. Altrimenti entra come la A. |
| **C**, l'agente decide | Come la B, ma in alcuni casi, invece di stare fermo, scommette nella direzione della notizia: se la notizia è buona per l'azienda che è salita, scommette che continui a salire rispetto all'altra. È la scommessa opposta a quella della A. Esce quando lo spread rientra (la notizia aveva torto), dopo 90 minuti o a fine giornata. |

I **set di decisioni** sono chi decide, segnale per segnale, se bloccare o seguire:

| Set | Chi decide | Segnali | Blocchi (B) | Segui (C) |
|---|---|---|---|---|
| `spark_24h` (principale) | L'agente con il modello Spark X2.6 4B, che legge le notizie delle 24 ore prima | 973 | 48 | 13 |
| `spark_6h` | Lo stesso agente, con le notizie delle 6 ore prima | 973 | 25 | 9 |
| `lessico` | Nessun modello: conta le parole positive e negative delle notizie con un dizionario della finanza (Loughran-McDonald) | 973 | 166 | 61 |
| `spark_24h_ragiona` | L'agente con il modello che "ragiona" prima di rispondere (molto più lento) | 40 | 5 | 2 |
| `mano` | Il gruppo, che ha classificato a mano le notizie, con la stessa regola dell'agente | 40 | 5 | 1 |

Gli ultimi due esistono solo per un campione di 40 segnali, perché classificare a mano e far ragionare il modello costa molto tempo.

## 5. Risultati della versione A

| Costo per operazione | Trade | Guadagno medio per trade | Trade in guadagno | Guadagno totale | Sul capitale |
|---|---|---|---|---|---|
| 0 bps | 973 | +7,4 bps | 60% | +7.239 $ | +2,4% |
| 2 bps | 973 | -0,6 bps | 53% | -545 $ | -0,2% |
| 5 bps | 973 | -12,6 bps | 39% | -12.221 $ | -4,1% |
| 10 bps | 973 | -32,6 bps | 20% | -31.681 $ | -10,6% |

Come leggerla:

- **Il guadagno c'è ma è piccolo**: 7,4 bps per trade, con un'incertezza di ±2 bps. Su 10.000 dollari sono 7,4 dollari a trade.
- **I costi lo mangiano tutto.** Il costo di pareggio è 1,86 bps per operazione: un trade costa 4 operazioni, quindi 7,4 bps, esattamente quanto guadagna in media. Un costo realistico è più alto.
- **Si guadagna solo quando lo spread rientra.** I 464 trade usciti per rientro guadagnano in media 38,8 bps; i 422 usciti per tempo perdono 23,2 bps e i 31 usciti per stop perdono 32,1 bps.
- **Il guadagno si concentra all'apertura.** I segnali tra il 15° e il 30° minuto di borsa (457) guadagnano 11,4 bps: è il rientro dei movimenti accumulati durante la notte. Quelli successivi (516) solo 3,9 bps.

## 6. Risultati della versione B: l'agente blocca i trade sbagliati?

Il confronto con la A, a costo 0:

| Set | Trade | Guadagno medio per trade | Guadagno totale | Differenza dalla A |
|---|---|---|---|---|
| A, senza agente | 973 | +7,44 bps | +7.239 $ | |
| B, `spark_24h` | 925 | +6,38 bps | +5.905 $ | -1.334 $ |
| B, `spark_6h` | 948 | +6,14 bps | +5.819 $ | -1.420 $ |
| B, `lessico` | 807 | +7,08 bps | +5.712 $ | -1.527 $ |

**Tutti i set guadagnano meno della A.** Per capire perché, si guarda quanto avrebbero guadagnato i trade bloccati e lo si confronta con un blocco fatto a caso dello stesso numero di trade (5.000 estrazioni):

| Set | Trade bloccati | Guadagno medio dei bloccati | Blocchi a caso, in media | p-value |
|---|---|---|---|---|
| `spark_24h` | 48 | +27,8 bps | +7,3 bps | 0,97 |
| `spark_6h` | 25 | +56,8 bps | +7,1 bps | 1,00 |
| `lessico` | 166 | +9,2 bps | +7,5 bps | 0,67 |

L'agente principale ha tolto proprio trade migliori della media: quasi quattro volte la media. Il 97% dei blocchi a caso avrebbe fatto meglio. Il lessico non fa né meglio né peggio del caso.

**Perché succede.** Una notizia vera su una sola azienda produce gli allargamenti più grandi dello spread, e in questi tre mesi molti di quegli allargamenti sono rientrati lo stesso nella giornata: 23 dei 48 trade bloccati sarebbero usciti per rientro, con +29,5 bps medi. Gli esempi più grandi sono acquisizioni vere: Silver Lake in trattativa per comprare Workday (13 agosto, il trade bloccato avrebbe guadagnato 985 bps) e una proposta di acquisto su PayPal (15 luglio, 564 bps).

**Attenzione però.** Il risultato dipende da pochissimi casi. La mediana dei trade bloccati (il valore centrale) è 7,6 bps, praticamente come la media generale. Togliendo i 3 trade più grandi, il guadagno medio dei bloccati diventa -6,6 bps, cioè l'agente avrebbe fatto bene. Quindi la conclusione onesta è: **non c'è prova che bloccare sulle notizie aiuti**, e c'è un'indicazione, fragile, che tolga alcuni dei trade migliori.

**Il caso del lessico con i costi.** Con un costo di 5 bps la B del lessico perde 10.428 dollari invece di 12.221, quindi sembra migliore della A. Non perché scelga bene: a quel costo ogni trade perde in media, e chi fa meno trade paga meno costi. Bloccare 166 trade a caso darebbe lo stesso effetto.

## 7. Risultati della versione C: seguire la notizia

| Set | Trade che seguono la notizia | Loro guadagno medio | La A sugli stessi segnali | Differenza dalla A, costo 0 |
|---|---|---|---|---|
| `spark_24h` | 13 | -154,9 bps | +125,7 bps | -3.348 $ |
| `spark_6h` | 9 | -224,9 bps | +182,6 bps | -3.444 $ |
| `lessico` | 61 | -16,0 bps | +16,0 bps | -2.502 $ |

Seguire la notizia vuol dire fare la scommessa opposta alla A. Quando la A guadagnava (lo spread rientrava), la C perde la stessa cifra; quando la A perdeva, la C guadagna. Le due differiscono solo se la A esce per stop, perché la C non ha stop. Su questi segnali la A guadagnava, quindi la C perde. Pesano soprattutto tre segnali di Salesforce-Workday del 13 agosto (-985 e -615 bps i due peggiori).

Con 9-13 trade (61 per il lessico) sono casi da leggere uno per uno, non una statistica.

## 8. Il campione dei 40 segnali

Su 40 segnali il gruppo ha classificato a mano le notizie. Risultato:

- agente e gruppo prendono la **stessa decisione su 38 segnali su 40 (95%)**;
- con il ragionamento acceso le decisioni dell'agente non cambiano;
- i due disaccordi: sul segnale 489 (Home Depot-Lowe's) il gruppo blocca e l'agente no, sul 901 (PayPal-Block) il contrario. In entrambi i casi la A guadagnava (64 e 82 bps).

Quindi l'agente classifica le notizie più o meno come farebbe una persona: il problema non è che l'agente sbagli a leggere, ma che la regola "fatto vero su un'azienda, quindi non entrare" in questo periodo non ha funzionato.

## 9. Le curve di capitale

![Curve di capitale delle versioni](curve_capitale.png)

Ogni linea mostra come cresce (o cala) il capitale giorno dopo giorno. A sinistra senza costi: la A (nera) sta sempre sopra le altre. Il salto verso il basso della C (blu tratteggiata) a metà agosto è il 13 agosto di Salesforce-Workday. A destra, con 5 bps di costo, tutte le linee scendono.

## 10. Cosa possiamo concludere, e cosa no

Possiamo dire:

- la strategia di base ha un piccolo guadagno lordo, che non sopravvive a costi realistici;
- sul train, nessun modo di usare le notizie che abbiamo provato migliora la strategia;
- l'agente legge le notizie in modo simile al gruppo (95% di accordo).

Non possiamo dire:

- che l'agente sia dannoso in generale: la differenza dipende da 2-3 operazioni e da un giorno;
- che la strategia funzioni o non funzioni nel futuro: il test non è stato ancora usato;
- che una variante sia migliore delle altre: sceglierla adesso guardando questi numeri vorrebbe dire adattarsi ai dati del train.

## 11. Limiti

- **Solo train.** Il segnale e le regole dell'agente sono stati costruiti su questi stessi dati, quindi i risultati sono ottimistici.
- **Pochi casi.** 25-166 blocchi e 9-61 trade che seguono la notizia: ogni conclusione è fragile.
- **La regola della C è nostra**: niente stop, uscita a 90 minuti. In 2 casi un trade che segue la notizia è ancora aperto quando arriva il segnale successivo della stessa coppia, e così usa due volte il capitale di quella coppia.
- **Il lessico** è un file già pronto: il codice che lo produce non è in questo repository.
- **Costi stimati**, non misurati; nessun costo per prendere in prestito le azioni vendute allo scoperto; una parte dei trade usa un prezzo di un minuto senza scambi (prezzo vecchio).
- **Il modello può "sapere" il futuro.** Se è stato addestrato su testi successivi a giugno 2026 può riconoscere gli eventi. Per ridurre il rischio i nomi delle aziende sono sostituiti con "Company A" e "Company B", ma non basta a escluderlo.

## 12. Cosa resta da fare

1. Decidere, prima di aprire il test, quale versione e quali regole portarci, e scriverlo.
2. Eseguire il test una volta sola, con tutto bloccato.
3. Aggiungere i controlli previsti dal programma: intervallo di confidenza con il bootstrap sulla differenza tra le versioni, beta e alpha rispetto all'S&P 500.

## Dove sono i file

| File | Contenuto |
|---|---|
| [confronto_versioni.csv](confronto_versioni.csv) | Tutte le metriche per set, versione e costo |
| [differenza_dalla_A.csv](differenza_dalla_A.csv) | Differenza di ogni versione dalla A |
| [bloccati_contro_caso.csv](bloccati_contro_caso.csv) | Trade bloccati contro blocco a caso |
| [confronto_campione_40.csv](confronto_campione_40.csv) | I 40 segnali del campione |
| [A_per_costo.csv](A_per_costo.csv), [A_per_coppia.csv](A_per_coppia.csv) | La versione A per costo e per coppia |
| [trades_A.csv](trades_A.csv), `<set>/trades_B.csv`, `<set>/trades_C.csv` | Ogni trade di ogni versione |
| [agent_decisions_15pairs_v2_train.csv](agent_decisions_15pairs_v2_train.csv) | Le decisioni dell'agente principale, segnale per segnale |

Per rifare tutto: [src/README.md](../src/README.md), passo 6.
