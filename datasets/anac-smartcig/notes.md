# Note tecniche - anac-smartcig

## Schema raw

| Anno | Formato | Delim | Encoding | Righe clean | Note |
|---|---|---|---|---|---|
| 2025 | CSV in ZIP (12 mesi) | `;` | UTF-8 | 2.992.245 | febbraio incompleto (11.904 righe) |

Pattern CKAN `smartcig-{year}`, 37 risorse per anno: 12 CSV (dentro ZIP),
12 JSON, 12 TTL e un CSV di log. `download_all: true` prende solo i CSV/ZIP
e scarta il log (`_is_csv_resource`).

`sample_size: -1` per evitare inferenze premature sui tipi; DuckDB riconosce
gia' come VARCHAR i codici con zeri iniziali (`cf_amministrazione_appaltante`,
`codice_ausa`, `istat_comune`), quindi non serve il mapping posizionale
usato per il dump IPA.

## Join testati

- `anac_bandi_gara` su `cig`: **0 CIG in comune** (2025, 2,99M vs 1,45M).
  SMARTCIG e' un flusso parallelo, non un sottoinsieme dei bandi.
- `anac_aggiudicazioni` su `cig`: atteso 0 (il flusso SMARTCIG non passa
  dalle procedure di aggiudicazione); verifica preliminare su maggio 2025
  gia' fatta nell'issue #2.
- `anac_sa_ipa` su `cf_amministrazione_appaltante`: 25.217 SA distinte.

## Performance

- Raw: 12 ZIP scaricati, CSV concatenato 1,6 GB
- Clean parquet: 292 MB, 28 colonne
- Mart: 23.581 righe totali (top_sa 23.576)
- Run completo (download + clean + mart): ~25 min

Attenzione: ogni run che cambia il `config_hash` riscarica tutti i 12 ZIP
(~2 GB). Durante lo sviluppo sono rimasti file raw duplicati
(`smartcig_{year}_1..3.csv`): cancellare le copie non referenziate da
`metadata.json`.

## Qualita' dati

- `importo_lotto` e' il valore del lotto: 99,96% <= 5.000 EUR. Il limite
  storico dello SMARTCIG (< 40k) non descrive il contenuto reale.
- `importo_complessivo_gara` ripete il totale della gara su ogni lotto
  (come nei bandi): per aggregazioni usare `importo_lotto`.
- 809 righe con importo NULL/zero/negativo (storni): `fascia_importo =
  'non_valido'`, escluse da `mart_fasce`.
- 11 CIG oltre 140k (max 220.000 EUR): fuori soglia per l'affidamento
  diretto, da verificare.
- 141 righe senza CF/denominazione SA; 66.911 senza regione (2,2%), 66.728
  senza ISTAT comune.
- `stato` sempre `ATTIVO`, `tipo_scelta_contraente` sempre
  `AFFIDAMENTO DIRETTO`, `tipo_fattispecie_contrattuale` unico valore.

## Buco febbraio 2025

Il dump `smartcig_csv_2025_02.zip` contiene 11.904 righe (6,4 MB di CSV)
contro 241-358k degli altri mesi. Anche il peso del file e' anomalo
(1,5 MB di ZIP contro 18-45 MB). Il buco e' nella fonte, non nella pipeline:
va segnalato ad ANAC e monitorato al prossimo aggiornamento.

## Warning clean

Tre warning non bloccanti dal check "numeric-suggestive name":
`id_centro_costo` e `denominazione_centro_costo` (nomi ereditati da ANAC) e
`fascia_importo` (contiene "importo" ma e' una categoria). Gli stessi warning
sono presenti in `anac_bandi_gara`.

## Limiti CI

`pr-toolkit-check.yml` usa `--sample-bytes`: i ZIP ANAC troncati producono
`BadZipFile` nello smoke check. Il run completo funziona.
