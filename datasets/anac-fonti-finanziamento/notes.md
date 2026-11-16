# Note tecniche — anac-fonti-finanziamento

Con quali soldi è pagata un'opera o un contratto. È il dataset che risponde a
«a carico di chi», che prima restava fuori dai dati del Lab.

## Fonte

CKAN `fonti-finanziamento` su `dati.anticorruzione.it`:
- **FULL** (191,6 MB) + 8 delta mensili (10-18 MB), stesso pattern di `aggiudicazioni`
- `delim = ";"`, `quote = '"'`, UTF-8, un CSV per risorsa (`split_resources`)

## Grano e chiave

**1 riga per (`cig`, `id_aggiudicazione`)** — chiave dal Manuale ANAC v1.4 §4.

Le **13 voci** non sono mutuamente esclusive: un contratto può essere finanziato
da bilancio della stazione appaltante + fondi UE + mutuo insieme. Per questo il
clean ha `totale_fonti`, `n_fonti` e `fonte_prevalente` (la voce più grande), e
il mart è in **formato lungo** — una riga per fonte valorizzata.

| colonna clean | colonna fonte |
|---|---|
| `fondi_bilancio_sa` | `fondi_di_bilancio_della_stazione_appaltante` |
| `fondi_bilancio_amministrazione` | `fondi_di_bilancio_dellamministrazione_competente` |
| `entrate_vincolate_ue` | `entrate_con_dest_vincolata_pubblica_comunitaria` |
| `entrate_vincolate_statali` | `entrate_con_dest_vincolata_pubblica_nazionale_centrale` |
| `entrate_vincolate_locali` | `entrate_con_dest_vincolata_pubblica_nazionale_locale` |
| `entrate_vincolate_regionali` | `entrate_con_dest_vincolata_pubblica_nazionale_regionale` |
| `entrate_vincolate_altri` | `entrate_con_dest_vincolata_pubblica_nazionale_altri` |
| `entrate_vincolate_privati` | `entrate_con_dest_vincolata_privati` |
| `capitali_privati` | `apporto_di_capitali_privati` |
| `mutuo` | `mutuo` |
| `sfruttamento_economico` | `sfruttamento_economico_e_funzionale_del_bene` |
| `trasferimento_immobili` | `trasferimento_di_immobili_ex_art53_c6_dlgs_n163_06_…` |
| `altro` | `altro` |

## Numeri del run (novembre 2026)

| | |
|---|---:|
| righe nel clean | **2.951.569** |
| righe con almeno una fonte | 2.856.342 (96,8%) |
| righe **senza** `id_aggiudicazione` | 517.857 (**17,5%**) |
| CIG/contratti con importi sospetti (≥ 1 mld) | 5.893 |
| totale dichiarato (esclusi i sospetti) | **4.833,8 mld** |
| `n_fonti` mediano | 1 |

**Il totale non è confrontabile col valore dei contratti**: 4.834 mld dichiarati
contro ~1.531 mld di importi contrattuali (`mart_cig`). Le fonti sono dichiarate
per **intervento**, non per contratto: un'opera con più CIG ha la stessa fonte
ripetuta, e l'importo può coprire l'intero progetto.

## Difetti della fonte (verificati sul delta di aprile 2026)

| difetto | evidenza | trattamento |
|---|---|---|
| Chiavi ripubblicate nei delta | **1.650** chiavi duplicate su 228.207 righe (0,7%) | sostituzione per chiave, vince la risorsa più recente (§5.1) |
| **`id_aggiudicazione` mancante** | 517.857 righe (17,5%): dichiarazioni a livello di CIG, senza aggiudicazione registrata | la chiave del Manuale non è applicabile a quelle righe: dedup **per chiave** dove c'è, **per riga intera** dove manca (partizionare per `(cig, NULL)` collasserebbe righe distinte). Per questo il dataset non dichiara `primary_key` |
| Righe senza alcuna fonte | **10.326 (4,5%)**: tutte le voci a zero o NULL | `totale_fonti` = 0 e `fonte_prevalente` NULL: «dato assente», non «finanziato da nessuno» |
| Coda di importi assurdi | stessa classe dei bandi (separatori appiattiti) | `flag_fonti_sospette` (≥ 1 mld dichiarato): il valore resta, il mart lo esclude dalle somme |

## Cosa dice e cosa non dice

**Dice** la composizione *dichiarata* del finanziamento per CIG: bilancio della
SA (la voce più frequente), bilancio dell'amministrazione competente, fondi UE,
entrate vincolate statali/regionali/locali, mutuo, capitali privati.

**Non dice**:
- se i soldi sono stati effettivamente pagati (sono fonti previste, non cassa);
- se gli importi sommano al valore del contratto (spesso no);
- *quale* bilancio, con quali vincoli di destinazione.

### Esempio: il ponte sul Ticino (CUP `I51B07000070001`)

Cosa dice il dataset sui quattro contratti principali:

| CIG | opera | fonte dichiarata | importo |
|---|---|---|---:|
| `02233000FD` | ponte (2008, 31,9 mln aggiudicati) | **bilancio amministrazione competente** | 51,2 mln |
| `8644006B66` | completamento (2021, 3,7 mln) | **entrate vincolate statali** | 7,6 mln |
| `B2EC7C6A2F` | rampe (2024, 7,35 mln) | **bilancio della stazione appaltante** | 12,0 mln |
| `632517210F` | lavori post-alluvione (2016, 1,18 mln) | entrate vincolate altri | 1,43 mln |

La stazione appaltante è la **Provincia di Pavia**, ma il ponte del 2008 non è
finanziato dal suo bilancio: la fonte dichiarata è quella dell'amministrazione
competente. È la differenza tra «chi appalta» e «chi paga» — e prima di questo
dataset il Lab non poteva vederla.

Gli importi sono più alti dei contratti (51,2 contro 31,9): coprono l'intervento,
non la singola gara.

## Mart

`mart_fonti` — formato lungo: `cig`, `id_aggiudicazione`, `fonte`, `importo`,
più `fonte_prevalente` e `n_fonti` dal clean. Solo voci > 0 e importi non
sospetti.
