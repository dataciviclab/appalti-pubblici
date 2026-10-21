"""Regression test: compose ANAC cross — conteggio dei SAL in ritardo (#6).

Il flag valido nella fonte e' ``'IN RITARDO'`` (valori osservati: ``IN LINEA``,
``IN RITARDO``, ``IN ANTICIPO``). Il vecchio confronto con ``'S'`` produceva
``sal_in_ritardo = 0`` su tutte le righe.

Il test costruisce support minimi e risolve i placeholder ``{support.*.clean}``
del compose, cosi' resta valido quando cambia il set di support.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CLEAN_SQL = REPO_ROOT / "compose" / "anac-cross" / "sql" / "clean.sql"
MART_SQL = REPO_ROOT / "compose" / "anac-cross" / "sql" / "mart_ritardi_per_sa.sql"

def _scrivi_parquet(con: duckdb.DuckDBPyConnection, percorso: Path, sql: str) -> Path:
    con.execute(f"COPY ({sql}) TO '{percorso.as_posix()}' (FORMAT PARQUET)")
    return percorso


def _aggiudicazioni(con: duckdb.DuckDBPyConnection, percorso: Path) -> Path:
    return _scrivi_parquet(
        con,
        percorso,
        """
        SELECT * FROM (VALUES
            ('CIG1', 1, 1000.0, DATE '2025-01-01', FALSE, 3, 2),
            ('CIG2', 2,  500.0, DATE '2025-02-01', TRUE,  1, 1),
            ('CIG3', 3,  100.0, DATE '2025-03-01', FALSE, 1, 1),
            ('CIG4', 4,  100.0, DATE '2025-04-01', FALSE, 1, 1)
        ) AS t(cig, id_aggiudicazione, importo_aggiudicazione, data_aggiudicazione_definitiva,
               flag_subappalto, num_imprese_offerenti, numero_offerte_ammesse)
        """,
    )


def _stati_avanzamento(con: duckdb.DuckDBPyConnection, percorso: Path) -> Path:
    return _scrivi_parquet(
        con,
        percorso,
        """
        SELECT * FROM (VALUES
            ('CIG1', 1, 1, DATE '2025-01-10', 100.0, 'IN LINEA'),
            ('CIG1', 1, 2, DATE '2025-02-10', 250.0, 'IN RITARDO'),
            ('CIG2', 2, 1, DATE '2025-03-10',  50.0, 'IN RITARDO'),
            ('CIG3', 3, 1, DATE '2025-03-15',  10.0, 'S'),
            ('CIG4', 4, 1, CAST(NULL AS DATE), 75.0, 'IN RITARDO')
        ) AS t(cig, id_aggiudicazione, progressivo_sal, data_emissione_sal, importo_sal, flag_ritardo)
        """,
    )


def _supporti(con: duckdb.DuckDBPyConnection, tmp_path: Path) -> dict[str, Path]:
    vuoto = {
        "aggiudicatari": "SELECT 'CIG1' AS cig, '111' AS codice_fiscale, 'Impresa A' AS denominazione",
        "partecipanti": "SELECT 'CIG1' AS cig, '111' AS codice_fiscale",
        "subappalti": "SELECT 'CIG1' AS cig, '222' AS codice_fiscale",
        "collaudo": (
            "SELECT 'CIG1' AS cig, 'positivo' AS esito_collaudo, CAST(NULL AS DATE) AS data_cert_collaudo, "
            "CAST(NULL AS DOUBLE) AS riserve_avanzate, CAST(NULL AS DOUBLE) AS importo_contenz_risolto"
        ),
        "cup": "SELECT 'CIG1' AS cig, 'CUP1' AS cup",
        "avvio_contratto": (
            "SELECT CAST(NULL AS VARCHAR) AS cig, CAST(NULL AS DATE) AS data_stipula_contratto, "
            "CAST(NULL AS DATE) AS data_inizio_effettiva, "
            "CAST(NULL AS DATE) AS data_termine_contrattuale WHERE FALSE"
        ),
        "fine_contratto": (
            "SELECT CAST(NULL AS VARCHAR) AS cig, "
            "CAST(NULL AS DATE) AS data_effettiva_ultimazione, "
            "CAST(NULL AS DATE) AS data_conclusione_anticipata, "
            "CAST(NULL AS VARCHAR) AS motivo_risoluzione, "
            "CAST(NULL AS VARCHAR) AS motivo_interruzione_anticipata WHERE FALSE"
        ),
        "sospensioni": (
            "SELECT CAST(NULL AS VARCHAR) AS cig, CAST(NULL AS DATE) AS data_sospensione, "
            "CAST(NULL AS DATE) AS data_ripresa WHERE FALSE"
        ),
        "varianti": (
            "SELECT CAST(NULL AS VARCHAR) AS cig, CAST(NULL AS BIGINT) AS id_variante, "
            "CAST(NULL AS VARCHAR) AS cig_proroga WHERE FALSE"
        ),
    }
    percorsi = {nome: _scrivi_parquet(con, tmp_path / f"{nome}.parquet", sql) for nome, sql in vuoto.items()}
    percorsi["stati_avanzamento"] = _stati_avanzamento(con, tmp_path / "stati_avanzamento.parquet")
    return percorsi


def _esegui_clean(tmp_path: Path) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    aggiudicazioni = _aggiudicazioni(con, tmp_path / "aggiudicazioni.parquet")
    con.execute(f"CREATE VIEW raw_input AS SELECT * FROM read_parquet('{aggiudicazioni.as_posix()}')")
    sql = CLEAN_SQL.read_text(encoding="utf-8")
    for nome, percorso in _supporti(con, tmp_path).items():
        sql = sql.replace(f"{{support.{nome}.clean}}", percorso.as_posix())
    con.execute(f"CREATE VIEW esito AS {sql}")
    return con


def _per_cig(con: duckdb.DuckDBPyConnection, colonne: str) -> dict[str, tuple]:
    righe = con.execute(f"SELECT cig, {colonne} FROM esito").fetchall()
    return {riga[0]: riga[1:] for riga in righe}


@pytest.mark.regression
def test_sal_in_ritardo_usa_il_flag_della_fonte(tmp_path: Path) -> None:
    con = _esegui_clean(tmp_path)
    esiti = _per_cig(con, "n_sal, sal_in_ritardo, importo_totale_sal")

    assert esiti["CIG1"] == (2, 1, 350.0)
    assert esiti["CIG2"] == (1, 1, 50.0)
    assert esiti["CIG3"] == (1, 0, 10.0), "il flag legacy 'S' non deve essere conteggiato"
    assert esiti["CIG4"] == (0, 0, 0.0), "SAL senza data di emissione escluso dal conteggio"


@pytest.mark.regression
def test_mart_ritardi_conta_anche_sal_senza_giorni(tmp_path: Path) -> None:
    con = duckdb.connect()
    clean = tmp_path / "data" / "clean" / "anac_stati_avanzamento" / "2026"
    bandi = tmp_path / "data" / "clean" / "anac_bandi_gara" / "2026"
    clean.mkdir(parents=True)
    bandi.mkdir(parents=True)

    _scrivi_parquet(
        con,
        clean / "anac_stati_avanzamento_2026_clean.parquet",
        """
        SELECT * FROM (VALUES
            ('CIG1', 1, 1, DATE '2025-01-10', 100.0, 'IN RITARDO', 10),
            ('CIG1', 1, 2, DATE '2025-02-10', 250.0, 'IN RITARDO', CAST(NULL AS INTEGER)),
            ('CIG2', 2, 1, DATE '2025-03-10',  50.0, 'IN RITARDO', 20)
        ) AS t(cig, id_aggiudicazione, progressivo_sal, data_emissione_sal, importo_sal,
               flag_ritardo, n_giorni_scostamento)
        """,
    )
    _scrivi_parquet(
        con,
        bandi / "anac_bandi_gara_2026_clean.parquet",
        """
        SELECT * FROM (VALUES
            ('CIG1', 'Comune X', 'Lavori', 'Lazio', 'CFX'),
            ('CIG2', 'Comune X', 'Lavori', 'Lazio', 'CFX')
        ) AS t(cig, denominazione_amministrazione_appaltante, oggetto_principale_contratto,
               sezione_regionale, cf_amministrazione_appaltante)
        """,
    )

    sql = MART_SQL.read_text(encoding="utf-8")
    sql = sql.replace(
        "{support.stati_avanzamento.clean}",
        (clean / "anac_stati_avanzamento_2026_clean.parquet").as_posix(),
    )
    sql = sql.replace(
        "{support.bandi_gara.clean}",
        (bandi / "anac_bandi_gara_2026_clean.parquet").as_posix(),
    )
    righe = con.execute(sql).fetchall()

    assert len(righe) == 1
    sa, settore, regione, n_ritardi, n_cig, max_gg, media_gg, importo = righe[0]
    assert (sa, settore, regione) == ("Comune X", "Lavori", "Lazio")
    assert n_ritardi == 3, "il SAL in ritardo senza n_giorni_scostamento va contato"
    assert n_cig == 2
    assert max_gg == 20.0
    assert media_gg == 15.0, "la media ignora i NULL"
    assert importo == 400.0
