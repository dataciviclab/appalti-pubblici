# ANAC - SmartCIG (affidamenti sotto soglia)

**Dataset**: `anac_smartcig`
**Fonte**: ANAC - Autorita Nazionale Anticorruzione, portale [dati.anticorruzione.it](https://dati.anticorruzione.it/)
**Protocollo**: CKAN, pattern `smartcig-{year}` con 12 dump mensili (CSV in ZIP)
**Licenza**: CC-BY-SA 4.0

## Contenuto

Affidamenti diretti registrati a sistema come SMARTCIG: la fascia di spesa piu'
numerosa della PA, invisibile in `anac_bandi_gara` (che copre le procedure
sopra soglia). Ogni riga e' un CIG con oggetto, importo, stazione appaltante,
territorio e tipo di scelta del contraente.

- **Oggetto**: `oggetto_gara`, `oggetto_lotto`, `oggetto_principale_contratto`
- **Importi**: `importo_lotto`, `importo_complessivo_gara`, numero lotti
- **Stazione appaltante**: CF, denominazione, AUSA, centro di costo
- **Territorio**: `sezione_regionale`, regione, citta, codice ISTAT comune
- **Comunicazione**: data, anno e mese di comunicazione ANAC

## Copertura

Anno campione **2025** (12 dump mensili). I dataset sono disponibili anche per
2014-2024: il backfill e' il prossimo passo.

| Mese | CIG | Importo |
|---|---|---|
| 2025-01 | 253.245 | 401,5 mln |
| 2025-02 | 11.904 | 17,0 mln |
| 2025-03 | 297.486 | 417,8 mln |
| 2025-04 | 274.724 | 387,1 mln |
| 2025-05 | 296.260 | 413,2 mln |
| 2025-06 | 247.643 | 378,0 mln |
| 2025-07 | 241.374 | 376,9 mln |
| 2025-08 | 136.671 | 216,4 mln |
| 2025-09 | 252.074 | 368,1 mln |
| 2025-10 | 321.845 | 462,5 mln |
| 2025-11 | 300.929 | 439,6 mln |
| 2025-12 | 358.090 | 599,2 mln |

Totale: **2.992.245 CIG**, **25.217 stazioni appaltanti**, **4,48 mld**,
importo mediano **919 EUR**. Zero sovrapposizione di CIG con `anac_bandi_gara`
2025 (verificato: 0 su 1,45M CIG), coerente con la natura parallela del flusso.

## Fasce di importo (2025)

| Fascia | CIG | Quota CIG | Importo | Quota importo |
|---|---|---|---|---|
| micro (< 1.000 EUR) | 1.553.837 | 51,9% | 632,5 mln | 14,1% |
| piccola (1.000-5.000 EUR) | 1.436.955 | 48,0% | 3.831,4 mln | 85,6% |
| media (5.000-40.000 EUR) | 578 | 0,02% | 7,5 mln | 0,17% |
| sopra 40k | 66 | < 0,01% | 6,1 mln | 0,14% |
| non valido (NULL/zero/negativo) | 809 | 0,03% | -0,5 mln | - |

## Schema clean (28 colonne)

`cig`, `numero_gara`, `oggetto_gara`, `oggetto_lotto`,
`oggetto_principale_contratto`, `importo_complessivo_gara`, `importo_lotto`,
`n_lotti_componenti`, `stato`, `data_comunicazione`,
`id_tipo_fattispecie_contrattuale`, `tipo_fattispecie_contrattuale`,
`cod_tipo_scelta_contraente`, `tipo_scelta_contraente`, `codice_ausa`,
`cf_amministrazione_appaltante`, `denominazione_amministrazione_appaltante`,
`sezione_regionale`, `indirizzo`, `istat_comune`, `citta`, `regione`,
`id_centro_costo`, `denominazione_centro_costo`, `anno_comunicazione`,
`mese_comunicazione`, `fascia_importo`, `flag_sopra_140k`.

Grain: **1 riga per CIG**. I dump mensili sono disgiunti, ma se un CIG
ricompare in comunicazioni successive vince la piu' recente.

## Mart

| Mart | Contenuto |
|---|---|
| `mart_annuale` | 1 riga per anno: CIG, SA, importi, distribuzione fasce |
| `mart_fasce` | distribuzione per fascia di importo con quote |
| `mart_top_sa` | profilo delle SA con almeno 5 affidamenti |

## Qualita' e limiti

- **Non e' "sotto 40k": e' un dataset di micro-acquisti.** Il 99,96% degli
  importi e' <= 5.000 EUR; solo 644 CIG superano i 5.000 EUR. Il nome storico
  SMARTCIG non riflette la soglia degli affidamenti diretti (140.000 EUR dal
  2023, D.Lgs. 36/2023).
- **Buco a febbraio 2025**: 11.904 righe contro ~250-320k degli altri mesi.
  Il file sorgente e' anomalo (6 MB contro ~75-170 MB); da segnalare ad ANAC.
- **809 importi non validi** (NULL, zero o negativi): quasi tutti storni o
  correzioni; esclusi dal mart delle fasce.
- **11 CIG sopra 140k** (max 220.000 EUR): oltre il limite di legge per
  l'affidamento diretto, da verificare sul portale ANAC.
- **Colonne assenti**: CPV, flag PNRR, flag urgenza/delega, esito.
  `tipo_fattispecie_contrattuale` e' un valore unico boilerplate, `stato` e'
  sempre `ATTIVO`.
- Il raw CKAN include anche risorse JSON/TTL e un CSV di log: il filtro del
  toolkit scarica solo i 12 ZIP CSV.

## Join

- `cig` -> `anac_bandi_gara`, `anac_aggiudicazioni` (0 overlap atteso)
- `cf_amministrazione_appaltante` -> `anac_sa_ipa` (identita' IPA della SA)
- `istat_comune` -> dimensioni territoriali

## Run

```bash
toolkit run --config datasets/anac-smartcig/dataset.yml
```

Raw: 13 file ZIP (~1,6 GB di CSV concatenato), clean parquet 292 MB,
run completo ~25 min (download incluso).
