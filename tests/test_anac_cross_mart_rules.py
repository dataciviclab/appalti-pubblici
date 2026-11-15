"""Regression test: regole di esecuzione e collaudo nei mart del compose.

Le regole che il vecchio clean CIG-level applicava una volta sola ora vivono
inline nei mart. Questi test le tengono ferme:

- `mart_esecuzione`: un CIG con una riga di avvio ma **senza stipula** non e'
  un contratto (il clean lo escludeva: `stipula IS NOT NULL OR ultimazione IS
  NOT NULL`). Senza il filtro `n_contratti` cresce del 22,5%;
- `mart_collaudo_ritardo`: "senza record di collaudo" e "record senza data di
  certificato" sono due cose diverse e non vanno sommate in una quota sola.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = REPO_ROOT / "compose" / "anac-cross" / "sql"


def _scrivi(con: duckdb.DuckDBPyConnection, path: Path, sql: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY ({sql}) TO '{path.as_posix()}' (FORMAT PARQUET)")
    return path.as_posix()


def _bandi(con: duckdb.DuckDBPyConnection, tmp_path: Path, cigs: list[str]) -> str:
    values = ", ".join(f"('{cig}', 2025, 'Lazio', 'Lavori', 'CFX', FALSE)" for cig in cigs)
    return _scrivi(
        con,
        tmp_path / "bandi" / "anac_bandi_gara_2026_clean.parquet",
        f"""
        SELECT * FROM (VALUES {values}) AS t(
            cig, anno_pubblicazione, sezione_regionale, oggetto_principale_contratto,
            cf_amministrazione_appaltante, flag_importo_sospetto)
        """,
    )


@pytest.mark.regression
def test_mart_esecuzione_non_conta_avvii_senza_stipula(tmp_path: Path) -> None:
    con = duckdb.connect()
    # 3 CIG contano (stipula o ultimazione), 1 no (avvio con stipula NULL).
    cigs = ["CIG_A", "CIG_B", "CIG_C", "CIG_SENZA_STIPULA"]
    bandi = _bandi(con, tmp_path, cigs)

    avvio = _scrivi(
        con,
        tmp_path / "avvio" / "anac_avvio_contratto_2026_clean.parquet",
        """
        SELECT * FROM (VALUES
            ('CIG_A', 1, DATE '2025-01-10', DATE '2025-02-01', DATE '2025-12-31'),
            ('CIG_B', 2, DATE '2025-03-10', DATE '2025-04-01', DATE '2025-12-31'),
            ('CIG_C', 3, DATE '2025-05-10', DATE '2025-06-01', DATE '2025-12-31'),
            ('CIG_SENZA_STIPULA', 4, CAST(NULL AS DATE), CAST(NULL AS DATE), CAST(NULL AS DATE))
        ) AS t(cig, id_aggiudicazione, data_stipula_contratto, data_inizio_effettiva,
               data_termine_contrattuale)
        """,
    )
    vuoto = _scrivi(
        con,
        tmp_path / "vuoto" / "vuoto_2026_clean.parquet",
        "SELECT CAST(NULL AS VARCHAR) AS cig, CAST(NULL AS DATE) AS data_effettiva_ultimazione",
    )
    agg = _scrivi(
        con,
        tmp_path / "agg" / "anac_aggiudicazioni_2026_clean.parquet",
        """
        SELECT * FROM (VALUES
            ('CIG_A', 1, 100.0, DATE '2024-11-01'),
            ('CIG_B', 2, 200.0, DATE '2025-01-01'),
            ('CIG_C', 3, 300.0, DATE '2025-03-01')
        ) AS t(cig, id_aggiudicazione, importo_aggiudicazione, data_aggiudicazione_definitiva)
        """,
    )
    sosp = _scrivi(
        con,
        tmp_path / "sosp" / "anac_sospensioni_2026_clean.parquet",
        "SELECT CAST(NULL AS VARCHAR) AS cig, CAST(NULL AS DATE) AS data_sospensione, "
        "CAST(NULL AS DATE) AS data_ripresa",
    )
    var = _scrivi(
        con,
        tmp_path / "var" / "anac_varianti_2026_clean.parquet",
        "SELECT CAST(NULL AS VARCHAR) AS cig",
    )

    sql = (SQL_DIR / "mart_esecuzione.sql").read_text(encoding="utf-8")
    for name, path in [
        ("bandi_gara", bandi),
        ("avvio_contratto", avvio),
        ("fine_contratto", vuoto),
        ("aggiudicazioni", agg),
        ("sospensioni", sosp),
        ("varianti", var),
    ]:
        sql = sql.replace(f"{{support.{name}.clean}}", path)

    righe = con.execute(sql).fetchall()
    assert len(righe) == 1
    anno, regione, settore, n_contratti, n_con_stipula, *_ = righe[0]
    assert n_contratti == 3, (
        "il CIG con avvio a stipula NULL non e' un contratto: attesi 3, "
        f"trovati {n_contratti}"
    )
    assert n_con_stipula == 3


@pytest.mark.regression
def test_mart_collaudo_separa_senza_record_da_senza_data(tmp_path: Path) -> None:
    con = duckdb.connect()
    cigs = ["CIG_NO_RECORD", "CIG_RECORD_NO_DATA", "CIG_CON_DATA"]
    bandi = _bandi(con, tmp_path, cigs)
    fine = _scrivi(
        con,
        tmp_path / "fine" / "anac_fine_contratto_2026_clean.parquet",
        """
        SELECT * FROM (VALUES
            ('CIG_NO_RECORD',      1, DATE '2026-01-10'),
            ('CIG_RECORD_NO_DATA', 2, DATE '2026-01-10'),
            ('CIG_CON_DATA',       3, DATE '2026-01-10')
        ) AS t(cig, id_aggiudicazione, data_effettiva_ultimazione)
        """,
    )
    collaudo = _scrivi(
        con,
        tmp_path / "collaudo" / "anac_collaudo_2026_clean.parquet",
        """
        SELECT * FROM (VALUES
            ('CIG_RECORD_NO_DATA', 2, CAST(NULL AS DATE), 'POSITIVO'),
            ('CIG_CON_DATA',       3, DATE '2026-03-01', 'POSITIVO')
        ) AS t(cig, id_aggiudicazione, data_cert_collaudo, esito_collaudo)
        """,
    )

    sql = (SQL_DIR / "mart_collaudo_ritardo.sql").read_text(encoding="utf-8")
    sql = sql.replace("{support.bandi_gara.clean}", bandi)
    sql = sql.replace("{support.fine_contratto.clean}", fine)
    sql = sql.replace("{support.collaudo.clean}", collaudo)

    righe = con.execute(sql).fetchall()
    assert len(righe) == 1
    (anno, regione, settore, n_opere, n_con_record, n_senza_record,
     n_record_senza_data, n_con_data, quota_record, quota_data, mediana, media) = righe[0]

    assert n_opere == 3
    assert n_con_record == 2
    assert n_senza_record == 1, "solo il CIG senza righe di collaudo"
    assert n_record_senza_data == 1, "il CIG con riga ma senza data di certificato"
    assert n_con_data == 1
    assert quota_record == pytest.approx(33.3, abs=0.1)
    assert quota_data == pytest.approx(66.7, abs=0.1)
    assert mediana == 50, "10/01 -> 01/03 sono 50 giorni"
