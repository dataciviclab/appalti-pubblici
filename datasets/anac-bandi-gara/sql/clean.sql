-- ANAC Bandi di Gara (CIG) — CLEAN
-- Macro toolkit: cast_int, cast_double, decode_flag, normalize_string
SELECT
    cig,
    cig_accordo_quadro,
    cig_collegamento,
    cui_programma,
    -- Identificativo, non misura: dal 2024 la fonte pubblica valori alfanumerici
    -- (es. CONSIP_RDO_4955828) mentre negli anni precedenti il campo e' numerico.
    -- Senza il cast il parquet cambia tipo per anno e le query cross-anno falliscono.
    TRY_CAST(numero_gara AS VARCHAR) AS numero_gara,
    oggetto_gara,
    cast_double(importo_complessivo_gara) AS importo_complessivo_gara,
    cast_int(n_lotti_componenti) AS n_lotti_componenti,
    oggetto_lotto,
    cast_double(importo_lotto) AS importo_lotto,
    -- Importo da verificare. Due firme note della fonte:
    --  1. importo >= 1 mld su un singolo lotto (alcuni reali: B77825C53E, 17,4
    --     mld per 20 anni di servizio idrico; altri con i separatori appiattiti:
    --     9.400.334,903 -> 9400334903);
    --  2. importo del lotto >= 10x l'importo della gara, logicamente impossibile:
    --     intercetta le righe appiattite sotto il miliardo (es. 16.236,51 ->
    --     1623651, dove il lotto "supera" la gara di 100 volte).
    -- Il clean conserva il valore pubblicato; i mart lo escludono dalle
    -- aggregazioni e ne dichiarano numero e importo.
    COALESCE(
        TRY_CAST(importo_lotto AS DOUBLE) >= 1000000000
        OR (TRY_CAST(importo_complessivo_gara AS DOUBLE) > 0
            AND TRY_CAST(importo_lotto AS DOUBLE) > TRY_CAST(importo_complessivo_gara AS DOUBLE) * 10),
        FALSE
    ) AS flag_importo_sospetto,
    oggetto_principale_contratto,
    stato,
    settore,
    luogo_istat AS codice_istat_luogo,
    provincia,
    safe_date(data_pubblicazione) AS data_pubblicazione,
    safe_date(data_scadenza_offerta) AS data_scadenza_offerta,
    cod_tipo_scelta_contraente,
    tipo_scelta_contraente,
    cod_modalita_realizzazione,
    modalita_realizzazione,
    codice_ausa,
    cf_amministrazione_appaltante,
    denominazione_amministrazione_appaltante,
    sezione_regionale,
    id_centro_costo,
    denominazione_centro_costo,
    cast_int(anno_pubblicazione) AS anno_pubblicazione,
    cast_int(mese_pubblicazione) AS mese_pubblicazione,
    cod_cpv,
    descrizione_cpv,
    decode_flag(FLAG_PNRR_PNC, '1') AS flag_pnrr,
    decode_flag(FLAG_URGENZA, '1') AS flag_urgenza,
    decode_flag(FLAG_DELEGA, '1') AS flag_delega,
    cod_modalita_indizione_speciali,
    modalita_indizione_speciali,
    cod_modalita_indizione_servizi,
    modalita_indizione_servizi,
    cast_double(durata_prevista) AS durata_prevista,
    cod_strumento_svolgimento,
    strumento_svolgimento,
    cod_motivo_urgenza,
    normalize_string(motivo_urgenza) AS motivo_urgenza,
    normalize_string(funzioni_delegate) AS funzioni_delegate,
    cf_sa_delegante,
    denominazione_sa_delegante,
    cf_sa_delegata,
    denominazione_sa_delegata,
    cast_double(importo_sicurezza) AS importo_sicurezza,
    cod_esito,
    esito,
    safe_date(data_comunicazione_esito) AS data_comunicazione_esito,
    safe_date(data_cancellazione) AS data_cancellazione,
    cod_motivo_cancellazione,
    motivo_cancellazione,
    tipo_appalto_riservato,
    safe_date(data_ultimo_perfezionamento) AS data_ultimo_perfezionamento
FROM raw_input
-- Ogni partizione anno contiene solo le righe di quell'anno. Per il 2026 la
-- fonte e' il dataset `cig` dei delta, che mescola tutti gli anni: qui restano
-- solo le pubblicazioni 2026 (le correzioni storiche non vengono applicate,
-- misurato: 0,2% degli importi).
WHERE TRY_CAST(anno_pubblicazione AS INTEGER) = {year}
-- La fonte ripete righe identiche nello stesso export (fino a 10 volte nello
-- stesso mese). Il grano e' 1 CIG = 1 lotto: tiene la comunicazione piu' recente.
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY cig
    ORDER BY data_ultimo_perfezionamento DESC NULLS LAST,
             data_pubblicazione DESC NULLS LAST
) = 1
