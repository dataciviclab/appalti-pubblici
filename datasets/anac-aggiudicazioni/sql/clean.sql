-- ANAC Aggiudicazioni — CLEAN
-- Macro toolkit: normalize_string, cast_bigint, cast_double, cast_int, decode_flag
SELECT
    normalize_string(cig) AS cig,
    TRY_CAST(data_aggiudicazione_definitiva AS DATE) AS data_aggiudicazione_definitiva,
    esito,
    criterio_aggiudicazione,
    TRY_CAST(data_comunicazione_esito AS DATE) AS data_comunicazione_esito,
    cast_int(numero_offerte_ammesse) AS numero_offerte_ammesse,
    cast_int(numero_offerte_escluse) AS numero_offerte_escluse,
    cast_double(importo_aggiudicazione) AS importo_aggiudicazione,
    cast_double(ribasso_aggiudicazione) AS ribasso_aggiudicazione,
    cast_int(num_imprese_offerenti) AS num_imprese_offerenti,
    decode_flag(flag_subappalto, 'S') AS flag_subappalto,
    cast_bigint(id_aggiudicazione) AS id_aggiudicazione,
    cast_int(cod_esito) AS cod_esito,
    cast_int(num_imprese_richiedenti) AS num_imprese_richiedenti,
    decode_flag(asta_elettronica, 'S') AS asta_elettronica,
    cast_int(num_imprese_invitate) AS num_imprese_invitate,
    cast_double(massimo_ribasso) AS massimo_ribasso,
    cast_double(minimo_ribasso) AS minimo_ribasso,
    -- raw columns pass-through (nullable, schema variabile)
    FLAG_SCOMPUTO,
    cast_double(COD_PRESTAZIONI_COMPRESE) AS COD_PRESTAZIONI_COMPRESE,
    PRESTAZIONI_COMPRESE,
    CIG_PROG_ESTERNA,
    TRY_CAST(DATA_INCARICO_PROG AS DATE) AS DATA_INCARICO_PROG,
    TRY_CAST(DATA_CONS_PROG AS DATE) AS DATA_CONS_PROG,
    cast_double(COD_MODO_RIAGGIUDICAZIONE) AS COD_MODO_RIAGGIUDICAZIONE,
    MODO_RIAGGIUDICAZIONE,
    decode_flag(FLAG_PROC_ACCELERATA, 'S') AS FLAG_PROC_ACCELERATA,
    cast_int(N_MANIF_INTERESSE) AS N_MANIF_INTERESSE
FROM raw_input
WHERE TRY_CAST(data_aggiudicazione_definitiva AS DATE) IS NOT NULL
  AND EXTRACT(YEAR FROM TRY_CAST(data_aggiudicazione_definitiva AS DATE)) BETWEEN 2005 AND 2026
