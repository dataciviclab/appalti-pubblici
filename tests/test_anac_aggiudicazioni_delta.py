"""Aggiudicazioni: full + delta con sostituzione per CIG (regola ANAC).

Il full `aggiudicazioni_csv` e' fermo al 2026-01-15: gli aggiornamenti arrivano
solo nei delta mensili. Il Manuale open data ANAC (§5.1) dice che il delta va
acquisito "nella sua totalita', sostituendo quanto acquisito in precedenza
dalla risorsa full **per lo specifico CIG**". Quindi non basta deduplicare per
riga: per ogni CIG presente in un delta, le righe del full vanno scartate.

I file raw sono nominati `00-...` (full) e `01-...`/`02-...` (delta in ordine
cronologico) da `split_resources: true`; il clean usa `__source_file`.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = REPO_ROOT / "datasets" / "anac-aggiudicazioni"
CLEAN_SQL = DATASET_DIR / "sql" / "clean.sql"

MACRO_SQL = """
CREATE OR REPLACE MACRO normalize_string(val) AS NULLIF(TRIM(val::VARCHAR), '');
CREATE OR REPLACE MACRO cast_int(val) AS TRY_CAST(val AS INTEGER);
CREATE OR REPLACE MACRO cast_bigint(val) AS TRY_CAST(val AS BIGINT);
CREATE OR REPLACE MACRO cast_double(val) AS TRY_CAST(val AS DOUBLE);
CREATE OR REPLACE MACRO safe_date(val) AS
    CASE WHEN TRY_CAST(val AS DATE) IS NULL THEN NULL
         WHEN year(TRY_CAST(val AS DATE)) BETWEEN 1990 AND 2100 THEN TRY_CAST(val AS DATE)
         ELSE NULL END;
CREATE OR REPLACE MACRO decode_flag(val, yes_value) AS
    CASE WHEN TRIM(val::VARCHAR) = yes_value::VARCHAR THEN TRUE ELSE FALSE END;
"""

RAW_SQL = """
SELECT * FROM (VALUES
    -- full: CIG1 ha due aggiudicazioni, CIG2 una (ripetuta per errore)
    ('CIG1', '2025-01-10', '1000', '2025-01-20', 1, '00-aggiudicazioni.csv'),
    ('CIG1', '2025-03-10',  '500', '2025-03-20', 2, '00-aggiudicazioni.csv'),
    ('CIG2', '2025-02-10',  '100', '2025-02-20', 5, '00-aggiudicazioni.csv'),
    ('CIG2', '2025-02-10',  '100', '2025-02-20', 5, '00-aggiudicazioni.csv'),
    -- delta: CIG1 aggiornato (id 1) e con una nuova aggiudicazione (id 3);
    -- l'id 2 non compare piu' -> per la regola ANAC decade.
    ('CIG1', '2025-01-10', '1200', '2025-06-20', 1, '01-20260401-aggiudicazioni.csv'),
    ('CIG1', '2025-04-10',  '300', '2025-06-21', 3, '01-20260401-aggiudicazioni.csv'),
    -- data impossibile nel delta: scartata, il CIG resta con la versione full
    ('CIG3', '7436-02-12', '9999', '2026-03-01', 9, '02-20260501-aggiudicazioni.csv')
) AS t(cig, data_aggiudicazione_definitiva, importo_aggiudicazione,
       data_comunicazione_esito, id_aggiudicazione, __source_file)
"""

EXTRA_COLUMNS = (
    "esito, criterio_aggiudicazione, numero_offerte_ammesse, numero_offerte_escluse, "
    "ribasso_aggiudicazione, num_imprese_offerenti, flag_subappalto, cod_esito, "
    "num_imprese_richiedenti, asta_elettronica, num_imprese_invitate, "
    "massimo_ribasso, minimo_ribasso, FLAG_SCOMPUTO, COD_PRESTAZIONI_COMPRESE, "
    "PRESTAZIONI_COMPRESE, CIG_PROG_ESTERNA, DATA_INCARICO_PROG, DATA_CONS_PROG, "
    "COD_MODO_RIAGGIUDICAZIONE, MODO_RIAGGIUDICAZIONE, FLAG_PROC_ACCELERATA, "
    "N_MANIF_INTERESSE"
)


def _conn() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(MACRO_SQL)
    con.execute(f"CREATE TABLE raw_input AS {RAW_SQL}")
    for colonna in EXTRA_COLUMNS.split(","):
        con.execute(f"ALTER TABLE raw_input ADD COLUMN {colonna.strip()} VARCHAR")
    con.execute(f"CREATE VIEW clean_input AS {CLEAN_SQL.read_text(encoding='utf-8')}")
    return con


@pytest.mark.regression
def test_il_delta_sostituisce_il_full_per_cig() -> None:
    con = _conn()
    righe = con.execute(
        """
        SELECT id_aggiudicazione, importo_aggiudicazione
        FROM clean_input WHERE cig = 'CIG1' ORDER BY id_aggiudicazione
        """
    ).fetchall()

    # id 2 c'era solo nel full: la sostituzione per CIG lo elimina.
    assert righe == [(1, 1200.0), (3, 300.0)]


@pytest.mark.regression
def test_righe_ripetute_nella_stessa_risorsa() -> None:
    con = _conn()
    righe = con.execute(
        "SELECT count(*) FROM clean_input WHERE cig = 'CIG2'"
    ).fetchone()

    assert righe == (1,)


@pytest.mark.contract
def test_date_impossibili_scartate() -> None:
    con = _conn()
    cig3 = con.execute("SELECT count(*) FROM clean_input WHERE cig = 'CIG3'").fetchone()
    totale = con.execute("SELECT count(*) FROM clean_input").fetchone()

    assert cig3 == (0,)
    assert totale == (3,)


@pytest.mark.contract
def test_la_provenienza_non_finisce_nel_clean() -> None:
    con = _conn()
    colonne = [r[0] for r in con.execute("SELECT * FROM clean_input LIMIT 0").description]

    assert "__source_file" not in colonne
    assert "__fonte_cig" not in colonne
