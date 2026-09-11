-- mart_imprese.sql — 1 riga per CF: profilo impresa nelle gare ANAC
-- Aggrega il clean unificato (CIG snapshot) a livello codice_fiscale.
-- Legge da clean_input che contiene tutti i CIG con attributi cross-dataset.

WITH
-- Estrai informazioni imprese dal clean unificato
-- Nota: il clean ha n_aggiudicatari, n_partecipanti, n_subappalti a livello CIG
-- ma non i singoli CF. Per il profilo impresa serve ancora leggere i support.
-- Usiamo il clean come base e aggiungiamo i dati impresa dai support.

impresa_agg AS (
    SELECT
        TRIM(codice_fiscale) AS cf,
        MAX(denominazione) AS denominazione,
        MAX(tipo_soggetto) AS tipo_soggetto,
        COUNT(DISTINCT cig) AS n_aggiudicazioni,
        COUNT(DISTINCT id_aggiudicazione) AS n_lotti_vinti
    FROM read_parquet('{support.aggiudicatari.clean}')
    WHERE codice_fiscale IS NOT NULL AND TRIM(codice_fiscale) != ''
    GROUP BY TRIM(codice_fiscale)
),

impresa_part AS (
    SELECT
        TRIM(codice_fiscale) AS cf,
        MAX(denominazione) AS denominazione,
        MAX(tipo_soggetto) AS tipo_soggetto,
        COUNT(DISTINCT cig) AS n_gare_partecipate
    FROM read_parquet('{support.partecipanti.clean}')
    WHERE codice_fiscale IS NOT NULL AND TRIM(codice_fiscale) != ''
      AND tipo_soggetto NOT ILIKE '%STAZIONE APPALTANTE%'
    GROUP BY TRIM(codice_fiscale)
),

impresa_sub AS (
    SELECT
        TRIM(codice_fiscale) AS cf,
        MAX(denominazione) AS denominazione,
        COUNT(DISTINCT cig) AS n_subappalti
    FROM read_parquet('{support.subappalti.clean}')
    WHERE codice_fiscale IS NOT NULL AND TRIM(codice_fiscale) != ''
    GROUP BY TRIM(codice_fiscale)
),

tutti AS (
    SELECT cf, denominazione, tipo_soggetto, n_aggiudicazioni, n_lotti_vinti,
           NULL::INTEGER AS n_gare_partecipate, NULL::INTEGER AS n_subappalti
    FROM impresa_agg
    UNION ALL
    SELECT cf, denominazione, tipo_soggetto, NULL, NULL,
           n_gare_partecipate, NULL
    FROM impresa_part
    UNION ALL
    SELECT cf, denominazione, NULL, NULL, NULL, NULL, n_subappalti
    FROM impresa_sub
)

SELECT
    cf,
    MAX(denominazione) AS denominazione,
    MAX(tipo_soggetto) AS tipo_soggetto,
    -- aggiudicazioni
    COALESCE(MAX(n_aggiudicazioni), 0) AS n_aggiudicazioni,
    COALESCE(MAX(n_lotti_vinti), 0) AS n_lotti_vinti,
    -- partecipazioni
    COALESCE(MAX(n_gare_partecipate), 0) AS n_gare_partecipate,
    -- subappalti
    COALESCE(MAX(n_subappalti), 0) AS n_subappalti,
    -- ruolo prevalente
    CASE
        WHEN MAX(CASE WHEN n_aggiudicazioni > 0 THEN 1 ELSE 0 END) = 1
            THEN 'aggiudicatario'
        WHEN MAX(CASE WHEN n_subappalti > 0 THEN 1 ELSE 0 END) = 1
            THEN 'subappaltante'
        WHEN MAX(CASE WHEN n_gare_partecipate > 0 THEN 1 ELSE 0 END) = 1
            THEN 'partecipante'
        ELSE 'sconosciuto'
    END AS ruolo_prevalente,
    -- attivita
    GREATEST(
        COALESCE(MAX(n_aggiudicazioni), 0),
        COALESCE(MAX(n_gare_partecipate), 0),
        COALESCE(MAX(n_subappalti), 0)
    ) AS totale_attivita
FROM tutti
GROUP BY cf
ORDER BY totale_attivita DESC
