-- mart_chi_paga.sql — chi appalta e chi paga, per anno × regione × settore
--
-- Unisce il contratto (`mart_cig`: importo a base d'asta) con le fonti di
-- finanziamento dichiarate (`mart_fonti`: formato lungo, una riga per fonte).
--
-- Le 13 voci ANAC sono raggruppate in 7 macro-categorie leggibili. Gli importi
-- finanziati **non si sommano** agli importi contrattuali: le fonti sono
-- dichiarate per intervento, non per gara (un'opera con molti CIG ripete la
-- stessa fonte). Per questo `rapporto_finanziato_contratto` va letto come
-- indicatore, non come contabilità.
--
-- Solo contratti con una base d'asta e CIG con metadati bandi: il resto
-- (importi zero, CIG senza bando) resta fuori e il conteggio lo dice.
--
-- I contratti con base >= 10 mld sono esclusi dagli aggregati e **contati** in
-- `n_esclusi_importo_sospetto`: è la coda della fonte (separatori appiattiti),
-- la stessa che nei bandi vale `flag_importo_sospetto`. Senza la guardia un
-- solo CIG da 20 mld domina il gruppo anno × regione.
--
-- **I totali di questo mart non sono i totali dei due dataset.** Riconciliazione
-- misurata (novembre 2026, dopo il fix del `COALESCE` in `mart_cig` — issue #33;
-- i valori precedenti erano calcolati sul 37,7% dei contratti e non valgono piu'):
--   contratti: 3.125,9 mld in `mart_cig` (coda sospetta esclusa) = 2.957,2
--     nella popolazione del mart + 168,7 senza metadati bandi; il mart ne
--     pubblica 2.921,2 perche' `HAVING COUNT(*) >= 10` scarta i gruppi piccoli
--     (-36,0 mld, 29.883 contratti).
--   finanziamenti: 4.849,7 mld dichiarati = 3.032,2 con `id_aggiudicazione`
--     + 1.817,5 senza id (non agganciabili a un contratto); dei 3.032,2 solo
--     2.943,3 si agganciano a un contratto della popolazione del mart, e il
--     mart ne pubblica 2.909,4 per la stessa soglia (-33,9 mld).
-- Chi legge 2.909,4 come "quanto e' finanziato in Italia" sbaglia: e' la fetta
-- agganciabile, non il totale dichiarato (4.849,7).

WITH contratti AS (
    SELECT cig, id_aggiudicazione, importo_base, flag_base_sospetta
    FROM read_parquet('{support.quadro_economico.mart}')
    WHERE importo_base > 0
),

fonti AS (
    SELECT cig, id_aggiudicazione, fonte, importo
    FROM read_parquet('{support.fonti_finanziamento.mart}')
),

fin AS (
    SELECT
        cig,
        id_aggiudicazione,
        SUM(importo) AS importo_finanziato,
        SUM(importo) FILTER (WHERE fonte = 'fondi_bilancio_sa') AS fin_bilancio_sa,
        SUM(importo) FILTER (WHERE fonte = 'fondi_bilancio_amministrazione') AS fin_bilancio_amministrazione,
        SUM(importo) FILTER (WHERE fonte = 'entrate_vincolate_ue') AS fin_ue,
        SUM(importo) FILTER (WHERE fonte IN ('entrate_vincolate_statali', 'entrate_vincolate_regionali',
                                             'entrate_vincolate_locali', 'entrate_vincolate_altri')) AS fin_altro_pubblico,
        SUM(importo) FILTER (WHERE fonte = 'mutuo') AS fin_mutuo,
        SUM(importo) FILTER (WHERE fonte IN ('capitali_privati', 'entrate_vincolate_privati',
                                             'sfruttamento_economico')) AS fin_privati,
        SUM(importo) FILTER (WHERE fonte IN ('altro', 'trasferimento_immobili')) AS fin_altro
    FROM fonti
    GROUP BY cig, id_aggiudicazione
),

bandi AS (
    SELECT
        cig,
        MAX(anno_pubblicazione) AS anno,
        MAX(sezione_regionale) AS regione,
        MAX(oggetto_principale_contratto) AS settore,
        MAX(cf_amministrazione_appaltante) AS cf_sa
    FROM read_parquet('{support.bandi_gara.clean}')
    WHERE cf_amministrazione_appaltante IS NOT NULL
      AND NOT flag_importo_sospetto
    GROUP BY cig
),

sa AS (
    SELECT codice_fiscale, natura_giuridica
    FROM read_parquet('{support.stazioni_appaltanti.clean}')
)

SELECT
    b.anno,
    b.regione,
    b.settore,
    COALESCE(sa.natura_giuridica, 'NON IN ANAGRAFICA') AS natura_sa,
    COUNT(*) AS n_contratti,
    COUNT(*) FILTER (WHERE c.flag_base_sospetta) AS n_esclusi_importo_sospetto,
    COUNT(*) FILTER (WHERE f.importo_finanziato IS NOT NULL) AS n_con_fonte,
    ROUND(COUNT(*) FILTER (WHERE f.importo_finanziato IS NOT NULL) * 100.0 / COUNT(*), 1)
        AS quota_con_fonte_pct,
    ROUND(SUM(c.importo_base) FILTER (WHERE NOT c.flag_base_sospetta) / 1e9, 3) AS importo_contrattuale_mld,
    ROUND(SUM(f.importo_finanziato) / 1e9, 3) AS importo_finanziato_mld,
    ROUND(SUM(f.importo_finanziato) FILTER (WHERE NOT c.flag_base_sospetta)
        / NULLIF(SUM(c.importo_base) FILTER (WHERE NOT c.flag_base_sospetta), 0), 2)
        AS rapporto_finanziato_contratto,
    ROUND(SUM(f.fin_bilancio_sa) / 1e9, 3) AS fin_bilancio_sa_mld,
    ROUND(SUM(f.fin_bilancio_amministrazione) / 1e9, 3) AS fin_bilancio_amministrazione_mld,
    ROUND(SUM(f.fin_ue) / 1e9, 3) AS fin_ue_mld,
    ROUND(SUM(f.fin_altro_pubblico) / 1e9, 3) AS fin_altro_pubblico_mld,
    ROUND(SUM(f.fin_mutuo) / 1e9, 3) AS fin_mutuo_mld,
    ROUND(SUM(f.fin_privati) / 1e9, 3) AS fin_privati_mld,
    ROUND(SUM(f.fin_altro) / 1e9, 3) AS fin_altro_mld
FROM contratti c
JOIN bandi b ON c.cig = b.cig
LEFT JOIN fin f ON c.cig = f.cig AND c.id_aggiudicazione = f.id_aggiudicazione
LEFT JOIN sa ON b.cf_sa = sa.codice_fiscale
GROUP BY b.anno, b.regione, b.settore, COALESCE(sa.natura_giuridica, 'NON IN ANAGRAFICA')
HAVING COUNT(*) >= 10
ORDER BY importo_contrattuale_mld DESC
