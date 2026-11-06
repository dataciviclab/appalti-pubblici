"""Query SQL — Interroga direttamente i dati ANAC.

Template predefiniti + editor SQL libero. La pagina è quella condivisa del
Lab (``render_sql_query``): risolve i file clean da ``location.path`` del
registry, senza la copia locale della UI.
"""

from pathlib import Path

import streamlit as st
from lab_connectors.duckdb.sql_page import render_sql_query
from lab_connectors.registry import load_registry
from sources import PREFIX

REGISTRY_PATH = Path(__file__).resolve().parents[3] / "registry" / "registry.json"

TEMPLATES = {
    "Seleziona un template...": None,
    "Conta righe": "SELECT COUNT(*) AS n FROM clean_input",
    "Preview (10 righe)": "SELECT * FROM clean_input LIMIT 10",
    "Colonne disponibili": "DESCRIBE SELECT * FROM clean_input",
    "Top SA per importo": (
        "SELECT denominazione_amministrazione_appaltante AS sa, "
        "COUNT(*) AS n_bandi, ROUND(SUM(importo_lotto), 0) AS importo_totale "
        "FROM clean_input "
        "WHERE cf_amministrazione_appaltante IS NOT NULL "
        "GROUP BY sa ORDER BY importo_totale DESC LIMIT 20"
    ),
    "Trend annuale": (
        "SELECT anno_pubblicazione AS anno, COUNT(*) AS n_bandi, "
        "ROUND(SUM(importo_lotto), 0) AS importo_totale "
        "FROM clean_input GROUP BY anno ORDER BY anno"
    ),
    "CIG con un solo offerente": (
        "SELECT cig, importo_aggiudicazione, num_imprese_offerenti "
        "FROM clean_input WHERE num_imprese_offerenti = 1 "
        "AND importo_aggiudicazione > 1000000 "
        "ORDER BY importo_aggiudicazione DESC LIMIT 20"
    ),
    "SAL in ritardo": (
        "SELECT cig, n_giorni_scostamento, importo_sal "
        "FROM clean_input WHERE flag_ritardo = 'IN RITARDO' "
        "ORDER BY n_giorni_scostamento DESC LIMIT 20"
    ),
}

render_sql_query(
    registry=load_registry(REGISTRY_PATH),
    prefix=PREFIX,
    default_slug="anac_bandi_gara",
    templates=TEMPLATES,
)
st.caption("Dati: ANAC (dati.anticorruzione.it) -- CC BY 4.0")
