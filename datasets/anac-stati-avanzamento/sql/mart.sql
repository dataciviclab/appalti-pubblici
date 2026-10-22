-- SAL: ritardi e importi per anno
-- Filtra date corrotte dalla fonte ANAC (pre-2008, post-2026)
-- importo_quota (calcolato in clean.sql) evita di sommare piu' volte le serie cumulative (#15).
SELECT
    EXTRACT(YEAR FROM data_emissione_sal) AS anno,
    flag_ritardo,
    COUNT(*) AS n_sal,
    COUNT(DISTINCT cig) AS n_cig,
    ROUND(SUM(importo_quota), 0) AS importo_totale,
    COUNT(DISTINCT CASE
        WHEN tipo_serie = 'ambigua'
        THEN COALESCE(CAST(id_aggiudicazione AS VARCHAR), 'cig:' || cig)
    END) AS n_serie_ambigue,
    ROUND(AVG(n_giorni_scostamento), 0) AS scostamento_medio_giorni
FROM clean_input
WHERE data_emissione_sal IS NOT NULL
  AND EXTRACT(YEAR FROM data_emissione_sal) BETWEEN 2008 AND 2026
GROUP BY anno, flag_ritardo
ORDER BY anno DESC, n_sal DESC
