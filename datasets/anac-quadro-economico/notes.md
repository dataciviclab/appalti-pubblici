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

## Chiave primaria e sostituzione

Il Manuale ANAC v1.4 **§4 (pag. 16)** dichiara la chiave:

```
quadro-economico = Cig + id_aggiudicazione + descrizione_evento + dettaglio_evento
```

`dettaglio_evento` è l'id della variante (347.275 valori distinti su 355.051
righe di `VARIANTE`): senza di lui le varianti collassano in una sola riga.
Nella prima stesura avevo assunto `(cig, id, evento, data)` — sbagliato: le
varianti hanno tutte la stessa data o data NULL.

Sui dati reali la chiave ha **3.625 duplicati** (2.553 con importi diversi): la
fonte le ripubblica corrette nei delta. Il clean tiene la riga della **risorsa
più recente** (`__source_file`), che è la regola del §5.1 applicata alla chiave
del dataset — non al CIG. Prima del fix la clean teneva entrambe le versioni
(6.939.652 righe); dopo, 6.933.965.

## Cosa misura (e cosa no)

`mart_cig` confronta `importo_base` (lavori+servizi+forniture della `BASE_ASTA`)
con `importo_finale` (il `CONSUNTIVO` se c'è, altrimenti il massimo osservato).
2.202.743 CIG con base > 0; di questi **397.674 (18,1%) hanno il consuntivo**.

| gruppo | n CIG | invariati | negativi | positivi |
|---|---:|---:|---:|---:|
| con consuntivo | 397.674 | 61,4% | **27,3%** (p10 −23,8%) | 11,3% (p90 +1,4%) |
| senza consuntivo | 1.805.069 | 99,1% | 0,0% | 0,9% |

### Il triangolo per studiare gli outlier

Confrontando i 5 casi peggiori con le altre due misure di denaro disponibili
(importo di aggiudicazione e somma dei SAL) emerge che **l'outlier non è sempre
il consuntivo**:

| CIG | base | consuntivo | aggiudicazione | SAL |
|---|---:|---:|---:|---:|
| `06472320BE` | 1,55 | **521,86** | 1,44 | **521,86** |
| `6626868877` | 0,88 | **1.062,21** | 0,82 | 1,08 |
| `42315788A0` | 150,0 | **375,0** | 150,0 | — |

Nel primo caso consuntivo e SAL **coincidono** (521,86 mln): il sospetto è la
base d'asta (1,55 mln), non il consuntivo. Cioè il confronto mescola anche la
**grana** (lotto vs opera). 216 CIG su 394.037 (0,05%) hanno consuntivo > 10×
la base: la coda è piccola ma va trattata prima di pubblicare qualunque totale.

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
