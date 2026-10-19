-- ANAC Fine Contratto — MART motivi
-- Risoluzioni e interruzioni anticipate per motivo.
WITH motivi AS (
    SELECT 'RISOLUZIONE' AS tipo, motivo_risoluzione AS motivo
    FROM clean_input
    WHERE motivo_risoluzione IS NOT NULL

    UNION ALL

    SELECT 'INTERRUZIONE ANTICIPATA' AS tipo, motivo_interruzione_anticipata AS motivo
    FROM clean_input
    WHERE motivo_interruzione_anticipata IS NOT NULL
)

SELECT
    tipo,
    motivo,
    COUNT(*) AS n_contratti
FROM motivi
GROUP BY tipo, motivo
ORDER BY n_contratti DESC
