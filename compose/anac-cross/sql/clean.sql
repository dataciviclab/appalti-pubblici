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
        SUM(importo_quota) AS importo_totale_sal,
        SUM(CASE WHEN flag_ritardo = 'IN RITARDO' THEN 1 ELSE 0 END) AS sal_in_ritardo,
        COUNT(DISTINCT COALESCE(CAST(id_aggiudicazione AS VARCHAR), 'cig:' || cig)) AS n_serie_sal,
        COUNT(DISTINCT CASE
            WHEN tipo_serie = 'ambigua'
            THEN COALESCE(CAST(id_aggiudicazione AS VARCHAR), 'cig:' || cig)
        END) AS n_serie_ambigue
    FROM read_parquet('{support.stati_avanzamento.clean}')
    WHERE data_emissione_sal IS NOT NULL
    GROUP BY cig
),

collaudo AS (
    -- Un CIG puo' avere piu' collaudi: tieni il piu' recente (grain 1 riga per CIG).
    SELECT
        cig,
        esito_collaudo,
        data_cert_collaudo,
        riserve_avanzate,
        importo_contenz_risolto
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY cig
                ORDER BY data_cert_collaudo DESC NULLS LAST, esito_collaudo NULLS LAST
            ) AS rn
        FROM read_parquet('{support.collaudo.clean}')
    )
    WHERE rn = 1
),

cup AS (
    -- Un CIG puo' avere piu' CUP: aggrega per evitare la moltiplicazione delle righe.
    SELECT
        cig,
        STRING_AGG(DISTINCT cup, ' | ' ORDER BY cup) AS cup
    FROM read_parquet('{support.cup.clean}')
    WHERE cup IS NOT NULL AND TRIM(cup) != ''
    GROUP BY cig
),

avvio AS (
    -- Un CIG può avere più contratti: prendi la stipula più recente.
    SELECT
        cig,
        data_stipula_contratto,
        data_inizio_effettiva,
        data_termine_contrattuale,
        n_avvii
    FROM (
        SELECT
            cig,
            data_stipula_contratto,
            data_inizio_effettiva,
            data_termine_contrattuale,
            COUNT(*) OVER (PARTITION BY cig) AS n_avvii,
            ROW_NUMBER() OVER (
                PARTITION BY cig
                ORDER BY data_stipula_contratto DESC NULLS LAST
            ) AS rn
        FROM read_parquet('{support.avvio_contratto.clean}')
    ) ranked
    WHERE rn = 1
),

fine AS (
    SELECT
        cig,
        MAX(data_effettiva_ultimazione) AS data_effettiva_ultimazione,
        MAX(data_conclusione_anticipata) AS data_conclusione_anticipata,
        MAX(motivo_risoluzione) AS motivo_risoluzione,
        MAX(motivo_interruzione_anticipata) AS motivo_interruzione_anticipata,
        COUNT(*) AS n_fini
    FROM read_parquet('{support.fine_contratto.clean}')
    GROUP BY cig
),

sospensioni AS (
    SELECT
        cig,
        COUNT(*) AS n_sospensioni,
        SUM(CASE WHEN data_ripresa >= data_sospensione
                  AND date_diff('day', data_sospensione, data_ripresa) <= 3650
             THEN date_diff('day', data_sospensione, data_ripresa) ELSE 0 END)
            AS giorni_sospensione,
        COUNT(*) FILTER (WHERE data_ripresa IS NULL OR data_ripresa < data_sospensione)
            AS n_sospensioni_senza_ripresa
    FROM read_parquet('{support.sospensioni.clean}')
    WHERE data_sospensione IS NOT NULL
    GROUP BY cig
),

varianti AS (
    SELECT
        cig,
        COUNT(*) AS n_varianti,
        COUNT(DISTINCT id_variante) AS n_varianti_distinte,
        COUNT(*) FILTER (WHERE cig_proroga IS NOT NULL) AS n_varianti_con_proroga
    FROM read_parquet('{support.varianti.clean}')
    GROUP BY cig
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
    UNION
    SELECT cig FROM avvio
    UNION
    SELECT cig FROM fine
    UNION
    SELECT cig FROM sospensioni
    UNION
    SELECT cig FROM varianti
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
    COALESCE(sa.n_serie_sal, 0) AS n_serie_sal,
    COALESCE(sa.n_serie_ambigue, 0) AS n_serie_ambigue,
    -- collaudo
    c.esito_collaudo,
    c.data_cert_collaudo,
    c.riserve_avanzate,
    c.importo_contenz_risolto,
    -- CUP
    cu.cup,
    -- avvio contratto
    av.data_stipula_contratto,
    av.data_inizio_effettiva,
    av.data_termine_contrattuale,
    CASE WHEN av.data_stipula_contratto IS NOT NULL
          AND a.data_ultima_agg IS NOT NULL
          AND date_diff('day', a.data_ultima_agg, av.data_stipula_contratto)
              BETWEEN 0 AND 3650
        THEN date_diff('day', a.data_ultima_agg, av.data_stipula_contratto) END
        AS giorni_aggiudicazione_stipula,
    CASE WHEN av.data_stipula_contratto IS NOT NULL AND av.data_inizio_effettiva IS NOT NULL
          AND date_diff('day', av.data_stipula_contratto, av.data_inizio_effettiva)
              BETWEEN -365 AND 3650
        THEN date_diff('day', av.data_stipula_contratto, av.data_inizio_effettiva) END
        AS giorni_stipula_inizio,
    -- fine contratto
    fi.data_effettiva_ultimazione,
    fi.motivo_risoluzione,
    fi.motivo_interruzione_anticipata,
    CASE WHEN av.data_termine_contrattuale IS NOT NULL
          AND fi.data_effettiva_ultimazione IS NOT NULL
          AND date_diff('day', av.data_termine_contrattuale, fi.data_effettiva_ultimazione)
              BETWEEN -3650 AND 3650
        THEN date_diff('day', av.data_termine_contrattuale, fi.data_effettiva_ultimazione) END
        AS giorni_scostamento_termine,
    -- sospensioni
    COALESCE(so.n_sospensioni, 0) AS n_sospensioni,
    COALESCE(so.giorni_sospensione, 0) AS giorni_sospensione,
    COALESCE(so.n_sospensioni_senza_ripresa, 0) AS n_sospensioni_senza_ripresa,
    -- varianti
    COALESCE(va.n_varianti, 0) AS n_varianti,
    COALESCE(va.n_varianti_distinte, 0) AS n_varianti_distinte,
    COALESCE(va.n_varianti_con_proroga, 0) AS n_varianti_con_proroga
FROM tutti_cig t
LEFT JOIN aggiudicazioni a ON t.cig = a.cig
LEFT JOIN aggiudicatari ag ON t.cig = ag.cig
LEFT JOIN partecipanti p ON t.cig = p.cig
LEFT JOIN subappalti su ON t.cig = su.cig
LEFT JOIN sal sa ON t.cig = sa.cig
LEFT JOIN collaudo c ON t.cig = c.cig
LEFT JOIN cup cu ON t.cig = cu.cig
LEFT JOIN avvio av ON t.cig = av.cig
LEFT JOIN fine fi ON t.cig = fi.cig
LEFT JOIN sospensioni so ON t.cig = so.cig
LEFT JOIN varianti va ON t.cig = va.cig
