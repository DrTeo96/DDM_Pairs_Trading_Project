# Il test: regole scritte prima di guardarlo

Questo file fissa che cosa si fa sul periodo di test e come si giudica il risultato. È scritto il 14 novembre 2026, prima di scaricare le notizie del test e prima di calcolare qualsiasi segnale o trade del test. Le regole non si cambiano dopo aver visto i risultati.

## Che cosa si prova

Sul train (16 giugno - 16 settembre 2026) il gruppo ha confrontato 21 varianti dell'agente di notizie e ha scelto `finbert_episodio`. La scelta e il criterio sono spiegati in [src/06_backtest.ipynb](../src/06_backtest.ipynb) e [src/07_robustezza.ipynb](../src/07_robustezza.ipynb).

Sul test si portano solo tre versioni, con le regole del train:

| Versione | Cosa fa |
|---|---|
| **A** | Entra a ogni segnale, senza agente. È il riferimento |
| **B** | `finbert_episodio` può bloccare il trade |
| **C** | `finbert_episodio` può bloccare o seguire la notizia (entrare nel verso opposto alla A) |

Nessun'altra variante va sul test.

## Il periodo e i dati

- **Test:** dal 17 settembre al 30 ottobre 2026, l'ultimo giorno con prezzi intraday. Sono 32 giorni di borsa; 5 coppie (CSX-UNP, HD-LOW, DHR-TMO, GS-MS, ISRG-SYK) hanno i prezzi dal 18 settembre, quindi 31 giorni, come nel train avevano 60 giorni invece di 64.
- **Prezzi:** i file di `pairs_intraday_v2/`, gli stessi del train, che arrivano già al 30 ottobre.
- **Notizie:** Alpaca (Benzinga), scaricate solo dal 17 settembre al 30 ottobre, in un file separato da quello del train. Gli episodi "dalla notte" del 17 settembre partono dalle 16:00 del 16: le notizie di quelle ore sono già nell'archivio del train e si usano da lì, con i punteggi FinBERT già calcolati.
- **Sentiment:** FinBERT (`ProsusAI/finbert`) su titolo e sommario di ogni notizia nuova, come nel train.
- **Mercato:** SPY giornaliero da Alpaca, aggiustato per i dividendi, dal 16 settembre (serve la chiusura del giorno prima per il rendimento del 17) al 30 ottobre.

## Le regole, bloccate

**Segnale** (come in `03_segnali.ipynb` e [src/signals.py](../src/signals.py)): spread logaritmico con beta 1, z-score con EMA continua e emivita di 60 minuti, ingresso a |z| ≥ 2, uscita a |z| ≤ 0, stop a |z| ≥ 3,5, tempo massimo 90 minuti, niente ingressi nei primi 15 e negli ultimi 30 minuti, niente ingresso se una gamba ha la barra riempita, esecuzione all'apertura della barra dopo. La EMA continua dal train: lo z-score del 17 settembre usa i prezzi passati, mai quelli futuri.

**`finbert_episodio`** (come in [src/varianti_agente/episodio.py](../src/varianti_agente/episodio.py)):
- inizio dell'episodio: andando indietro dal segnale, la prima barra di fila con z oltre 1 dello stesso segno, meno 5 minuti; se l'episodio arriva alla prima barra della giornata, dalle 16:00 del giorno di borsa prima;
- fine della finestra: la chiusura della barra del segnale;
- notizia mirata: cita una sola delle due aziende e ha al massimo 3 ticker; notizia forte: la classe vincente di FinBERT ha probabilità di almeno 0,8;
- **B:** blocca se c'è almeno una notizia mirata forte, tutte le forti riguardano la stessa azienda e almeno una contiene una parola dell'evento (la stessa lista del train). Altrimenti entra;
- **C:** segue se la differenza dei punteggi medi (azienda A meno azienda B) ha modulo almeno 0,5 e lo stesso segno del movimento relativo dei 30 minuti prima; altrimenti decide come la B. Il trade seguito esce al primo tra rientro dello spread, 90 minuti e fine giornata, senza stop.

**Backtest** (come in [src/backtest.py](../src/backtest.py)): 10.000 dollari per gamba, senza leva, tutto chiuso a fine giornata; capitale di 20.000 dollari per coppia, 300.000 in tutto; un trade ha 4 operazioni.

**Costi:** 0 punti base per operazione (scenario principale, indicazione del docente) e 5 per confronto.

## Come si giudica

**Criterio principale:** la differenza in dollari tra la B e la A, e tra la C e la A, a costo 0. È lo stesso criterio con cui `finbert_episodio` è stata scelta sul train.

**Controlli** (gli stessi del train, calcolati anche sul test):
1. intervallo di confidenza al 95% della differenza, ricampionando i giorni con reinserimento (10.000 volte): dice se la differenza è distinguibile da zero;
2. solo B: guadagno dei trade bloccati contro 5.000 blocchi a caso dello stesso numero (`p_caso`);
3. solo B: quota di rientro dei trade bloccati contro quella dei tenuti, con il test esatto di Fisher;
4. solo C: quota dei trade seguiti in guadagno ("notizia giusta") e loro guadagno medio;
5. per A, B e C: guadagno netto per trade, win rate, profit factor, Sharpe, drawdown. Lo Sharpe su 32 giorni è poco affidabile e va riportato così;
6. gli stessi risultati a costo 5;
7. differenza dalla A per coppia, per settore e senza PYPL-XYZ;
8. beta e alpha rispetto a SPY;
9. coerenza con il train: la differenza dalla A ha lo stesso segno che sul train (B −285 $, C −651 $)?

**Non si fanno** il confronto tra le due metà del periodo né il controllo "senza 13 agosto", che è un giorno del train.

**Se l'agente non blocca o non segue niente.** Se sul test l'agente non blocca nessun trade, la B coincide con la A e il test non dice nulla sui blocchi; lo stesso per la C se non segue nessuna notizia. Lo si riporta così, senza cambiare le regole.

## Una volta sola

Il test è stato fatto una volta, il 14 novembre 2026, e **non si rifà**: rifarlo dopo aver visto i risultati toglierebbe valore al test.

- Prima del test, gli stessi script hanno rifatto il train e hanno ritrovato esattamente i 973 segnali di `03_segnali.ipynb` e le decisioni e i trade di `finbert_episodio` salvati in `Results/varianti_agente/finbert_episodio/`. Se non avessero coinciso, il test non sarebbe partito.
- [src/test_finale.py](../src/test_finale.py) ha calcolato segnali, decisioni e trade del test e li ha salvati in `Results/test/`.
- I notebook [src/06_test_backtest.ipynb](../src/06_test_backtest.ipynb) e [src/07_test_robustezza.ipynb](../src/07_test_robustezza.ipynb) leggono solo i file salvati in `Results/test/`: si possono rieseguire quante volte serve senza rifare il test.

## Come è stato fatto

Dalla cartella del progetto, in quest'ordine. I comandi sono qui per documentare il lavoro: non vanno rilanciati.

```bash
uv run python -m src.test_dati                                              # notizie e SPY del test, con le chiavi Alpaca in .env
uv run --with torch --with transformers python -m src.test_finbert          # FinBERT sulle notizie del test
uv run python -m src.test_finale                                            # il test
```

Poi si eseguono `06_test_backtest.ipynb` e `07_test_robustezza.ipynb`.
