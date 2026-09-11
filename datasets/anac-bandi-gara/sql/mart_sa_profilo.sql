-- mart_sa_profilo.sql — 1 riga per stazione appaltante
-- Profilo completo: quanti bandi, che importi, che settori, che territorio.
-- Base per l'analisi "chi compra" nella dashboard intelligence.

SELECT
    cf_amministrazione_appaltante AS cf_sa,
    MAX(denominazione_amministrazione_appaltante) AS denominazione_sa,
    MAX(sezione_regionale) AS regione,
    COUNT(*) AS n_bandi,
    COUNT(DISTINCT cig) AS n_cig,
    ROUND(SUM(importo_lotto), 0) AS importo_totale,
    ROUND(AVG(importo_lotto), 0) AS importo_mediano,
    COUNT(DISTINCT oggetto_principale_contratto) AS n_settori,
    MIN(anno_pubblicazione) AS anno_primo,
    MAX(anno_pubblicazione) AS ultimo_anno,
    SUM(CASE WHEN flag_pnrr = TRUE THEN 1 ELSE 0 END) AS n_pnrr,
    ROUND(SUM(CASE WHEN flag_pnrr = TRUE THEN importo_lotto ELSE 0 END), 0) AS importo_pnrr
FROM clean_input
WHERE stato = 'ATTIVO'
  AND cf_amministrazione_appaltante IS NOT NULL
  AND cf_amministrazione_appaltante != ''
GROUP BY cf_amministrazione_appaltante
HAVING COUNT(*) >= 10
ORDER BY importo_totale DESC
