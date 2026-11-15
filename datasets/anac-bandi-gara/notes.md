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

Espansione 2007-2025 (19 anni), pattern CKAN `cig-{year}` stabile. Gli header
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

Misura 2016-2025: **192 righe su 6,1 milioni (0,003%) valgono €649,8 mld, il
18,2% del totale**; nel 2024 sono 54 righe per €242 mld (34,9%). Includerle
rendeva inutilizzabili i totali e le classifiche per stazione appaltante.
Il flag non distingue reale da corrotto: è una lista di verifica, non una
correzione.

### Difetti noti della fonte (verificati 2026-11)

| Difetto | Evidenza | Trattamento |
|---|---|---|
| Righe identiche ripetute nello stesso export | dic-2024: 2.799 righe duplicate (1,89%), fino a 10 volte lo stesso CIG | dedup per CIG in clean (vince `data_ultimo_perfezionamento`) |
| Separatori degli importi appiattiti | `9.400.334,903` → `9400334903` (raw ANAC); /1000 riporta 189/189 righe in un range credibile | flag + esclusione dalle somme, nessuna riscrittura |
| `numero_gara` numerico fino al 2023, alfanumerico dal 2024 (`CONSIP_RDO_4955828`) | il parquet cambia tipo per anno e le query cross-anno falliscono | cast a VARCHAR in clean |

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
