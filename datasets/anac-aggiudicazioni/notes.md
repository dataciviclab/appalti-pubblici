# Note tecniche — anac-aggiudicazioni

## Struttura fonte

CKAN dataset `aggiudicazioni` su dati.anticorruzione.it:
- Full dump: risorsa `aggiudicazioni_csv` (~759MB ZIP)
- Delta mensili: risorse `YYYYMMDD-aggiudicazioni_csv` (XXX MB)
- Senza DataStore — download diretto CSV via filesystem API

Config scelta: **full + delta** via `download_all: true` + `split_resources: true`,
con sostituzione per CIG nel clean.

> **Correzione 2026-11-15.** La config precedente leggeva solo il full
> (`resource_name: "aggiudicazioni_csv"`), sul presupposto che fosse cumulativo.
> Non lo è: il full ha `last_modified = 2026-01-15` e da aprile 2026 gli
> aggiornamenti arrivano solo nei delta `YYYYMMDD-aggiudicazioni_csv`.
> Effetto misurato: dataset fermo a metà gennaio 2026, ~300mila aggiudicazioni
> mancanti solo nel primo trimestre (il delta di aprile contiene 98.421 record
> di febbraio e 103.491 di marzo).

**Regola di merge (Manuale open data ANAC v1.4 §5.1):** «tutte le informazioni
contenute nel delta vanno acquisite nella loro totalità, sostituendo quanto
acquisito in precedenza dalla risorsa full **per lo specifico CIG**».

Implementazione:

- `split_resources: true` → un file raw per risorsa, nominato `00-...` (full) e
  `01-...`, `02-...` (delta in ordine di `last_modified`);
- `clean.read.source_file: true` → `__source_file` in `raw_input`;
- nel clean: `WHERE __source_file = max(__source_file) OVER (PARTITION BY cig)`;
- dentro la risorsa vince la chiave primaria ufficiale (`cig` + `id_aggiudicazione`,
  Manuale §4) ordinata per `data_comunicazione_esito` discendente.

Il full contiene già righe identiche ripetute (6.760 coppie `(cig, id_aggiudicazione)`
su 4,8M) e i delta ripubblicano interi CIG con id sintetici negativi: entrambi i
casi sono coperti da queste due regole.

`raw.output_policy: overwrite` è obbligatorio con `split_resources`: il default
`versioned` accumulerebbe `00-..._1`, `00-..._2` a ogni run.

**Tre limiti noti della regola per CIG** (misurati, non corretti):

1. **Il filtro sulla data gira prima della finestra di sostituzione.** Nel clean
   `WHERE safe_date(data_aggiudicazione_definitiva) IS NOT NULL …` sta dentro la
   subquery che sceglie la risorsa vincente: una riga di delta con data NULL
   non partecipa mai, quindi per quel CIG resta la riga vecchia del full invece
   dell'aggiornamento. Non corrompe, ma «il delta vince» non vale per gli
   aggiornamenti senza data.
2. **La sostituzione può perdere qualche riga.** Per 490 CIG di `partecipanti`
   (su 767.526 condivisi, 0,06%) e 1.816 di `aggiudicatari` (0,25%) il delta ha
   meno righe del full: la regola del Manuale sostituisce, quindi quelle righe
   spariscono. È il verso giusto (l'alternativa `(cig, id)` produrrebbe ~507mila
   duplicati dai soli id sintetici), ma è una perdita silenziosa.
3. **Coerente con la scelta di non applicare le correzioni storiche**: i delta
   riemettono anche record di anni passati, e per quei CIG vince il delta.

## Schema osservato

Dal delta CSV `20260701-aggiudicazioni_csv.csv` (190.829 righe):

Colonne raw (CSV, delim `;`, quoted `"`):
cig, data_aggiudicazione_definitiva, esito, criterio_aggiudicazione,
data_comunicazione_esito, numero_offerte_ammesse, numero_offerte_escluse,
importo_aggiudicazione, ribasso_aggiudicazione, num_imprese_offerenti,
flag_subappalto, id_aggiudicazione, cod_esito, num_imprese_richiedenti,
asta_elettronica, num_imprese_invitate, massimo_ribasso, minimo_ribasso,
FLAG_SCOMPUTO, COD_PRESTAZIONI_COMPRESE, PRESTAZIONI_COMPRESE,
CIG_PROG_ESTERNA, DATA_INCARICO_PROG, DATA_CONS_PROG,
COD_MODO_RIAGGIUDICAZIONE, MODO_RIAGGIUDICAZIONE,
FLAG_PROC_ACCELERATA, N_MANIF_INTERESSE

## Join chain

anac_bandi_gara (cig) ←→ anac_aggiudicazioni (cig)
anac_aggiudicazioni (id_aggiudicazione) ←→ aggiudicatari (id_aggiudicazione)

Note: id_aggiudicazione con valori negativi (-1, -2xxxx) indica
aggiudicazioni senza corrispondenza in anagrafica aggiudicatari.

## Warning ANAC WAF

Il portale dati.anticorruzione.it blocca richieste senza User-Agent browser.
Già risolto in anac-bandi-gara con `client.user_agent` config.

## Qualità dati (run 2026-11-15, full + delta)

| Metrica | Solo full (fino al 2026-11-15) | Full + delta (dopo la correzione) |
|---|---|---|
| Righe totali | 4.817.672 | **5.786.635** |
| Importo totale | €3.882,9 Mld | **€4.198,7 Mld** |
| Aggiudicazioni 2024 | 1.146.584 / €448,2 Mld | 1.174.960 / €433,2 Mld |
| Aggiudicazioni 2025 | 1.219.225 / €405,9 Mld | 1.283.816 / €473,9 Mld |
| Aggiudicazioni 2026 | 16.666 | **877.419** (gen-set) |

Sui **SAL** il confronto va fatto a parità di filtro: le 149.666 righe sono
`data_emissione_sal >= 2026-01-01` (e includono 284 date future, fino al 2062);
per anno di emissione = 2026 sono **149.382**, contro le 929 di prima. Le 284
future sono refusi plausibili che `safe_date` non intercetta: l'audit le elenca
come avviso.

Il 2026 passa da 16mila a 877mila righe: è la parte che i delta coprono. Il
mese **parziale è gennaio** (il full si ferma al 15/1): febbraio e marzo sono
pieni, perché il primo delta utile li contiene. Non c'è nessun buco feb-mar.
Il 2024 scende leggermente perché per i CIG ripubblicati dai delta vale la
versione del delta (regola ANAC), non quella del full.

**Anomalie note:**
- date con anno impossibile (5, 7436, 9202): scartate dal filtro 2005-2026
- **571** aggiudicazioni con `data_aggiudicazione_definitiva` successiva a oggi,
  di cui **158** datate esattamente `2026-12-31` (placeholder ricorrente). Non
  filtrate: l'audit controlla le date a livello di anno, e queste sono
  formalmente nel 2026: le contiamo qui, il report dell'audit non le distingue
- importi ≥ 1 mld: 336 righe per €1.503,8 Mld — stessa corruzione dei bandi
  (separatori appiattiti). Da flaggare anche qui (follow-up).
- **`importo_aggiudicazione` cambia comportamento nel 2024.** Fino al 2023 è
  un prezzo: coincide col lotto nel 38-63% dei casi e nel 3-6% ha un ribasso
  > 0. Dal 2024 è una copia della base: 96,5% identico nel 2024, 97,1% nel
  2025, 98,3% nel 2026, con ribasso > 0 sceso a 0,2%. Su gare a lotto unico:

  | anni | identico alla base (±1%) | con ribasso > 0 |
  |---|---:|---:|
  | 2007-2010 | 38-53% | 2-4% |
  | 2011-2023 | 43-63% | 3-6% |
  | 2024 | 96,5% | 0,2% |
  | 2025-2026 | 97-98% | 0,1-0,2% |

  Conseguenza: il prezzo di aggiudicazione non è ricostruibile dal 2024
  (`base × (1−ribasso)` darebbe la base), e le analisi su prezzo e ribasso
  sono confrontabili solo **fino al 2023**. Non è correggibile a valle: è la
  fonte che ha smesso di pubblicare i due campi distinti.
- 69% dei record senza criterio di aggiudicazione (NULL)
