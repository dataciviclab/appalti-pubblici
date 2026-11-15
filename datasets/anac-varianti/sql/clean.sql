-- ANAC Varianti — CLEAN
-- Macro toolkit: normalize_string, cast_bigint
-- Date plausibili: 2000 -> anno corrente + 1. Il resto diventa NULL.
WITH src AS (
    SELECT
        cast_bigint(id_variante) AS id_variante,
        normalize_string(cod_motivo_variante) AS cod_motivo_variante,
        normalize_string(motivo_variante) AS motivo_variante,
        safe_date(NULLIF(data_approvazione_variante, '0001-01-01')) AS d_approvazione,
        normalize_string(cig) AS cig,
        cast_bigint(id_aggiudicazione) AS id_aggiudicazione,
        normalize_string(CIG_PROROGA) AS cig_proroga,
        safe_date(NULLIF(DATA_ATTO_AGGIUNTIVO, '0001-01-01')) AS d_atto
    FROM (
        -- Sostituzione per CIG (Manuale ANAC §5.1): il delta sostituisce il
        -- full per lo specifico CIG; `__source_file` porta l'ordine risorse.
        SELECT *, max(__source_file) OVER (PARTITION BY cig) AS __fonte_cig
        FROM raw_input
    ) __delta
    WHERE __source_file = __fonte_cig
)

SELECT
    id_variante,
    cod_motivo_variante,
    motivo_variante,
    CASE WHEN d_approvazione BETWEEN DATE '2000-01-01' AND CURRENT_DATE
        THEN d_approvazione END AS data_approvazione_variante,
    cig,
    id_aggiudicazione,
    cig_proroga,
    CASE WHEN d_atto BETWEEN DATE '2000-01-01' AND CURRENT_DATE
        THEN d_atto END AS data_atto_aggiuntivo
FROM src
WHERE cig IS NOT NULL
