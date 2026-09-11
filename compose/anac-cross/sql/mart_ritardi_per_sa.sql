-- mart_ritardi_per_sa.sql — SA × settore: ritardi e importi
-- Cross-dataset: legge SAL clean + bandi clean via read_parquet diretto.
-- Base per l'analisi "dove ci sono problemi" nella dashboard intelligence.

WITH sal_ritardo AS (
    SELECT
        cig,
        flag_ritardo,
        n_giorni_scostamento,
        importo_sal
    FROM read_parquet('{root_posix}/data/clean/anac_stati_avanzamento/*/*_clean.parquet')
    WHERE flag_ritardo = 'IN RITARDO'
      AND n_giorni_scostamento IS NOT NULL
),
bandi AS (
    SELECT
        cig,
        MAX(denominazione_amministrazione_appaltante) AS sa,
        MAX(oggetto_principale_contratto) AS settore,
        MAX(sezione_regionale) AS regione
    FROM read_parquet('{root_posix}/data/clean/anac_bandi_gara/*/*_clean.parquet')
    WHERE cf_amministrazione_appaltante IS NOT NULL
      AND cf_amministrazione_appaltante != ''
    GROUP BY cig
)
SELECT
    b.sa,
    b.settore,
    b.regione,
    COUNT(*) AS n_ritardi,
    COUNT(DISTINCT r.cig) AS n_cig_ritardo,
    ROUND(MAX(r.n_giorni_scostamento), 0) AS max_gg_ritardo,
    ROUND(AVG(r.n_giorni_scostamento), 0) AS media_gg_ritardo,
    ROUND(SUM(r.importo_sal), 0) AS importo_ritardo_totale
FROM sal_ritardo r
LEFT JOIN bandi b ON r.cig = b.cig
WHERE b.sa IS NOT NULL AND b.sa != ''
GROUP BY b.sa, b.settore, b.regione
HAVING COUNT(*) >= 3
ORDER BY n_ritardi DESC
