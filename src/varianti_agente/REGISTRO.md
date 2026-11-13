# Registro delle varianti dell'agente (solo train, test mai letto)

Registro tenuto da Beatrice durante le prove (13 novembre 2026), copiato qui com'era; cambiano solo i percorsi dei file, che ora sono in
`Results/varianti_agente/`. L'indice di tutte le varianti, con il codice e i comandi, è in [README.md](README.md).

Ogni variante è scritta qui **prima** di essere lanciata, con regola, motivo e soglie. Si lancia una volta sola e non si ritocca dopo aver visto
i risultati. Tutte le varianti, anche quelle andate male, vanno nel report con il numero totale di prove.

## Varianti già provate

| # | Variante | Chi | Esito sul train (lordo, costo 0) |
|---|---|---|---|
| 1 | B `spark_24h` (Spark X2.6 4B, 24 ore) | Giulio | 925 trade, +6,38 bps (A: +7,44) |
| 2 | C `spark_24h` | Giulio | +4,15 bps |
| 3 | B `spark_6h` | Giulio | +6,14 bps |
| 4 | C `spark_6h` | Giulio | +3,97 bps |
| 5 | B `lessico` (Loughran-McDonald) | Giulio | +7,08 bps |
| 6 | C `lessico` | Giulio | +5,46 bps |
| 7 | B `spark_24h_ragiona` e `mano` (solo 40 segnali) | Giulio | campione |
| 8 | B 3B 6 ore, prompt completo, filtro a parole chiave | noi | 958 trade, +7,03 bps |
| 9 | B FinBERT, finestra legata alla seduta | noi | 964 trade, +7,02 bps; bloccati: rientro 1 su 9 |
| 10 | C FinBERT, finestra legata alla seduta | noi | +6,05 bps; notizia giusta 40% |

## Variante 11 (punto 1, a regole): il prezzo è diventato definitivo?

Scritta il 13 novembre 2026, prima di cercare le notizie.

**Motivo.** Un'acquisizione definitiva con prezzo fissato blocca il prezzo del bersaglio vicino all'offerta: lo spread della coppia non può
rientrare. Una trattativa, una voce o un'offerta non concordata danno spesso una reazione eccessiva, che può rientrare. Il compratore e le
altre notizie (risultati, analisti, prodotti) sono rumore per questa regola.

**Notizie considerate.** Notizie che citano almeno uno dei 30 titoli e hanno al massimo 3 ticker in totale (no elenchi).

**Regole sul testo (titolo e sommario, in inglese):**
1. È una notizia di M&A se contiene parole di acquisizione o fusione (acquire, merger, takeover, buyout, deal to buy, bid for, tender offer, go private...).
2. Fase: **definitiva** se c'è un accordo firmato o un prezzo fissato (definitive agreement, agreed to acquire / be acquired, to be acquired by,
   per share, all-cash, all-stock); **trattativa** se ci sono parole di incertezza (in talks, exploring, considering, weighs, reportedly,
   people familiar, approach, bid, offer, interest, could, may, potential); **completata** se l'operazione è chiusa (completes, completed, closes);
   **approvazione** se è un via libera di un'autorità. Se compaiono sia parole definitive sia di incertezza, vale **trattativa**.
3. Ruolo di ogni titolo della coppia: **bersaglio** se è chi viene comprato (acquire / buy / offer for <azienda>, <azienda> to be acquired / sold to),
   **compratore** se è chi compra (<azienda> to acquire / acquires / agrees to acquire / buys), altrimenti **citata**.

**Decisioni (da applicare dopo aver mostrato la lista al gruppo, senza cambiare le regole):**
- B: `blocca` se nella finestra legata alla seduta (gap della notte: dall'ultima chiusura; resto della seduta: dalle 9:30) c'è una notizia di
  M&A **definitiva** in cui un titolo della coppia è il **bersaglio**. Altrimenti `entra`.
- C: nessun `segui`: con il prezzo del bersaglio fermo all'offerta, seguire la notizia non ha un motivo economico.

**Variante 11b (agente perfetto).** Le notizie di M&A trovate si classificano anche a mano (fase e ruolo). Le stesse decisioni con le etichette a
mano dicono quanto vale la regola se il classificatore non sbaglia mai.

**Esito (13 novembre).** 61 notizie di M&A sui 30 titoli; nessuna acquisizione definitiva di una delle 30 aziende (i bersagli sono solo due
trattative: PayPal il 15 luglio, Workday il 13 agosto). La variante 11 non blocca nessun trade: sul train coincide con la A e la sua ipotesi
non si può verificare. Lista in `Results/varianti_agente/ma_regole/notizie_ma.csv`.

## Variante 12 (punto 3): ridurre invece di bloccare

Scritta il 13 novembre 2026, prima di lanciarla.

**Motivo.** Il programma prevede "entra, eventualmente con dimensione ridotta". I blocchi tolgono a volte i trade migliori (i movimenti grandi
che rientrano): dimezzare l'importo limita le perdite dei trade con una notizia senza perdere del tutto i guadagni di quelli che rientrano.

**Come si calcola.** Ogni trade ha una dimensione: 1 (10.000 dollari per gamba), 0,5 o 0. Guadagno e costi in dollari si moltiplicano per la
dimensione (i costi sono proporzionali all'importo). Si riportano dollari, rendimento sul capitale (sempre 300.000 dollari), Sharpe e guadagno
medio per dollaro investito (media dei bps pesata con la dimensione). Costi 0 e 5 bps per operazione.

**Varianti (nessun nuovo run dei modelli):**
- 12a: `spark_24h` di Giulio con la sua colonna `size`: 0,5 se c'è rumore su un titolo, 1 altrimenti, 0 se blocca.
- 12b: `spark_24h` di Giulio, ridurre invece di bloccare: blocca diventa 0,5, tutto il resto 1.
- 12c: il nostro 3B 6 ore: blocca e `enter_reduced` diventano 0,5, tutto il resto 1.
- 12d: FinBERT con la finestra legata alla seduta: 0,5 se c'è almeno una notizia mirata con sentiment forte (113 segnali), 1 altrimenti.

**Esito (13 novembre), costo 0.** Nessuna variante supera la A in dollari (A +7.239 $; 12a +4.075; 12b +6.572; 12c +6.818; 12d +6.137).
Lo Sharpe di 12b (8,59) e 12d (8,29) è appena sopra quello della A (8,13): differenza non significativa su 64 giorni. In tutte le varianti i
trade ridotti guadagnavano più della media (da +9,8 a +27,8 bps lordi). Tabella in `Results/varianti_agente/dimensione/size.csv`.

## Variante 13 (punto 5): C solo su notizie fresche e forti

Scritta il 13 novembre 2026, prima di lanciarla.

**Motivo.** Una notizia importante appena uscita durante la seduta può non essere ancora tutta nel prezzo (sottoreazione e drift dopo le
notizie, letteratura da verificare prima di citarla): l'allargamento dello spread può continuare. Una notizia della notte invece è già
incorporata nel gap di apertura, e quel gap tende a rientrare: lì non si segue mai.

**Regola.** `segui` solo se valgono tutte:
1. il segnale non è nel gap della notte (minuti 15-29 dall'apertura);
2. c'è una notizia uscita durante la seduta di oggi (dalle 9:30) ed entro 60 minuti prima del segnale;
3. la notizia è mirata: cita una sola delle due aziende e ha al massimo 3 ticker;
4. la notizia ha un evento forte: una parola dell'evento (acquisizione, indagine, dimissioni...) o un cambio di guidance (stesse espressioni del nostro agente 3B);
5. FinBERT dà una direzione chiara: probabilità della classe vincente almeno 0,8;
6. la direzione della notizia per la coppia (positiva su A o negativa su B = A sale rispetto a B) ha lo stesso segno del movimento relativo
   dei 30 minuti prima del segnale.
Il trade va nel verso della notizia ed esce come nella C di Giulio (rientro, 90 minuti, fine giornata; nessuno stop). In tutti gli altri casi
`entra` come la A: le differenze dalla A vengono solo dai trade che seguono la notizia.

**Esito (13 novembre).** Nessun `segui`: la variante coincide con la A e la sua ipotesi non si può verificare sul train. Le notizie con evento,
sentiment forte e al massimo 3 ticker sono 59 su 2.106; nessuna esce durante la seduta nei 60 minuti prima di un segnale fuori dal gap (le
due trovate sono prima di segnali del gap). Descrittivo: dei 516 segnali fuori dal gap, 34 hanno una notizia mirata qualsiasi nei 60 minuti
prima e 16 una con sentiment forte, ma nessuna con un evento. Decisioni in `Results/varianti_agente/c_fresca/decisioni.csv`.

## Varianti 14 e 15: notizie in concomitanza con il movimento (finestra dell'episodio)

Scritte il 13 novembre 2026, prima di lanciarle.

**Motivo.** La domanda giusta non è "c'è una notizia nelle ultime N ore?" ma "c'è una notizia che spiega *questo* allargamento?". Si guardano
le notizie uscite mentre lo spread si allontanava dalla media, fino al momento della decisione.

**Momento della decisione (verificato).** Le barre sono etichettate con il minuto di inizio: lo z-score del segnale usa la chiusura della
barra `t_signal` e si entra all'apertura della barra dopo. La decisione è quindi alla fine della barra del segnale: si usano le notizie con
`ts < t_signal + 1 minuto` (prima: `ts <= t_signal`, che escludeva le notizie uscite durante la barra del segnale).

**Inizio dell'episodio.** Dalla barra del segnale si va indietro finché lo z-score resta oltre 1 con lo stesso segno del segnale, senza uscire
dalla giornata. L'episodio comincia alla prima di queste barre, con 5 minuti di margine prima (una notizia muove il prezzo in pochi secondi).
Se l'episodio arriva fino alla prima barra della giornata, il movimento è nato nella notte: si comincia dalla chiusura del giorno di borsa prima (16:00).

**Regole sulle notizie: le stesse delle varianti 9 e 10 (FinBERT)**, così cambia solo la finestra:
- 14 (B): blocca se c'è almeno una notizia mirata (una sola azienda, al massimo 3 ticker) con sentiment forte (almeno 0,8), tutte le forti
  riguardano la stessa azienda e almeno una ha una parola dell'evento. Altrimenti entra.
- 15 (C): segue se il punteggio relativo (A meno B) ha modulo almeno 0,5 e lo stesso segno del movimento dei 30 minuti prima; altrimenti come la 14.
Si valutano come al punto 4 (quota di rientro dei bloccati, blocco a caso, notizia giusta nella C) e con il backtest a costo 0 e 5.

**Esito (13 novembre), costo 0.** Episodi: 802 nati in seduta (durata mediana 11 minuti), 171 dalla notte. Solo 96 segnali hanno una notizia
mirata nell'episodio (71 dalla notte, 25 in seduta), 3 nella barra del segnale. 14 B: 5 blocchi, tutti nel gap della notte, nessuno rientra
(p Fisher 0,06), lordo medio +57 per PayPal (+564), mediano -9; 968 trade, +6.955 $ (A +7.239). 15 C: 20 trade invertiti, notizia giusta 55%,
lordo medio -8,9, mediano +5,8; +6.589 $. Due blocchi su cinque nascono da "settle" in contesti non legali (riacquisto di azioni, accordo FTC
di un'altra azienda). Tabella in `Results/varianti_agente/finbert_episodio/episodio.csv`.

## Varianti 16 e 17: decidere k minuti dopo il segnale (opzione 3)

Scritte il 13 novembre 2026, prima di lanciarle.

**Motivo.** Una notizia può uscire subito dopo l'inizio del movimento. Per poterla leggere senza lookahead bisogna spostare più avanti sia la
decisione sia l'ingresso. È una strategia diversa dalla A: si confronta con una "A ritardata" con lo stesso ritardo, così la differenza misura
solo il valore dell'agente; il confronto tra A e A ritardata misura il costo dell'attesa.

**Ritardi:** k = 5 e k = 15 minuti, fissati prima (due prove).

**A ritardata (A_k).** Stessi 973 segnali. La decisione è alla chiusura della barra `t_signal + k`, l'ingresso all'apertura della barra dopo,
nella stessa direzione della A. Uscita con le stesse regole di `signals.run_rules` (rientro, stop a z 3,5, 90 minuti, fine giornata). Nessun
trade se alla barra della decisione lo spread è già rientrato (z oltre la soglia di uscita) o se la giornata finisce prima dell'ingresso.
Con k = 0 la simulazione deve riprodurre esattamente i 973 trade della A (controllo).

**Agente (FinBERT, stesse regole delle varianti 14 e 15).** Finestra dall'inizio dell'episodio (variante 14) alla chiusura della barra della
decisione. Movimento relativo dei 30 minuti per la C calcolato fino alla barra della decisione.
- 16 (B_k): blocca come la 14; altrimenti entra come la A_k.
- 17 (C_k): segue come la 15, nel verso della notizia, con uscita al rientro, 90 minuti o fine giornata, senza stop; altrimenti come la 16.

**Esito (13 novembre), costo 0.** Controllo superato: con k = 0 i 973 trade coincidono con la A. Costo dell'attesa: A ritardata di 5 minuti
964 trade, +5,26 bps, +5.071 $; di 15 minuti 941 trade (32 segnali già rientrati), +7,18 bps, +6.752 $ (A: +7.239 $). Valore dell'agente
rispetto alla A ritardata: k = 5, B 4 blocchi (nessuno rientra, mediano -49 bps), -75 $; C 22 trade seguiti, notizia giusta 45%, -788 $.
k = 15, B 6 blocchi (1 rientra, mediano -63 bps), -63 $; C 23 seguiti, notizia giusta 35%, -1.227 $. Tabella in `Results/varianti_agente/ritardo/ritardo.csv`.
