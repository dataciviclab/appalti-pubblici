-- mart_cig_imprese.sql — i campi larghi del compose, in una tabella stretta
--
-- Prima vivevano dentro il clean CIG-level (`aggiudicatari` e `cups`, due
-- STRING_AGG da centinaia di byte per riga) e gonfiavano ogni riga del join a
-- 11 vie. Qui stanno da soli: chi serve li join-a su `cig`.

WITH agg AS (
    SELECT
        cig,
        STRING_AGG(DISTINCT denominazione, ' | ' ORDER BY denominazione) AS aggiudicatari
    FROM read_parquet('{support.aggiudicatari.clean}')
    WHERE codice_fiscale IS NOT NULL
      AND TRIM(codice_fiscale) != ''
    GROUP BY cig
),

cup AS (
    SELECT
        cig,
        STRING_AGG(DISTINCT cup, ' | ' ORDER BY cup) AS cups
    FROM read_parquet('{support.cup.clean}')
    WHERE cup IS NOT NULL AND TRIM(cup) != ''
    GROUP BY cig
)

SELECT
    COALESCE(a.cig, c.cig) AS cig,
    a.aggiudicatari,
    c.cups
FROM agg a
FULL OUTER JOIN cup c ON a.cig = c.cig
