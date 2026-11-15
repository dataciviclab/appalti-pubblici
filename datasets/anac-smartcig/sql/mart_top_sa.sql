-- Profilo delle stazioni appaltanti che usano l'affidamento diretto.
SELECT
    cf_amministrazione_appaltante AS cf_sa,
    MAX(denominazione_amministrazione_appaltante) AS denominazione_sa,
    MAX(sezione_regionale) AS sezione_regionale,
    MAX(regione) AS regione,
    COUNT(*) AS n_cig,
    ROUND(SUM(importo_lotto), 0) AS importo_totale,
    ROUND(AVG(importo_lotto), 0) AS importo_medio,
    ROUND(MEDIAN(importo_lotto), 0) AS importo_mediano,
    SUM(CASE WHEN fascia_importo = 'micro' THEN 1 ELSE 0 END) AS n_micro,
    MIN(anno_comunicazione) AS anno_primo,
    MAX(anno_comunicazione) AS anno_ultimo
FROM clean_input
WHERE cf_amministrazione_appaltante IS NOT NULL
  AND cf_amministrazione_appaltante != ''
GROUP BY cf_amministrazione_appaltante
HAVING COUNT(*) >= 5
ORDER BY importo_totale DESC
