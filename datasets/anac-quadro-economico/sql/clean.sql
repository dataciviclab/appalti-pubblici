-- ANAC quadro economico — CLEAN
-- Macro toolkit: normalize_string, cast_bigint, cast_double, safe_date
--
-- Grano: 1 riga per evento del CIG (base d'asta, varianti, consuntivo). Gli
-- importi sono **istantanee cumulative**, non delta: ogni riga porta lo stato
-- del quadro economico dopo quell'evento. Per questo il mart confronta gli
-- importi invece di sommarli.
--
-- `data` e' valorizzata solo per le VARIANTI (BASE_ASTA e CONSUNTIVO hanno
-- sempre data NULL): non e' una serie temporale completa, la sequenza si
-- ricostruisce dagli importi.
--
-- Dedup per **riga intera** (DISTINCT), non per CIG come dice il Manuale
-- (§5.1): nei delta non tutti i CIG vengono ripubblicati con la base d'asta
-- (nel delta di aprile 2026 sono 1.555 su 373.687) e la base e' proprio cio'
-- che serve al confronto — sostituire per CIG la cancellerebbe. Due righe
-- identiche sono lo stesso evento ripubblicato da due risorse e collassano.
-- Una correzione con importo diverso resta come riga distinta: il mart prende
-- il consuntivo o, in mancanza, il valore massimo osservato.
SELECT DISTINCT
    normalize_string(cig) AS cig,
    cast_bigint(id_aggiudicazione) AS id_aggiudicazione,
    safe_date(data) AS data,
    normalize_string(descrizione_evento) AS descrizione_evento,
    normalize_string(dettaglio_evento) AS dettaglio_evento,
    cast_double(importo_lavori) AS importo_lavori,
    cast_double(importo_servizi) AS importo_servizi,
    cast_double(importo_forniture) AS importo_forniture,
    cast_double(importo_progettazione) AS importo_progettazione,
    cast_double(importo_sicurezza) AS importo_sicurezza,
    cast_double(somme_a_disposizione) AS somme_a_disposizione,
    cast_double(ulteriori_oneri_non_soggetti_ribasso) AS ulteriori_oneri_non_soggetti_ribasso
FROM raw_input
WHERE cig IS NOT NULL AND TRIM(cig) != ''
  AND id_aggiudicazione IS NOT NULL
