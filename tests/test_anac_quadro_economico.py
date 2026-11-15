"""Quadro economico ANAC: date quasi tutte NULL e importi cumulativi.

Due cose non ovvie che questo test tiene ferme:

1. `BASE_ASTA` e `CONSUNTIVO` hanno **sempre** `data` NULL: un filtro sulle date
   butterebbe via il 94% delle righe, cioe' quasi tutto il dataset;
2. gli importi sono **istantanee cumulative**, non delta: il confronto
   base/consuntivo si fa prendendo i valori, non sommandoli.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = REPO_ROOT / "datasets" / "anac-quadro-economico"
CLEAN_SQL = DATASET_DIR / "sql" / "clean.sql"
MART_CIG = DATASET_DIR / "sql" / "mart_cig.sql"
MART_EVENTI = DATASET_DIR / "sql" / "mart_eventi.sql"

MACRO_SQL = """
CREATE OR REPLACE MACRO normalize_string(val) AS NULLIF(TRIM(val::VARCHAR), '');
CREATE OR REPLACE MACRO cast_bigint(val) AS TRY_CAST(val AS BIGINT);
CREATE OR REPLACE MACRO cast_double(val) AS TRY_CAST(val AS DOUBLE);
CREATE OR REPLACE MACRO safe_date(val) AS
    CASE WHEN TRY_CAST(val AS DATE) IS NULL THEN NULL
         WHEN year(TRY_CAST(val AS DATE)) BETWEEN 1800 AND 2100 THEN TRY_CAST(val AS DATE)
         ELSE NULL END;
"""

RAW_SQL = """
SELECT * FROM (VALUES
    -- CIG_A: base + variante + consuntivo, come nella fonte (date NULL su
    -- base e consuntivo, data solo sulla variante)
    ('CIG_A', 1, NULL,           'BASE_ASTA',   100.0, 0.0, 0.0, 10.0, '000-full.csv'),
    ('CIG_A', 1, DATE '2025-03-01', 'VARIANTE', 120.0, 0.0, 0.0, 12.0, '000-full.csv'),
    ('CIG_A', 1, NULL,           'CONSUNTIVO',  130.0, 0.0, 0.0, 13.0, '001-delta.csv'),
    -- CIG_B: nel full, poi ripubblicato dal delta: vince il delta
    ('CIG_B', 2, NULL,           'BASE_ASTA',    50.0, 0.0, 0.0,  5.0, '000-full.csv'),
    ('CIG_B', 2, DATE '2025-06-01', 'VARIANTE',  60.0, 0.0, 0.0,  6.0, '000-full.csv'),
    ('CIG_B', 2, DATE '2025-07-01', 'VARIANTE',  70.0, 0.0, 0.0,  7.0, '001-delta.csv'),
    -- CIG_C: solo consuntivo su servizi, nessuna base d'asta
    ('CIG_C', 3, NULL,           'CONSUNTIVO',   0.0, 40.0, 0.0,  4.0, '000-full.csv')
) AS t(cig, id_aggiudicazione, data, descrizione_evento, importo_lavori,
       importo_servizi, importo_forniture, somme_a_disposizione, __source_file)
"""


def _conn() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(MACRO_SQL)
    con.execute(f"CREATE TABLE raw_input AS {RAW_SQL}")
    for colonna in ("dettaglio_evento", "importo_progettazione", "importo_sicurezza",
                    "ulteriori_oneri_non_soggetti_ribasso"):
        con.execute(f"ALTER TABLE raw_input ADD COLUMN {colonna} VARCHAR")
    con.execute("CREATE VIEW clean_input AS " + CLEAN_SQL.read_text(encoding="utf-8"))
    return con


@pytest.mark.regression
def test_clean_tiene_le_righe_senza_data_e_sostituisce_per_cig() -> None:
    con = _conn()
    righe = con.execute(
        "SELECT cig, descrizione_evento, data FROM clean_input ORDER BY cig, descrizione_evento"
    ).fetchall()

    # Le righe senza data restano: sarebbero il 94% del dataset reale.
    assert ("CIG_A", "BASE_ASTA", None) in righe
    assert ("CIG_A", "CONSUNTIVO", None) in righe
    # CIG_B: il delta ripubblica una sola variante, la base resta dal full.
    # Con la sostituzione per CIG la base sarebbe sparita (e' il caso reale dei
    # 1.555 CIG che nei delta non hanno BASE_ASTA).
    righe_b = sorted(r[1] for r in righe if r[0] == "CIG_B")
    assert righe_b == ["BASE_ASTA", "VARIANTE", "VARIANTE"]


@pytest.mark.regression
def test_mart_cig_confronta_base_e_consuntivo() -> None:
    con = _conn()
    cur = con.execute(MART_CIG.read_text(encoding="utf-8"))
    colonne = [c[0] for c in cur.description]
    righe = {r[colonne.index("cig")]: dict(zip(colonne, r)) for r in cur.fetchall()}

    a = righe["CIG_A"]
    assert a["importo_base"] == 100.0
    assert a["importo_finale"] == 130.0, "il consuntivo vince sul massimo osservato"
    assert a["scostamento"] == 30.0
    assert float(a["scostamento_pct"]) == pytest.approx(30.0)
    assert a["n_varianti"] == 1
    assert a["ha_consuntivo"] is True

    b = righe["CIG_B"]
    assert b["importo_base"] == 50.0, "la base sopravvive al delta che non la ripubblica"
    assert b["importo_finale"] == 70.0, "senza consuntivo vale il massimo osservato"
    assert b["n_varianti"] == 2

    assert "CIG_C" not in righe, "senza base d'asta non c'e' scostamento da misurare"


@pytest.mark.regression
def test_mart_eventi_espone_le_date_mancanti() -> None:
    con = _conn()
    cur = con.execute(MART_EVENTI.read_text(encoding="utf-8"))
    colonne = [c[0] for c in cur.description]
    righe = {r[colonne.index("descrizione_evento")]: dict(zip(colonne, r)) for r in cur.fetchall()}

    assert righe["BASE_ASTA"]["n_con_data"] == 0, "la fonte non data la base d'asta"
    assert righe["CONSUNTIVO"]["n_con_data"] == 0
    assert righe["VARIANTE"]["n_con_data"] >= 1
