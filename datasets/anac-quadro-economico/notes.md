# Note tecniche — anac-quadro-economico

Gli importi per CIG: base d'asta, varianti, consuntivo. È la fonte che mancava a
`varianti` (che ha date e motivi ma **zero importi**).

## Fonte

CKAN `quadro-economico`: FULL (446,9 MB, fermo al 2026-01-15) + 8 delta mensili
(aprile-novembre 2026, 5-33 MB). 582 MB totali, 9 file.

## Grano e forma dei dati

**1 riga per evento del CIG**, non una serie temporale:

| `descrizione_evento` | righe | CIG | importo contratto |
|---|---:|---:|---:|
| `BASE_ASTA` | 5.874.924 | 5.457.996 | 1.532,4 mld |
| `CONSUNTIVO` | 706.522 | 701.799 | 182,9 mld |
| `VARIANTE` | 355.051 | 251.081 | 389,0 mld |
| `AGGIUDICAZIONE` | 1.175 | 1.153 | 1,0 mld |

Totale clean: **6.937.672 righe**.

Gli importi sono **istantanee cumulative**, non delta: ogni riga porta lo stato
del quadro economico *dopo* quell'evento. Sommare le righe di un CIG è sbagliato;
il confronto si fa prendendo i valori.

`data` è valorizzata **solo per le VARIANTI** (346.529 righe su 355.051): `BASE_ASTA`,
`CONSUNTIVO` e `AGGIUDICAZIONE` hanno sempre data NULL. Non è un dataset
temporale: la sequenza si ricostruisce dagli importi. Per *quando* è successo
serve `varianti` (che ha le date) o `pubblicazioni`.

## Sostituzione: per riga, non per CIG

Il Manuale (§5.1) dice «il delta sostituisce il full per CIG». Qui **non si può**:
nei delta non tutti i CIG vengono ripubblicati con la base d'asta (nel delta di
aprile 2026, **1.555 CIG su 373.687** non hanno `BASE_ASTA`) e la base è proprio
ciò che serve al confronto — sostituire per CIG la cancellerebbe.

Il clean deduplica quindi per **riga intera** (`SELECT DISTINCT`): due righe
identiche sono lo stesso evento ripubblicato da due risorse. Una correzione con
importo diverso resta come riga distinta, e il mart prende il consuntivo o, in
mancanza, il valore massimo osservato.

6.500 CIG restano senza `BASE_ASTA` anche dopo full+delta: presenti solo nei
delta, con varianti o consuntivo e senza il quadro iniziale.

## Cosa misura (e cosa no)

`mart_cig` confronta `importo_base` (lavori+servizi+forniture della `BASE_ASTA`)
con `importo_finale` (il `CONSUNTIVO` se c'è, altrimenti il massimo osservato).
2.202.743 CIG con base > 0; di questi **397.674 (18,1%) hanno il consuntivo**.

| gruppo | n CIG | invariati | negativi | positivi |
|---|---:|---:|---:|---:|
| con consuntivo | 397.674 | 61,4% | **27,3%** (p10 −23,8%) | 11,3% (p90 +1,4%) |
| senza consuntivo | 1.805.069 | 99,1% | 0,0% | 0,9% |

**Attenzione al nome**: questo non è ancora lo «sforamento costi». Il 27,3% di
scostamenti negativi dove c'è il consuntivo è in larga parte il **ribasso**
d'asta: la base è l'importo a base, il consuntivo è quello effettivamente
speso. Per isolare lo sforamento serve confrontare il consuntivo con l'importo
**contrattuale post-ribasso**, che in questo dataset non c'è: `ribasso_aggiudicazione`
sta in `anac-aggiudicazioni`. Il mart che lo fa è un compose
(`quadro-economico` × `aggiudicazioni` × `varianti`), non questo dataset.

## Mart

- `mart_cig`: per CIG+aggiudicazione, importo base/finale, scostamento assoluto e
  percentuale, somme a disposizione, numero di varianti ed eventi, date delle
  varianti (prima/ultima), flag `ha_consuntivo`.
- `mart_eventi`: per tipo di evento, righe, CIG, righe con data, importo mediano,
  medio e totale.

## Difetti della fonte

| difetto | evidenza | trattamento |
|---|---|---|
| `data` NULL fuori dalle varianti | `BASE_ASTA` e `CONSUNTIVO` 0% con data | documentato: nessun filtro sulle date, la sequenza si ricostruisce dagli importi |
| Delta incompleti per CIG | 1.555 CIG senza base nel solo delta di aprile | dedup per riga, non per CIG |
| 573 righe con importi tutti a zero | nel delta di aprile | restano (sono eventi senza importo) |
| 14 righe con importi negativi | storni | restano, il mart prende il massimo |
