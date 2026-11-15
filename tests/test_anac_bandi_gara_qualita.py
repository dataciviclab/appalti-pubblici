"""Qualita' della fonte ANAC nei bandi: duplicati, importi appiattiti, tipo di numero_gara.

Tre difetti verificati sull'export ANAC (novembre 2026):

1. la fonte ripete righe identiche nello stesso export (fino a 10 volte su un CIG);
2. alcune righe hanno i separatori degli importi appiattiti (``9.400.334,903`` ->
   ``9400334903``): un lotto da oltre un miliardo non e' credibile e gonfia i totali;
3. ``numero_gara`` e' numerico negli anni vecchi e alfanumerico dal 2024, quindi il
   parquet cambia tipo per anno e le query cross-anno falliscono.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = REPO_ROOT / "datasets" / "anac-bandi-gara"
CLEAN_SQL = DATASET_DIR / "sql" / "clean.sql"
MART_SQL = DATASET_DIR / "sql" / "mart.sql"

MACRO_SQL = """
CREATE OR REPLACE MACRO normalize_string(val) AS NULLIF(TRIM(val::VARCHAR), '');
CREATE OR REPLACE MACRO cast_int(val) AS TRY_CAST(val AS INTEGER);
CREATE OR REPLACE MACRO cast_double(val) AS TRY_CAST(val AS DOUBLE);
CREATE OR REPLACE MACRO decode_flag(val, yes_value) AS
    CASE WHEN TRIM(val::VARCHAR) = yes_value::VARCHAR THEN TRUE ELSE FALSE END;
"""

# Solo le colonne usate dalle asserzioni: le altre, lette ma non valorizzate,
# vengono aggiunte come VARCHAR come farebbe il reader in config_only.
RAW_COLUMNS = (
    "cig, numero_gara, oggetto_gara, importo_complessivo_gara, n_lotti_componenti, "
    "oggetto_lotto, importo_lotto, anno_pubblicazione, mese_pubblicazione, "
    "data_pubblicazione, data_ultimo_perfezionamento, esito, "
    "cf_amministrazione_appaltante, oggetto_principale_contratto, FLAG_PNRR_PNC"
)

RAW_SQL = f"""
SELECT * FROM (VALUES
    -- CIG_A: due righe identiche nello stesso export (duplicato della fonte)
    ('CIG_A', '123456', 'GARA A', '1500000', '1', 'LOTTO A', '1500000', '2024', '3',
     '2024-03-01', '2024-03-01', 'AGGIUDICATA', 'CF1', 'LAVORI', '0'),
    ('CIG_A', '123456', 'GARA A', '1500000', '1', 'LOTTO A', '1500000', '2024', '3',
     '2024-03-01', '2024-03-01', 'AGGIUDICATA', 'CF1', 'LAVORI', '0'),
    -- CIG_B: importo con i separatori appiattiti dalla fonte (9.400.334,903)
    ('CIG_B', 'CONSIP_RDO_4955828', 'GARA B', '9400334903', '1', 'LOTTO B',
     '9400334903', '2024', '9', '2024-09-16', '2024-09-12', 'AGGIUDICATA',
     'CF2', 'FORNITURE', '0'),
    -- CIG_C: due comunicazioni con importo diverso, vince la piu' recente
    ('CIG_C', '789', 'GARA C', '300000', '1', 'LOTTO C', '250000', '2024', '5',
     '2024-05-10', '2024-05-01', 'AGGIUDICATA', 'CF3', 'SERVIZI', '0'),
    ('CIG_C', '789', 'GARA C', '300000', '1', 'LOTTO C', '300000', '2024', '6',
     '2024-06-10', '2024-06-01', 'AGGIUDICATA', 'CF3', 'SERVIZI', '0'),
    -- CIG_D: separatori appiattiti sotto il miliardo (16.236,51 -> 1623651):
    -- il lotto "supera" la gara di 100 volte
    ('CIG_D', '999', 'GARA D', '16236.51', '1', 'LOTTO D', '1623651', '2024', '7',
     '2024-07-10', '2024-07-01', 'AGGIUDICATA', 'CF4', 'SERVIZI', '0'),
    -- CIG_E: pubblicato nel 2023, non deve entrare nella partizione 2024
    ('CIG_E', '888', 'GARA E', '500000', '1', 'LOTTO E', '500000', '2023', '11',
     '2023-11-10', '2023-11-01', 'AGGIUDICATA', 'CF5', 'LAVORI', '0')
) AS t({RAW_COLUMNS})
"""

EXTRA_COLUMNS = (
    "cig_accordo_quadro, cig_collegamento, cui_programma, "
    "stato, settore, luogo_istat, provincia, data_scadenza_offerta, "
    "cod_tipo_scelta_contraente, tipo_scelta_contraente, cod_modalita_realizzazione, "
    "modalita_realizzazione, codice_ausa, denominazione_amministrazione_appaltante, "
    "sezione_regionale, id_centro_costo, denominazione_centro_costo, cod_cpv, "
    "descrizione_cpv, FLAG_URGENZA, FLAG_DELEGA, cod_modalita_indizione_speciali, "
    "modalita_indizione_speciali, cod_modalita_indizione_servizi, "
    "modalita_indizione_servizi, durata_prevista, cod_strumento_svolgimento, "
    "strumento_svolgimento, cod_motivo_urgenza, motivo_urgenza, funzioni_delegate, "
    "cf_sa_delegante, denominazione_sa_delegante, cf_sa_delegata, "
    "denominazione_sa_delegata, importo_sicurezza, cod_esito, "
    "data_comunicazione_esito, data_cancellazione, cod_motivo_cancellazione, "
    "motivo_cancellazione, tipo_appalto_riservato"
)


def _conn() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(MACRO_SQL)
    con.execute(f"CREATE TABLE raw_input AS {RAW_SQL}")
    for colonna in EXTRA_COLUMNS.split(","):
        con.execute(f"ALTER TABLE raw_input ADD COLUMN {colonna.strip()} VARCHAR")
    con.execute(
        "CREATE VIEW clean_input AS " + CLEAN_SQL.read_text(encoding="utf-8").replace("{year}", "2024")
    )
    return con


@pytest.mark.regression
def test_dedup_righe_identiche_della_fonte() -> None:
    con = _conn()
    righe = con.execute(
        "SELECT cig, count(*) FROM clean_input GROUP BY cig ORDER BY cig"
    ).fetchall()

    assert righe == [("CIG_A", 1), ("CIG_B", 1), ("CIG_C", 1), ("CIG_D", 1)]


@pytest.mark.regression
def test_importo_sospetto_tracciato_ma_non_riscritto() -> None:
    con = _conn()
    riga = con.execute(
        """
        SELECT importo_lotto, flag_importo_sospetto
        FROM clean_input WHERE cig = 'CIG_B'
        """
    ).fetchone()

    # Il valore pubblicato resta: la fonte non permette di ricostruirlo con certezza.
    assert riga == (9_400_334_903.0, True)


@pytest.mark.regression
def test_importo_appiattito_sotto_il_miliardo() -> None:
    con = _conn()
    riga = con.execute(
        """
        SELECT importo_lotto, flag_importo_sospetto
        FROM clean_input WHERE cig = 'CIG_D'
        """
    ).fetchone()

    # Il lotto non puo' valere 100 volte la gara: firma dei separatori appiattiti.
    assert riga == (1_623_651.0, True)


@pytest.mark.regression
def test_vince_la_comunicazione_piu_recente() -> None:
    con = _conn()
    importo = con.execute(
        "SELECT importo_lotto FROM clean_input WHERE cig = 'CIG_C'"
    ).fetchone()

    assert importo == (300_000.0,)


@pytest.mark.contract
def test_numero_gara_sempre_varchar() -> None:
    con = _conn()
    tipi = con.execute(
        "SELECT DISTINCT typeof(numero_gara) FROM clean_input"
    ).fetchall()
    valori = con.execute(
        "SELECT numero_gara FROM clean_input WHERE cig = 'CIG_B'"
    ).fetchone()

    assert tipi == [("VARCHAR",)]
    assert valori == ("CONSIP_RDO_4955828",)


@pytest.mark.contract
def test_mart_esclude_e_dichiara_gli_importi_sospetti() -> None:
    con = _conn()
    con.execute("CREATE VIEW mart_annuale AS " + MART_SQL.read_text(encoding="utf-8"))
    riga = con.execute(
        """
        SELECT anno, importo_totale, n_importi_sospetti, importo_sospetti
        FROM mart_annuale
        """
    ).fetchone()

    assert riga == (2024, 1_800_000.0, 2, 9_400_334_903.0 + 1_623_651.0)
