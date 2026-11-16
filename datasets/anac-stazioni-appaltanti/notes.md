# Note tecniche — anac-stazioni-appaltanti

Anagrafica ANAC delle stazioni appaltanti. Non è un dataset di gare: è la
**chiave di lettura** di tutti gli altri.

## Fonte

CKAN `stazioni-appaltanti` su `dati.anticorruzione.it`:
- 4 risorse, **1 sola CSV** (`stazioni-appaltanti_csv`, 12,9 MB in ZIP)
- nessun delta mensile: è un **FULL ripubblicato** (anagrafica)
- ultima pubblicazione osservata: gennaio 2026
- `delim = ";"`, `quote = '"'`, encoding UTF-8

## Grano e copertura

**1 riga per codice fiscale**: 48.040 righe, 48.040 CF distinti (0 duplicati),
`validate.primary_key: [codice_fiscale]` verde.

Copertura sulle altre fonti: **38.727 delle 39.488 SA presenti nei bandi
(98,1%)**. Il join è su `cf_amministrazione_appaltante`.

## Cosa aggiunge

| campo | a cosa serve |
|---|---|
| `natura_giuridica` (+ codice) | distinguere enti pubblici (20.555), SRL (5.107), altri enti (3.468), PA (3.310), SPA (2.464)… |
| `codice_ausa` | identificativo univoco della SA (AUSA), utile per join stabili |
| `provincia`, `citta`, `indirizzo`, `cap` | localizzazione normalizzata, più pulita del campo `sezione_regionale` dei bandi |
| `stato` | ATTIVO (45.202) / CESSATO (2.838) |
| `data_inizio` | da quando la SA è censita |

## Difetti della fonte (verificati)

| difetto | evidenza | trattamento |
|---|---|---|
| Flag in-house / partecipata / soggetto estero **inutilizzabili** | `flag_inHouse`, `flag_partecipata`, `soggetto_estero` valgono `"false"` su **tutte** le 48.040 righe | restano nel clean (se ANAC li popola, lo schema regge), **esclusi dai mart**: una colonna a zero fisso suggerirebbe «nessun in-house in Italia» |
| `data_fine` = sola sentinella | `2099-12-31` su tutte le righe, anche per le 2.838 cessate | colonna **omessa**: sarebbe sempre NULL. L'informazione è `stato` |
| Righe senza classificazione | 340 (0,7%) senza natura giuridica, 6 senza denominazione | restano nel clean (sono SA vere): `not_null` solo sulla chiave, quote NULL dichiarate in `max_null_pct`; nel mart la natura mancante è `NON DICHIARATA` |
| Riga con un `;` di troppo | 82 righe con 19 campi invece di 18 (un separatore prima di `data_fine`) | il reader con `null_padding` le legge; il campo extra viene scartato |
| P.IVA sentinella | `"00000000000"` sul 52% delle righe (SA senza partita IVA) | `NULL`, non un valore |

## Note di lettura

- L'anagrafica è una **fotografia**: contiene le SA censite oggi, non la storia.
  Una SA cessata resta con `stato = CESSATO`, ma non sappiamo quando.
- Il codice fiscale è la chiave giusta per il join, non la denominazione: la
  stessa SA cambia nome (accorpamenti, fusioni) e nei bandi la denominazione è
  quella al momento della gara.
- `natura_giuridica` è la descrizione pubblicata, non una tassonomia nostra: le
  20 categorie sono quelle ANAC.

## Mart

- `mart_natura`: quante SA per natura giuridica, attive/cessate, quota %.
- `mart_territorio`: quante SA per provincia, comuni distinti, quota %.
