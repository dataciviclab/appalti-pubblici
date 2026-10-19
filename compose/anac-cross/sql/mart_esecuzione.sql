-- mart_esecuzione.sql — tempi e ritardi reali di esecuzione
-- Grana: anno × regione × settore. Join bandi (attributi) + snapshot CIG
-- (date di avvio/fine, sospensioni, varianti).

WITH bandi AS (
    SELECT
        cig,
        MAX(anno_pubblicazione) AS anno,
        MAX(sezione_regionale) AS regione,
        MAX(oggetto_principale_contratto) AS settore
    FROM read_parquet('{root_posix}/data/clean/anac_bandi_gara/*/*_clean.parquet')
    WHERE cf_amministrazione_appaltante IS NOT NULL
    GROUP BY cig
),

esec AS (
    SELECT *
    FROM clean_input
    WHERE data_stipula_contratto IS NOT NULL
       OR data_effettiva_ultimazione IS NOT NULL
)

SELECT
    b.anno,
    b.regione,
    b.settore,
    COUNT(*) AS n_contratti,
    COUNT(*) FILTER (WHERE e.data_stipula_contratto IS NOT NULL) AS n_con_stipula,
    COUNT(*) FILTER (WHERE e.data_inizio_effettiva IS NOT NULL) AS n_con_inizio,
    COUNT(*) FILTER (WHERE e.data_effettiva_ultimazione IS NOT NULL) AS n_con_ultimazione,
    ROUND(AVG(e.giorni_aggiudicazione_stipula), 0)
        AS giorni_medi_aggiudicazione_stipula,
    ROUND(AVG(e.giorni_stipula_inizio), 0) AS giorni_medi_stipula_inizio,
    ROUND(AVG(e.giorni_scostamento_termine), 0) AS giorni_medi_scostamento_termine,
    COUNT(*) FILTER (WHERE e.giorni_scostamento_termine > 0) AS n_in_ritardo,
    ROUND(COUNT(*) FILTER (WHERE e.giorni_scostamento_termine > 0) * 100.0
        / NULLIF(COUNT(*) FILTER (WHERE e.giorni_scostamento_termine IS NOT NULL), 0), 1)
        AS quota_in_ritardo_pct,
    ROUND(AVG(e.giorni_sospensione), 0) AS giorni_medi_sospensione,
    ROUND(AVG(e.n_varianti), 2) AS varianti_medie
FROM esec e
JOIN bandi b ON e.cig = b.cig
WHERE b.anno IS NOT NULL
GROUP BY b.anno, b.regione, b.settore
HAVING COUNT(*) >= 3
ORDER BY b.anno DESC, n_contratti DESC
