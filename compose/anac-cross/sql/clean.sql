-- clean.sql — ANAC Cross Compose: CIG-level snapshot unificato (2026)
-- Unisce aggiudicazioni + 6 support dataset a livello di CIG.
-- Output: 1 riga per CIG con tutti gli attributi cross-dataset.
-- Questa e' la single source of truth: i mart leggono da questo clean.

WITH
aggiudicazioni AS (
    SELECT
        cig,
        COUNT(DISTINCT id_aggiudicazione) AS n_aggiudicazioni,
        SUM(importo_aggiudicazione) AS importo_totale_agg,
        MAX(data_aggiudicazione_definitiva) AS data_ultima_agg,
        MAX(CASE WHEN flag_subappalto = TRUE THEN 1 ELSE 0 END) AS ha_subappalto_flag,
        SUM(COALESCE(num_imprese_offerenti, 0)) AS totale_offerenti,
        SUM(COALESCE(numero_offerte_ammesse, 0)) AS totale_offerte_ammesse
    FROM raw_input
    WHERE importo_aggiudicazione > 0
      AND importo_aggiudicazione < 100000000000
    GROUP BY cig
),

aggiudicatari AS (
    SELECT
        cig,
        COUNT(DISTINCT codice_fiscale) AS n_aggiudicatari,
        STRING_AGG(DISTINCT denominazione, ' | ' ORDER BY denominazione) AS aggiudicatari
    FROM read_parquet('{support.aggiudicatari.clean}')
    WHERE codice_fiscale IS NOT NULL
      AND TRIM(codice_fiscale) != ''
    GROUP BY cig
),

partecipanti AS (
    SELECT
        cig,
        COUNT(DISTINCT codice_fiscale) AS n_partecipanti
    FROM read_parquet('{support.partecipanti.clean}')
    WHERE codice_fiscale IS NOT NULL
      AND TRIM(codice_fiscale) != ''
    GROUP BY cig
),

subappalti AS (
    SELECT
        cig,
        COUNT(*) AS n_subappalti,
        COUNT(DISTINCT codice_fiscale) AS n_subappaltatori
    FROM read_parquet('{support.subappalti.clean}')
    WHERE codice_fiscale IS NOT NULL
      AND TRIM(codice_fiscale) != ''
    GROUP BY cig
),

sal AS (
    SELECT
        cig,
        COUNT(*) AS n_sal,
        SUM(importo_sal) AS importo_totale_sal,
        SUM(CASE WHEN flag_ritardo = 'S' THEN 1 ELSE 0 END) AS sal_in_ritardo
    FROM read_parquet('{support.stati_avanzamento.clean}')
    WHERE data_emissione_sal IS NOT NULL
    GROUP BY cig
),

collaudo AS (
    SELECT
        cig,
        esito_collaudo,
        data_cert_collaudo,
        riserve_avanzate,
        importo_contenz_risolto
    FROM read_parquet('{support.collaudo.clean}')
),

cup AS (
    SELECT cig, cup
    FROM read_parquet('{support.cup.clean}')
),

-- Tutti i CIG unici da tutte le sorgenti
tutti_cig AS (
    SELECT cig FROM aggiudicazioni
    UNION
    SELECT cig FROM aggiudicatari
    UNION
    SELECT cig FROM partecipanti
    UNION
    SELECT cig FROM subappalti
    UNION
    SELECT cig FROM sal
    UNION
    SELECT cig FROM collaudo
    UNION
    SELECT cig FROM cup
)

SELECT
    t.cig,
    -- aggiudicazioni
    COALESCE(a.n_aggiudicazioni, 0) AS n_aggiudicazioni,
    COALESCE(a.importo_totale_agg, 0) AS importo_totale_agg,
    a.data_ultima_agg,
    COALESCE(a.ha_subappalto_flag, 0) AS ha_subappalto_flag,
    COALESCE(a.totale_offerenti, 0) AS totale_offerenti,
    COALESCE(a.totale_offerte_ammesse, 0) AS totale_offerte_ammesse,
    -- aggiudicatari
    COALESCE(ag.n_aggiudicatari, 0) AS n_aggiudicatari,
    ag.aggiudicatari,
    -- partecipanti
    COALESCE(p.n_partecipanti, 0) AS n_partecipanti,
    -- subappalti
    COALESCE(su.n_subappalti, 0) AS n_subappalti,
    COALESCE(su.n_subappaltatori, 0) AS n_subappaltatori,
    -- SAL
    COALESCE(sa.n_sal, 0) AS n_sal,
    COALESCE(sa.importo_totale_sal, 0) AS importo_totale_sal,
    COALESCE(sa.sal_in_ritardo, 0) AS sal_in_ritardo,
    -- collaudo
    c.esito_collaudo,
    c.data_cert_collaudo,
    c.riserve_avanzate,
    c.importo_contenz_risolto,
    -- CUP
    cu.cup
FROM tutti_cig t
LEFT JOIN aggiudicazioni a ON t.cig = a.cig
LEFT JOIN aggiudicatari ag ON t.cig = ag.cig
LEFT JOIN partecipanti p ON t.cig = p.cig
LEFT JOIN subappalti su ON t.cig = su.cig
LEFT JOIN sal sa ON t.cig = sa.cig
LEFT JOIN collaudo c ON t.cig = c.cig
LEFT JOIN cup cu ON t.cig = cu.cig
