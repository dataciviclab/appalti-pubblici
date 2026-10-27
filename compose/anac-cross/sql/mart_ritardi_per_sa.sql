-- mart_ritardi_per_sa.sql - SA / settore: ritardi e importi
-- Cross-dataset: legge SAL clean + bandi clean via read_parquet diretto.
-- Base per l'analisi "dove ci sono problemi" nella dashboard intelligence.
-- importo_quota (da clean.sql) evita di sommare piu' volte le serie cumulative (#15).
-- L'importo in ritardo e' attribuito alla serie, non alla singola riga: per le
-- serie cumulative la quota sta sulla riga di picco, quindi sommare solo le righe
-- in ritardo sottostimerebbe il totale.

WITH sal AS (
    SELECT
        cig,
        flag_ritardo,
        n_giorni_scostamento,
        importo_quota,
        COALESCE(CAST(id_aggiudicazione AS VARCHAR), 'cig:' || cig) AS serie_key
    FROM read_parquet('{support.stati_avanzamento.clean}')
),
serie AS (
    SELECT
        cig,
        serie_key,
        SUM(importo_quota) AS importo_serie,
        MAX(CASE WHEN flag_ritardo = 'IN RITARDO' THEN 1 ELSE 0 END) AS in_ritardo
    FROM sal
    GROUP BY cig, serie_key
),
bandi AS (
    SELECT
        cig,
        MAX(denominazione_amministrazione_appaltante) AS sa,
        MAX(oggetto_principale_contratto) AS settore,
        MAX(sezione_regionale) AS regione
    FROM read_parquet('{support.bandi_gara.clean}')
    WHERE cf_amministrazione_appaltante IS NOT NULL
      AND cf_amministrazione_appaltante != ''
    GROUP BY cig
),
ritardi AS (
    SELECT
        b.sa,
        b.settore,
        b.regione,
        COUNT(*) AS n_ritardi,
        COUNT(DISTINCT s.cig) AS n_cig_ritardo,
        ROUND(MAX(s.n_giorni_scostamento), 0) AS max_gg_ritardo,
        ROUND(AVG(s.n_giorni_scostamento), 0) AS media_gg_ritardo
    FROM sal s
    JOIN bandi b ON s.cig = b.cig
    WHERE s.flag_ritardo = 'IN RITARDO'
      AND b.sa IS NOT NULL
      AND b.sa != ''
    GROUP BY b.sa, b.settore, b.regione
),
importi AS (
    SELECT
        b.sa,
        b.settore,
        b.regione,
        ROUND(SUM(se.importo_serie), 0) AS importo_ritardo_totale
    FROM serie se
    JOIN bandi b ON se.cig = b.cig
    WHERE se.in_ritardo = 1
      AND b.sa IS NOT NULL
      AND b.sa != ''
    GROUP BY b.sa, b.settore, b.regione
)
SELECT
    r.sa,
    r.settore,
    r.regione,
    r.n_ritardi,
    r.n_cig_ritardo,
    r.max_gg_ritardo,
    r.media_gg_ritardo,
    COALESCE(i.importo_ritardo_totale, 0) AS importo_ritardo_totale
FROM ritardi r
LEFT JOIN importi i
    ON r.sa = i.sa
   AND r.settore = i.settore
   AND r.regione = i.regione
WHERE r.n_ritardi >= 3
ORDER BY r.n_ritardi DESC
