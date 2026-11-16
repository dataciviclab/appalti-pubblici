-- ANAC fonti di finanziamento — CLEAN
-- Macro toolkit: normalize_string, cast_bigint, cast_double
--
-- Grano: 1 riga per (cig, id_aggiudicazione) con le 13 voci di finanziamento.
-- Chiave dal Manuale ANAC v1.4 §4. Le voci NON sono mutuamente esclusive: un
-- contratto può essere finanziato da bilancio della stazione appaltante + UE +
-- mutuo insieme. Per questo esiste `totale_fonti` e il mart in formato lungo.
WITH base AS (
    SELECT * FROM raw_input
),

-- La chiave del Manuale e' (cig, id_aggiudicazione), ma il 17,5% delle righe
-- non ha `id_aggiudicazione`: sono dichiarazioni di finanziamento a livello di
-- CIG, senza un'aggiudicazione registrata. Su quelle righe la chiave non
-- esiste, e partizionare per (cig, NULL) collasserebbe righe distinte.
-- Quindi due dedup: per chiave dove c'e', per riga intera dove manca.
con_id AS (
    SELECT * EXCLUDE (rn)
    FROM (
        SELECT *, ROW_NUMBER() OVER (
            PARTITION BY cig, id_aggiudicazione ORDER BY __source_file DESC
        ) AS rn
        FROM base
        WHERE id_aggiudicazione IS NOT NULL
    )
    WHERE rn = 1
),

senza_id AS (
    SELECT * EXCLUDE (rn)
    FROM (
        SELECT *, ROW_NUMBER() OVER (
            PARTITION BY cig,
                entrate_con_dest_vincolata_pubblica_nazionale_regionale,
                trasferimento_di_immobili_ex_art53_c6_dlgs_n163_06_economia_su_stanziamenti_non_vincolati,
                fondi_di_bilancio_dellamministrazione_competente, mutuo,
                entrate_con_dest_vincolata_pubblica_nazionale_centrale,
                entrate_con_dest_vincolata_pubblica_nazionale_locale, altro,
                entrate_con_dest_vincolata_pubblica_nazionale_altri,
                apporto_di_capitali_privati,
                sfruttamento_economico_e_funzionale_del_bene,
                fondi_di_bilancio_della_stazione_appaltante,
                entrate_con_dest_vincolata_pubblica_comunitaria,
                entrate_con_dest_vincolata_privati
            ORDER BY __source_file DESC
        ) AS rn
        FROM base
        WHERE id_aggiudicazione IS NULL
    )
    WHERE rn = 1
),

dedup AS (
    SELECT * FROM con_id UNION ALL SELECT * FROM senza_id
),

fonti AS (
    SELECT
        normalize_string(cig) AS cig,
        cast_bigint(id_aggiudicazione) AS id_aggiudicazione,
        COALESCE(cast_double(entrate_con_dest_vincolata_pubblica_nazionale_regionale), 0) AS entrate_vincolate_regionali,
        COALESCE(cast_double(trasferimento_di_immobili_ex_art53_c6_dlgs_n163_06_economia_su_stanziamenti_non_vincolati), 0) AS trasferimento_immobili,
        COALESCE(cast_double(fondi_di_bilancio_dellamministrazione_competente), 0) AS fondi_bilancio_amministrazione,
        COALESCE(cast_double(mutuo), 0) AS mutuo,
        COALESCE(cast_double(entrate_con_dest_vincolata_pubblica_nazionale_centrale), 0) AS entrate_vincolate_statali,
        COALESCE(cast_double(entrate_con_dest_vincolata_pubblica_nazionale_locale), 0) AS entrate_vincolate_locali,
        COALESCE(cast_double(altro), 0) AS altro,
        COALESCE(cast_double(entrate_con_dest_vincolata_pubblica_nazionale_altri), 0) AS entrate_vincolate_altri,
        COALESCE(cast_double(apporto_di_capitali_privati), 0) AS capitali_privati,
        COALESCE(cast_double(sfruttamento_economico_e_funzionale_del_bene), 0) AS sfruttamento_economico,
        COALESCE(cast_double(fondi_di_bilancio_della_stazione_appaltante), 0) AS fondi_bilancio_sa,
        COALESCE(cast_double(entrate_con_dest_vincolata_pubblica_comunitaria), 0) AS entrate_vincolate_ue,
        COALESCE(cast_double(entrate_con_dest_vincolata_privati), 0) AS entrate_vincolate_privati
    FROM dedup
),

con_totale AS (
    SELECT
        *,
        entrate_vincolate_regionali + trasferimento_immobili + fondi_bilancio_amministrazione
            + mutuo + entrate_vincolate_statali + entrate_vincolate_locali + altro
            + entrate_vincolate_altri + capitali_privati + sfruttamento_economico
            + fondi_bilancio_sa + entrate_vincolate_ue + entrate_vincolate_privati
            AS totale_fonti,
        GREATEST(
            entrate_vincolate_regionali, trasferimento_immobili, fondi_bilancio_amministrazione,
            mutuo, entrate_vincolate_statali, entrate_vincolate_locali, altro,
            entrate_vincolate_altri, capitali_privati, sfruttamento_economico,
            fondi_bilancio_sa, entrate_vincolate_ue, entrate_vincolate_privati
        ) AS max_fonte,
        (entrate_vincolate_regionali > 0)::INT + (trasferimento_immobili > 0)::INT
            + (fondi_bilancio_amministrazione > 0)::INT + (mutuo > 0)::INT
            + (entrate_vincolate_statali > 0)::INT + (entrate_vincolate_locali > 0)::INT
            + (altro > 0)::INT + (entrate_vincolate_altri > 0)::INT
            + (capitali_privati > 0)::INT + (sfruttamento_economico > 0)::INT
            + (fondi_bilancio_sa > 0)::INT + (entrate_vincolate_ue > 0)::INT
            + (entrate_vincolate_privati > 0)::INT AS n_fonti
    FROM fonti
)

SELECT
    * EXCLUDE (max_fonte),
    -- NULL quando tutte le voci sono a zero (4,5% delle righe): "dato assente",
    -- non "finanziato da nessuno".
    CASE
        WHEN max_fonte = 0 THEN NULL
        WHEN fondi_bilancio_sa = max_fonte THEN 'bilancio stazione appaltante'
        WHEN fondi_bilancio_amministrazione = max_fonte THEN 'bilancio amministrazione competente'
        WHEN entrate_vincolate_ue = max_fonte THEN 'fondi UE'
        WHEN entrate_vincolate_statali = max_fonte THEN 'entrate vincolate statali'
        WHEN mutuo = max_fonte THEN 'mutuo'
        WHEN capitali_privati = max_fonte THEN 'capitali privati'
        ELSE 'altre fonti'
    END AS fonte_prevalente,
    -- Coda corrotta: >= 1 mld dichiarato su un singolo contratto. Il valore
    -- resta nel clean, il flag lo segnala, il mart lo esclude dalle somme.
    totale_fonti >= 1000000000 AS flag_fonti_sospette
FROM con_totale
