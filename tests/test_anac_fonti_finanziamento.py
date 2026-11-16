"""Fonti di finanziamento ANAC: chiave, forma larga/lunga, casi limite.

Tre cose non ovvie che il test tiene ferme:

1. la chiave è `(cig, id_aggiudicazione)` e i delta ripubblicano le righe:
   vince la risorsa più recente;
2. le voci non sono mutuamente esclusive — `totale_fonti` somma, `n_fonti` conta,
   `fonte_prevalente` è la maggiore;
3. una riga con tutte le voci a zero è «dato assente» (NULL), non
   «finanziato da nessuno»; e la coda degli importi assurdi resta fuori dal mart.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = REPO_ROOT / "datasets" / "anac-fonti-finanziamento"
CLEAN_SQL = DATASET_DIR / "sql" / "clean.sql"
MART_SQL = DATASET_DIR / "sql" / "mart_fonti.sql"

MACRO_SQL = """
CREATE OR REPLACE MACRO normalize_string(val) AS NULLIF(TRIM(val::VARCHAR), '');
CREATE OR REPLACE MACRO cast_bigint(val) AS TRY_CAST(val AS BIGINT);
CREATE OR REPLACE MACRO cast_double(val) AS TRY_CAST(val AS DOUBLE);
"""

RAW_SQL = """
-- ordine delle colonne = ordine della fonte, come nel CSV ANAC
SELECT * FROM (VALUES
    ('CIG_A', 1, '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '100', '50', '0', '000-full.csv'),
    ('CIG_B', 2, '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0',   '0',  '0', '000-full.csv'),
    ('CIG_C', 3, '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '2000000000', '0', '0', '000-full.csv'),
    ('CIG_A', 1, '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '120', '50', '0', '001-delta.csv')
) AS t(
    cig, id_aggiudicazione,
    entrate_con_dest_vincolata_pubblica_nazionale_regionale,
    trasferimento_di_immobili_ex_art53_c6_dlgs_n163_06_economia_su_stanziamenti_non_vincolati,
    fondi_di_bilancio_dellamministrazione_competente,
    mutuo,
    entrate_con_dest_vincolata_pubblica_nazionale_centrale,
    entrate_con_dest_vincolata_pubblica_nazionale_locale,
    altro,
    entrate_con_dest_vincolata_pubblica_nazionale_altri,
    apporto_di_capitali_privati,
    sfruttamento_economico_e_funzionale_del_bene,
    fondi_di_bilancio_della_stazione_appaltante,
    entrate_con_dest_vincolata_pubblica_comunitaria,
    entrate_con_dest_vincolata_privati,
    __source_file
)
"""


def _conn() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(MACRO_SQL)
    con.execute(f"CREATE TABLE raw_input AS {RAW_SQL}")
    con.execute("CREATE VIEW clean_input AS " + CLEAN_SQL.read_text(encoding="utf-8"))
    return con


@pytest.mark.regression
def test_clean_deduplica_per_chiave_e_calcola_totale() -> None:
    con = _conn()
    cur = con.execute("SELECT * FROM clean_input ORDER BY cig")
    colonne = [c[0] for c in cur.description]
    righe = {r[colonne.index("cig")]: dict(zip(colonne, r)) for r in cur.fetchall()}

    assert len(righe) == 3, "una riga per chiave: il delta sostituisce il full"

    a = righe["CIG_A"]
    assert a["fondi_bilancio_sa"] == 120.0, "vince la risorsa più recente"
    assert a["totale_fonti"] == 170.0
    assert a["n_fonti"] == 2
    assert a["fonte_prevalente"] == "bilancio stazione appaltante"

    b = righe["CIG_B"]
    assert b["totale_fonti"] == 0
    assert b["fonte_prevalente"] is None, "tutte le voci a zero = dato assente"
    assert b["flag_fonti_sospette"] is False

    c = righe["CIG_C"]
    assert c["flag_fonti_sospette"] is True, "2 mld dichiarati: coda da escludere"


@pytest.mark.regression
def test_mart_lungo_una_riga_per_fonte_valorizzata() -> None:
    con = _conn()
    cur = con.execute(MART_SQL.read_text(encoding="utf-8"))
    colonne = [c[0] for c in cur.description]
    righe = [dict(zip(colonne, r)) for r in cur.fetchall()]

    # CIG_A -> 2 fonti valorizzate, CIG_B -> nessuna, CIG_C -> escluso dal flag
    assert len(righe) == 2, f"attese 2 righe (CIG_A x 2 fonti), trovate {len(righe)}"
    assert {r["fonte"] for r in righe} == {"fondi_bilancio_sa", "entrate_vincolate_ue"}
    assert {r["cig"] for r in righe} == {"CIG_A"}
    assert all(float(r["importo"]) > 0 for r in righe)
