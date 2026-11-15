"""Regression test: compose ANAC cross — conteggio dei SAL in ritardo (#6).

Il flag valido nella fonte e' ``'IN RITARDO'`` (valori osservati: ``IN LINEA``,
``IN RITARDO``, ``IN ANTICIPO``). Il vecchio confronto con ``'S'`` produceva
``sal_in_ritardo = 0`` su tutte le righe.

Il compose e' mart-only (niente clean): il test costruisce i support minimi e
risolve i placeholder ``{support.*.clean}`` del mart.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MART_SQL = REPO_ROOT / "compose" / "anac-cross" / "sql" / "mart_ritardi_per_sa.sql"


def _scrivi_parquet(con: duckdb.DuckDBPyConnection, percorso: Path, sql: str) -> Path:
    con.execute(f"COPY ({sql}) TO '{percorso.as_posix()}' (FORMAT PARQUET)")
    return percorso


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
            ('CIG1', 1, 1, DATE '2025-01-10', 100.0, 'IN RITARDO', 10, 'monotona', 100.0),
            ('CIG1', 1, 2, DATE '2025-02-10', 250.0, 'IN RITARDO', CAST(NULL AS INTEGER), 'monotona', 150.0),
            ('CIG2', 2, 1, DATE '2025-03-10',  50.0, 'IN RITARDO', 20, 'singola', 50.0),
            ('CIG3', 3, 1, DATE '2025-04-10', 500.0, 'IN RITARDO', 5, 'singola', 500.0)
        ) AS t(cig, id_aggiudicazione, progressivo_sal, data_emissione_sal, importo_sal,
               flag_ritardo, n_giorni_scostamento, tipo_serie, importo_quota)
        """,
    )
    _scrivi_parquet(
        con,
        bandi / "anac_bandi_gara_2026_clean.parquet",
        """
        SELECT * FROM (VALUES
            ('CIG1', 'Comune X', 'Lavori', 'Lazio', 'CFX', FALSE),
            ('CIG2', 'Comune X', 'Lavori', 'Lazio', 'CFX', FALSE),
            ('CIG3', 'Comune X', 'Lavori', 'Lazio', 'CFX', TRUE)
        ) AS t(cig, denominazione_amministrazione_appaltante, oggetto_principale_contratto,
               sezione_regionale, cf_amministrazione_appaltante, flag_importo_sospetto)
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
    assert n_cig == 2, "i CIG con importo sospetto restano fuori dal mart"
    assert max_gg == 20.0
    assert media_gg == 15.0, "la media ignora i NULL"
    assert importo == 300.0, "le quote evitano di sommare due volte la serie cumulativa"
