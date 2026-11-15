-- ANAC Aggiudicazioni — CLEAN
-- Macro toolkit: normalize_string, cast_bigint, cast_double, cast_int, decode_flag
SELECT
    normalize_string(cig) AS cig,
    safe_date(data_aggiudicazione_definitiva) AS data_aggiudicazione_definitiva,
    esito,
    criterio_aggiudicazione,
    safe_date(data_comunicazione_esito) AS data_comunicazione_esito,
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
    safe_date(DATA_INCARICO_PROG) AS DATA_INCARICO_PROG,
    safe_date(DATA_CONS_PROG) AS DATA_CONS_PROG,
    cast_double(COD_MODO_RIAGGIUDICAZIONE) AS COD_MODO_RIAGGIUDICAZIONE,
    MODO_RIAGGIUDICAZIONE,
    decode_flag(FLAG_PROC_ACCELERATA, 'S') AS FLAG_PROC_ACCELERATA,
    cast_int(N_MANIF_INTERESSE) AS N_MANIF_INTERESSE
FROM (
    -- Provenienza per riga: `00-...` e' il full, `01-...`/`02-...` i delta
    -- mensili in ordine cronologico (split_resources nel raw). La regola ANAC
    -- (Manuale open data §5.1) e' per CIG: il delta sostituisce integralmente
    -- quanto il full diceva di quel CIG.
    SELECT *, max(__source_file) OVER (PARTITION BY cig) AS __fonte_cig
    FROM raw_input
    WHERE safe_date(data_aggiudicazione_definitiva) IS NOT NULL
      AND EXTRACT(YEAR FROM safe_date(data_aggiudicazione_definitiva)) BETWEEN 2005 AND 2026
) AS r
WHERE __source_file = __fonte_cig
-- Dentro la stessa risorsa la fonte puo' ripetere la riga: chiave primaria
-- ufficiale (Manuale §4) = (cig, id_aggiudicazione), vince la comunicazione
-- piu' recente.
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY cig, id_aggiudicazione
    ORDER BY safe_date(data_comunicazione_esito) DESC NULLS LAST,
             safe_date(data_aggiudicazione_definitiva) DESC NULLS LAST
) = 1
