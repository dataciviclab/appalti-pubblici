# ANAC — Sospensioni

**Dataset**: `anac_sospensioni`
**Fonte**: ANAC — Autorità Nazionale Anticorruzione, [dati.anticorruzione.it](https://dati.anticorruzione.it/)
**Protocollo**: CKAN diretto
**Licenza**: CC BY-SA 4.0

## Contenuto

Sospensioni dei contratti in esecuzione: data di sospensione, data di ripresa
e motivo. Permette di misurare **perché e per quanto tempo** i cantieri si
fermano.

## Copertura

| Metrica | Valore |
|---|---|
| Righe (full dump) | 227.747 |
| CIG distinti | 126.325 |
| Colonne | 5 |
| CSV zippato (full) | ~19 MB |
| Copertura temporale | 2000-2026 |
| Aggiornamento | Mensile |

## Schema (5 colonne)

| Colonna | Tipo | Descrizione |
|---|---|---|
| `cig` | VARCHAR | CIG (join con bandi/aggiudicazioni) |
| `data_sospensione` | DATE | Inizio sospensione |
| `data_ripresa` | DATE | Ripresa dei lavori |
| `descrizione_motivo` | VARCHAR | Motivo della sospensione |
| `id_aggiudicazione` | BIGINT | FK aggiudicazioni |

## Mart

`mart_sospensioni`: anno × motivo con numero sospensioni, CIG e giorni medi/max.

## Join

- `cig` → `anac_bandi_gara`, `anac_aggiudicazioni`
- `id_aggiudicazione` → `anac_aggiudicazioni`

## Limiti

- `data_ripresa` mancante nel ~8% dei record: la durata non è calcolabile.
- Una stessa gara può avere più sospensioni.
- Durate oltre 10 anni (10 record) sono trattate come anomalie di codifica ed
  escluse da medie/totali.
