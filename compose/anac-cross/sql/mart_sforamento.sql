-- mart_sforamento.sql — di quanto è cresciuto un contratto rispetto al quadro iniziale
--
-- Grana: 1 riga per (cig, id_aggiudicazione) con consuntivo registrato.
--
-- **Il ribasso entra nel confronto, e va esposto.** La versione precedente di
-- questo header diceva il contrario, «mediana cons/base = 1,000 in ogni fascia»:
-- era misurata su un perimetro sbagliato. `importo_base` esisteva solo per il
-- 37,7% dei CIG (somma senza COALESCE, issue #33) e quel sottoinsieme — i CIG
-- con tutti e tre i componenti valorizzati — non e' rappresentativo. Con il
-- perimetro corretto (95,5% delle righe BASE_ASTA) il segnale si inverte:
--
--   fascia di ribasso   mediana cons/base
--   0                   1,000
--   0-10                0,989
--   10-20               0,905
--   20-30               0,817
--   >30                 0,715
--
-- Il consuntivo e' quindi in buona parte **post-ribasso**. Conseguenza: lo
-- `sforamento` grezzo (consuntivo − base) misura soprattutto lo sconto, non le
-- varianti — totale **−11,69 mld**, mediana −1,0%, e il 54,5% dei contratti
-- "risparmia" invece di sforare.
--
-- Per questo il mart espone **due misure**, e non sceglie in silenzio:
--   - `sforamento` (grezzo, invariato rispetto alle versioni precedenti);
--   - `sforamento_scontato`: consuntivo − base scontata del ribasso
--     (`base_scontata`). Totale **+7,83 mld**, mediana 0,0%, con mediana
--     cons/base_scontata 1,056-1,117 nelle fasce alte: varianti che recuperano
--     parte dello sconto.
-- Quale sia la misura canonica e' una decisione aperta, non un dettaglio, e la
-- scelta **non e' neutra nel tempo**: il ribasso sparisce dal 2023 (la
-- degradazione gia' nota della fonte: dal 2024 `importo_aggiudicazione` e' una
-- copia della base, ribassi > 0 allo 0,2%). Ribasso mediano per anno di
-- pubblicazione, e le due misure:
--
--   anno   n        rib.med   grezzo   scontato   mediana grezza   mediana scontata
--   2008   10.513   14,6%     -0,44    +0,80      -4,0%            +4,9%
--   2013   28.314    6,2%     -0,52    +0,73      -3,0%             0,0%
--   2019   43.059    3,0%     -1,06    +0,23      -3,9%             0,0%
--   2022   57.719    0,6%     -0,92    +0,11      -0,2%             0,0%
--   2024   31.812    0,0%     -0,06    -0,01       0,0%             0,0%
--
-- Quindi: la misura scontata e' una correzione reale **fino al 2022** e un
-- **no-op dal 2023**, dove `base_scontata = base` perche' il ribasso non e' nel
-- dato. La fascia a ribasso 0 della tabella sopra (mediana 1,000) e' per il 30%
-- contratti 2023+ — dove lo sconto manca per dato mancante, non perche' il
-- consuntivo sia pre-ribasso. Conseguenza pratica: **un trend di "sforamento" a
-- cavallo del 2022 non e' interpretabile in nessuna delle due misure**, e il
-- confronto va fatto dentro un periodo omogeneo.
--
-- `plausibile` marca i CIG il cui confronto ha senso; le righe escluse restano
-- nel mart con il motivo, cosi' l'esclusione e' verificabile e non silenziosa.
-- Criteri (misurati in notes.md):
--   - base sotto i 10 mld (`flag_base_sospetta` di mart_cig): la coda della fonte
--   - consuntivo tra 0,5x e 2x la base (fuori: 76.088 e 8.689 CIG)
--   - aggiudicazione non oltre 2x la base (fuori: 2.838 CIG)
-- Le righe senza metadati bandi non sono piu' scartate: restano con
-- motivo 'senza metadati bandi', come le altre escluse.

WITH qe AS (
    SELECT * FROM read_parquet('{support.quadro_economico.mart}')
    WHERE ha_consuntivo
      AND importo_base > 0
),

agg AS (
    -- Per (cig, id_aggiudicazione): sommare per CIG e attaccare il totale a
    -- ogni riga sbaglia il confronto sui CIG con piu' aggiudicazioni.
    SELECT cig, id_aggiudicazione, sum(importo_aggiudicazione) AS importo_aggiudicato
    FROM read_parquet('{support.aggiudicazioni.clean}')
    GROUP BY cig, id_aggiudicazione
),

ribasso AS (
    SELECT cig, max(ribasso_aggiudicazione) AS ribasso_pct
    FROM read_parquet('{support.aggiudicazioni.clean}')
    WHERE ribasso_aggiudicazione BETWEEN 0 AND 99
    GROUP BY cig
),

bandi AS (
    SELECT
        cig,
        max(anno_pubblicazione) AS anno,
        max(sezione_regionale) AS regione,
        max(oggetto_principale_contratto) AS settore,
        max(denominazione_amministrazione_appaltante) AS sa
    FROM read_parquet('{support.bandi_gara.clean}')
    WHERE cf_amministrazione_appaltante IS NOT NULL
      AND NOT flag_importo_sospetto
    GROUP BY cig
),

varianti AS (
    SELECT
        cig,
        count(*) AS n_varianti_totali,
        string_agg(DISTINCT motivo_variante, ' | ' ORDER BY motivo_variante) AS motivi
    FROM read_parquet('{support.varianti.clean}')
    GROUP BY cig
),

base AS (
    SELECT
        q.cig,
        q.id_aggiudicazione,
        b.anno,
        b.regione,
        b.settore,
        b.sa,
        q.importo_base,
        q.importo_finale AS importo_consuntivo,
        a.importo_aggiudicato,
        r.ribasso_pct,
        COALESCE(v.n_varianti_totali, 0) AS n_varianti,
        v.motivi,
        -- Doppio esatto: firma di compilazione (annualita' contro totale, o
        -- duplicazione). Nei CIG senza variante vale il 3,2%, in quelli con
        -- variante lo 0,12%: 27 volte piu' raro, non e' distribuzione naturale.
        abs(q.importo_finale / q.importo_base - 2) < 0.005 AS doppio_esatto,
        CASE
            -- Prima di tutto la coda: una base >= 10 mld (flag da mart_cig) rende
            -- il rapporto senza senso, qualunque sia il consuntivo.
            WHEN q.flag_base_sospetta THEN 'base oltre 10 mld'
            WHEN b.regione IS NULL OR b.settore IS NULL THEN 'senza metadati bandi'
            WHEN q.importo_finale < q.importo_base * 0.5 THEN 'consuntivo sotto 0,5x la base'
            WHEN q.importo_finale > q.importo_base * 2 THEN 'consuntivo oltre 2x la base'
            WHEN a.importo_aggiudicato > q.importo_base * 2 THEN 'aggiudicazione oltre 2x la base'
        END AS motivo_esclusione
    FROM qe q
    LEFT JOIN agg a ON q.cig = a.cig AND q.id_aggiudicazione = a.id_aggiudicazione
    LEFT JOIN ribasso r ON q.cig = r.cig
    LEFT JOIN bandi b ON q.cig = b.cig
    LEFT JOIN varianti v ON q.cig = v.cig
)

SELECT
    cig,
    id_aggiudicazione,
    anno,
    regione,
    settore,
    sa,
    ROUND(importo_base, 2) AS importo_base,
    ROUND(importo_consuntivo, 2) AS importo_consuntivo,
    ROUND(importo_consuntivo - importo_base, 2) AS sforamento,
    ROUND((importo_consuntivo - importo_base) * 100.0 / NULLIF(importo_base, 0), 2) AS sforamento_pct,
    -- Base scontata del ribasso: NULL quando il ribasso non e' noto (5.632
    -- righe, di cui 4.659 plausibili), non 0 — senza ribasso lo sconto non
    -- esiste e fingere 0 direbbe "nessuno sconto" invece di "non lo so".
    ROUND(importo_base * (1 - ribasso_pct / 100.0), 2) AS base_scontata,
    ROUND(importo_consuntivo - importo_base * (1 - ribasso_pct / 100.0), 2)
        AS sforamento_scontato,
    ROUND(
        (importo_consuntivo - importo_base * (1 - ribasso_pct / 100.0)) * 100.0
        / NULLIF(importo_base * (1 - ribasso_pct / 100.0), 0), 2
    ) AS sforamento_scontato_pct,
    ROUND(importo_aggiudicato, 2) AS importo_aggiudicato,
    ribasso_pct,
    n_varianti,
    motivi,
    motivo_esclusione IS NULL AS plausibile,
    motivo_esclusione,
    doppio_esatto
FROM base
ORDER BY sforamento DESC
