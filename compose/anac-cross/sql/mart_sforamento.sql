-- mart_sforamento.sql — di quanto è cresciuto un contratto rispetto a quello firmato
--
-- Grana: 1 riga per CIG con consuntivo registrato.
--
-- Il pezzo che mancava: `varianti` ha date e motivi ma nessun importo, e
-- `quadro-economico` da solo confronta base d'asta e consuntivo — un confronto
-- che mescola il ribasso (negativo) con le varianti (positive). Qui si toglie
-- il ribasso: l'importo contrattuale e' la base d'asta scontata del ribasso di
-- aggiudicazione, e lo sforamento e' il consuntivo meno quello.
--
-- `{support.quadro_economico.mart}` = `mart_cig` del dataset anac-quadro-economico
-- (prima tabella mart dichiarata): importo base, importo finale, consuntivo,
-- numero di varianti. Non si ricostruisce qui: la regola "consuntivo, altrimenti
-- massimo osservato" vive in un posto solo.

WITH qe AS (
    SELECT * FROM read_parquet('{support.quadro_economico.mart}')
    WHERE ha_consuntivo
      AND importo_base > 0
),

ribasso AS (
    -- Percentuale di ribasso sull'importo a base d'asta. Valori fuori da
    -- [0, 99] sono corruzione della fonte (fino a -37 miliardi): esclusi e
    -- contati nel report, non usati.
    SELECT
        cig,
        max(ribasso_aggiudicazione) AS ribasso_pct
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
        r.ribasso_pct,
        -- importo contrattuale = base d'asta scontata del ribasso
        q.importo_base * (1 - COALESCE(r.ribasso_pct, 0) / 100.0) AS importo_contrattuale,
        q.importo_finale AS importo_consuntivo,
        COALESCE(v.n_varianti_totali, 0) AS n_varianti,
        v.motivi
    FROM qe q
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
    ribasso_pct,
    ROUND(importo_contrattuale, 2) AS importo_contrattuale,
    ROUND(importo_consuntivo, 2) AS importo_consuntivo,
    ROUND(importo_consuntivo - importo_contrattuale, 2) AS sforamento,
    ROUND((importo_consuntivo - importo_contrattuale) * 100.0
        / NULLIF(importo_contrattuale, 0), 2) AS sforamento_pct,
    n_varianti,
    motivi
FROM base
WHERE importo_contrattuale > 0
  AND regione IS NOT NULL
  AND settore IS NOT NULL
ORDER BY sforamento DESC
