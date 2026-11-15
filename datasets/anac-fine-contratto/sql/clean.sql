-- ANAC Fine Contratto — CLEAN
-- Macro toolkit: normalize_string, cast_bigint, cast_int
-- Date plausibili: 2000 -> anno corrente + 1. Il resto diventa NULL.
WITH src AS (
    SELECT
        normalize_string(cig) AS cig,
        normalize_string(cod_motivo_risoluzione) AS cod_motivo_risoluzione,
        normalize_string(motivo_risoluzione) AS motivo_risoluzione,
        normalize_string(cod_motivo_interruzione_anticipata) AS cod_motivo_interruzione_anticipata,
        normalize_string(motivo_interruzione_anticipata) AS motivo_interruzione_anticipata,
        safe_date(NULLIF(data_conclusione_anticipata, '0001-01-01')) AS d_conclusione,
        safe_date(NULLIF(data_effettiva_ultimazione, '0001-01-01')) AS d_ultimazione,
        cast_bigint(id_aggiudicazione) AS id_aggiudicazione,
        cast_int(giorni_proroga) AS giorni_proroga
    FROM (
        -- Sostituzione per CIG (Manuale ANAC §5.1): il delta sostituisce il
        -- full per lo specifico CIG; `__source_file` porta l'ordine risorse.
        SELECT *, max(__source_file) OVER (PARTITION BY cig) AS __fonte_cig
        FROM raw_input
    ) __delta
    WHERE __source_file = __fonte_cig
    -- Dentro la risorsa la fonte puo' ripetere la chiave ufficiale: vince la
    -- comunicazione piu' recente.
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY cig, id_aggiudicazione
        ORDER BY d_ultimazione DESC NULLS LAST
    ) = 1
)

SELECT
    cig,
    cod_motivo_risoluzione,
    motivo_risoluzione,
    cod_motivo_interruzione_anticipata,
    motivo_interruzione_anticipata,
    CASE WHEN d_conclusione BETWEEN DATE '2000-01-01' AND CURRENT_DATE
        THEN d_conclusione END AS data_conclusione_anticipata,
    CASE WHEN d_ultimazione BETWEEN DATE '2000-01-01' AND CURRENT_DATE
        THEN d_ultimazione END AS data_effettiva_ultimazione,
    id_aggiudicazione,
    giorni_proroga
FROM src
WHERE cig IS NOT NULL
