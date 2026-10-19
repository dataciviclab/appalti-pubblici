# Note tecniche — anac-fine-contratto

## Struttura fonte

CKAN dataset `fine-contratto` su dati.anticorruzione.it:
- Full dump cumulativo: risorsa `fine-contratto_csv` (~48 MB ZIP)
- Delta mensili esclusi (full dump sostitutivo)

## Qualità (full dump, 1.070.254 righe)

| Colonna | Non-null |
|---|---|
| `data_effettiva_ultimazione` | 99.0% |
| `data_conclusione_anticipata` | 1.5% |
| `motivo_risoluzione` | 0.9% |
| `motivo_interruzione_anticipata` | 1.4% |
| `giorni_proroga` | **0.0%** |

- `giorni_proroga` è una colonna prevista ma sempre vuota: non usarla.
- Date sentinella (`0001-01-01`) e malformate → NULL; resta 2000-oggi.
- Motivi con varianti accentate/case: normalizzati con `normalize_string`.

## Calcolo dei ritardi (compose)

```
giorni_scostamento_termine =
    date_diff('day', avvio.data_termine_contrattuale, fine.data_effettiva_ultimazione)
```

Valore positivo = ultimazione dopo il termine contrattuale.

## Join

- `cig` → bandi/aggiudicazioni
- `id_aggiudicazione` → aggiudicazioni (sempre positivo nel campione)
