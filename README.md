# Pairs trading intraday sull'S&P 500 con un agente di notizie

Progetto d'esame (LUISS). Il testo del progetto è in [resources/instructions.pdf](resources/instructions.pdf).

Il pairs trading scommette su due aziende simili: quando i loro prezzi si allontanano più del solito, si compra il titolo rimasto indietro e si vende quello andato avanti, aspettando che la distanza rientri. Qui la distanza (lo spread) si misura minuto per minuto su 15 coppie di titoli dell'S&P 500, con dati Bloomberg. Un agente legge le notizie uscite prima di ogni segnale e blocca il trade quando l'allontanamento ha una causa vera in una sola delle due aziende. Il progetto confronta la strategia senza agente con quella con l'agente.

## Per iniziare

1. Installa [uv](https://docs.astral.sh/uv/) seguendo [docs/setup.md](docs/setup.md). Non serve installare Python: ci pensa uv.
2. Dalla cartella del progetto crea l'ambiente:

   ```bash
   uv sync    # crea .venv/ con Python e le versioni delle librerie scritte in uv.lock
   ```

3. Segui [src/README.md](src/README.md): dice quali dati servono e, passo per passo, cosa eseguire, cosa legge, cosa scrive e quanto tempo e memoria richiede.

## Dove sono le cose

| Dove | Cosa c'è |
|---|---|
| [src/](src/README.md) | Il codice della pipeline, nell'ordine di esecuzione |
| [docs/Programma.md](docs/Programma.md) | Il diario del gruppo: decisioni, risultati e limiti di ogni passaggio |
| [docs/setup.md](docs/setup.md) | Uso di uv: installare, eseguire, aggiungere librerie |
| `data/` | Dati grezzi e file prodotti dalla pipeline. Non è su git: ognuno tiene la sua copia |
| `resources/` | Testo del progetto, modello della presentazione, nomi dei titoli |
| `Old files/` | Ciò che non fa più parte della pipeline, conservato com'era |
| `.env.example` | Modello del file `.env` con chiavi e indirizzi personali, che git ignora |
