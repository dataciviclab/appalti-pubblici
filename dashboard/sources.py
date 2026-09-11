"""Fonti dati ANAC — Appalti Pubblici Italiani.

Legge i mart locali (parquet) + clean layer via DuckDB pushdown.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

# ── Path ──────────────────────────────────────────────────────────────────────

_MART_BASE = (
    Path(__file__).resolve().parent.parent / "out" / "data" / "mart"
)
_CLEAN_BASE = (
    Path(__file__).resolve().parent.parent / "out" / "data" / "clean"
)

ALL_YEARS = list(range(2016, 2026))

# ── Dataset registry (per SQL page) ───────────────────────────────────────────

DATASETS = {
    "anac_bandi_gara": {"label": "Bandi di Gara", "years": list(range(2016, 2026))},
    "anac_aggiudicazioni": {"label": "Aggiudicazioni", "years": [2026]},
    "anac_aggiudicatari": {"label": "Aggiudicatari", "years": [2026]},
    "anac_partecipanti": {"label": "Partecipanti", "years": [2026]},
    "anac_subappalti": {"label": "Subappalti", "years": [2026]},
    "anac_stati_avanzamento": {"label": "Stati di Avanzamento", "years": [2026]},
    "anac_collaudo": {"label": "Collaudo", "years": [2026]},
    "anac_cup": {"label": "CUP", "years": [2026]},
}

# ── Low-level loaders ─────────────────────────────────────────────────────────


def _read_parquet(path: Path) -> pd.DataFrame:
    """Legge un singolo parquet via DuckDB."""
    with duckdb.connect() as con:
        return con.sql(f"SELECT * FROM read_parquet('{path}')").df()


def _read_parquet_multi(paths: list[Path]) -> pd.DataFrame:
    """Legge più parquet con UNIONByName."""
    if not paths:
        return pd.DataFrame()
    if len(paths) == 1:
        return _read_parquet(paths[0])
    quoted = ", ".join(f"'{p}'" for p in paths)
    with duckdb.connect() as con:
        return con.sql(
            f"SELECT * FROM read_parquet([{quoted}], union_by_name=true)"
        ).df()


def _mart_path(dataset: str, year: int, table: str) -> Path:
    return _MART_BASE / dataset / str(year) / f"{table}.parquet"


def _clean_path(dataset: str, year: int) -> Path:
    return _CLEAN_BASE / dataset / str(year) / f"{dataset}_{year}_clean.parquet"


# ── Mart loaders (leggeri, cached) ────────────────────────────────────────────


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_annuale_bandi() -> pd.DataFrame:
    """Riepilogo annuale bandi: 1 riga/anno, KPI complessivi."""
    paths = [_mart_path("anac_bandi_gara", y, "mart_annuale") for y in ALL_YEARS]
    return _read_parquet_multi([p for p in paths if p.exists()])


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_top_stazioni(year: int = 2024) -> pd.DataFrame:
    p = _mart_path("anac_bandi_gara", year, "mart_top_stazioni")
    return _read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_trend_pnrr(year: int = 2024) -> pd.DataFrame:
    p = _mart_path("anac_bandi_gara", year, "mart_trend_pnrr")
    return _read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_esiti_procedura(year: int = 2024) -> pd.DataFrame:
    p = _mart_path("anac_bandi_gara", year, "mart_esiti_per_procedura")
    return _read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_trend_settore(year: int = 2024) -> pd.DataFrame:
    p = _mart_path("anac_bandi_gara", year, "mart_trend_settore")
    return _read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_annuale_agg() -> pd.DataFrame:
    """Riepilogo annuale aggiudicazioni."""
    p = _mart_path("anac_aggiudicazioni", 2026, "mart_annuale")
    return _read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_top_aggiudicatari() -> pd.DataFrame:
    p = _mart_path("anac_aggiudicatari", 2026, "mart_top_aggiudicatari")
    return _read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_cup() -> pd.DataFrame:
    p = _mart_path("anac_cup", 2026, "mart_cup")
    return _read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_sal() -> pd.DataFrame:
    p = _mart_path("anac_stati_avanzamento", 2026, "mart_sal")
    return _read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_collaudo() -> pd.DataFrame:
    p = _mart_path("anac_collaudo", 2026, "mart_collaudo")
    return _read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_top_subappalti() -> pd.DataFrame:
    p = _mart_path("anac_subappalti", 2026, "mart_top_subappalti")
    return _read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_mart_top_partecipanti() -> pd.DataFrame:
    p = _mart_path("anac_partecipanti", 2026, "mart_top_partecipanti")
    return _read_parquet(p) if p.exists() else pd.DataFrame()


# ── Compose marts (anac-cross) ───────────────────────────────────────────────

_COMPOSE_MART_BASE = (
    Path(__file__).resolve().parent.parent / "out" / "data" / "mart" / "anac_cross"
)


def _compose_mart_path(year: int, table: str) -> Path:
    return _COMPOSE_MART_BASE / str(year) / f"{table}.parquet"


@st.cache_data(ttl=3600, show_spinner=False)
def load_compose_panoramica() -> pd.DataFrame:
    """Compose: KPI aggregati per anno x settore x regione (691 righe, 25KB)."""
    p = _compose_mart_path(2026, "mart_panoramica")
    return _read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_compose_panoramica_annuale() -> pd.DataFrame:
    """Compose panoramica aggregata a livello annuale (compatibile con formati esistenti)."""
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
def load_compose_cig_snapshot() -> pd.DataFrame:
    """Compose: 1 riga per CIG con stats 2026 (aggiudicazioni, partecipanti, SAL, collaudo, CUP)."""
    p = _compose_mart_path(2026, "mart_cig_snapshot")
    return _read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_compose_lifecycle() -> pd.DataFrame:
    """Compose: bandi 2016-2025 con contesto 2026 (LEFT JOIN su snapshot)."""
    p = _compose_mart_path(2026, "mart_lifecycle")
    return _read_parquet(p) if p.exists() else pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def load_compose_imprese() -> pd.DataFrame:
    """Compose: 1 riga per CF con profilo impresa (aggiudicatari, partecipanti, subappalti)."""
    p = _compose_mart_path(2026, "mart_imprese")
    return _read_parquet(p) if p.exists() else pd.DataFrame()


# ── Clean layer: query con DuckDB pushdown ────────────────────────────────────


def _clean_url(dataset: str, year: int) -> str:
    """Path locale del clean parquet."""
    p = _clean_path(dataset, year)
    return str(p) if p.exists() else ""


@st.cache_data(ttl=3600, show_spinner=False)
def query_clean_local(sql: str, dataset: str, years: tuple[int, ...]) -> pd.DataFrame:
    """Esegue SQL sul clean layer locale con CTE virtual."""
    urls = [_clean_url(dataset, y) for y in years]
    urls = [u for u in urls if u]
    if not urls:
        return pd.DataFrame()
    paths = ", ".join(f"'{u}'" for u in urls)
    cte = f"WITH clean_input AS (SELECT * FROM read_parquet([{paths}], union_by_name=true))"
    with duckdb.connect() as con:
        return con.sql(f"{cte} {sql}").df()


@st.cache_data(ttl=3600, show_spinner=False)
def load_clean_local(dataset: str, years: tuple[int, ...]) -> pd.DataFrame:
    """Carica il clean layer locale per uno slug e anni specifici."""
    urls = [_clean_url(dataset, y) for y in years]
    urls = [u for u in urls if u]
    if not urls:
        return pd.DataFrame()
    return _read_parquet_multi([Path(u) for u in urls])


@st.cache_data(ttl=3600, show_spinner=False)
def search_cig(cig: str) -> dict[str, pd.DataFrame]:
    """Cerca un CIG in tutti i dataset e restituisce dict {dataset: DataFrame}."""
    results = {}
    cig = cig.strip().upper()

    # bandi_gara: cerca in tutti gli anni
    bandi_urls = [_clean_url("anac_bandi_gara", y) for y in ALL_YEARS]
    bandi_urls = [u for u in bandi_urls if u]
    if bandi_urls:
        paths = ", ".join(f"'{u}'" for u in bandi_urls)
        q = f"WITH ci AS (SELECT * FROM read_parquet([{paths}], union_by_name=true)) SELECT * FROM ci WHERE UPPER(cig) = '{cig}'"
        with duckdb.connect() as con:
            df = con.sql(q).df()
            if not df.empty:
                results["anac_bandi_gara"] = df

    # altri dataset: snapshot 2026
    for dataset in ["anac_aggiudicazioni", "anac_aggiudicatari", "anac_cup",
                     "anac_partecipanti", "anac_collaudo", "anac_stati_avanzamento",
                     "anac_subappalti"]:
        url = _clean_url(dataset, 2026)
        if url:
            q = f"SELECT * FROM read_parquet('{url}') WHERE UPPER(cig) = '{cig}'"
            with duckdb.connect() as con:
                df = con.sql(q).df()
                if not df.empty:
                    results[dataset] = df

    return results


@st.cache_data(ttl=3600, show_spinner=False)
def search_by_sa(query: str, limit: int = 50) -> pd.DataFrame:
    """Cerca bandi per nome stazione appaltante. Restituisce CIG + info."""
    query = query.strip().upper()
    bandi_urls = [_clean_url("anac_bandi_gara", y) for y in ALL_YEARS]
    bandi_urls = [u for u in bandi_urls if u]
    if not bandi_urls:
        return pd.DataFrame()
    paths = ", ".join(f"'{u}'" for u in bandi_urls)
    q = f"""
        WITH ci AS (SELECT * FROM read_parquet([{paths}], union_by_name=true))
        SELECT DISTINCT
            cig,
            denominazione_amministrazione_appaltante AS sa,
            oggetto_gara,
            importo_lotto,
            anno_pubblicazione AS anno
        FROM ci
        WHERE UPPER(denominazione_amministrazione_appaltante) LIKE '%{query}%'
        ORDER BY importo_lotto DESC NULLS LAST
        LIMIT {limit}
    """
    with duckdb.connect() as con:
        return con.sql(q).df()


@st.cache_data(ttl=3600, show_spinner=False)
def top_cig_by_importo(limit: int = 20) -> pd.DataFrame:
    """Top CIG per importo di lotto (dai bandi piu' recenti)."""
    # Usa l'anno piu' recente disponibile
    for y in reversed(ALL_YEARS):
        url = _clean_url("anac_bandi_gara", y)
        if url:
            q = f"""
                SELECT DISTINCT
                    cig,
                    denominazione_amministrazione_appaltante AS sa,
                    oggetto_gara,
                    importo_lotto,
                    {y} AS anno
                FROM read_parquet('{url}')
                WHERE importo_lotto IS NOT NULL
                ORDER BY importo_lotto DESC
                LIMIT {limit}
            """
            with duckdb.connect() as con:
                return con.sql(q).df()
    return pd.DataFrame()
