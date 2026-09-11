"""Data sources — tutto derivato dal registry.

Anni, slug e anni-per-dataset vengono da registry.json.
Niente hardcoding di anni o slug nelle funzioni.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
from lab_connectors.duckdb.queries import load_mart_table, load_mart_all_years, query_clean
from lab_connectors.duckdb.core import safe_connect
from lab_connectors.formatters import fmt_num
from lab_connectors.registry import load_registry


def fmt_eur_short(val: float) -> str:
    """Formatta importi in formato italiano abbreviato: € 634 mld, € 12 mln."""
    if val is None or val == 0:
        return "€ 0"
    abs_val = abs(val)
    if abs_val >= 1_000_000_000:
        return f"€ {val / 1_000_000_000:,.1f} mld".replace(",", ".")
    if abs_val >= 1_000_000:
        return f"€ {val / 1_000_000:,.1f} mln".replace(",", ".")
    if abs_val >= 1_000:
        return f"€ {val / 1_000:,.1f} K".replace(",", ".")
    return f"€ {val:,.0f}"

ROOT = Path(__file__).parent.parent
PREFIX = "appalti_pubblici/"
_data_dir = ROOT / "out" / "data"
LOCAL_ROOT = str(_data_dir) if _data_dir.is_dir() and any(_data_dir.rglob("*.parquet")) else None


def _clean_path(dataset: str, year: int) -> str:
    """Path locale del clean parquet per un dataset/anno."""
    p = _data_dir / "clean" / dataset / str(year) / f"{dataset}_{year}_clean.parquet"
    return str(p) if p.exists() else ""

# ── Registry ─────────────────────────────────────────────────────────────────

_registry = load_registry(ROOT / "registry" / "registry.json")


def _years_for(slug: str) -> list[int]:
    """Anni disponibili per uno slug dal registry period.
    
    Se LOCAL_ROOT e' impostato, filtra per anni che hanno file su disco.
    """
    ds = next((d for d in _registry.datasets if d.slug == slug), None)
    if ds is None or ds.period is None:
        return []
    start = ds.period.get("start") if isinstance(ds.period, dict) else getattr(ds.period, "start", None)
    end = ds.period.get("end") if isinstance(ds.period, dict) else getattr(ds.period, "end", None)
    if not (start and end):
        return []
    years = list(range(int(start), int(end) + 1))
    if LOCAL_ROOT:
        clean_dir = Path(LOCAL_ROOT) / "clean" / slug
        years = [y for y in years if (clean_dir / str(y)).is_dir()]
    return years


def _all_slugs() -> list[str]:
    """Tutti gli slug dei dataset nel registry."""
    return [d.slug for d in _registry.datasets]


# Anni globali (per bandi multi-anno)
_bandi_years = _years_for("anac_bandi_gara")
YEARS_BANDI = _bandi_years if _bandi_years else list(range(2016, 2026))
YEARS_SNAPSHOT = [2026]

# ── Dataset registry (per SQL page) ───────────────────────────────────────────

DATASETS = {}
for _ds in _registry.datasets:
    _y = _years_for(_ds.slug)
    DATASETS[_ds.slug] = {"label": _ds.name, "years": _y if _y else YEARS_SNAPSHOT}

# ── Core loaders ─────────────────────────────────────────────────────────────


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart(table: str, year: int = 2026, slug: str = "") -> pd.DataFrame:
    return load_mart_table(slug or table, table, year, prefix=PREFIX, local_root=LOCAL_ROOT)


@st.cache_data(ttl=3600, show_spinner=False)
def query(sql: str, years: list[int] | None = None, slug: str = "anac_bandi_gara") -> pd.DataFrame:
    if years is None:
        years = _years_for(slug) or YEARS_SNAPSHOT
    return query_clean(slug, sql, years, prefix=PREFIX, local_root=LOCAL_ROOT)


@st.cache_data(ttl=3600, show_spinner=False)
def query_duckdb(sql: str) -> pd.DataFrame:
    with safe_connect() as con:
        return con.sql(sql).df()


# ── Panoramica ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_annuale_bandi() -> pd.DataFrame:
    """Riepilogo annuale bandi: 1 riga/anno, KPI complessivi."""
    years = _years_for("anac_bandi_gara")
    if not years:
        return pd.DataFrame()
    return load_mart_all_years("anac_bandi_gara", "mart_annuale", years, prefix=PREFIX, local_root=LOCAL_ROOT)


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_top_stazioni(year: int | None = None) -> pd.DataFrame:
    if year is None:
        years = _years_for("anac_bandi_gara")
        year = max(years) if years else 2025
    return load_mart("mart_top_stazioni", year=year, slug="anac_bandi_gara")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_trend_pnrr(year: int | None = None) -> pd.DataFrame:
    if year is None:
        years = _years_for("anac_bandi_gara")
        year = max(years) if years else 2025
    return load_mart("mart_trend_pnrr", year=year, slug="anac_bandi_gara")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_esiti_procedura(year: int | None = None) -> pd.DataFrame:
    if year is None:
        years = _years_for("anac_bandi_gara")
        year = max(years) if years else 2025
    return load_mart("mart_esiti_per_procedura", year=year, slug="anac_bandi_gara")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_trend_settore(year: int | None = None) -> pd.DataFrame:
    if year is None:
        years = _years_for("anac_bandi_gara")
        year = max(years) if years else 2025
    return load_mart("mart_trend_settore", year=year, slug="anac_bandi_gara")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_annuale_agg() -> pd.DataFrame:
    years = _years_for("anac_aggiudicazioni")
    return load_mart("mart_annuale", year=max(years) if years else 2026, slug="anac_aggiudicazioni")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_top_aggiudicatari() -> pd.DataFrame:
    years = _years_for("anac_aggiudicatari")
    return load_mart("mart_top_aggiudicatari", year=max(years) if years else 2026, slug="anac_aggiudicatari")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_cup() -> pd.DataFrame:
    years = _years_for("anac_cup")
    return load_mart("mart_cup", year=max(years) if years else 2026, slug="anac_cup")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_sal() -> pd.DataFrame:
    years = _years_for("anac_stati_avanzamento")
    return load_mart("mart_sal", year=max(years) if years else 2026, slug="anac_stati_avanzamento")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_collaudo() -> pd.DataFrame:
    years = _years_for("anac_collaudo")
    return load_mart("mart_collaudo", year=max(years) if years else 2026, slug="anac_collaudo")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_top_subappalti() -> pd.DataFrame:
    years = _years_for("anac_subappalti")
    return load_mart("mart_top_subappalti", year=max(years) if years else 2026, slug="anac_subappalti")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_top_partecipanti() -> pd.DataFrame:
    years = _years_for("anac_partecipanti")
    return load_mart("mart_top_partecipanti", year=max(years) if years else 2026, slug="anac_partecipanti")


# ── Intelligence marts ──────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_sa_profilo() -> pd.DataFrame:
    """Profilo completo per SA: n_bandi, importi, settori, regione."""
    years = _years_for("anac_bandi_gara")
    year = max(years) if years else 2025
    return load_mart("mart_sa_profilo", year=year, slug="anac_bandi_gara")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_ritardi_per_sa() -> pd.DataFrame:
    """Ritardi per SA × settore (compose)."""
    years = _years_for("anac_cross")
    return load_mart("mart_ritardi_per_sa", year=max(years) if years else 2026, slug="anac_cross")


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_competitivita() -> pd.DataFrame:
    """Competitività per anno × regione (compose)."""
    years = _years_for("anac_cross")
    return load_mart("mart_competitivita", year=max(years) if years else 2026, slug="anac_cross")


# ── Compose (anac_cross) ───────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_compose_panoramica() -> pd.DataFrame:
    years = _years_for("anac_cross")
    return load_mart("mart_panoramica", year=max(years) if years else 2026, slug="anac_cross")


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
    years = _years_for("anac_cross")
    return load_mart("mart_lifecycle", year=max(years) if years else 2026, slug="anac_cross")


@st.cache_data(ttl=3600, show_spinner=False)
def load_compose_imprese() -> pd.DataFrame:
    years = _years_for("anac_cross")
    return load_mart("mart_imprese", year=max(years) if years else 2026, slug="anac_cross")


# ── Ricerca CIG (cross-dataset) ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def search_cig(cig: str) -> dict[str, pd.DataFrame]:
    """Cerca un CIG in tutti i dataset dal registry."""
    cig = cig.strip().upper()
    results = {}
    for slug in _all_slugs():
        years = _years_for(slug)
        if not years:
            continue
        try:
            df = query(
                f"SELECT * FROM clean_input WHERE UPPER(cig) = '{cig}'",
                years=years,
                slug=slug,
            )
            if not df.empty:
                results[slug] = df
        except Exception:
            pass
    return results


@st.cache_data(ttl=3600, show_spinner=False)
def search_by_sa(query_sa: str, limit: int = 50) -> pd.DataFrame:
    """Cerca bandi per nome stazione appaltante."""
    sa = query_sa.strip().upper().replace("'", "''")
    return query(
        f"""SELECT DISTINCT
            cig,
            denominazione_amministrazione_appaltante AS sa,
            oggetto_gara,
            importo_lotto,
            anno_pubblicazione AS anno
        FROM clean_input
        WHERE UPPER(denominazione_amministrazione_appaltante) LIKE '%{sa}%'
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
