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
| `BASE_ASTA` | 5.873.183 | 5.457.996 | 1.532,4 mld |
| `CONSUNTIVO` | 706.316 | 701.799 | 182,9 mld |
| `VARIANTE` | 353.292 | 251.081 | 389,0 mld |
| `AGGIUDICAZIONE` | 1.174 | 1.153 | 1,0 mld |

Totale clean: **6.933.965 righe** (le 3.707 righe in meno rispetto al primo run
sono i duplicati di chiave risolti dal §5.1).

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

`mart_cig` confronta `importo_base` (lavori+servizi+forniture della `BASE_ASTA`,
sommati con `COALESCE`) con `importo_finale` (il `CONSUNTIVO` se c'è, altrimenti
il massimo osservato). **5.611.100 CIG con base > 0**; di questi **682.233
(12,2%) hanno il consuntivo**.

Fino alla issue #33 la somma era senza `COALESCE`: il 62,3% delle righe
`BASE_ASTA` ha almeno un componente NULL, quindi `importo_base` esisteva solo
per 2.202.896 CIG (37,7% dei CIG con una base) e il resto spariva in silenzio.
Il fix porta la copertura al 95,5% delle righe `BASE_ASTA`; il totale con la
coda fuori (`flag_base_sospetta`, 16 righe) è **3.125,9 mld**.

| gruppo | n CIG | invariati | negativi | positivi |
|---|---:|---:|---:|---:|
| con consuntivo, plausibili | 585.363 | 26,3% | **54,5%** (p10 −28,5%) | 18,9% (p90 +8,3%) |

### Il ribasso: la lettura precedente non regge

Il rapporto cons/base **scende** con il ribasso: mediana 1,000 nella fascia 0,
0,989 fra 0-10, 0,905 fra 10-20, 0,817 fra 20-30, **0,715 sopra il 30%**. Il
consuntivo è quindi in buona parte **post-ribasso**, e lo `sforamento` grezzo
(consuntivo − base) misura soprattutto lo sconto: totale −11,69 mld, mediana
−1,0%, 54,5% dei contratti «in risparmio».

Questa nota diceva prima l'opposto («mediana 1,000 in ogni fascia»): era
misurata sul sottoinsieme con tutti i componenti valorizzati — il 37,7% dei CIG,
non rappresentativo. Per questo `mart_sforamento` espone sia `sforamento`
(grezzo) sia `sforamento_scontato` (consuntivo − base scontata del ribasso:
+7,83 mld, mediana 0,0%). La misura canonica è una decisione aperta.

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
