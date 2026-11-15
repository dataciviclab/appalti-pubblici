-- mart_esecuzione.sql — tempi e ritardi reali di esecuzione
-- Grana: anno × regione × settore.
--
-- Mart-only: legge i support direttamente (modello `pil-intelligence`), senza
-- passare da un clean CIG-level. Le stesse regole del vecchio clean:
-- avvio = stipula piu' recente per CIG, fine = ultimazione piu' recente,
-- sospensioni = somma dei giorni con ripresa entro 3650 giorni.

WITH bandi AS (
    SELECT
        cig,
        MAX(anno_pubblicazione) AS anno,
        MAX(sezione_regionale) AS regione,
        MAX(oggetto_principale_contratto) AS settore
    FROM read_parquet('{support.bandi_gara.clean}')
    WHERE cf_amministrazione_appaltante IS NOT NULL
      AND NOT flag_importo_sospetto
    GROUP BY cig
),

agg AS (
    SELECT
        cig,
        MAX(data_aggiudicazione_definitiva) AS data_ultima_agg
    FROM read_parquet('{support.aggiudicazioni.clean}')
    WHERE importo_aggiudicazione > 0
    GROUP BY cig
),

avvio AS (
    SELECT cig, data_stipula_contratto, data_inizio_effettiva, data_termine_contrattuale
    FROM (
        SELECT
            cig,
            data_stipula_contratto,
            data_inizio_effettiva,
            data_termine_contrattuale,
            ROW_NUMBER() OVER (
                PARTITION BY cig
                ORDER BY data_stipula_contratto DESC NULLS LAST,
                         id_aggiudicazione DESC NULLS LAST
            ) AS rn
        FROM read_parquet('{support.avvio_contratto.clean}')
    ) ranked
    WHERE rn = 1
),

fine AS (
    SELECT
        cig,
        MAX(data_effettiva_ultimazione) AS data_effettiva_ultimazione
    FROM read_parquet('{support.fine_contratto.clean}')
    GROUP BY cig
),

sosp AS (
    SELECT
        cig,
        SUM(CASE WHEN data_ripresa >= data_sospensione
                  AND date_diff('day', data_sospensione, data_ripresa) <= 3650
             THEN date_diff('day', data_sospensione, data_ripresa) ELSE 0 END)
            AS giorni_sospensione
    FROM read_parquet('{support.sospensioni.clean}')
    WHERE data_sospensione IS NOT NULL
    GROUP BY cig
),

var AS (
    SELECT cig, COUNT(*) AS n_varianti
    FROM read_parquet('{support.varianti.clean}')
    GROUP BY cig
),

esec AS (
    SELECT
        t.cig,
        av.data_stipula_contratto,
        av.data_inizio_effettiva,
        fi.data_effettiva_ultimazione,
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
        CASE WHEN av.data_termine_contrattuale IS NOT NULL
              AND fi.data_effettiva_ultimazione IS NOT NULL
              AND date_diff('day', av.data_termine_contrattuale, fi.data_effettiva_ultimazione)
                  BETWEEN -3650 AND 3650
            THEN date_diff('day', av.data_termine_contrattuale, fi.data_effettiva_ultimazione) END
            AS giorni_scostamento_termine,
        COALESCE(s.giorni_sospensione, 0) AS giorni_sospensione,
        COALESCE(v.n_varianti, 0) AS n_varianti
    -- Il vecchio clean teneva solo i CIG con una stipula o un'ultimazione
    -- (`WHERE stipula IS NOT NULL OR ultimazione IS NOT NULL`). Senza questo
    -- filtro la union di `avvio` porta dentro anche i CIG che hanno una riga di
    -- avvio con stipula NULL: 445.332 in piu' contati come "contratti", +22,5%
    -- su n_contratti, senza toccare n_con_stipula / n_con_ultimazione.
    FROM (
        SELECT cig FROM avvio WHERE data_stipula_contratto IS NOT NULL
        UNION
        SELECT cig FROM fine WHERE data_effettiva_ultimazione IS NOT NULL
    ) t
    LEFT JOIN avvio av ON t.cig = av.cig
    LEFT JOIN agg a ON t.cig = a.cig
    LEFT JOIN fine fi ON t.cig = fi.cig
    LEFT JOIN sosp s ON t.cig = s.cig
    LEFT JOIN var v ON t.cig = v.cig
)

SELECT
    b.anno,
    b.regione,
    b.settore,
    COUNT(*) AS n_contratti,
    COUNT(*) FILTER (WHERE e.data_stipula_contratto IS NOT NULL) AS n_con_stipula,
    COUNT(*) FILTER (WHERE e.data_inizio_effettiva IS NOT NULL) AS n_con_inizio,
    COUNT(*) FILTER (WHERE e.data_effettiva_ultimazione IS NOT NULL) AS n_con_ultimazione,
    ROUND(AVG(e.giorni_aggiudicazione_stipula), 0)
        AS giorni_medi_aggiudicazione_stipula,
    ROUND(AVG(e.giorni_stipula_inizio), 0) AS giorni_medi_stipula_inizio,
    ROUND(AVG(e.giorni_scostamento_termine), 0) AS giorni_medi_scostamento_termine,
    COUNT(*) FILTER (WHERE e.giorni_scostamento_termine > 0) AS n_in_ritardo,
    ROUND(COUNT(*) FILTER (WHERE e.giorni_scostamento_termine > 0) * 100.0
        / NULLIF(COUNT(*) FILTER (WHERE e.giorni_scostamento_termine IS NOT NULL), 0), 1)
        AS quota_in_ritardo_pct,
    ROUND(AVG(e.giorni_sospensione), 0) AS giorni_medi_sospensione,
    ROUND(AVG(e.n_varianti), 2) AS varianti_medie
FROM esec e
JOIN bandi b ON e.cig = b.cig
WHERE b.anno IS NOT NULL
GROUP BY b.anno, b.regione, b.settore
HAVING COUNT(*) >= 3
ORDER BY b.anno DESC, n_contratti DESC
