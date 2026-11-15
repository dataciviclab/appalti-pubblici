-- mart_ritardi_contratto.sql — ritardi reali per stazione appaltante
-- Grana: SA × regione × settore. Ritardo = ultimazione effettiva - termine
-- contrattuale (positivo = oltre il termine).
--
-- Mart-only: bandi + avvio + fine letti direttamente (niente clean CIG-level).

WITH bandi AS (
    SELECT
        cig,
        MAX(cf_amministrazione_appaltante) AS cf_sa,
        MAX(denominazione_amministrazione_appaltante) AS sa,
        MAX(sezione_regionale) AS regione,
        MAX(oggetto_principale_contratto) AS settore,
        SUM(importo_lotto) AS importo_lotto
    FROM read_parquet('{support.bandi_gara.clean}')
    WHERE cf_amministrazione_appaltante IS NOT NULL
      AND NOT flag_importo_sospetto
    GROUP BY cig
),

avvio AS (
    SELECT cig, data_termine_contrattuale
    FROM (
        SELECT
            cig,
            data_termine_contrattuale,
            ROW_NUMBER() OVER (
                PARTITION BY cig
                ORDER BY data_stipula_contratto DESC NULLS LAST
            ) AS rn
        FROM read_parquet('{support.avvio_contratto.clean}')
    ) ranked
    WHERE rn = 1
),

fine AS (
    SELECT
        cig,
        MAX(data_effettiva_ultimazione) AS data_effettiva_ultimazione
    FROM read_parquet('{support.fine_contratto.clean}')
    GROUP BY cig
),

esec AS (
    SELECT
        av.cig,
        CASE WHEN av.data_termine_contrattuale IS NOT NULL
              AND fi.data_effettiva_ultimazione IS NOT NULL
              AND date_diff('day', av.data_termine_contrattuale, fi.data_effettiva_ultimazione)
                  BETWEEN -3650 AND 3650
            THEN date_diff('day', av.data_termine_contrattuale, fi.data_effettiva_ultimazione) END
            AS giorni_scostamento_termine
    FROM avvio av
    JOIN fine fi ON av.cig = fi.cig
)

SELECT
    b.cf_sa,
    b.sa,
    b.regione,
    b.settore,
    COUNT(*) AS n_contratti,
    COUNT(*) FILTER (WHERE e.giorni_scostamento_termine > 0) AS n_in_ritardo,
    ROUND(COUNT(*) FILTER (WHERE e.giorni_scostamento_termine > 0) * 100.0
        / NULLIF(COUNT(*), 0), 1) AS quota_in_ritardo_pct,
    ROUND(AVG(e.giorni_scostamento_termine), 0) AS giorni_medi_scostamento,
    ROUND(median(e.giorni_scostamento_termine), 0) AS giorni_mediani_scostamento,
    MAX(e.giorni_scostamento_termine) AS giorni_max_scostamento,
    ROUND(SUM(b.importo_lotto), 0) AS importo_lotto_totale,
    ROUND(SUM(CASE WHEN e.giorni_scostamento_termine > 0
        THEN b.importo_lotto ELSE 0 END), 0) AS importo_in_ritardo
FROM esec e
JOIN bandi b ON e.cig = b.cig
WHERE e.giorni_scostamento_termine IS NOT NULL
  AND b.cf_sa IS NOT NULL
  AND b.sa IS NOT NULL
GROUP BY b.cf_sa, b.sa, b.regione, b.settore
HAVING COUNT(*) >= 3
ORDER BY n_in_ritardo DESC
