-- mart_cig.sql — importo a base d'asta vs stato finale, per CIG
--
-- Gli importi del quadro economico sono istantanee cumulative: il "finale" e'
-- il CONSUNTIVO se c'e', altrimenti il valore massimo osservato (le varianti
-- possono non avere un consuntivo registrato). Il confronto e' sul contratto
-- (lavori + servizi + forniture), che e' la parte soggetta a ribasso; le somme
-- a disposizione restano separate perche' non sono importo contrattuale.
WITH base AS (
    SELECT DISTINCT ON (cig, id_aggiudicazione)
        cig, id_aggiudicazione,
        importo_lavori + importo_servizi + importo_forniture AS importo_contratto,
        somme_a_disposizione
    FROM clean_input
    WHERE descrizione_evento = 'BASE_ASTA'
    ORDER BY cig, id_aggiudicazione
),
consuntivo AS (
    SELECT DISTINCT ON (cig, id_aggiudicazione)
        cig, id_aggiudicazione,
        importo_lavori + importo_servizi + importo_forniture AS importo_contratto,
        somme_a_disposizione
    FROM clean_input
    WHERE descrizione_evento = 'CONSUNTIVO'
    ORDER BY cig, id_aggiudicazione
),
stato AS (
    SELECT
        cig,
        id_aggiudicazione,
        max(importo_lavori + importo_servizi + importo_forniture) AS contratto_max,
        max(somme_a_disposizione) AS somme_max,
        count(*) FILTER (WHERE descrizione_evento = 'VARIANTE') AS n_varianti,
        count(*) AS n_eventi,
        min(data) FILTER (WHERE descrizione_evento = 'VARIANTE') AS data_prima_variante,
        max(data) FILTER (WHERE descrizione_evento = 'VARIANTE') AS data_ultima_variante,
        bool_or(descrizione_evento = 'CONSUNTIVO') AS ha_consuntivo
    FROM clean_input
    GROUP BY cig, id_aggiudicazione
)
SELECT
    s.cig,
    s.id_aggiudicazione,
    b.importo_contratto AS importo_base,
    COALESCE(c.importo_contratto, s.contratto_max) AS importo_finale,
    COALESCE(c.importo_contratto, s.contratto_max) - b.importo_contratto AS scostamento,
    ROUND(
        (COALESCE(c.importo_contratto, s.contratto_max) - b.importo_contratto) * 100.0
        / NULLIF(b.importo_contratto, 0), 2
    ) AS scostamento_pct,
    b.somme_a_disposizione AS somme_base,
    COALESCE(c.somme_a_disposizione, s.somme_max) AS somme_finali,
    s.n_varianti,
    s.n_eventi,
    s.ha_consuntivo,
    s.data_prima_variante,
    s.data_ultima_variante
FROM stato s
JOIN base b ON s.cig = b.cig AND s.id_aggiudicazione = b.id_aggiudicazione
LEFT JOIN consuntivo c ON s.cig = c.cig AND s.id_aggiudicazione = c.id_aggiudicazione
WHERE b.importo_contratto > 0
