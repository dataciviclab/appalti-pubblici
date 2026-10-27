# ANAC — Stati di Avanzamento Lavori (SAL)

**Dataset**: `anac_stati_avanzamento`
**Fonte**: ANAC — Autorità Nazionale Anticorruzione, [dati.anticorruzione.it](https://dati.anticorruzione.it/opendata/dataset/stati-avanzamento)
**Licenza**: CC BY-SA 4.0

## Contenuto

Stati di Avanzamento Lavori (SAL) degli appalti ordinari. Ogni SAL rappresenta una tranche di pagamento in corso d'opera, con importo, date e scostamenti rispetto al cronoprogramma.

La scheda SA1 di ANAC (campo `impSal`) definisce `importo_sal` come **importo dello stato di avanzamento progressivo (cumulato)**: il totale della serie e' il **MAX** (ultimo valore cumulato), non la somma. Il clean calcola `importo_quota`, il contributo attribuito al singolo SAL: il MAX sulla riga di picco, 0 sulle altre. Sommare `importo_quota` (non `importo_sal`) da' il totale corretto. Le righe duplicate (stessa data e stesso importo) non contribuiscono all'importo, ma restano in output e sono contate da `n_sal`.

| `tipo_serie` | Significato |
|---|---|
| `singola` | un solo SAL nella serie |
| `monotona` | serie non decrescente (nessun delta negativo) |
| `anomala` | serie con delta negativi (errore di compilazione): si usa comunque il MAX, ma va segnalata |

## Schema

| Colonna | Tipo | Descrizione |
|---|---|---|
| `cig` | VARCHAR | Chiave — join con `anac_bandi_gara` |
| `denominazione_sal` | VARCHAR | Descrizione SAL (es. "1 STATO AVANZAMENTO LAVORO") |
| `flag_ritardo` | VARCHAR | IN LINEA / IN RITARDO / IN ANTICIPO |
| `data_emissione_sal` | DATE | Data emissione SAL |
| `importo_sal` | DOUBLE | Importo dello stato di avanzamento progressivo (cumulato, scheda SA1 ANAC) |
| `n_giorni_scostamento` | INTEGER | Giorni di scostamento dal cronoprogramma |
| `progressivo_sal` | INTEGER | Numero progressivo del SAL |
| `id_aggiudicazione` | BIGINT | Join con `anac_aggiudicazioni` |
| `data_cert_pagamento` | DATE | Data certificato di pagamento |
| `importo_cert_pagamento` | DOUBLE | Importo del certificato/mandato di pagamento (incrementale) |
| `giorni_proroga` | DOUBLE | Giorni di proroga concessi |
| `tipo_serie` | VARCHAR | Qualita' della serie SAL: singola / monotona / anomala |
| `importo_quota` | DOUBLE | Contributo del SAL: MAX della serie sulla riga di picco, 0 sulle altre |

## Copertura

| Metrica | Valore |
|---|---|
| Righe | ~1.27M |
| CIG distinti | ~344k |
| Peso CSV zippato | ~30 MB |
