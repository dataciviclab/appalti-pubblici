-- mart_natura.sql — quante stazioni appaltanti per natura giuridica
-- Le righe senza classificazione restano contate come 'NON DICHIARATA':
-- togliendole il totale non tornerebbe con l'anagrafica (48.040).
-- I flag in-house/partecipata non sono qui: in questo export ANAC sono "false"
-- su tutte le righe (vedi notes.md), una colonna a zero fisso suggerirebbe il
-- contrario di quello che dice.
SELECT
    COALESCE(natura_giuridica, 'NON DICHIARATA') AS natura_giuridica,
    COUNT(*) AS n_sa,
    COUNT(*) FILTER (WHERE stato = 'ATTIVO') AS n_attive,
    COUNT(*) FILTER (WHERE stato != 'ATTIVO') AS n_cessate,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS quota_pct
FROM clean_input
GROUP BY 1
ORDER BY n_sa DESC
