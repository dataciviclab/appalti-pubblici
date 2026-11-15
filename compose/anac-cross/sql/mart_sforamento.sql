-- mart_sforamento.sql — di quanto è cresciuto un contratto rispetto al quadro iniziale
--
-- Grana: 1 riga per CIG con consuntivo registrato.
--
-- **Il ribasso non entra nella formula.** Ci ho provato e i dati dicono che è
-- sbagliato: il consuntivo si comporta come un importo *pre-ribasso* — è uguale
-- alla base d'asta nel 95% dei CIG e il suo rapporto con la base ha mediana
-- esattamente 1,0 in ogni fascia di ribasso. Scontare la base del ribasso
-- trasforma un contratto senza varianti in uno «sforamento» pari al ribasso:
-- mediana 0% con ribasso 0, +15,3% con ribasso 10-20, +45,7% sopra il 30.
-- Quindi lo sforamento è `consuntivo - base`, che misura solo le varianti.
--
-- Il ribasso resta esposto come colonna informativa, non come correzione.
--
-- `plausibile` marca i CIG il cui confronto ha senso; le righe escluse restano
-- nel mart con il motivo, così l'esclusione è verificabile e non silenziosa.
-- Criteri (misurati in notes.md):
--   - consuntivo tra 0,5x e 2x la base (fuori: 19.832 CIG, 0,9%)
--   - aggiudicazione non oltre 2x la base (fuori: 19.343 CIG, 0,9%)
-- Insieme escludono 39.175 CIG su 2.202.897 (1,8%).

WITH qe AS (
    SELECT * FROM read_parquet('{support.quadro_economico.mart}')
    WHERE ha_consuntivo
      AND importo_base > 0
),

agg AS (
    SELECT cig, sum(importo_aggiudicazione) AS importo_aggiudicato
    FROM read_parquet('{support.aggiudicazioni.clean}')
    GROUP BY cig
),

ribasso AS (
    SELECT cig, max(ribasso_aggiudicazione) AS ribasso_pct
    FROM read_parquet('{support.aggiudicazioni.clean}')
    WHERE ribasso_aggiudicazione BETWEEN 0 AND 99
    GROUP BY cig
),

bandi AS (
    SELECT
        cig,
        max(anno_pubblicazione) AS anno,
        max(sezione_regionale) AS regione,
        max(oggetto_principale_contratto) AS settore,
        max(denominazione_amministrazione_appaltante) AS sa
    FROM read_parquet('{support.bandi_gara.clean}')
    WHERE cf_amministrazione_appaltante IS NOT NULL
      AND NOT flag_importo_sospetto
    GROUP BY cig
),

varianti AS (
    SELECT
        cig,
        count(*) AS n_varianti_totali,
        string_agg(DISTINCT motivo_variante, ' | ' ORDER BY motivo_variante) AS motivi
    FROM read_parquet('{support.varianti.clean}')
    GROUP BY cig
),

base AS (
    SELECT
        q.cig,
        q.id_aggiudicazione,
        b.anno,
        b.regione,
        b.settore,
        b.sa,
        q.importo_base,
        q.importo_finale AS importo_consuntivo,
        a.importo_aggiudicato,
        r.ribasso_pct,
        COALESCE(v.n_varianti_totali, 0) AS n_varianti,
        v.motivi,
        CASE
            WHEN q.importo_finale < q.importo_base * 0.5 THEN 'consuntivo sotto 0,5x la base'
            WHEN q.importo_finale > q.importo_base * 2 THEN 'consuntivo oltre 2x la base'
            WHEN a.importo_aggiudicato > q.importo_base * 2 THEN 'aggiudicazione oltre 2x la base'
        END AS motivo_esclusione
    FROM qe q
    LEFT JOIN agg a ON q.cig = a.cig
    LEFT JOIN ribasso r ON q.cig = r.cig
    LEFT JOIN bandi b ON q.cig = b.cig
    LEFT JOIN varianti v ON q.cig = v.cig
)

SELECT
    cig,
    id_aggiudicazione,
    anno,
    regione,
    settore,
    sa,
    ROUND(importo_base, 2) AS importo_base,
    ROUND(importo_consuntivo, 2) AS importo_consuntivo,
    ROUND(importo_consuntivo - importo_base, 2) AS sforamento,
    ROUND((importo_consuntivo - importo_base) * 100.0 / NULLIF(importo_base, 0), 2) AS sforamento_pct,
    ROUND(importo_aggiudicato, 2) AS importo_aggiudicato,
    ribasso_pct,
    n_varianti,
    motivi,
    motivo_esclusione IS NULL AS plausibile,
    motivo_esclusione
FROM base
WHERE regione IS NOT NULL
  AND settore IS NOT NULL
ORDER BY sforamento DESC
