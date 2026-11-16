-- ANAC quadro economico — CLEAN
-- Macro toolkit: normalize_string, cast_bigint, cast_double, safe_date
--
-- Grano: **1 riga per evento** del CIG. La chiave e' quella del Manuale ANAC
-- v1.4 §4 (pag. 16): `Cig + id_aggiudicazione + descrizione_evento +
-- dettaglio_evento`. `dettaglio_evento` e' l'id della variante (347.275 valori
-- distinti su 355.051 righe di VARIANTE): senza di lui le varianti collassano.
--
-- Gli importi sono **istantanee cumulative**: ogni riga porta lo stato del
-- quadro economico dopo quell'evento. Per questo il mart confronta gli importi
-- invece di sommarli.
--
-- `data` e' valorizzata solo per le VARIANTI (BASE_ASTA e CONSUNTIVO hanno
-- sempre data NULL): non e' una serie temporale completa.
--
-- Sostituzione per chiave (Manuale §5.1): tra due righe con la stessa chiave
-- vince la risorsa piu' recente. Nei dati reali 3.625 chiavi sono duplicate
-- (2.553 con importi diversi): la fonte le ripubblica corrette nei delta.
WITH dedup AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY cig, id_aggiudicazione, descrizione_evento, dettaglio_evento
            ORDER BY __source_file DESC
        ) AS rn
    FROM raw_input
)
SELECT
    normalize_string(cig) AS cig,
    cast_bigint(id_aggiudicazione) AS id_aggiudicazione,
    -- Il dominio ANAC parte dal 2005: 1901-01-01 (sentinella) e 1812-08-25
    -- (refuso) non sono date. `safe_date` e' generica (1800-2100), la stretta
    -- di dominio sta qui, come per le varianti con '0001-01-01'.
    CASE WHEN year(safe_date(data)) < 1990 THEN NULL ELSE safe_date(data) END AS data,
    normalize_string(descrizione_evento) AS descrizione_evento,
    normalize_string(dettaglio_evento) AS dettaglio_evento,
    cast_double(importo_lavori) AS importo_lavori,
    cast_double(importo_servizi) AS importo_servizi,
    cast_double(importo_forniture) AS importo_forniture,
    cast_double(importo_progettazione) AS importo_progettazione,
    cast_double(importo_sicurezza) AS importo_sicurezza,
    cast_double(somme_a_disposizione) AS somme_a_disposizione,
    cast_double(ulteriori_oneri_non_soggetti_ribasso) AS ulteriori_oneri_non_soggetti_ribasso
FROM dedup
WHERE rn = 1
  AND cig IS NOT NULL AND TRIM(cig) != ''
  AND id_aggiudicazione IS NOT NULL
