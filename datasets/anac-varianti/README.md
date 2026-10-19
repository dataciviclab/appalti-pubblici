# ANAC — Varianti

**Dataset**: `anac_varianti`
**Fonte**: ANAC — Autorità Nazionale Anticorruzione, [dati.anticorruzione.it](https://dati.anticorruzione.it/)
**Protocollo**: CKAN diretto
**Licenza**: CC BY-SA 4.0

## Contenuto

Varianti contrattuali: motivo, data di approvazione, CIG della proroga e data
dell'atto aggiuntivo. Misura quanto i contratti vengono modificati dopo
l'aggiudicazione.

## Copertura

| Metrica | Valore |
|---|---|
| Righe (full dump) | 321.294 |
| CIG distinti | 220.976 |
| Colonne | 8 |
| CSV zippato (full) | ~41 MB |
| Copertura temporale | 2000-2026 |
| Aggiornamento | Annuale (full dump) |

## Schema (8 colonne)

| Colonna | Tipo | Descrizione |
|---|---|---|
| `id_variante` | BIGINT | ID variante |
| `cod_motivo_variante` | VARCHAR | Codice motivo |
| `motivo_variante` | VARCHAR | Motivo della variante |
| `data_approvazione_variante` | DATE | Data approvazione |
| `cig` | VARCHAR | CIG (join con bandi/aggiudicazioni) |
| `id_aggiudicazione` | BIGINT | FK aggiudicazioni |
| `cig_proroga` | VARCHAR | CIG della proroga (se presente) |
| `data_atto_aggiuntivo` | DATE | Data atto aggiuntivo |

## Mart

`mart_varianti`: anno × motivo con numero varianti, CIG e quota con proroga.

## Join

- `cig` → `anac_bandi_gara`, `anac_aggiudicazioni`
- `id_aggiudicazione` → `anac_aggiudicazioni`

## Limiti

- `id_variante` non è univoco nel dump (può comparire fino a 10 volte).
- `cig_proroga` valorizzato in ~0,6% dei record.
- Date malformate filtrate nell'intervallo 2000-oggi.
- La variante non riporta l'importo: per lo scostamento economico usare
  `quadro-economico` (evento `VARIANTE`/`CONSUNTIVO`).
