# ANAC — Fine Contratto

**Dataset**: `anac_fine_contratto`
**Fonte**: ANAC — Autorità Nazionale Anticorruzione, [dati.anticorruzione.it](https://dati.anticorruzione.it/)
**Protocollo**: CKAN diretto
**Licenza**: CC BY-SA 4.0

## Contenuto

Date di conclusione del contratto e motivi di risoluzione/interruzione
anticipata. Chiude il ciclo di vita iniziato con `anac_avvio_contratto`.

## Copertura

| Metrica | Valore |
|---|---|
| Righe (full dump) | 1.070.254 |
| CIG distinti | 1.068.186 |
| Colonne | 9 |
| CSV zippato (full) | ~48 MB |
| Copertura temporale | 2000-2026 |
| Aggiornamento | Mensile |

## Schema (9 colonne)

| Colonna | Tipo | Descrizione |
|---|---|---|
| `cig` | VARCHAR | CIG (join con bandi/aggiudicazioni) |
| `cod_motivo_risoluzione` | VARCHAR | Codice motivo risoluzione |
| `motivo_risoluzione` | VARCHAR | Motivo risoluzione |
| `cod_motivo_interruzione_anticipata` | VARCHAR | Codice interruzione |
| `motivo_interruzione_anticipata` | VARCHAR | Motivo interruzione |
| `data_conclusione_anticipata` | DATE | Conclusione anticipata |
| `data_effettiva_ultimazione` | DATE | Ultimazione effettiva |
| `id_aggiudicazione` | BIGINT | FK aggiudicazioni |
| `giorni_proroga` | INTEGER | Giorni di proroga (vuota nella fonte) |

## Mart

- `mart_fine_contratto`: conclusi/risoluzioni/interruzioni per anno
- `mart_motivi_fine`: conteggio per motivo

## Join

- `cig` → `anac_bandi_gara`, `anac_aggiudicazioni`
- `id_aggiudicazione` → `anac_aggiudicazioni`

## Limiti

- `giorni_proroga` è **vuota** in tutti i record osservati: il ritardo va
  calcolato con `data_effettiva_ultimazione - data_termine_contrattuale`.
- `data_effettiva_ultimazione` è valorizzata nel ~99% dei record.
- Motivi di risoluzione/interruzione presenti in una minoranza di record
  (~0,9% risoluzioni, ~1,4% interruzioni).
- Date malformate filtrate nell'intervallo 2000-oggi.
