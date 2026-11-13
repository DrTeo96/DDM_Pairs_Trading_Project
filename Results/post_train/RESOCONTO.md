# Esperimento post-train: dove l'agente blocca bene

**Questo esperimento è stato deciso il 13 novembre 2026, dopo aver visto i risultati del train in [../RESOCONTO.md](../RESOCONTO.md).** Non fa parte delle regole fissate prima dei risultati. I numeri vengono da [src/post_train.py](../../src/post_train.py) (`uv run python -m src.post_train`) e riguardano solo il **periodo di addestramento** (train, dal 16 giugno al 16 settembre 2026). Il test non è stato usato.

## In breve

- Nel backtest la versione B (l'agente blocca un fatto vero su una sola azienda) toglie 48 operazioni che guadagnavano **più** della media: +27,8 punti base contro +7,4.
- Guardando dentro quei 48 blocchi, si comportano in tre modi diversi a seconda della **direzione** della notizia e del **movimento** del titolo nei 30 minuti prima.
- Una variante della B, **B_esagerazione**, entra quando la notizia conferma il movimento invece di bloccare. Sul train batte la A di circa **+0,6 punti base per operazione**, in entrambe le metà del periodo.
- **Non è una prova**: la variante è stata costruita guardando questi stessi numeri, e il risultato dipende da pochi casi. È un'ipotesi da verificare su dati nuovi.

## 1. I tre casi

L'agente, quando trova un fatto vero (acquisizione, indagine, frode, cambio del management) su una sola delle due aziende, dice anche se la notizia è **positiva**, **negativa** o **incerta** per quell'azienda. La regola della versione C confronta questa direzione con il movimento del titolo rispetto all'altro nei 30 minuti prima del segnale. Ne vengono tre casi:

| Caso | Cosa vuol dire | Esempio |
|---|---|---|
| **Conferma** | Notizia positiva e il titolo è salito rispetto all'altro, oppure negativa ed è sceso | Silver Lake in trattativa per comprare Workday, e Workday sale rispetto a Salesforce |
| **Contraddice** | La notizia va in direzione opposta al movimento | Notizia positiva, ma il titolo scende rispetto all'altro |
| **Direzione incerta** | L'agente non sa dire se la notizia è buona o cattiva, oppure più notizie vere sullo stesso titolo vanno in direzioni diverse | |

## 2. Quanto avrebbero guadagnato

Il guadagno è quello che l'operazione avrebbe fatto nella versione A, cioè entrando comunque e scommettendo sul rientro.

| Caso | Operazioni | Guadagno medio | Valore centrale (mediana) | In guadagno |
|---|---|---|---|---|
| Conferma | 13 | +125,7 bps | +15,4 bps | 69% |
| Contraddice | 17 | +7,2 bps | +17,7 bps | 59% |
| Direzione incerta | 18 | -23,4 bps | -14,0 bps | 44% |
| Nessun blocco nella B | 925 | +6,4 bps | +10,9 bps | 60% |

Come leggerla:

- **Conferma**: in media guadagnano moltissimo, ma la mediana è +15: il risultato dipende da due giorni, PayPal (15 luglio) e Workday (13 agosto). Quando la notizia conferma il movimento, il mercato ha già reagito e spesso ha esagerato: lo spread rientra.
- **Contraddice**: guadagnano come le operazioni normali.
- **Direzione incerta**: è l'unico gruppo che perde. È un'osservazione, non una regola: si basa su 18 operazioni ed è emersa guardando questi dati.

## 3. La variante B_esagerazione

**Cosa fa.** Usa le decisioni che l'agente produce già, senza nuove chiamate al modello: blocca dove la versione C blocca (contraddice e direzione incerta, 35 operazioni) ed entra sul rientro, come la A, dove la C seguirebbe la notizia (conferma, 13 operazioni).

Risultati a costo 0 (scenario principale, come nel resoconto del backtest):

| Versione | Operazioni | Guadagno medio per operazione | Guadagno totale | Sharpe | 1ª metà | 2ª metà |
|---|---|---|---|---|---|---|
| A, senza agente | 973 | +7,44 bps | +7.239 $ | 8,13 | +9,17 | +5,59 |
| B del backtest | 925 | +6,38 bps | +5.905 $ | 8,06 | +8,47 | +4,13 |
| **B_esagerazione** | 938 | **+8,04 bps** | **+7.539 $** | **8,30** | **+9,72** | **+6,22** |

Le operazioni bloccate, contro blocchi fatti a caso dello stesso numero (5.000 estrazioni, stessa funzione del backtest):

| Versione | Bloccate | Guadagno medio delle bloccate | Blocchi a caso, in media | p-value |
|---|---|---|---|---|
| B del backtest | 48 | +27,8 bps | +7,3 bps | 0,97 |
| B_esagerazione | 35 | -8,6 bps | +7,5 bps | 0,044 |

Un p-value piccolo vuol dire che pochi blocchi a caso avrebbero tolto operazioni altrettanto cattive: B_esagerazione sceglie meglio del caso, la B del backtest peggio.

Con 5 punti base di costo per operazione tutte le versioni perdono, come nel resoconto del backtest: B_esagerazione perde un po' meno della A (-11.221 $ contro -12.221 $).

## 4. Cosa possiamo concludere, e cosa no

Possiamo dire:

- l'agente non legge male le notizie (95% di accordo con il gruppo sul campione di 40): il problema della B è la regola, che blocca anche casi in cui la distanza rientra;
- dentro i blocchi c'è una struttura che dipende dalla direzione della notizia.

Non possiamo dire:

- che B_esagerazione sia migliore della A in generale: è stata scelta guardando gli stessi dati su cui viene misurata;
- che la storia "il mercato esagera quando la notizia conferma il movimento" sia vera: si basa su 13 operazioni e due eventi;
- niente sul test, che non è stato usato.

## 5. Se la variante va nel test

Va decisa **prima** di aprire il test, scritta con la data e dichiarata come scelta fatta dopo aver visto il train. Va contata come prova in più (per esempio nel Deflated Sharpe Ratio). Sul test di circa 32 giorni, la differenza dalla A (circa +0,6 punti base per operazione) avrebbe un'incertezza di circa 0,5 punti base: visibile come stima, non come prova forte.

## Dove sono i file

| File | Contenuto |
|---|---|
| [per_caso.csv](per_caso.csv) | Guadagno dei 48 blocchi della B per caso (conferma, contraddice, direzione incerta) |
| [blocchi_B.csv](blocchi_B.csv) | I 48 blocchi uno per uno, con direzione, movimento, guadagno e motivo dell'agente |
| [confronto.csv](confronto.csv) | A, B e B_esagerazione a costo 0 e 5, con le due metà del train |
| [bloccati_contro_caso.csv](bloccati_contro_caso.csv) | Operazioni bloccate contro blocchi a caso |
| [trades_B_esagerazione.csv](trades_B_esagerazione.csv) | Ogni operazione della variante |
| [curve_capitale.png](curve_capitale.png) | Curve di capitale a costo 0 |
