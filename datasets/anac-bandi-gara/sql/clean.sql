-- ANAC Bandi di Gara (CIG) — CLEAN
-- Macro toolkit: cast_int, cast_double, decode_flag, normalize_string
-- Date: `safe_date` e' generica (1800-2100); il dominio ANAC parte dal 2005, e
-- i valori ante-1990 sono refusi (es. 1977-04-13 al posto di 2027) o sentinelle.
-- Stessa stretta di dominio applicata in anac-quadro-economico.
--
-- I codici restano VARCHAR in tutte le partizioni. Lo sniffing del CSV li
-- leggeva BIGINT/DOUBLE in certi anni e VARCHAR in altri: schema diverso per la
-- stessa colonna, che rompe i consumatori che leggono una partizione alla volta
-- (non DuckDB, che coercizza). Sono codici, non misure: nessun mart li usa
-- come numeri.
--
-- L'alias CONSERVA il nome pubblicato (maiuscolo per 8 colonne, minuscolo per
-- cod_tipo_scelta_contraente e cod_modalita_realizzazione): un cast che cambia
-- il tipo non deve cambiare il nome, altrimenti e' una rinomina su 20 partizioni.
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
    CASE WHEN year(safe_date(data_pubblicazione)) < 1990 THEN NULL
         ELSE safe_date(data_pubblicazione) END AS data_pubblicazione,
    CASE WHEN year(safe_date(data_scadenza_offerta)) < 1990 THEN NULL
         ELSE safe_date(data_scadenza_offerta) END AS data_scadenza_offerta,
    TRY_CAST(cod_tipo_scelta_contraente AS VARCHAR) AS cod_tipo_scelta_contraente,
    tipo_scelta_contraente,
    TRY_CAST(cod_modalita_realizzazione AS VARCHAR) AS cod_modalita_realizzazione,
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
    TRY_CAST(cod_modalita_indizione_speciali AS VARCHAR) AS COD_MODALITA_INDIZIONE_SPECIALI,
    modalita_indizione_speciali,
    TRY_CAST(cod_modalita_indizione_servizi AS VARCHAR) AS COD_MODALITA_INDIZIONE_SERVIZI,
    modalita_indizione_servizi,
    cast_double(durata_prevista) AS durata_prevista,
    TRY_CAST(cod_strumento_svolgimento AS VARCHAR) AS COD_STRUMENTO_SVOLGIMENTO,
    strumento_svolgimento,
    TRY_CAST(cod_motivo_urgenza AS VARCHAR) AS COD_MOTIVO_URGENZA,
    normalize_string(motivo_urgenza) AS motivo_urgenza,
    normalize_string(funzioni_delegate) AS funzioni_delegate,
    TRY_CAST(cf_sa_delegante AS VARCHAR) AS CF_SA_DELEGANTE,
    denominazione_sa_delegante,
    TRY_CAST(cf_sa_delegata AS VARCHAR) AS CF_SA_DELEGATA,
    denominazione_sa_delegata,
    cast_double(importo_sicurezza) AS importo_sicurezza,
    TRY_CAST(cod_esito AS VARCHAR) AS COD_ESITO,
    esito,
    CASE WHEN year(safe_date(data_comunicazione_esito)) < 1990 THEN NULL
         ELSE safe_date(data_comunicazione_esito) END AS data_comunicazione_esito,
    CASE WHEN year(safe_date(data_cancellazione)) < 1990 THEN NULL
         ELSE safe_date(data_cancellazione) END AS data_cancellazione,
    TRY_CAST(cod_motivo_cancellazione AS VARCHAR) AS COD_MOTIVO_CANCELLAZIONE,
    motivo_cancellazione,
    tipo_appalto_riservato,
    CASE WHEN year(safe_date(data_ultimo_perfezionamento)) < 1990 THEN NULL
         ELSE safe_date(data_ultimo_perfezionamento) END AS data_ultimo_perfezionamento
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
