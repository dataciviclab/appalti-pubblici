-- mart_competitivita.sql — anno × regione: competitivita del mercato
-- Legge direttamente i clean originali (non lo snapshot CIG).
-- bandi_gara per trend/importi, aggiudicazioni per offerenti/ribassi.

WITH bandi AS (
    SELECT
        cig,
        anno_pubblicazione AS anno,
        sezione_regionale AS regione,
        oggetto_principale_contratto AS settore,
        importo_lotto,
        esito
    FROM read_parquet('{root_posix}/data/clean/anac_bandi_gara/*/*_clean.parquet')
    WHERE stato = 'ATTIVO'
      AND sezione_regionale IS NOT NULL
      AND sezione_regionale != ''
),
agg AS (
    SELECT
        cig,
        num_imprese_offerenti,
        importo_aggiudicazione,
        ribasso_aggiudicazione
    FROM read_parquet('{root_posix}/data/clean/anac_aggiudicazioni/*/*_clean.parquet')
    WHERE importo_aggiudicazione > 0
      AND importo_aggiudicazione < 100000000000
)
SELECT
    b.anno,
    b.regione,
    COUNT(*) AS n_bandi,
    COUNT(DISTINCT b.cig) AS n_cig,
    ROUND(SUM(b.importo_lotto), 0) AS importo_totale,
    SUM(CASE WHEN b.esito = 'AGGIUDICATA' THEN 1 ELSE 0 END) AS n_aggiudicati,
    ROUND(SUM(CASE WHEN b.esito = 'AGGIUDICATA' THEN b.importo_lotto ELSE 0 END), 0) AS importo_aggiudicati,
    ROUND(AVG(a.num_imprese_offerenti), 1) AS offerenti_medi,
    ROUND(AVG(a.ribasso_aggiudicazione), 2) AS ribasso_medio,
    ROUND(SUM(CASE WHEN b.esito = 'AGGIUDICATA' THEN 1 ELSE 0 END) * 100.0
        / NULLIF(COUNT(*), 0), 1) AS tasso_aggiudicazione_pct
FROM bandi b
LEFT JOIN agg a ON b.cig = a.cig
GROUP BY b.anno, b.regione
ORDER BY b.anno DESC, importo_totale DESC
