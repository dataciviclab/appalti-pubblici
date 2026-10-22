-- Macro toolkit: cast_int, cast_double, normalize_string
-- Classificazione delle serie SAL per aggiudicazione (#15).
-- importo_sal nella fonte puo' essere cumulativo (valore progressivo) o incrementale
-- (importo del singolo SAL): sommare tutte le righe gonfia i totali.
--   singola      -> un solo SAL
--   incrementale -> valori costanti (rate/installmenti) o oscillanti senza trend: si somma
--   cumulativa   -> serie in crescita: il totale e' il MAX della serie
--   ambigua      -> trend misto: trattata come cumulativa (stima conservativa)
-- Le righe duplicate (stessa data e stesso importo) contano una sola volta.
-- importo_quota e' il contributo attribuito al singolo SAL: il MAX per le serie
-- cumulative/ambigue (sulla riga del picco), l'importo per le incrementali.
WITH base AS (
    SELECT
        normalize_string(cig) AS cig,
        normalize_string(denominazione_sal) AS denominazione_sal,
        normalize_string(flag_ritardo) AS flag_ritardo,
        TRY_CAST(data_emissione_sal AS DATE) AS data_emissione_sal,
        cast_double(importo_sal) AS importo_sal,
        cast_int(n_giorni_scostamento) AS n_giorni_scostamento,
        cast_int(progressivo_sal) AS progressivo_sal,
        cast_int(id_aggiudicazione) AS id_aggiudicazione,
        TRY_CAST(DATA_CERT_PAGAMENTO AS DATE) AS data_cert_pagamento,
        cast_double(IMPORTO_CERT_PAGAMENTO) AS importo_cert_pagamento,
        cast_double(GIORNI_PROROGA) AS giorni_proroga
    FROM raw_input
    WHERE cig IS NOT NULL AND TRIM(cig) != ''
),

serie AS (
    SELECT
        *,
        COALESCE('agg:' || CAST(id_aggiudicazione AS VARCHAR), 'cig:' || cig) AS serie_key
    FROM base
),

righe AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY serie_key, data_emissione_sal, importo_sal
            ORDER BY progressivo_sal NULLS LAST
        ) AS dup_rn
    FROM serie
),

uniche AS (
    SELECT * FROM righe WHERE dup_rn = 1
),

ordinate AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY serie_key
            ORDER BY data_emissione_sal NULLS LAST, progressivo_sal NULLS LAST, importo_sal NULLS LAST
        ) AS rn
    FROM uniche
),

delta AS (
    SELECT
        *,
        importo_sal - LAG(importo_sal) OVER (PARTITION BY serie_key ORDER BY rn) AS importo_delta
    FROM ordinate
),

metriche AS (
    SELECT
        *,
        COUNT(*) OVER (PARTITION BY serie_key) AS n_serie,
        MIN(importo_sal) OVER (PARTITION BY serie_key) AS importo_min,
        MAX(importo_sal) OVER (PARTITION BY serie_key) AS importo_max,
        SUM(CASE WHEN importo_delta > 0 THEN 1 ELSE 0 END)
            OVER (PARTITION BY serie_key) AS n_delta_pos,
        SUM(CASE WHEN importo_delta <> 0 THEN 1 ELSE 0 END)
            OVER (PARTITION BY serie_key) AS n_delta_nonzero,
        SUM(CASE WHEN importo_delta IS NOT NULL AND ABS(importo_delta) <= 0.25 * importo_sal
                 THEN 1 ELSE 0 END)
            OVER (PARTITION BY serie_key) AS n_delta_piccoli
    FROM delta
),

metriche_picco AS (
    SELECT
        *,
        MIN(rn) FILTER (WHERE importo_sal = importo_max) OVER (PARTITION BY serie_key) AS rn_max
    FROM metriche
),

classificata AS (
    SELECT
        *,
        CASE
            WHEN n_serie = 1 THEN 'singola'
            WHEN importo_min = importo_max THEN 'incrementale'
            WHEN n_delta_pos::DOUBLE / NULLIF(n_delta_nonzero, 0) >= 0.8
              OR n_delta_piccoli::DOUBLE / NULLIF(n_serie - 1, 0) >= 0.7 THEN 'cumulativa'
            WHEN n_delta_pos::DOUBLE / NULLIF(n_delta_nonzero, 0) <= 0.4
              AND n_delta_piccoli::DOUBLE / NULLIF(n_serie - 1, 0) < 0.5 THEN 'incrementale'
            ELSE 'ambigua'
        END AS tipo_serie
    FROM metriche_picco
),

quota AS (
    SELECT
        *,
        CASE
            WHEN tipo_serie = 'incrementale' THEN COALESCE(importo_sal, 0)
            WHEN rn = rn_max THEN COALESCE(importo_max, 0)
            ELSE 0
        END AS importo_quota
    FROM classificata
)

SELECT
    r.cig,
    r.denominazione_sal,
    r.flag_ritardo,
    r.data_emissione_sal,
    r.importo_sal,
    r.n_giorni_scostamento,
    r.progressivo_sal,
    r.id_aggiudicazione,
    r.data_cert_pagamento,
    r.importo_cert_pagamento,
    r.giorni_proroga,
    q.tipo_serie,
    CASE WHEN r.dup_rn = 1 THEN q.importo_quota ELSE 0 END AS importo_quota
FROM righe r
LEFT JOIN quota q
    ON r.serie_key = q.serie_key
   AND r.data_emissione_sal IS NOT DISTINCT FROM q.data_emissione_sal
   AND r.importo_sal IS NOT DISTINCT FROM q.importo_sal
