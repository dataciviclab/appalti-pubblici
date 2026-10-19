-- ANAC Avvio Contratto — CLEAN
-- Macro toolkit: normalize_string, cast_bigint, decode_flag
-- Le date ANAC contengono valori malformati (es. 2710-08-24, 0001-01-01)
-- e slittamenti di 20 anni sull'inizio effettivo. Teniamo solo date
-- plausibili e differenze stipula->inizio tra -365 e 3650 giorni.
WITH src AS (
    SELECT
        normalize_string(cig) AS cig,
        TRY_CAST(NULLIF(data_stipula_contratto, '0001-01-01') AS DATE) AS d_stipula,
        TRY_CAST(NULLIF(data_esecutivita_contratto, '0001-01-01') AS DATE) AS d_esecutivita,
        TRY_CAST(NULLIF(data_termine_contrattuale, '0001-01-01') AS DATE) AS d_termine,
        TRY_CAST(NULLIF(data_verbale_consegna_definitiva, '0001-01-01') AS DATE) AS d_consegna,
        TRY_CAST(NULLIF(data_inizio_effettiva, '0001-01-01') AS DATE) AS d_inizio,
        TRY_CAST(NULLIF(data_verbale_prima_consegna, '0001-01-01') AS DATE) AS d_prima_consegna,
        decode_flag(consegna_frazionata, '1') AS consegna_frazionata,
        decode_flag(consegna_sotto_riserva, '1') AS consegna_sotto_riserva,
        cast_bigint(id_aggiudicazione) AS id_aggiudicazione,
        TRY_CAST(NULLIF(DATA_APPR_PROG_ESE, '0001-01-01') AS DATE) AS d_appr_prog_ese
    FROM raw_input
)

SELECT
    cig,
    CASE WHEN d_stipula BETWEEN DATE '2000-01-01' AND CURRENT_DATE
        THEN d_stipula END AS data_stipula_contratto,
    CASE WHEN d_esecutivita BETWEEN DATE '2000-01-01' AND CURRENT_DATE
        THEN d_esecutivita END AS data_esecutivita_contratto,
    CASE WHEN d_termine BETWEEN DATE '2000-01-01' AND DATE '2060-12-31'
          AND (d_stipula IS NULL OR d_termine >= d_stipula)
        THEN d_termine END AS data_termine_contrattuale,
    CASE WHEN d_consegna BETWEEN DATE '2000-01-01' AND CURRENT_DATE
        THEN d_consegna END AS data_verbale_consegna_definitiva,
    CASE WHEN d_inizio BETWEEN DATE '2000-01-01' AND CURRENT_DATE
          AND (d_stipula IS NULL
               OR date_diff('day', d_stipula, d_inizio) BETWEEN -365 AND 3650)
        THEN d_inizio END AS data_inizio_effettiva,
    CASE WHEN d_prima_consegna BETWEEN DATE '2000-01-01' AND CURRENT_DATE
        THEN d_prima_consegna END AS data_verbale_prima_consegna,
    consegna_frazionata,
    consegna_sotto_riserva,
    id_aggiudicazione,
    CASE WHEN d_appr_prog_ese BETWEEN DATE '2000-01-01' AND CURRENT_DATE
        THEN d_appr_prog_ese END AS data_appr_prog_ese
FROM src
WHERE cig IS NOT NULL
