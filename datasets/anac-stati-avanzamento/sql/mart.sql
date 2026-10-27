-- SAL: ritardi e importi per anno
-- Filtra date corrotte dalla fonte ANAC (pre-2008, post-2026)
-- importo_sal e' cumulativo (scheda SA1 ANAC): importo_quota (calcolato in
-- clean.sql) usa il MAX della serie e evita di sommare piu' volte (#15).
-- Nota: n_serie_anomale e' per (anno, flag_ritardo); una stessa serie puo'
-- comparire in piu' anni, quindi non va sommata tra gruppi come conteggio
-- distinto.
SELECT
    EXTRACT(YEAR FROM data_emissione_sal) AS anno,
    flag_ritardo,
    COUNT(*) AS n_sal,
    COUNT(DISTINCT cig) AS n_cig,
    ROUND(SUM(importo_quota), 0) AS importo_totale,
    COUNT(DISTINCT CASE
        WHEN tipo_serie = 'anomala'
        THEN COALESCE(CAST(id_aggiudicazione AS VARCHAR), 'cig:' || cig)
    END) AS n_serie_anomale,
    ROUND(AVG(n_giorni_scostamento), 0) AS scostamento_medio_giorni
FROM clean_input
WHERE data_emissione_sal IS NOT NULL
  AND EXTRACT(YEAR FROM data_emissione_sal) BETWEEN 2008 AND 2026
GROUP BY anno, flag_ritardo
ORDER BY anno DESC, n_sal DESC
