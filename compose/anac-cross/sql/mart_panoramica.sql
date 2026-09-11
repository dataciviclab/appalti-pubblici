-- mart_panoramica.sql — KPI aggregati per anno/settore/regione per dashboard overview
-- Grana: anno × settore × regione. Derivato da bandi_gara (2016-2025).

SELECT
    anno_pubblicazione AS anno,
    oggetto_principale_contratto AS settore,
    sezione_regionale AS regione,
    COUNT(*) AS n_lotti,
    COUNT(DISTINCT cig) AS n_cig,
    COUNT(DISTINCT cf_amministrazione_appaltante) AS n_stazioni_appaltanti,
    ROUND(SUM(importo_lotto), 0) AS importo_lotto_totale,
    ROUND(AVG(importo_lotto), 0) AS importo_lotto_medio,
    SUM(CASE WHEN flag_pnrr = TRUE THEN 1 ELSE 0 END) AS n_pnrr,
    ROUND(SUM(CASE WHEN flag_pnrr = TRUE THEN importo_lotto ELSE 0 END), 0) AS importo_pnrr,
    SUM(CASE WHEN esito = 'AGGIUDICATA' THEN 1 ELSE 0 END) AS n_aggiudicati,
    ROUND(SUM(CASE WHEN esito = 'AGGIUDICATA' THEN importo_lotto ELSE 0 END), 0) AS importo_aggiudicati,
    ROUND(SUM(CASE WHEN esito = 'AGGIUDICATA' THEN 1 ELSE 0 END) * 100.0
        / NULLIF(COUNT(*), 0), 1) AS tasso_aggiudicazione_pct,
    ROUND(SUM(CASE WHEN flag_pnrr = TRUE THEN importo_lotto ELSE 0 END) * 100.0
        / NULLIF(SUM(importo_lotto), 0), 1) AS quota_pnrr_pct
FROM read_parquet('{root_posix}/data/clean/anac_bandi_gara/*/*_clean.parquet')
WHERE stato = 'ATTIVO'
  AND oggetto_principale_contratto IS NOT NULL
  AND sezione_regionale IS NOT NULL
GROUP BY anno_pubblicazione, oggetto_principale_contratto, sezione_regionale
ORDER BY anno DESC, importo_lotto_totale DESC
