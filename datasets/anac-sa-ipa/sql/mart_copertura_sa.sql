-- Copertura dell'arricchimento IPA: quanti CIG hanno una SA mappata, per regione e tipologia.
-- Serve a monitorare la qualita' del bridge senza imporre soglie nel clean.

SELECT
    COALESCE(sezione_regionale, 'N/D') AS sezione_regionale,
    COALESCE(tipologia_sa, 'non in IPA') AS tipologia_sa,
    COUNT(*) AS n_cig,
    COUNT(codice_ipa_sa) AS n_cig_con_ipa,
    COUNT(DISTINCT codice_ipa_sa) AS n_enti_ipa,
    ROUND(100.0 * COUNT(codice_ipa_sa) / COUNT(*), 1) AS pct_con_ipa
FROM clean_input
GROUP BY 1, 2
ORDER BY n_cig DESC
