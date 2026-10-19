# ANAC — Avvio Contratto

**Dataset**: `anac_avvio_contratto`
**Fonte**: ANAC — Autorità Nazionale Anticorruzione, [dati.anticorruzione.it](https://dati.anticorruzione.it/)
**Protocollo**: CKAN diretto
**Licenza**: CC BY-SA 4.0

## Contenuto

Date di avvio dell'esecuzione contrattuale: stipula, esecutività, termine
contrattuale, consegna definitiva, inizio effettivo. Collega il momento della
gara all'avvio reale dei lavori/servizi.

## Copertura

| Metrica | Valore |
|---|---|
| Righe (full dump) | 1.925.829 |
| CIG distinti | 1.922.826 |
| Colonne | 11 |
| CSV zippato (full) | ~149 MB |
| Copertura temporale | 2000-2026 |
| Aggiornamento | Mensile (full dump + delta) |

## Schema (11 colonne)

| Colonna | Tipo | Descrizione |
|---|---|---|
| `cig` | VARCHAR | CIG (join con bandi/aggiudicazioni) |
| `data_stipula_contratto` | DATE | Stipula del contratto |
| `data_esecutivita_contratto` | DATE | Esecutività |
| `data_termine_contrattuale` | DATE | Termine contrattuale |
| `data_verbale_consegna_definitiva` | DATE | Verbale di consegna definitiva |
| `data_inizio_effettiva` | DATE | Inizio effettivo |
| `data_verbale_prima_consegna` | DATE | Verbale di prima consegna |
| `consegna_frazionata` | BOOLEAN | Consegna frazionata |
| `consegna_sotto_riserva` | BOOLEAN | Consegna sotto riserva |
| `id_aggiudicazione` | BIGINT | FK aggiudicazioni |
| `data_appr_prog_ese` | DATE | Approvazione progetto esecutivo |

## Join

- `cig` → `anac_bandi_gara`, `anac_aggiudicazioni`
- `id_aggiudicazione` → `anac_aggiudicazioni`

## Limiti

- `data_esecutivita_contratto` è valorizzata solo nel ~21% dei casi.
- Date sentinella `0001-01-01` e date malformate (es. `2710-08-24`) normalizzate
  a NULL: restano solo valori tra 2000 e oggi.
- Un CIG può avere più contratti (fino a 6 righe): nel compose si usa la
  stipula più recente.
