-- mart_collaudo_ritardo.sql — dal "finito" al "collaudato"
-- Grana: anno × regione × settore.
--
-- Due domande che solo il join tra fine-contratto e collaudo puo' rispondere:
-- quanto tempo passa tra l'ultimazione effettiva e il certificato di collaudo,
-- e quante opere risultano ultimate senza un collaudo registrato.
-- (E' il caso del ponte di Vigevano: opera finita e non fruibile.)
--
-- Attenzione a cosa vuol dire "senza collaudo": i tre stati sono diversi e
-- vanno tenuti separati, altrimenti la quota finale e' inutilizzabile.
--   - `n_senza_record`     : nessuna riga di collaudo per il CIG
--   - `n_record_senza_data`: la riga esiste ma `data_cert_collaudo` e' NULL
--                            (l'81% delle righe del dataset collaudo e' cosi')
--   - `n_con_data`         : c'e' il certificato con la data
-- "Senza collaudo registrato" = senza record. "Senza data di certificato" e'
-- la somma delle prime due: sono due misure di trasparenza diverse.

WITH bandi AS (
    SELECT
        cig,
        MAX(anno_pubblicazione) AS anno,
        MAX(sezione_regionale) AS regione,
        MAX(oggetto_principale_contratto) AS settore
    FROM read_parquet('{support.bandi_gara.clean}')
    WHERE cf_amministrazione_appaltante IS NOT NULL
      AND NOT flag_importo_sospetto
    GROUP BY cig
),

fine AS (
    SELECT
        cig,
        MAX(data_effettiva_ultimazione) AS ultimazione
    FROM read_parquet('{support.fine_contratto.clean}')
    GROUP BY cig
),

collaudo AS (
    SELECT
        cig,
        MAX(data_cert_collaudo) AS data_cert_collaudo,
        MAX(esito_collaudo) AS esito_collaudo,
        COUNT(*) AS n_record
    FROM read_parquet('{support.collaudo.clean}')
    GROUP BY cig
),

base AS (
    SELECT
        b.anno,
        b.regione,
        b.settore,
        f.ultimazione,
        c.cig IS NOT NULL AS ha_record,
        c.data_cert_collaudo,
        CASE WHEN c.data_cert_collaudo IS NOT NULL
              AND date_diff('day', f.ultimazione, c.data_cert_collaudo) BETWEEN 0 AND 3650
            THEN date_diff('day', f.ultimazione, c.data_cert_collaudo) END
            AS giorni_ultimazione_collaudo
    FROM fine f
    JOIN bandi b ON f.cig = b.cig
    LEFT JOIN collaudo c ON f.cig = c.cig
    WHERE f.ultimazione IS NOT NULL
)

SELECT
    anno,
    regione,
    settore,
    COUNT(*) AS n_opere_ultimate,
    COUNT(*) FILTER (WHERE ha_record) AS n_con_record,
    COUNT(*) FILTER (WHERE NOT ha_record) AS n_senza_record,
    COUNT(*) FILTER (WHERE ha_record AND data_cert_collaudo IS NULL) AS n_record_senza_data,
    COUNT(*) FILTER (WHERE data_cert_collaudo IS NOT NULL) AS n_con_data,
    ROUND(COUNT(*) FILTER (WHERE NOT ha_record) * 100.0
        / NULLIF(COUNT(*), 0), 1) AS quota_senza_record_pct,
    ROUND(COUNT(*) FILTER (WHERE data_cert_collaudo IS NULL) * 100.0
        / NULLIF(COUNT(*), 0), 1) AS quota_senza_data_certificato_pct,
    ROUND(median(giorni_ultimazione_collaudo), 0) AS giorni_mediani_ultimazione_collaudo,
    ROUND(AVG(giorni_ultimazione_collaudo), 0) AS giorni_medi_ultimazione_collaudo
FROM base
GROUP BY anno, regione, settore
HAVING COUNT(*) >= 3
ORDER BY n_senza_record DESC
