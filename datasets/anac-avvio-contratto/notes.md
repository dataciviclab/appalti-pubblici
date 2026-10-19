# Note tecniche — anac-avvio-contratto

## Struttura fonte

CKAN dataset `avvio-contratto` su dati.anticorruzione.it:
- Full dump cumulativo: risorsa `avvio-contratto_csv` (~149 MB ZIP)
- Delta mensili: risorse `YYYYMMDD-avvio-contratto_csv` (esclusi)
- Schema stabile, delimitatore `;`, quoting `"`

## Qualità (full dump, 1.925.829 righe)

| Colonna | Non-null |
|---|---|
| `data_stipula_contratto` | 62.0% |
| `data_inizio_effettiva` | 71.9% |
| `data_termine_contrattuale` | 83.5% |
| `data_verbale_consegna_definitiva` | 76.2% |
| `data_esecutivita_contratto` | 20.9% |
| `data_appr_prog_ese` | ~4% |

- `consegna_frazionata` / `consegna_sotto_riserva`: `0`/`1`, decodificati a BOOLEAN.
- `id_aggiudicazione` sempre presente e positivo.
- Date `0001-01-01` e valori malformati (es. `2710-08-24`, `0024-08-07`)
  → NULL in clean; resta solo l'intervallo 2000-oggi.
- 1.925.829 righe ma 1.922.826 CIG: un CIG può avere fino a 6 contratti.

## Uso

Il valore è nel compose `anac-cross`:
- `giorni_aggiudicazione_stipula` = stipula - ultima aggiudicazione
- `giorni_stipula_inizio` = inizio effettivo - stipula
- `giorni_scostamento_termine` = ultimazione effettiva - termine contrattuale
