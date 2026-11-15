-- mart_eventi.sql — quanti eventi per tipo e che importi portano
SELECT
    descrizione_evento,
    count(*) AS n_righe,
    count(DISTINCT cig) AS n_cig,
    count(data) AS n_con_data,
    ROUND(median(importo_lavori + importo_servizi + importo_forniture), 0) AS importo_contratto_mediano,
    ROUND(avg(importo_lavori + importo_servizi + importo_forniture), 0) AS importo_contratto_medio,
    ROUND(sum(importo_lavori + importo_servizi + importo_forniture) / 1e9, 1) AS importo_contratto_mld
FROM clean_input
GROUP BY descrizione_evento
ORDER BY n_righe DESC
