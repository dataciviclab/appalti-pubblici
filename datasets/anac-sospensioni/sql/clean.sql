-- ANAC Sospensioni — CLEAN
-- Macro toolkit: normalize_string, cast_bigint
-- Date plausibili: 2000 -> anno corrente + 1. Il resto diventa NULL.
WITH src AS (
    SELECT
        normalize_string(cig) AS cig,
        TRY_CAST(NULLIF(data_sospensione, '0001-01-01') AS DATE) AS d_sospensione,
        TRY_CAST(NULLIF(data_ripresa, '0001-01-01') AS DATE) AS d_ripresa,
        normalize_string(descrizione_motivo) AS descrizione_motivo,
        cast_bigint(id_aggiudicazione) AS id_aggiudicazione
    FROM raw_input
)

SELECT
    cig,
    CASE WHEN d_sospensione BETWEEN DATE '2000-01-01' AND CURRENT_DATE
        THEN d_sospensione END AS data_sospensione,
    CASE WHEN d_ripresa BETWEEN DATE '2000-01-01' AND CURRENT_DATE
        THEN d_ripresa END AS data_ripresa,
    descrizione_motivo,
    id_aggiudicazione
FROM src
WHERE cig IS NOT NULL
