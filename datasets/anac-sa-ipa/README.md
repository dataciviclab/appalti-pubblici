# ANAC - IPA: stazione appaltante per CIG

**Dataset**: `anac_sa_ipa`
**Fonti**: ANAC (`anac_bandi_gara`, CF della SA) + AgID Indice PA ([indicepa.gov.it](https://indicepa.gov.it/ipa-dati/dataset/enti))
**Licenza**: CC-BY-4.0 (IPA) / CC-BY-SA 4.0 (ANAC)
**Aggiornamento IPA**: giornaliero

## Contenuto

Bridge CIG -> identita' canonica della stazione appaltante: una riga per CIG con il
codice IPA dell'ente che ha bandito la gara. Serve ad arricchire `anac_cross` (e altri
consumer) con l'identita' univoca della SA senza duplicare le anagrafiche.

- Il CF della SA arriva da `anac_bandi_gara` (2016-2025): le aggiudicazioni ANAC non lo portano.
- I dati IPA (codice, denominazione, tipologia, ISTAT) arrivano dal dump CSV AgID.
- Se un CIG ha piu' bandi vince il piu' recente; se un CF ha piu' codici IPA vince il minore.

## Copertura

Enrichment **parziale**: gli enti fuori perimetro IPA (es. TERNA, Trenitalia, Open Fiber)
non hanno `codice_ipa_sa`, ma restano nel dataset con `cf_sa` e denominazione ANAC.
Sui CIG del compose `anac_cross` la copertura IPA e' ~36% (i CIG senza bando non sono mappabili);
sui CIG presenti in `anac_bandi_gara` e' ~87%.

## Schema

| Colonna | Tipo | Descrizione |
|---|---|---|
| `cig` | VARCHAR | Codice identificativo gara (chiave) |
| `cf_sa` | VARCHAR | Codice fiscale della stazione appaltante (da ANAC) |
| `codice_ipa_sa` | VARCHAR | Codice IPA dell'ente (NULL se fuori IPA) |
| `denominazione_sa` | VARCHAR | Denominazione IPA, fallback ANAC |
| `tipologia_sa` | VARCHAR | Tipologia IPA (Comuni, Gestori di Pubblici Servizi, ...) |
| `codice_istat_sa` | VARCHAR | Codice ISTAT dell'ente secondo IPA |
| `sezione_regionale` | VARCHAR | Sezione regionale ANAC |

## Mart

| Tabella | Contenuto |
|---|---|
| `mart_copertura_sa` | Copertura IPA per sezione regionale e tipologia (n CIG, % con IPA) |

## Note

- Il dump IPA e' posizionale e con righe irregolari: `clean.read.columns` elenca tutte
  le 35 colonne come VARCHAR (preserva gli zeri iniziali, es. `058091`).
- `min_rows` del clean resta 1 per contratto di repo; la copertura si monitora nel mart.
