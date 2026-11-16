-- mart_fonti.sql — formato lungo: 1 riga per (CIG, aggiudicazione, fonte)
--
-- Le 13 voci del clean sono in formato largo; qui diventano lunghe, che è la
-- forma con cui si risponde a «a carico di chi» e si aggrega per fonte.
-- Solo le voci valorizzate (> 0): un contratto con 2 fonti produce 2 righe.
--
-- `flag_fonti_sospette` (>= 1 mld dichiarato) è escluso dalle aggregazioni: la
-- fonte ha una coda di importi assurdi (stessa classe dei bandi).
SELECT * FROM (
    UNPIVOT (
        SELECT
            cig,
            id_aggiudicazione,
            fonte_prevalente,
            n_fonti,
            entrate_vincolate_regionali,
            trasferimento_immobili,
            fondi_bilancio_amministrazione,
            mutuo,
            entrate_vincolate_statali,
            entrate_vincolate_locali,
            altro,
            entrate_vincolate_altri,
            capitali_privati,
            sfruttamento_economico,
            fondi_bilancio_sa,
            entrate_vincolate_ue,
            entrate_vincolate_privati
        FROM clean_input
        WHERE NOT flag_fonti_sospette
    )
    ON entrate_vincolate_regionali, trasferimento_immobili, fondi_bilancio_amministrazione,
       mutuo, entrate_vincolate_statali, entrate_vincolate_locali, altro,
       entrate_vincolate_altri, capitali_privati, sfruttamento_economico,
       fondi_bilancio_sa, entrate_vincolate_ue, entrate_vincolate_privati
    INTO NAME fonte VALUE importo
)
WHERE importo > 0
