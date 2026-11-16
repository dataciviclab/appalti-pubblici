"""mart_chi_paga: copertura delle fonti e composizione per macro-categoria.

Il mart unisce il contratto (`mart_cig`) alle fonti dichiarate (`mart_fonti`).
Due invarianti che il test tiene fermi:

1. **un contratto senza fonte resta contato** in `n_contratti` ma non in
   `n_con_fonte`: la copertura è dichiarata, non silenziosa;
2. le 13 voci ANAC finiscono in **7 macro-categorie** e gli importi finanziati
   non si sommano a quelli contrattuali (le fonti sono per intervento).
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MART_SQL = REPO_ROOT / "compose" / "anac-cross" / "sql" / "mart_chi_paga.sql"


def _scrivi(con: duckdb.DuckDBPyConnection, path: Path, sql: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY ({sql}) TO '{path.as_posix()}' (FORMAT PARQUET)")
    return path.as_posix()


@pytest.mark.regression
def test_chi_paga_dichiara_la_copertura_e_raggruppa_le_fonti(tmp_path: Path) -> None:
    con = duckdb.connect()

    mart_cig = _scrivi(
        con,
        tmp_path / "qe" / "mart_cig.parquet",
        """
        SELECT * FROM (VALUES
            ('CIG_A', 1,  4e9, FALSE),
            ('CIG_B', 2,  6e9, FALSE),
            -- coda della fonte: resta contato ma fuori dagli aggregati
            ('CIG_S', 3, 12e9, TRUE)
        ) AS t(cig, id_aggiudicazione, importo_base, flag_base_sospetta)
        """,
    )
    mart_fonti = _scrivi(
        con,
        tmp_path / "ff" / "mart_fonti.parquet",
        """
        SELECT * FROM (VALUES
            ('CIG_A', 1, 'fondi_bilancio_sa', 3e9),
            ('CIG_A', 1, 'entrate_vincolate_ue', 1e9)
        ) AS t(cig, id_aggiudicazione, fonte, importo)
        """,
    )
    bandi = _scrivi(
        con,
        tmp_path / "bandi" / "bandi.parquet",
        """
        SELECT * FROM (VALUES
            ('CIG_A', 2024, 'LOMBARDIA', 'LAVORI', 'CF1', FALSE),
            ('CIG_B', 2024, 'LOMBARDIA', 'LAVORI', 'CF1', FALSE),
            ('CIG_S', 2024, 'LOMBARDIA', 'LAVORI', 'CF1', FALSE)
        ) AS t(cig, anno_pubblicazione, sezione_regionale, oggetto_principale_contratto,
               cf_amministrazione_appaltante, flag_importo_sospetto)
        """,
    )
    sa = _scrivi(
        con,
        tmp_path / "sa" / "sa.parquet",
        """
        SELECT * FROM (VALUES ('CF1', 'ENTI PUBBLICI NON ECONOMICI'))
        AS t(codice_fiscale, natura_giuridica)
        """,
    )

    sql = MART_SQL.read_text(encoding="utf-8")
    for name, path in [
        ("quadro_economico", mart_cig),
        ("fonti_finanziamento", mart_fonti),
        ("bandi_gara", bandi),
        ("stazioni_appaltanti", sa),
    ]:
        sql = sql.replace(f"{{support.{name}.mart}}", path)
        sql = sql.replace(f"{{support.{name}.clean}}", path)

    # la soglia di 10 contratti per gruppo non ha senso su una fixture da 2
    sql = sql.replace("HAVING COUNT(*) >= 10", "HAVING COUNT(*) >= 1")

    cur = con.execute(sql)
    colonne = [c[0] for c in cur.description]
    righe = [dict(zip(colonne, r)) for r in cur.fetchall()]
    assert len(righe) == 1, "un solo gruppo (anno × regione × settore × natura)"

    r = righe[0]
    assert r["n_contratti"] == 3, "anche il contratto sospetto resta contato"
    assert r["n_con_fonte"] == 1, "CIG_B e CIG_S non hanno fonti: contati, ma non nella copertura"
    assert float(r["quota_con_fonte_pct"]) == pytest.approx(33.3, abs=0.1)
    assert r["n_esclusi_importo_sospetto"] == 1, "12 mld: contato e fuori dagli aggregati"
    assert float(r["importo_contrattuale_mld"]) == pytest.approx(10.0), (
        "4 + 6 mld: il contratto sospetto da 12 non entra negli aggregati"
    )

    # macro-categorie: 80 bilancio SA, 20 UE
    assert float(r["fin_bilancio_sa_mld"]) == pytest.approx(3.0)
    assert float(r["fin_ue_mld"]) == pytest.approx(1.0)
    assert float(r["fin_mutuo_mld"] or 0) == 0
    assert float(r["rapporto_finanziato_contratto"]) == pytest.approx(0.4), (
        "4 finanziati su 10 di contratti: le fonti coprono l'intervento, non la gara"
    )
    assert r["natura_sa"] == "ENTI PUBBLICI NON ECONOMICI"
