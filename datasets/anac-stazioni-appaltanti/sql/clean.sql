-- Anagrafica ANAC stazioni appaltanti — CLEAN
-- Macro toolkit: normalize_string, decode_flag, safe_date
--
-- I codici sono codici, non misure: `natura_giuridica_codice` e `codice_ausa`
-- restano VARCHAR (il valore pubblicato ha zeri iniziali, es. "0000323919").
SELECT
    normalize_string(codice_fiscale) AS codice_fiscale,
    -- P.IVA sentinella "00000000000" = non dichiarata: NULL, non un valore.
    NULLIF(normalize_string(partita_iva), '00000000000') AS partita_iva,
    normalize_string(denominazione) AS denominazione,
    normalize_string(codice_ausa) AS codice_ausa,
    normalize_string(natura_giuridica_codice) AS natura_giuridica_codice,
    normalize_string(natura_giuridica_descrizione) AS natura_giuridica,
    -- In questo export i tre flag sono "false" su tutte le righe (verificato):
    -- li decodifichiamo comunque, cosi' il giorno in cui ANAC li popola il
    -- clean li espone senza cambiare schema.
    decode_flag(soggetto_estero, 'true') AS soggetto_estero,
    decode_flag(flag_inHouse, 'true') AS flag_inhouse,
    decode_flag(flag_partecipata, 'true') AS flag_partecipata,
    normalize_string(provincia_codice) AS provincia_codice,
    normalize_string(provincia_nome) AS provincia,
    normalize_string(citta_codice) AS citta_codice,
    normalize_string(citta_nome) AS citta,
    normalize_string(indirizzo_odonimo) AS indirizzo,
    normalize_string(cap) AS cap,
    normalize_string(stato) AS stato,
    -- Nota: `data_fine` non entra. La fonte pubblica solo la sentinella
    -- 2099-12-31 (100% delle righe, anche per le cessate): sarebbe una colonna
    -- sempre NULL. L'informazione utile e' `stato` (ATTIVO / CESSATO).
    safe_date(data_inizio) AS data_inizio
FROM raw_input
WHERE codice_fiscale IS NOT NULL AND TRIM(codice_fiscale) != ''
