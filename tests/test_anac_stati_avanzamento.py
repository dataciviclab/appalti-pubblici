"""Classificazione delle serie SAL e quote di avanzamento (#15).

``importo_sal`` puo' essere cumulativo (valore progressivo) o incrementale
(importo del singolo SAL): sommare tutte le righe gonfia i totali. ``clean.sql``
classifica ogni serie per ``id_aggiudicazione`` e calcola ``importo_quota``, il
contributo attribuito al singolo SAL.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
CLEAN_SQL = REPO_ROOT / "datasets" / "anac-stati-avanzamento" / "sql" / "clean.sql"
MART_SQL = REPO_ROOT / "datasets" / "anac-stati-avanzamento" / "sql" / "mart.sql"

MACRO_SQL = """
CREATE OR REPLACE MACRO normalize_string(val) AS NULLIF(TRIM(val::VARCHAR), '');
CREATE OR REPLACE MACRO cast_int(val) AS TRY_CAST(val AS INTEGER);
CREATE OR REPLACE MACRO cast_double(val) AS TRY_CAST(val AS DOUBLE);
"""

RAW_SQL = """
SELECT * FROM (VALUES
    ('CIG1', 'SAL 1', 'IN LINEA',   DATE '2024-01-10', 100.0,  0, 1, 1),
    ('CIG1', 'SAL 2', 'IN RITARDO', DATE '2024-06-10', 250.0, 10, 2, 1),
    ('CIG1', 'SAL 3', 'IN LINEA',   DATE '2025-01-10', 400.0,  0, 3, 1),
    ('CIG2', 'SAL 1', 'IN LINEA',   DATE '2024-02-10',  50.0,  0, 1, 2),
    ('CIG2', 'SAL 2', 'IN LINEA',   DATE '2024-08-10',  50.0,  0, 2, 2),
    ('CIG2', 'SAL 3', 'IN LINEA',   DATE '2025-02-10',  50.0,  0, 3, 2),
    ('CIG3', 'SAL 1', 'IN LINEA',   DATE '2024-03-10', 100.0,  0, 1, 3),
    ('CIG3', 'SAL 2', 'IN LINEA',   DATE '2024-09-10', 200.0,  0, 2, 3),
    ('CIG3', 'SAL 3', 'IN LINEA',   DATE '2025-03-10', 150.0,  0, 3, 3),
    ('CIG4', 'SAL 1', 'IN LINEA',   DATE '2024-04-10', 300.0,  0, 1, 4),
    ('CIG4', 'SAL 2', 'IN LINEA',   DATE '2024-10-10', 200.0,  0, 2, 4),
    ('CIG4', 'SAL 3', 'IN LINEA',   DATE '2025-04-10', 100.0,  0, 3, 4),
    ('CIG5', 'SAL 1', 'IN RITARDO', DATE '2024-05-10',  75.0,  5, 1, 5),
    ('CIG6', 'SAL 1', 'IN LINEA',   DATE '2024-05-11',  10.0,  0, 1, NULL),
    ('CIG6', 'SAL 2', 'IN LINEA',   DATE '2024-11-11',  30.0,  0, 2, NULL),
    ('CIG7', 'SAL 1', 'IN LINEA',   DATE '2024-06-01', 500.0,  0, 1, 7),
    ('CIG7', 'SAL 1', 'IN LINEA',   DATE '2024-06-01', 500.0,  0, 2, 7),
    ('CIG7', 'SAL 1', 'IN LINEA',   DATE '2024-06-01', 500.0,  0, 3, 7),
    ('CIG8', 'SAL 1', 'IN LINEA',   DATE '2024-01-01',  10.0,  0, 1, 8),
    ('CIG8', 'SAL 2', 'IN LINEA',   DATE '2024-02-01', 100.0,  0, 2, 8),
    ('CIG8', 'SAL 3', 'IN LINEA',   DATE '2024-03-01',  10.0,  0, 3, 8),
    ('CIG8', 'SAL 4', 'IN LINEA',   DATE '2024-04-01', 100.0,  0, 4, 8),
    ('CIG8', 'SAL 5', 'IN LINEA',   DATE '2024-05-01',  10.0,  0, 5, 8),
    ('CIG8', 'SAL 6', 'IN LINEA',   DATE '2024-06-01', 100.0,  0, 6, 8)
) AS t(cig, denominazione_sal, flag_ritardo, data_emissione_sal, importo_sal,
       n_giorni_scostamento, progressivo_sal, id_aggiudicazione)
"""


def _conn() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(MACRO_SQL)
    con.execute(f"CREATE TABLE raw_input AS {RAW_SQL}")
    con.execute("ALTER TABLE raw_input ADD COLUMN DATA_CERT_PAGAMENTO VARCHAR")
    con.execute("ALTER TABLE raw_input ADD COLUMN IMPORTO_CERT_PAGAMENTO VARCHAR")
    con.execute("ALTER TABLE raw_input ADD COLUMN GIORNI_PROROGA VARCHAR")
    con.execute(f"CREATE VIEW clean_input AS {CLEAN_SQL.read_text(encoding='utf-8')}")
    return con


def test_classificazione_serie_sal() -> None:
    con = _conn()
    righe = con.execute(
        """
        SELECT cig, ANY_VALUE(tipo_serie), SUM(importo_quota)
        FROM clean_input
        GROUP BY cig
        ORDER BY cig
        """
    ).fetchall()

    assert righe == [
        ("CIG1", "cumulativa", 400.0),
        ("CIG2", "incrementale", 150.0),
        ("CIG3", "ambigua", 200.0),
        ("CIG4", "incrementale", 600.0),
        ("CIG5", "singola", 75.0),
        ("CIG6", "cumulativa", 30.0),
        ("CIG7", "singola", 500.0),
        ("CIG8", "incrementale", 330.0),
    ]


def test_righe_duplicate_contano_una_volta() -> None:
    con = _conn()
    righe = con.execute(
        "SELECT tipo_serie, importo_quota FROM clean_input WHERE cig = 'CIG7' ORDER BY progressivo_sal"
    ).fetchall()

    assert righe[0] == ("singola", 500.0)
    assert all(quota == 0.0 for _, quota in righe[1:])


def test_quote_per_sal() -> None:
    con = _conn()
    righe = con.execute(
        """
        SELECT cig, progressivo_sal, importo_quota
        FROM clean_input
        WHERE cig IN ('CIG1', 'CIG3')
        ORDER BY cig, progressivo_sal
        """
    ).fetchall()

    assert righe == [
        ("CIG1", 1, 0.0),
        ("CIG1", 2, 0.0),
        ("CIG1", 3, 400.0),
        ("CIG3", 1, 0.0),
        ("CIG3", 2, 200.0),
        ("CIG3", 3, 0.0),
    ]


def test_mart_sal_non_gonfia_i_cumulativi() -> None:
    con = _conn()
    sql = MART_SQL.read_text(encoding="utf-8")
    con.execute(f"CREATE VIEW mart_sal AS {sql}")

    totali = con.execute(
        "SELECT anno, SUM(importo_totale), SUM(n_serie_ambigue) FROM mart_sal GROUP BY anno ORDER BY anno"
    ).fetchall()

    assert totali == [(2024, 1735.0, 1), (2025, 550.0, 1)]

    grezzo = con.execute(
        """
        SELECT SUM(importo_sal)
        FROM clean_input
        WHERE EXTRACT(YEAR FROM data_emissione_sal) = 2024
        """
    ).fetchone()[0]
    assert grezzo == 3195.0, "la somma grezza gonfia il 2024: il mart non deve usarla"
