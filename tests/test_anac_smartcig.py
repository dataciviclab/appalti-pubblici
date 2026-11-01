"""Clean e mart di ANAC SmartCIG (affidamenti diretti sotto soglia)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CLEAN_SQL = REPO_ROOT / "datasets" / "anac-smartcig" / "sql" / "clean.sql"
MART_FASCE_SQL = REPO_ROOT / "datasets" / "anac-smartcig" / "sql" / "mart_fasce.sql"

MACRO_SQL = """
CREATE OR REPLACE MACRO normalize_string(val) AS NULLIF(TRIM(val::VARCHAR), '');
CREATE OR REPLACE MACRO cast_int(val) AS TRY_CAST(val AS INTEGER);
CREATE OR REPLACE MACRO cast_double(val) AS TRY_CAST(val AS DOUBLE);
"""

RAW_SQL = """
SELECT * FROM (VALUES
    ('CIG1', 'GARA1', 'Forniture', 800.0,  1, 'ATTIVO', DATE '2025-03-10', 1, 1),
    ('CIG1', 'GARA1', 'Forniture', 900.0,  1, 'ATTIVO', DATE '2025-05-10', 1, 5),
    ('CIG2', 'GARA2', 'Servizi',  1000.0,  1, 'ATTIVO', DATE '2025-04-01', 1, 1),
    ('CIG3', 'GARA3', 'Servizi',  5000.0,  1, 'ATTIVO', DATE '2025-04-02', 1, 1),
    ('CIG4', 'GARA4', 'Lavori',  40000.0,  1, 'ATTIVO', DATE '2025-06-02', 1, 1),
    ('CIG5', 'GARA5', 'Lavori',  40001.0,  1, 'ATTIVO', DATE '2025-06-03', 1, 1),
    ('CIG6', 'GARA6', 'Lavori',      0.0,  1, 'ATTIVO', DATE '2025-07-03', 1, 1),
    ('CIG7', 'GARA7', 'Lavori',   NULL,    1, 'ATTIVO', DATE '2025-07-04', 1, 1)
) AS t(cig, numero_gara, oggetto_gara, importo_lotto, n_lotti_componenti, stato,
       data_comunicazione, anno_comunicazione, mese_comunicazione)
"""


def _conn() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(MACRO_SQL)
    con.execute(f"CREATE TABLE raw_input AS {RAW_SQL}")
    for col in (
        "oggetto_lotto VARCHAR",
        "oggetto_principale_contratto VARCHAR",
        "importo_complessivo_gara VARCHAR",
        "id_tipo_fattispecie_contrattuale VARCHAR",
        "tipo_fattispecie_contrattuale VARCHAR",
        "cod_tipo_scelta_contraente VARCHAR",
        "tipo_scelta_contraente VARCHAR",
        "codice_ausa VARCHAR",
        "cf_amministrazione_appaltante VARCHAR",
        "denominazione_amministrazione_appaltante VARCHAR",
        "sezione_regionale VARCHAR",
        "indirizzo VARCHAR",
        "istat_comune VARCHAR",
        "citta VARCHAR",
        "regione VARCHAR",
        "id_centro_costo VARCHAR",
        "denominazione_centro_costo VARCHAR",
    ):
        con.execute(f"ALTER TABLE raw_input ADD COLUMN {col}")
    con.execute("UPDATE raw_input SET cf_amministrazione_appaltante = '80000000001'")
    con.execute(f"CREATE VIEW clean_input AS {CLEAN_SQL.read_text(encoding='utf-8')}")
    return con


@pytest.mark.regression
def test_clean_una_riga_per_cig_con_comunicazione_piu_recente() -> None:
    con = _conn()
    righe = con.execute(
        "SELECT cig, importo_lotto, data_comunicazione FROM clean_input ORDER BY cig"
    ).fetchall()

    assert len(righe) == 7
    assert righe[0] == ("CIG1", 900.0, date(2025, 5, 10))
    assert len({r[0] for r in righe}) == len(righe)


@pytest.mark.regression
def test_fasce_importo_confini() -> None:
    con = _conn()
    fasce = dict(
        con.execute(
            "SELECT cig, fascia_importo FROM clean_input ORDER BY cig"
        ).fetchall()
    )

    assert fasce["CIG1"] == "micro"
    assert fasce["CIG2"] == "piccola", "1000 e' il primo valore della fascia piccola"
    assert fasce["CIG3"] == "media", "5000 e' ancora media"
    assert fasce["CIG4"] == "media", "40000 e' il limite incluso"
    assert fasce["CIG5"] == "sopra_40k"
    assert fasce["CIG6"] == "non_valido"
    assert fasce["CIG7"] == "non_valido", "importo NULL non e' classificabile"


@pytest.mark.regression
def test_flag_sopra_140k_solo_oltre_la_soglia() -> None:
    con = _conn()
    flag = dict(
        con.execute(
            "SELECT cig, flag_sopra_140k FROM clean_input ORDER BY cig"
        ).fetchall()
    )

    assert flag["CIG4"] is False
    assert not any(flag.values()), "nessun importo di test supera i 140k"


@pytest.mark.regression
def test_mart_fasce_esclude_importi_non_validi() -> None:
    con = _conn()
    righe = con.execute(MART_FASCE_SQL.read_text(encoding="utf-8")).fetchall()
    totale_n = sum(r[1] for r in righe)
    totale_quota = round(sum(r[4] for r in righe), 2)

    assert totale_n == 5, "CIG6 e CIG7 non entrano nella distribuzione"
    assert {r[0] for r in righe} == {"micro", "piccola", "media", "sopra_40k"}
    assert abs(totale_quota - 100.0) < 0.1, "le quote sono arrotondate per fascia"
