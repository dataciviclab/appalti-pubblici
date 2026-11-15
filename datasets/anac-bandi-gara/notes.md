# Note tecniche — anac-bandi-gara

## Schema raw

| Anno | Formato | Delim | Encoding | Righe clean | Note |
|---|---|---|---|---|---|---|
| 2007 | CSV in ZIP | `;` | UTF-8 | 96.801 | |
| 2008 | CSV in ZIP | `;` | UTF-8 | 140.167 | |
| 2009 | CSV in ZIP | `;` | UTF-8 | 203.293 | |
| 2010 | CSV in ZIP | `;` | UTF-8 | 639.809 | |
| 2011 | CSV in ZIP | `;` | UTF-8 | 1.741.388 | volume anomalo: molti affidamenti sotto soglia |
| 2012 | CSV in ZIP | `;` | UTF-8 | 750.923 | |
| 2013 | CSV in ZIP | `;` | UTF-8 | 540.581 | |
| 2014 | CSV in ZIP | `;` | UTF-8 | 434.253 | |
| 2015 | CSV in ZIP | `;` | UTF-8 | 381.278 | |
| 2016 | CSV in ZIP | `;` | UTF-8 | 332.115 | |
| 2017 | CSV in ZIP | `;` | UTF-8 | 374.234 | |
| 2018 | CSV in ZIP | `;` | UTF-8 | 371.944 | |
| 2019 | CSV in ZIP | `;` | UTF-8 | 369.654 | |
| 2020 | CSV in ZIP | `;` | UTF-8 | 388.451 | |
| 2021 | CSV in ZIP | `;` | UTF-8 | 431.227 | |
| 2022 | CSV in ZIP | `;` | UTF-8 | 490.443 | |
| 2023 | CSV in ZIP | `;` | UTF-8 | 655.125 | |
| 2024 | CSV in ZIP | `;` | UTF-8 | 1.213.524 | raw 1.228.909: 15.385 duplicati rimossi |
| 2025 | CSV in ZIP | `;` | UTF-8 | 1.453.920 | raw 1.475.581: 21.661 duplicati rimossi |
| 2026 | CSV in ZIP (delta `cig`) | `;` | UTF-8 | 1.071.679 | solo `anno_pubblicazione=2026`; 8 delta apr-nov |

Espansione 2007-2026 (20 anni), pattern CKAN `cig-{year}` stabile.

### Il 2026 arriva dai delta `cig`

I pacchetti annuali si fermano al 2025: `cig-2026` non esiste. Dal 2023 ANAC
pubblica un dataset separato `cig` con delta mensili che coprono **tutti** gli
anni, non solo quello corrente. Nel delta di novembre 2026: 69.161 righe 2026,
26.511 nel 2025, 13.639 nel 2024, e una coda fino al 2007.

Misura su cosa cambia nei CIG già noti (delta di novembre 2026):

| anno | CIG toccati | importo cambiato | oggetto cambiato |
|---|---|---|---|
| 2025 | 26.338 | 72 (0,27%) | 36 |
| 2024 | 13.323 | 30 (0,2%) | 58 |
| ≤2023 | ~12.000 | ~40 | ~20 |

Scelta: **si importa solo `anno_pubblicazione = 2026`**, le correzioni storiche
non vengono applicate. Costo misurato: 0,2% degli importi, 0,1% degli oggetti.
Il filtro `anno_pubblicazione = {year}` nel clean rende la partizione coerente
per costruzione.

Dettagli tecnici:

- la sorgente annuale è `optional: true`: per il 2026 il pacchetto non esiste e
  il run prosegue (il toolkit salta la sorgente con un warning);
- la sorgente `cig_delta` ha `year: 2026`, quindi viene scaricata una volta sola;
- i delta hanno virgolette escapate male (`\"SCALA 4\"`): serve
  `clean.read.strict_mode: false`, altrimenti DuckDB scarta ~16mila righe per file. Gli header
dei CSV sono identici (61 colonne) su tutti gli anni: nessun adattamento di
schema, solo la lista `years` in `dataset.yml`. Il 2007 è il primo anno
pubblicato da ANAC (`cig-2006` non esiste).

### Omogeneità della serie (leggere prima di fare trend)

Il dataset BandiCIG dovrebbe coprire solo gli affidamenti sopra i €40k, ma il
perimetro effettivo cambia nel tempo. Importo mediano per lotto:

| Periodo | Mediana per lotto | CIG/anno | Cosa succede |
|---|---|---|---|
| 2007-2009 | €64k-122k | 97k-203k | solo sopra soglia, volumi bassi |
| **2010-2014** | **€1,5k-15k** | 434k-1,74M | entrano gli affidamenti sotto soglia |
| 2015-2023 | €37k-74k | 332k-655k | di nuovo sopra soglia, serie stabile |
| **2024-2025** | **€16,6k-16,8k** | 1,2-1,45M | digitalizzazione: rientrano i micro-contratti |

Due discontinuità, non una: **2010-2014** e **2024-2025**. Il picco 2011 (1,74M
CIG, 944k affidamenti diretti) è un artefatto di perimetro, non un anno record
di spesa. La finestra confrontabile è **2015-2023**; per analisi di lungo
periodo filtrare `tipo_scelta_contraente`, non solo l'anno.

Toolkit v1.44.1: raw QA checka null byte solo nei primi 4 KB.
`sample_size: -1` per evitare auto-detection errata di CIG_COLLEGAMENTO (2017).

## Join testati

- `openga_ricorsi_appalto` su `cig` — già integrato dalla fonte OpenGA
- `bdap_anagrafe_enti` su `cf_amministrazione_appaltante` — chiave CF

## Performance

- Raw: 12 file ZIP mensili per anno → **7,3 GB** totali su 16 anni (37 risorse CKAN per anno, filtrate a 12 CSV)
- Clean parquet: 185MB (2025), 58 colonne (v2: +cig_collegamento, cui_programma, cod_motivo_cancellazione, tipo_appalto_riservato; v3: +flag_importo_sospetto)
- Mart: ~5MB (2025), 611K righe aggregate
- Run time (2025): ~3.5s mart, raw/clean via cache; run completo 16 anni ~25 min con download

## Schema coverage

| Layer | Colonne |
|---|---|
| Raw CSV | 61 |
| Clean | **58** (53 v1 + 4 recuperate v2 + `flag_importo_sospetto`) |
| Non passate | 4 — tutte a bassissima densità (86-99% missing) |

Colonne raw escluse volutamente: `flag_prevalente`, `FLAG_PREV_RIPETIZIONI` (98.7% null), `COD_IPOTESI_COLLEGAMENTO` (86.2% null), `IPOTESI_COLLEGAMENTO` (86.2% null).

## Colonne recuperate (v2, 2026-06-19)

Da issue #514: recuperate 4 colonne raw omesse nello scaffold iniziale.

| Colonna | Missing % | Utilità |
|---|---|---|
| `cig_collegamento` | 99.99% | Tracciare varianti/modifiche tra CIG |
| `cui_programma` | 97.4% | Join con OpenCoesione (CUI) |
| `cod_motivo_cancellazione` | 100% | Codice motivo cancellazione (complementa `motivo_cancellazione` che è sempre NULL) |
| `tipo_appalto_riservato` | 85.3% | Appalti riservati a cooperative sociali, inclusione |

Nota: tutte e 4 hanno alta % null perché sono colonne opzionali del dataset ANAC (varianti, CUI, riserve). I dati presenti sono comunque preziosi per le analisi specifiche.

## Normalizzazioni applicate (v2)

- `motivo_urgenza`: normalizzato con `UPPER()` — eliminati 5 duplicati case-sensitivi
  (es. "non applicabile" / "NON APPLICABILE", "Somma urgenza e protezione civile" / "SOMMA URGENZA E PROTEZIONE CIVILE")
- `funzioni_delegate`: normalizzato con `UPPER()` — eliminati 3 duplicati

## Qualità dati

**`importo_complessivo_gara` è l'importo dell'intera gara, non del lotto**.
Se una gara ha N lotti, l'importo viene ripetuto N volte. Per aggregazioni
usare `importo_lotto`, non `importo_complessivo_gara`.

**Importi elevati — verificare caso per caso**: alcuni importi sopra il
miliardo sono reali (es. `B77825C53E` — €17.37Mld per servizio idrico Puglia
2026-2046, confermato su ANAC), altri sono errati.

Dal 2026-11 gli importi `>= 1 mld` su un singolo lotto sono marcati
`flag_importo_sospetto` e **esclusi dalle aggregazioni** dei mart: il clean
conserva il valore pubblicato (non lo riscrive), `mart_annuale` dichiara il
peso escluso in `n_importi_sospetti` / `importo_sospetti`.

Misura 2007-2026: **1.828 righe su 12,1 milioni (0,015%) valgono €1.021 mld, il
19,2% del totale**; nel 2024 sono 726 righe per €243 mld (35,7%). Includerle
rendeva inutilizzabili i totali e le classifiche per stazione appaltante.
Il flag non distingue reale da corrotto: è una lista di verifica, non una
correzione. Le due firme sono complementari: la soglia sul miliardo prende gli
importi grandi, il rapporto lotto/gara ≥ 10 prende gli appiattimenti piccoli
(2024: 672 righe in più per €0,9 mld).

### Difetti noti della fonte (verificati 2026-11)

| Difetto | Evidenza | Trattamento |
|---|---|---|
| Righe identiche ripetute nello stesso export | dic-2024: 2.799 righe duplicate (1,89%), fino a 10 volte lo stesso CIG | dedup per CIG in clean (vince `data_ultimo_perfezionamento`) |
| Separatori degli importi appiattiti | `9.400.334,903` → `9400334903` (raw ANAC). Lo schema SIMOG ammette `fractionDigits = 3` su `ImportoType`: gli importi a 3 decimali sono legali, è l'export che perde il separatore | flag + esclusione dalle somme, nessuna riscrittura |
| Importi del lotto ≥ 10x l'importo della gara | 1.535 righe appiattite sotto il miliardo (es. `16.236,51` → `1.623.651`) | seconda firma del flag |
| `-1` come sentinella | `ImportoLottoType` ha `minInclusive = -1` nello schema SIMOG: il -1 di 2010-2012 (~10k righe) è ammesso dalla fonte | da escludere dalle somme, non dai conteggi (follow-up) |
| `numero_gara` numerico fino al 2023, alfanumerico dal 2024 (`CONSIP_RDO_4955828`) | il parquet cambia tipo per anno e le query cross-anno falliscono | cast a VARCHAR in clean |
| `data_scadenza_offerta` prima della pubblicazione | 1,5M righe, di cui 1,44M affidamenti diretti | ANAC conferma (risposta PEC 30/07/2026): la scadenza offerte "non ricorre negli affidamenti diretti". Non usare per calcoli di efficienza |

Modello dati di riferimento: `anticorruzione/simog-docs` (XSD 3.04.16) e
`anticorruzione/npa` (`docs/modello-dati/schede/*.yaml`).

### CIG verificati su ANAC 2025 (issue #512)

Verifica completata su file CSV ANAC 2025 (12 mesi).

| CIG | Importo | Ente | Oggetto | Esito |
|-----|---------|------|---------|-------|
| `B77825C53E` | €17,37 Mld | Autorità Idrica Pugliese | Servizio idrico integrato Puglia 2026-2046 | **Reale** (20 anni) |
| `B737822CB8` | €12,62 Mld | CCIAA Cagliari-Oristano | Formazione personale camerale | Errore |
| `B98FB8A800` | €11,09 Mld | Corte dei Conti | Buoni pasto elettronici | Errore |
| `B683A6EB40` | €9,24 Mld | A.O. G. Rummo Benevento | Lotto 13 | Errore |
| `B7A484F39D` | €7,90 Mld | Liceo F. Silvestri | Materiale di consumo | Errore |
| `B8B40BE774` | €6,14 Mld | ASP Agrigento | Emodinamica | Dubbio |
| `B8F7CC264D` | €5,74 Mld | Marina Militare (Tesei) | PA 615 | Dubbio |
| `B66A1238E3` | €5,41 Mld | ASL Salerno | Energia elettrica | Errore |
| `B641EBD927` | €5,21 Mld | Comune Castelguglielmo | Pulizie immobili comunali | Errore |

**Pattern**: 6 CIG su 8 non verificati mostrano enti piccoli (comune, liceo,
CCIAA) con importi miliardari per servizi ordinari (pulizie, formazione,
buoni pasto). Probabile errore di codifica ANAC (decimali/centesimi).
I 2 CIG dubbi (ASP Agrigento e Marina Militare) andrebbero verificati
visivamente sul portale ANAC prima di classificarli come errori.

## Limiti CI

- `pr-toolkit-check.yml` usa `--sample-bytes 5242880`: le risorse ANAC sono ZIP
  da 66-143MB, lo smoke check scarica solo i primi 5MB → ZIP troncato →
  `BadZipFile`. Lo smoke fallisce ma il full run funziona.
