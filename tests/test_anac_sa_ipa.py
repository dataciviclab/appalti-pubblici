"""Test del bridge ANAC - IPA (CIG -> identita' canonica della stazione appaltante)."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CLEAN_SQL = REPO_ROOT / "datasets" / "anac-sa-ipa" / "sql" / "clean.sql"
MART_SQL = REPO_ROOT / "datasets" / "anac-sa-ipa" / "sql" / "mart_copertura_sa.sql"


def _scrivi_parquet(con: duckdb.DuckDBPyConnection, percorso: Path, sql: str) -> Path:
    con.execute(f"COPY ({sql}) TO '{percorso.as_posix()}' (FORMAT PARQUET)")
    return percorso


def _bandi(con: duckdb.DuckDBPyConnection, percorso: Path) -> Path:
    return _scrivi_parquet(
        con,
        percorso,
        """
        SELECT * FROM (VALUES
            ('CIG1', 'cf1', 'Comune Vecchio', 'Lazio', 2020, DATE '2020-05-01'),
            ('CIG1', 'CF1', 'Comune Nuovo',   'Lazio', 2024, DATE '2024-05-01'),
            ('CIG2', 'CF9', 'Ente Fuori IPA', 'Puglia', 2023, DATE '2023-03-01')
        ) AS t(cig, cf_amministrazione_appaltante, denominazione_amministrazione_appaltante,
               sezione_regionale, anno_pubblicazione, data_pubblicazione)
        """,
    )


def _ipa(con: duckdb.DuckDBPyConnection, percorso: Path) -> Path:
    return _scrivi_parquet(
        con,
        percorso,
        """
        SELECT * FROM (VALUES
            ('IPA002', 'cf1', 'Comune di X (dup)', 'Comuni', '058091'),
            ('IPA001', 'CF1', 'Comune di X',       'Comuni', '058091'),
            ('IPA003', 'CF3', 'Ente Senza Bandi',  'Comuni', '058092')
        ) AS t(Codice_IPA, Codice_fiscale_ente, Denominazione_ente, Tipologia, Codice_ISTAT)
        """,
    )


def _esegui_clean(tmp_path: Path) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    ipa = _ipa(con, tmp_path / "ipa.parquet")
    bandi = _bandi(con, tmp_path / "bandi.parquet")
    con.execute(f"CREATE VIEW raw_input AS SELECT * FROM read_parquet('{ipa.as_posix()}')")
    sql = CLEAN_SQL.read_text(encoding="utf-8").replace(
        "{support.bandi_gara.clean}", bandi.as_posix()
    )
    con.execute(f"CREATE VIEW esito AS {sql}")
    return con


@pytest.mark.regression
def test_clean_una_riga_per_cig_e_dedup_ipa(tmp_path: Path) -> None:
    con = _esegui_clean(tmp_path)
    righe = con.execute(
        "SELECT cig, cf_sa, codice_ipa_sa, denominazione_sa, tipologia_sa, codice_istat_sa,"
        " sezione_regionale FROM esito ORDER BY cig"
    ).fetchall()

    assert len(righe) == 2, "solo i CIG con bando entrano nel bridge"
    assert righe[0] == (
        "CIG1",
        "CF1",
        "IPA001",
        "Comune di X",
        "Comuni",
        "058091",
        "Lazio",
    ), "vince il bando piu' recente e il codice IPA piu' basso"
    assert righe[1] == (
        "CIG2",
        "CF9",
        None,
        "Ente Fuori IPA",
        None,
        None,
        "Puglia",
    ), "ente fuori IPA: resta il CF e la denominazione ANAC"


@pytest.mark.regression
def test_clean_dedup_per_cig(tmp_path: Path) -> None:
    con = _esegui_clean(tmp_path)
    duplicati = con.execute(
        "SELECT COUNT(*) FROM (SELECT cig FROM esito GROUP BY cig HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    assert duplicati == 0


@pytest.mark.regression
def test_mart_copertura_sa(tmp_path: Path) -> None:
    con = _esegui_clean(tmp_path)
    con.execute("CREATE VIEW clean_input AS SELECT * FROM esito")
    righe = con.execute(MART_SQL.read_text(encoding="utf-8")).fetchall()

    per_tipologia = {(r[0], r[1]): r[2:] for r in righe}
    assert per_tipologia[("Lazio", "Comuni")] == (1, 1, 1, 100.0)
    assert per_tipologia[("Puglia", "non in IPA")] == (1, 0, 0, 0.0)
