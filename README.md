# ANAC Integrazione — DataCivicLab

Questo repository raccoglie **dataset sugli appalti pubblici ANAC** per rispondere a
domande civiche: **come funzionano gli appalti pubblici in Italia, dove ci sono
ritardi, e quali imprese partecipano?**

E' un repo **multi-dataset**: ogni dataset vive in `datasets/<slug/>`, il compose
cross-dataset in `compose/anac-cross/`. E' pensato per chi vuole orientarsi in
fretta: capire cosa mostrano i dati, dove sono solidi, quali limiti hanno e
quali domande aiutano ad approfondire.

- **Stato:** alpha
- **Copertura:** 2016-2026, Italia (tutte le regioni)
- **Unità di analisi:** CIG (Codice Identificativo Gara)

## La domanda civica

**Come variano gli appalti pubblici tra territori e nel tempo? Dove ci sono
ritardi, concentrazione di potere, e opportunità per le imprese?**

## Dataset

| Slug | Cosa contiene | Anni | Stato |
|---|---|---|---|
| `datasets/anac-bandi-gara` | Bandi di gara e lotti (CIG) | 2016-2025 | alpha |
| `datasets/anac-aggiudicazioni` | Esiti e importi delle aggiudicazioni | 2026 | alpha |
| `datasets/anac-aggiudicatari` | Imprese aggiudicatarie | 2026 | alpha |
| `datasets/anac-partecipanti` | Imprese partecipanti alle gare | 2026 | alpha |
| `datasets/anac-subappalti` | Subappalti | 2026 | alpha |
| `datasets/anac-stati-avanzamento` | Stati di avanzamento (SAL) | 2026 | alpha |
| `datasets/anac-collaudo` | Collaudo dei lavori | 2026 | alpha |
| `datasets/anac-cup` | CUP associati ai CIG | 2026 | alpha |
| `compose/anac-cross` | CIG snapshot unificato (cross-dataset) | 2026 | alpha |

## Compose

Il compose `anac-cross` unisce tutti i dataset a livello di CIG: ogni riga
rappresenta un singolo CIG con tutti gli attributi (aggiudicazioni, imprese,
SAL, collaudo, CUP). E' la base per analisi cross-dataset.

## Perché fidarsi

- fonti ufficiali ANAC (`dati.anticorruzione.it`)
- trasformazioni documentate in `docs/`
- controlli automatici prima della pubblicazione (CI + contract test)
- standard condivisi del DataCivicLab (`.github`)

## Partecipa

- **Discussions** → domande civiche, interpretazioni, proposte di metriche
- **Issues** → bug, problemi tecnici, miglioramenti della pipeline

## Esecuzione tecnica

```bash
pip install -r requirements.txt
make check        # valida tutti i dataset.yml (preflight)
make run          # esegue tutti i dataset singoli
make compose      # esegue il compose cross-dataset
python -m pytest tests/
```

## Struttura

```
datasets/          # 8 dataset singoli (bandi, aggiudicazioni, imprese, ...)
compose/           # 1 compose cross-dataset (anac-cross)
tests/             # contract test
Makefile           # interfaccia stabile
requirements.txt   # dipendenze runtime
```

## Confine con il toolkit

Il motore della pipeline vive nel repository `toolkit`. Questa repo non replica
la logica di esecuzione: definisce input, regole e output attesi per ogni dataset.

- bug o feature di CLI, runner, validazioni runtime → repo `toolkit`
- bug o modifiche a fonti, mapping, SQL, mart, docs → questa repo
