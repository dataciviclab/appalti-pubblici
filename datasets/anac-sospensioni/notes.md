# Note tecniche — anac-sospensioni

## Struttura fonte

CKAN dataset `sospensioni` su dati.anticorruzione.it:
- Full dump cumulativo: risorsa `sospensioni_csv` (~19 MB ZIP)
- Delta mensili esclusi

## Qualità (full dump, 227.747 righe)

| Colonna | Non-null |
|---|---|
| `data_sospensione` | 100% |
| `data_ripresa` | 92.3% |
| `descrizione_motivo` | 100% |

- 126.325 CIG distinti: una gara può avere più sospensioni.
- Durata media 92 giorni; 609 record con ripresa precedente alla sospensione
  (incoerenti, esclusi dal calcolo); 10 durate oltre 10 anni (anomalie).

Motivi più frequenti nel campione:
- INTERFERENZE DI NATURA TECNICA
- AVVERSE CONDIZIONI CLIMATICHE
- CAUSE DI FORZA MAGGIORE
- REDAZIONE DI VARIANTI IN CORSO DI ESECUZIONE
- PUBBLICO INTERESSE O NECESSITA'

## Calcolo durata

```
giorni = date_diff('day', data_sospensione, data_ripresa)
```

Scartare i casi con `data_ripresa < data_sospensione` (dato incoerente) e
quelli oltre 3650 giorni (anomalie di codifica).
