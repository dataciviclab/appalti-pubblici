# Appalti Pubblici ANAC

**Come funzionano gli appalti pubblici in Italia, dove ci sono ritardi, e quali imprese partecipano?**

Sistema di intelligence sugli appalti pubblici: raccoglie i dati ufficiali ANAC (dati.anticorruzione.it),
li trasforma in mart analitici e li rende interrogabili via dashboard Streamlit.

- **Fonte**: [ANAC Open Data](https://dati.anticorruzione.it/opendata)
- **Copertura**: 2016-2026, Italia (tutte le regioni)
- **Unità di analisi**: CIG (Codice Identificativo Gara)
- **Output pubblico**: Dashboard Streamlit + Discussion

## Cosa risponde

1. **Quanto si spende negli appalti e come varia nel tempo?** → trend bandi e importi 2016-2025
2. **Dove si concentra la spesa?** → top regioni, SA, settori per importo
3. **Quanti affidamenti sono diretti vs gara?** → distribuzione tipo scelta contraente
4. **Dove ci sono ritardi nell'esecuzione?** → SAL in ritardo per SA e settore
5. **Quali imprese dominano il mercato?** → concentrazione, ruolo (aggiudicatario/partecipante/subappaltante)
6. **Come si organizzano i raggruppamenti?** → RTI (mandataria + mandanti), catene di subappalto

## Dataset

| Dataset | Cosa contiene | Anni | Mart |
|---|---|---|---|
| `anac-bandi-gara` | Bandi di gara e lotti (CIG) | 2016-2025 | 6 |
| `anac-aggiudicazioni` | Esiti e importi delle aggiudicazioni | 2005-2026 | 2 |
| `anac-aggiudicatari` | Imprese aggiudicatarie | 2005-2026 | 1 |
| `anac-partecipanti` | Imprese partecipanti alle gare | 2005-2026 | 1 |
| `anac-subappalti` | Subappalti | 2005-2026 | 1 |
| `anac-stati-avanzamento` | Stati di avanzamento (SAL) | 2008-2026 | 1 |
| `anac-collaudo` | Collaudo dei lavori | 2005-2026 | 1 |
| `anac-cup` | CUP associati ai CIG | 2005-2026 | 1 |
| `compose/anac-cross` | CIG snapshot unificato (cross-dataset) | 2026 | 5 |

### Mart analitici (19 totali)

**Bandi** (6): mart_annuale, mart_trend_pnrr, mart_top_stazioni, mart_esiti_per_procedura, mart_trend_settore, mart_sa_profilo

**Aggiudicazioni** (2): mart_annuale, mart_dettaglio

**Support** (4): mart_top_aggiudicatari, mart_top_partecipanti, mart_top_subappalti, mart_sal

**Compose** (5): mart_panoramica, mart_lifecycle, mart_imprese, mart_ritardi_per_sa, mart_competitivita

**Altri** (2): mart_collaudo, mart_cup

## Dashboard

Dashboard Streamlit con 3 livelli:

| Livello | Pagina | Contenuto |
|---|---|---|
| **Monitoraggio** | Panoramica | KPI principali, trend 2016-2025, affidamenti diretti vs gara |
| | Trend Territorio | Heatmap regioni x anni, top 5 trend |
| **Intelligence** | Trasparenza | Concentrazione mercato, top imprese, tipo scelta contraente |
| | Esecuzione | Funnel bando→SAL, ritardi per SA e settore |
| | Imprese | Profilo imprese, RTI, catene subappalto |
| **Esplorazione** | Scheda CIG | Ricerca cross-dataset per CIG |
| | Scheda SA | Profilo stazione appaltante |
| | Query SQL | Query libera su tutti i dataset |

## Come si usa

```bash
# Setup
pip install -r requirements.txt

# Validare config
make check

# Eseguire tutte le pipeline
make run

# Eseguire compose (dopo i singoli)
make compose

# Dashboard
cd dashboard && streamlit run app.py

# Test
python -m pytest tests/
```

## Struttura

```
appalti-pubblici/
├── datasets/                   # 8 dataset singoli (toolkit pipeline)
│   ├── anac-bandi-gara/
│   ├── anac-aggiudicazioni/
│   ├── anac-aggiudicatari/
│   ├── anac-partecipanti/
│   ├── anac-subappalti/
│   ├── anac-stati-avanzamento/
│   ├── anac-collaudo/
│   └── anac-cup/
├── compose/
│   └── anac-cross/             # cross-dataset (CIG snapshot unificato)
├── dashboard/                  # Streamlit (3 livelli, 8 pagine)
├── out/                        # output pipeline (raw/clean/mart)
├── registry/                   # artifact catalog
├── tests/                      # contract test
├── Makefile
└── requirements.txt
```

## CI/CD

- **check.yml**: Valida i config YAML su ogni PR/push
- **pipeline.yml**: Esegue le pipeline, sync GCS, aggiorna registry

## Perché fidarsi

- Fonti ufficiali ANAC (`dati.anticorruzione.it`)
- Trasformazioni documentate in SQL
- Controlli automatici prima della pubblicazione (CI + contract test)
- Standard condivisi del DataCivicLab (`.github`)

## Partecipa

- **Discussions** → domande civiche, interpretazioni, proposte di metriche
- **Issues** → bug, problemi tecnici, miglioramenti della pipeline

## Confine con il toolkit

Il motore della pipeline vive nel repository `toolkit`. Questa repo non replica
la logica di esecuzione: definisce input, regole e output attesi per ogni dataset.

- bug o feature di CLI, runner, validazioni runtime → repo `toolkit`
- bug o modifiche a fonti, mapping, SQL, mart, docs → questa repo

## Licenza

- **Dati ANAC**: CC BY 4.0
- **Codice**: MIT
