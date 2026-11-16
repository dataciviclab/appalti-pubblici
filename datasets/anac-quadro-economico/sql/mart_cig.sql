-- mart_cig.sql — importo a base d'asta vs stato finale, per CIG
--
-- Gli importi del quadro economico sono istantanee cumulative: il "finale" e'
-- il CONSUNTIVO se c'e', altrimenti il valore massimo osservato (le varianti
-- possono non avere un consuntivo registrato). Il confronto e' sul contratto
-- (lavori + servizi + forniture), che e' la parte soggetta a ribasso; le somme
-- a disposizione restano separate perche' non sono importo contrattuale.
--
-- **I componenti vanno sommati con `COALESCE`.** Il quadro economico compila la
-- voce dell'appalto (lavori *o* servizi *o* forniture): il 62,3% delle righe
-- BASE_ASTA ha almeno un componente NULL, quindi la somma stretta annullava il
-- totale e il CIG spariva dal mart senza che nulla lo dicesse — importo_base
-- esisteva solo per 2.202.896 CIG, il 37,7% dei CIG con una base (issue #33).
-- Con il `COALESCE` la copertura passa a 5.611.100 CIG: **95,5% delle righe
-- BASE_ASTA** (5.873.183). NULL resta "voce assente": una riga con tutti e tre
-- i componenti nulli vale 0 ed e' scartata dal filtro finale.
--
-- **La coda va segnalata, non sommata.** Il `COALESCE` da solo fa esplodere il
-- totale a 6e64 mld: 170 CIG hanno una base >= 1 mld e 16 >= 10 mld (massimo
-- 6e73), separatori appiattiti nella fonte. Le due guardie:
--   - `flag_base_sospetta` (>= 10 mld): importo non plausibile, i mart la
--     escludono dagli aggregati;
--   - `flag_base_grande` (>= 1 mld): segnalazione, la riga resta nel dato.
-- Le righe restano tutte nel mart, col flag: l'esclusione e' verificabile.
-- Il totale con la coda fuori e' **3.125,9 mld** (5.611.084 contratti); le 16
-- righe sospette valgono 6e64 mld da sole. Chi somma `importo_base` senza
-- filtrare il flag ottiene un numero che non esiste.
WITH base AS (
    SELECT DISTINCT ON (cig, id_aggiudicazione)
        cig, id_aggiudicazione,
        COALESCE(importo_lavori, 0) + COALESCE(importo_servizi, 0)
            + COALESCE(importo_forniture, 0) AS importo_contratto,
        somme_a_disposizione
    FROM clean_input
    WHERE descrizione_evento = 'BASE_ASTA'
    ORDER BY cig, id_aggiudicazione
),
consuntivo AS (
    SELECT DISTINCT ON (cig, id_aggiudicazione)
        cig, id_aggiudicazione,
        COALESCE(importo_lavori, 0) + COALESCE(importo_servizi, 0)
            + COALESCE(importo_forniture, 0) AS importo_contratto,
        somme_a_disposizione
    FROM clean_input
    WHERE descrizione_evento = 'CONSUNTIVO'
    ORDER BY cig, id_aggiudicazione
),
stato AS (
    SELECT
        cig,
        id_aggiudicazione,
        max(COALESCE(importo_lavori, 0) + COALESCE(importo_servizi, 0)
            + COALESCE(importo_forniture, 0)) AS contratto_max,
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
    s.data_ultima_variante,
    -- Coda della fonte: >= 10 mld su un contratto non e' plausibile, >= 1 mld
    -- e' fuori scala ma possibile. Fuori dagli aggregati la prima, segnalata
    -- la seconda.
    b.importo_contratto >= 10000000000 AS flag_base_sospetta,
    b.importo_contratto >= 1000000000 AS flag_base_grande
FROM stato s
JOIN base b ON s.cig = b.cig AND s.id_aggiudicazione = b.id_aggiudicazione
LEFT JOIN consuntivo c ON s.cig = c.cig AND s.id_aggiudicazione = c.id_aggiudicazione
WHERE b.importo_contratto > 0
