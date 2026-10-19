-- mart_ritardi_contratto.sql — ritardi reali per stazione appaltante
-- Grana: SA × regione × settore. Ritardo = ultimazione effettiva - termine
-- contrattuale (positivo = oltre il termine).

WITH bandi AS (
    SELECT
        cig,
        MAX(cf_amministrazione_appaltante) AS cf_sa,
        MAX(denominazione_amministrazione_appaltante) AS sa,
        MAX(sezione_regionale) AS regione,
        MAX(oggetto_principale_contratto) AS settore,
        SUM(importo_lotto) AS importo_lotto
    FROM read_parquet('{root_posix}/data/clean/anac_bandi_gara/*/*_clean.parquet')
    WHERE cf_amministrazione_appaltante IS NOT NULL
    GROUP BY cig
),

esec AS (
    SELECT *
    FROM clean_input
    WHERE giorni_scostamento_termine IS NOT NULL
)

SELECT
    b.cf_sa,
    b.sa,
    b.regione,
    b.settore,
    COUNT(*) AS n_contratti,
    COUNT(*) FILTER (WHERE e.giorni_scostamento_termine > 0) AS n_in_ritardo,
    ROUND(COUNT(*) FILTER (WHERE e.giorni_scostamento_termine > 0) * 100.0
        / NULLIF(COUNT(*), 0), 1) AS quota_in_ritardo_pct,
    ROUND(AVG(e.giorni_scostamento_termine), 0) AS giorni_medi_scostamento,
    ROUND(median(e.giorni_scostamento_termine), 0) AS giorni_mediani_scostamento,
    MAX(e.giorni_scostamento_termine) AS giorni_max_scostamento,
    ROUND(SUM(b.importo_lotto), 0) AS importo_lotto_totale,
    ROUND(SUM(CASE WHEN e.giorni_scostamento_termine > 0
        THEN b.importo_lotto ELSE 0 END), 0) AS importo_in_ritardo
FROM esec e
JOIN bandi b ON e.cig = b.cig
WHERE b.cf_sa IS NOT NULL
  AND b.sa IS NOT NULL
GROUP BY b.cf_sa, b.sa, b.regione, b.settore
HAVING COUNT(*) >= 3
ORDER BY n_in_ritardo DESC
