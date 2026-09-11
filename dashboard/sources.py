"""Data sources — usa load_mart_table / query_clean da lab_connectors.

anni e dataset derivati dal registry (registry.json).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
from lab_connectors.duckdb.queries import load_mart_table, query_clean, years_from_registry
from lab_connectors.duckdb.core import safe_connect
from lab_connectors.formatters import fmt_num
from lab_connectors.registry import load_registry

ROOT = Path(__file__).parent.parent
PREFIX = "appalti_pubblici/"
_data_dir = ROOT / "out" / "data"
LOCAL_ROOT = str(_data_dir) if _data_dir.is_dir() and any(_data_dir.rglob("*.parquet")) else None

# ── Registry-driven config ───────────────────────────────────────────────────

_registry = load_registry(ROOT / "registry" / "registry.json")
_all_years = years_from_registry(_registry)
YEARS_BANDI = list(range(min(_all_years), max(_all_years) + 1)) if _all_years else list(range(2016, 2026))
YEARS_SNAPSHOT = [2026]

# ── Dataset registry (per SQL page) ───────────────────────────────────────────

DATASETS = {
    "anac_bandi_gara": {"label": "Bandi di Gara", "years": YEARS_BANDI},
    "anac_aggiudicazioni": {"label": "Aggiudicazioni", "years": YEARS_SNAPSHOT},
    "anac_aggiudicatari": {"label": "Aggiudicatari", "years": YEARS_SNAPSHOT},
    "anac_partecipanti": {"label": "Partecipanti", "years": YEARS_SNAPSHOT},
    "anac_subappalti": {"label": "Subappalti", "years": YEARS_SNAPSHOT},
    "anac_stati_avanzamento": {"label": "Stati di Avanzamento", "years": YEARS_SNAPSHOT},
    "anac_collaudo": {"label": "Collaudo", "years": YEARS_SNAPSHOT},
    "anac_cup": {"label": "CUP", "years": YEARS_SNAPSHOT},
}

# ── Core loaders (lab-connectors) ───────────────────────────────────────────


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart(table: str, year: int = 2026, slug: str = "") -> pd.DataFrame:
    return load_mart_table(slug or table, table, year, prefix=PREFIX, local_root=LOCAL_ROOT)


@st.cache_data(ttl=3600, show_spinner=False)
def query(sql: str, years: list[int] | None = None, slug: str = "anac_bandi_gara") -> pd.DataFrame:
    if years is None:
        years = DATASETS.get(slug, {}).get("years", YEARS_SNAPSHOT)
    return query_clean(slug, sql, years, prefix=PREFIX, local_root=LOCAL_ROOT)


@st.cache_data(ttl=3600, show_spinner=False)
def query_duckdb(sql: str) -> pd.DataFrame:
    """Esegui SQL arbitrario su più parquet con DuckDB safe_connect."""
    with safe_connect() as con:
        return con.sql(sql).df()


# ── Panoramica ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_annuale_bandi() -> pd.DataFrame:
    return load_mart("mart_annuale", year=max(YEARS_BANDI), slug="anac_bandi_gara")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_top_stazioni(year: int = 2025) -> pd.DataFrame:
    return load_mart("mart_top_stazioni", year=year, slug="anac_bandi_gara")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_trend_pnrr(year: int = 2025) -> pd.DataFrame:
    return load_mart("mart_trend_pnrr", year=year, slug="anac_bandi_gara")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_esiti_procedura(year: int = 2025) -> pd.DataFrame:
    return load_mart("mart_esiti_per_procedura", year=year, slug="anac_bandi_gara")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_trend_settore(year: int = 2025) -> pd.DataFrame:
    return load_mart("mart_trend_settore", year=year, slug="anac_bandi_gara")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_annuale_agg() -> pd.DataFrame:
    return load_mart("mart_annuale", year=2026, slug="anac_aggiudicazioni")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_top_aggiudicatari() -> pd.DataFrame:
    return load_mart("mart_top_aggiudicatari", year=2026, slug="anac_aggiudicatari")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_cup() -> pd.DataFrame:
    return load_mart("mart_cup", year=2026, slug="anac_cup")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_sal() -> pd.DataFrame:
    return load_mart("mart_sal", year=2026, slug="anac_stati_avanzamento")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_collaudo() -> pd.DataFrame:
    return load_mart("mart_collaudo", year=2026, slug="anac_collaudo")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_top_subappalti() -> pd.DataFrame:
    return load_mart("mart_top_subappalti", year=2026, slug="anac_subappalti")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_top_partecipanti() -> pd.DataFrame:
    return load_mart("mart_top_partecipanti", year=2026, slug="anac_partecipanti")


# ── Compose (anac_cross) ───────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_compose_panoramica() -> pd.DataFrame:
    return load_mart("mart_panoramica", year=2026, slug="anac_cross")


@st.cache_data(ttl=3600, show_spinner=False)
def load_compose_panoramica_annuale() -> pd.DataFrame:
    df = load_compose_panoramica()
    if df.empty:
        return df
    return (
        df.groupby("anno")
        .agg(
            n_cig=("n_cig", "sum"),
            n_lotti=("n_lotti", "sum"),
            importo_totale=("importo_lotto_totale", "sum"),
            n_stazioni_appaltanti=("n_stazioni_appaltanti", "sum"),
            n_pnrr=("n_pnrr", "sum"),
            importo_pnrr=("importo_pnrr", "sum"),
            n_aggiudicati=("n_aggiudicati", "sum"),
            importo_aggiudicati=("importo_aggiudicati", "sum"),
            n_settori=("settore", "nunique"),
        )
        .reset_index()
        .sort_values("anno")
    )


@st.cache_data(ttl=3600, show_spinner=False)
def load_compose_lifecycle() -> pd.DataFrame:
    return load_mart("mart_lifecycle", year=2026, slug="anac_cross")


@st.cache_data(ttl=3600, show_spinner=False)
def load_compose_imprese() -> pd.DataFrame:
    return load_mart("mart_imprese", year=2026, slug="anac_cross")


# ── Ricerca CIG (cross-dataset via DuckDB) ─────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def search_cig(cig: str) -> dict[str, pd.DataFrame]:
    """Cerca un CIG in tutti i dataset ANAC."""
    cig = cig.strip().upper()
    results = {}

    # Bandi gara: tutti gli anni
    bandi = query(
        "SELECT * FROM clean_input WHERE UPPER(cig) = ?",
        years=YEARS_BANDI,
        slug="anac_bandi_gara",
    )
    if not bandi.empty:
        results["anac_bandi_gara"] = bandi

    # Altri dataset: snapshot 2026
    for dataset in ["anac_aggiudicazioni", "anac_aggiudicatari", "anac_cup",
                     "anac_partecipanti", "anac_collaudo", "anac_stati_avanzamento",
                     "anac_subappalti"]:
        try:
            df = query(
                "SELECT * FROM clean_input WHERE UPPER(cig) = ?",
                years=YEARS_SNAPSHOT,
                slug=dataset,
            )
            if not df.empty:
                results[dataset] = df
        except Exception:
            pass

    return results


@st.cache_data(ttl=3600, show_spinner=False)
def search_by_sa(query_sa: str, limit: int = 50) -> pd.DataFrame:
    """Cerca bandi per nome stazione appaltante."""
    return query(
        f"""SELECT DISTINCT
            cig,
            denominazione_amministrazione_appaltante AS sa,
            oggetto_gara,
            importo_lotto,
            anno_pubblicazione AS anno
        FROM clean_input
        WHERE UPPER(denominazione_amministrazione_appaltante) LIKE ?
        ORDER BY importo_lotto DESC NULLS LAST
        LIMIT {limit}""",
        years=YEARS_BANDI,
        slug="anac_bandi_gara",
    )


@st.cache_data(ttl=3600, show_spinner=False)
def top_cig_by_importo(limit: int = 20) -> pd.DataFrame:
    """Top CIG per importo di lotto."""
    return query(
        f"""SELECT DISTINCT
            cig,
            denominazione_amministrazione_appaltante AS sa,
            oggetto_gara,
            importo_lotto,
            anno_pubblicazione AS anno
        FROM clean_input
        WHERE importo_lotto IS NOT NULL
        ORDER BY importo_lotto DESC
        LIMIT {limit}""",
        years=YEARS_BANDI,
        slug="anac_bandi_gara",
    )
