# Vibe coding con le build phases

Metodo per costruire un'applicazione con Claude senza affidarsi a un unico prompt lunghissimo. Il lavoro si divide in build phases piccole, tracciate e verificate una alla volta.

Fonte: reel Instagram di andrei.bsns ("VOGLIO VIBE CODARMI VERSO I MILIONI", ottobre 2026). Nomi di skill e strumenti riportati come citati nel video.

---

## Step 1: Scrivi lo spec

- Descrivi come immagini l'applicazione: cosa fa, per chi, quali funzioni ha.
- Dettalo a voce con Wispr Flow per andare più veloce e dare più contesto.
- L'output è uno spec del progetto, la base per tutti gli step successivi.

## Step 2: Chiarisci i requisiti con Wayfinder

- Usa la skill **Wayfinder** di Matt Pocock.
- La skill ti fa una serie di domande finché non capisce esattamente cosa vuoi costruire.
- Rispondi a tutte: ogni risposta diventa una decisione di progetto.
- Claude annota tutte le decisioni prese.

## Step 3: Scegli l'issue tracker

Serve un posto dove tenere i task che tu e Claude dovete seguire. Opzioni:

- **GitHub Issues**: se il codice sta già su GitHub.
- **Linear**: ha un MCP pensato per lo sviluppo.
- **ClickUp**, **Jira**, **Google Tasks**: vanno bene anche questi.

## Step 4: Dividi il progetto in build phases

Lo step che quasi nessuno fa.

- Chiedi a Claude di dividere il progetto in **build phases**.
- Digli di crearne **tra 10 e 50**.
- Ogni build phase diventa **un issue** sull'issue tracker.

## Step 5: Esegui il loop

Ripeti per ogni build phase:

1. Di' a Claude: "vai build phase". Se ha bisogno di te per uno step, te lo chiede.
2. A fine fase lancia **/handoff** (skill di Matt Pocock), così Claude non perde il contesto.
3. Lancia **/compact** per restare **sotto i 200.000 token** usati.
4. Controlla o testa la feature. Se puoi, usa il **TDD** (Test Driven Development).
5. Passa alla build phase successiva.

### Gestione del contesto

- Sotto i 200.000 token: zona ottimale.
- Intorno a 500.000-600.000 token: le prestazioni calano.
- Non cercare di fare tutto in un'unica sessione: handoff e compact servono proprio a questo.

---

## Checklist rapida

- [ ] Spec scritto (dettato con Wispr Flow)
- [ ] Domande di Wayfinder completate e decisioni annotate
- [ ] Issue tracker scelto e collegato
- [ ] Progetto diviso in 10-50 build phases, una per issue
- [ ] Per ogni fase: build, /handoff, /compact, test, fase successiva

---

## Note

- Il metodo ha una base solida: spec chiaro, task piccoli e tracciati, gestione del contesto, test a ogni fase.
- Le cifre del video ("10 milioni di MRR in 10 giorni", le metriche della sua piattaforma) sono iperboli promozionali, non risultati verificabili.
