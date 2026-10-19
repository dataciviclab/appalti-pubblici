# Note tecniche — anac-varianti

## Struttura fonte

CKAN dataset `varianti` su dati.anticorruzione.it:
- Full dump cumulativo: risorsa `varianti_csv` (~41 MB ZIP)
- Delta mensili esclusi (full dump sostitutivo)

## Qualità (full dump, 321.294 righe)

| Colonna | Non-null |
|---|---|
| `motivo_variante` | 100% |
| `data_approvazione_variante` | 99.1% |
| `data_atto_aggiuntivo` | 50.3% |
| `cig_proroga` | 0.6% |
| `id_aggiudicazione` | 100% (positivo) |

- 321.294 righe, 220.976 CIG distinti, 303.272 `id_variante` distinti.
- `cod_motivo_variante`: `99` e `15` i codici più frequenti.
- `motivo_variante` include valori `-` o descrittivi; normalizzare in clean.
- `id_variante` ripetuto fino a 10 volte: non usarlo come chiave univoca.
- `cig_proroga` è il CIG della proroga collegata, non il CIG della variante.
- Date malformate (es. `213-08-24`, `3013-08-25`) → NULL; resta 2000-oggi.

## Join

- `cig` → bandi/aggiudicazioni
- `id_aggiudicazione` → aggiudicazioni
