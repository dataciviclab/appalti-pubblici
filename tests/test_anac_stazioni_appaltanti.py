"""Anagrafica stazioni appaltanti ANAC: chiave, codici e difetti della fonte.

Protegge le scelte di pulizia che non sono ovvie:

1. i **codici** restano testo: `codice_ausa` e `natura_giuridica_codice` hanno
   zeri iniziali (`0000323919`), un cast a intero li perderebbe;
2. la P.IVA sentinella `00000000000` diventa NULL, non un valore;
3. le SA **senza natura giuridica** restano nel clean (sono enti veri) e nel
   mart finiscono sotto `NON DICHIARATA`;
4. `data_fine` non esiste in uscita: la fonte pubblica solo la sentinella
   2099-12-31, sarebbe una colonna sempre NULL.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = REPO_ROOT / "datasets" / "anac-stazioni-appaltanti"
CLEAN_SQL = DATASET_DIR / "sql" / "clean.sql"
MART_SQL = DATASET_DIR / "sql" / "mart_natura.sql"

MACRO_SQL = """
CREATE OR REPLACE MACRO normalize_string(val) AS NULLIF(TRIM(val::VARCHAR), '');
CREATE OR REPLACE MACRO decode_flag(val, yes_value) AS
    CASE WHEN TRIM(val::VARCHAR) = yes_value::VARCHAR THEN TRUE ELSE FALSE END;
CREATE OR REPLACE MACRO safe_date(val) AS
    CASE WHEN TRY_CAST(val AS DATE) IS NULL THEN NULL
         WHEN year(TRY_CAST(val AS DATE)) BETWEEN 1800 AND 2100 THEN TRY_CAST(val AS DATE)
         ELSE NULL END;
"""

RAW_SQL = """
SELECT * FROM (VALUES
    -- SA normale: AUSA e natura con zero iniziale, P.IVA reale
    (' 80106870159 ', '01111111111', 'ISTITUTO PARETO', '0000323919', '15',
     'ENTI PUBBLICI NON ECONOMICI', 'false', 'IT-MI', 'MILANO', '015146', 'MILANO',
     'VIA LITTA 55', '20161', 'false', 'false', 'ATTIVO', '2013-07-09 19:19:04.143'),
    -- SA senza natura giuridica: i campi sono vuoti nella fonte
    ('04634700241', '04634700241', 'COMUNE CASTEGNERO NANTO', '0000765156', NULL,
     NULL, 'false', NULL, NULL, NULL, 'COLMURANO', NULL, NULL, 'false', 'false',
     'ATTIVO', '2026-02-27 13:19:58.27'),
    -- P.IVA sentinella e flag a "true" (oggi nessuna riga li ha, domani chissà)
    ('94134700213', '00000000000', 'FACHSCHULE HASLACH', '0000560852', '10',
     'ALTRI ENTI', 'true', 'IT-BZ', 'BOLZANO', '021008', 'BOLZANO', 'PIAZZA 14',
     '39100', 'true', 'true', 'CESSATO', '2017-02-06 17:18:45.623'),
    -- denominazione vuota: resta (la chiave c'e'), ma senza nome
    ('00613760677', NULL, NULL, '0000258556', '24', 'SOCIETA IN NOME COLLETTIVO',
     'false', 'IT-TE', 'TERAMO', '067041', 'TERAMO', 'VIA ROMAGNA 24', '64100',
     'false', 'false', 'ATTIVO', '2022-12-13 09:39:59.343')
) AS t(codice_fiscale, partita_iva, denominazione, codice_ausa,
       natura_giuridica_codice, natura_giuridica_descrizione, soggetto_estero,
       provincia_codice, provincia_nome, citta_codice, citta_nome, indirizzo_odonimo,
       cap, flag_inHouse, flag_partecipata, stato, data_inizio)
"""


def _conn() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(MACRO_SQL)
    con.execute(f"CREATE TABLE raw_input AS {RAW_SQL}")
    con.execute("CREATE VIEW clean_input AS " + CLEAN_SQL.read_text(encoding="utf-8"))
    return con


@pytest.mark.regression
def test_anagrafica_conserva_codici_e_tiene_le_sa_senza_natura() -> None:
    con = _conn()
    cur = con.execute("SELECT * FROM clean_input")
    colonne = [c[0] for c in cur.description]
    righe = {r[colonne.index("codice_fiscale")]: dict(zip(colonne, r)) for r in cur.fetchall()}

    assert len(righe) == 4, "nessuna SA viene scartata: sono enti reali"

    normale = righe["80106870159"]
    assert normale["codice_ausa"] == "0000323919", "AUSA resta testo, zeri iniziali compresi"
    assert normale["natura_giuridica_codice"] == "15"
    assert normale["partita_iva"] == "01111111111"

    senza_natura = righe["04634700241"]
    assert senza_natura["natura_giuridica"] is None

    sentinella = righe["94134700213"]
    assert sentinella["partita_iva"] is None, "00000000000 e' un sentinella, non una P.IVA"
    assert sentinella["flag_inhouse"] is True, "i flag si decodificano se la fonte li popola"
    assert sentinella["flag_partecipata"] is True

    assert "data_fine" not in colonne, (
        "data_fine e' solo sentinella 2099-12-31 nella fonte: niente colonna sempre NULL"
    )


@pytest.mark.regression
def test_mart_natura_conta_anche_le_non_dichiarate() -> None:
    con = _conn()
    sql = MART_SQL.read_text(encoding="utf-8")
    righe = con.execute(sql).fetchall()
    per_natura = {r[0]: r[1] for r in righe}

    assert per_natura.get("NON DICHIARATA") == 1
    assert sum(per_natura.values()) == 4, "il mart non deve perdere righe"
