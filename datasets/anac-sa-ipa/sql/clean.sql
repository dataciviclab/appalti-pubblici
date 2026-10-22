-- Bridge CIG -> identita' canonica della stazione appaltante (IPA).
-- 1 riga per CIG: il CF arriva da anac_bandi_gara, i dati IPA dal dump AgID.
-- Enrichment parziale: i CIG senza bando o con ente fuori IPA restano con IPA NULL.

WITH bandi AS (
    SELECT
        cig,
        cf_sa,
        denominazione_bandi,
        sezione_regionale
    FROM (
        SELECT
            UPPER(TRIM(cig)) AS cig,
            UPPER(TRIM(cf_amministrazione_appaltante)) AS cf_sa,
            TRIM(denominazione_amministrazione_appaltante) AS denominazione_bandi,
            TRIM(sezione_regionale) AS sezione_regionale,
            ROW_NUMBER() OVER (
                PARTITION BY UPPER(TRIM(cig))
                ORDER BY anno_pubblicazione DESC NULLS LAST, data_pubblicazione DESC NULLS LAST
            ) AS rn
        FROM read_parquet('{support.bandi_gara.clean}', union_by_name = true)
        WHERE cig IS NOT NULL AND TRIM(cig) != ''
          AND cf_amministrazione_appaltante IS NOT NULL
          AND TRIM(cf_amministrazione_appaltante) != ''
    )
    WHERE rn = 1
),

ipa AS (
    -- Un CF puo' comparire piu' volte: tieni il codice IPA piu' basso (deterministico).
    SELECT
        cf_sa,
        codice_ipa_sa,
        denominazione_ipa,
        tipologia_sa,
        codice_istat_sa
    FROM (
        SELECT
            UPPER(TRIM(Codice_fiscale_ente)) AS cf_sa,
            UPPER(TRIM(Codice_IPA)) AS codice_ipa_sa,
            TRIM(Denominazione_ente) AS denominazione_ipa,
            TRIM(Tipologia) AS tipologia_sa,
            TRIM(Codice_ISTAT) AS codice_istat_sa,
            ROW_NUMBER() OVER (
                PARTITION BY UPPER(TRIM(Codice_fiscale_ente))
                ORDER BY UPPER(TRIM(Codice_IPA))
            ) AS rn
        FROM raw_input
        WHERE Codice_fiscale_ente IS NOT NULL AND TRIM(Codice_fiscale_ente) != ''
          AND Codice_IPA IS NOT NULL AND TRIM(Codice_IPA) != ''
    )
    WHERE rn = 1
)

SELECT
    b.cig,
    b.cf_sa,
    i.codice_ipa_sa,
    COALESCE(i.denominazione_ipa, b.denominazione_bandi) AS denominazione_sa,
    i.tipologia_sa,
    i.codice_istat_sa,
    b.sezione_regionale
FROM bandi b
LEFT JOIN ipa i ON i.cf_sa = b.cf_sa
