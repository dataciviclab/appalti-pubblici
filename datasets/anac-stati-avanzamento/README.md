# ANAC — Stati di Avanzamento Lavori (SAL)

**Dataset**: `anac_stati_avanzamento`
**Fonte**: ANAC — Autorità Nazionale Anticorruzione, [dati.anticorruzione.it](https://dati.anticorruzione.it/opendata/dataset/stati-avanzamento)
**Licenza**: CC BY-SA 4.0

## Contenuto

Stati di Avanzamento Lavori (SAL) degli appalti ordinari. Ogni SAL rappresenta una tranche di pagamento in corso d'opera, con importo, date e scostamenti rispetto al cronoprogramma.

`importo_sal` nella fonte non ha semantica univoca: per alcune aggiudicazioni e' cumulativo (valore progressivo), per altre e' incrementale (importo del singolo SAL). Il clean classifica ogni serie per `id_aggiudicazione` in `tipo_serie` e calcola `importo_quota`, il contributo attribuito al singolo SAL: per le serie cumulative e ambigue e' il MAX della serie (sulla riga del picco), per quelle incrementali e' l'importo pieno. Le righe duplicate (stessa data e stesso importo) non contribuiscono all'importo, ma restano in output e sono contate da `n_sal`. Sommare `importo_quota` (non `importo_sal`) da' il totale corretto.

| `tipo_serie` | Significato |
|---|---|
| `cumulativa` | serie in crescita (>=80% delta positivi o incrementi piccoli): il totale e' il MAX |
| `incrementale` | valori costanti, oscillanti senza trend o con forti variazioni (`somma delta positivi > 2x MAX`): il totale e' la SUM |
| `ambigua` | trend misto non riconducibile ai casi sopra: trattata come cumulativa, stima conservativa |
| `singola` | un solo SAL nella serie |

## Schema

| Colonna | Tipo | Descrizione |
|---|---|---|
| `cig` | VARCHAR | Chiave — join con `anac_bandi_gara` |
| `denominazione_sal` | VARCHAR | Descrizione SAL (es. "1 STATO AVANZAMENTO LAVORO") |
| `flag_ritardo` | VARCHAR | IN LINEA / IN RITARDO / IN ANTICIPO |
| `data_emissione_sal` | DATE | Data emissione SAL |
| `importo_sal` | DOUBLE | Importo del SAL come da fonte (cumulativo o incrementale, vedi `tipo_serie`) |
| `n_giorni_scostamento` | INTEGER | Giorni di scostamento dal cronoprogramma |
| `progressivo_sal` | INTEGER | Numero progressivo del SAL |
| `id_aggiudicazione` | BIGINT | Join con `anac_aggiudicazioni` |
| `data_cert_pagamento` | DATE | Data certificato di pagamento |
| `importo_cert_pagamento` | DOUBLE | Importo certificato di pagamento (€) |
| `giorni_proroga` | DOUBLE | Giorni di proroga concessi |
| `tipo_serie` | VARCHAR | Classificazione della serie SAL: cumulativa / incrementale / ambigua / singola |
| `importo_quota` | DOUBLE | Contributo del SAL: MAX della serie sulle righe di picco per cumulative/ambigue, importo pieno per le incrementali |

## Copertura

| Metrica | Valore |
|---|---|
| Righe | ~1.27M |
| CIG distinti | ~344k |
| Peso CSV zippato | ~30 MB |
