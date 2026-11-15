-- ANAC SmartCIG (affidamenti diretti sotto soglia) — CLEAN
-- I dump sono mensili e disgiunti, ma un CIG puo' ricomparire in comunicazioni
-- successive: teniamo la comunicazione piu' recente per CIG.
WITH dedup AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY cig
            ORDER BY
                TRY_CAST(data_comunicazione AS DATE) DESC NULLS LAST,
                TRY_CAST(anno_comunicazione AS INT) DESC NULLS LAST,
                TRY_CAST(mese_comunicazione AS INT) DESC NULLS LAST
        ) AS rn
    FROM raw_input
)
SELECT
    cig,
    numero_gara,
    oggetto_gara,
    oggetto_lotto,
    oggetto_principale_contratto,
    cast_double(importo_complessivo_gara) AS importo_complessivo_gara,
    cast_double(importo_lotto) AS importo_lotto,
    cast_int(n_lotti_componenti) AS n_lotti_componenti,
    stato,
    TRY_CAST(data_comunicazione AS DATE) AS data_comunicazione,
    id_tipo_fattispecie_contrattuale,
    tipo_fattispecie_contrattuale,
    cast_int(cod_tipo_scelta_contraente) AS cod_tipo_scelta_contraente,
    tipo_scelta_contraente,
    codice_ausa,
    cf_amministrazione_appaltante,
    denominazione_amministrazione_appaltante,
    sezione_regionale,
    indirizzo,
    istat_comune,
    citta,
    regione,
    id_centro_costo,
    denominazione_centro_costo,
    cast_int(anno_comunicazione) AS anno_comunicazione,
    cast_int(mese_comunicazione) AS mese_comunicazione,
    CASE
        WHEN importo_lotto IS NULL OR importo_lotto <= 0 THEN 'non_valido'
        WHEN importo_lotto < 1000 THEN 'micro'
        WHEN importo_lotto < 5000 THEN 'piccola'
        WHEN importo_lotto <= 40000 THEN 'media'
        ELSE 'sopra_40k'
    END AS fascia_importo,
    importo_lotto > 140000 AS flag_sopra_140k
FROM dedup
WHERE rn = 1
