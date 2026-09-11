-- mart_lifecycle.sql — Bandi 2016-2025 LEFT JOIN CIG snapshot 2026 (clean)
-- La snapshot 2026 e' il clean stesso: 1 riga per CIG con tutti gli attributi.
-- I bandi 2016-2025 restano da fonte esterna (bandi_gara clean parquet).

WITH
snapshot AS (
    SELECT * FROM clean_input
),

bandi AS (
    SELECT
        cig,
        anno_pubblicazione AS anno,
        mese_pubblicazione,
        COALESCE(oggetto_lotto, oggetto_gara) AS oggetto,
        denominazione_amministrazione_appaltante AS stazione_appaltante,
        sezione_regionale AS regione,
        oggetto_principale_contratto AS settore,
        importo_lotto,
        stato,
        esito,
        flag_pnrr,
        tipo_scelta_contraente,
        descrizione_cpv,
        data_pubblicazione
    FROM read_parquet('{root_posix}/data/clean/anac_bandi_gara/*/*_clean.parquet')
)

SELECT
    b.cig,
    b.anno,
    b.mese_pubblicazione,
    b.oggetto,
    b.stazione_appaltante,
    b.regione,
    b.settore,
    b.importo_lotto,
    b.stato,
    b.esito,
    b.flag_pnrr,
    b.tipo_scelta_contraente,
    b.descrizione_cpv,
    b.data_pubblicazione,
    s.n_aggiudicazioni,
    s.importo_totale_agg,
    s.data_ultima_agg,
    s.n_aggiudicatari,
    s.aggiudicatari,
    s.n_partecipanti,
    s.n_subappalti,
    s.n_sal,
    s.importo_totale_sal,
    s.sal_in_ritardo,
    s.esito_collaudo,
    s.data_cert_collaudo,
    s.riserve_avanzate,
    s.cup
FROM bandi b
LEFT JOIN snapshot s ON b.cig = s.cig
