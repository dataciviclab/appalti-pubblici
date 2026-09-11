#!/usr/bin/env python3
"""
ANAC Appalti Pubblici · Dashboard Streamlit
Dashboard interattiva per l'esplorazione dei dati ANAC sugli appalti pubblici.
"""

import streamlit as st
from lab_connectors.branding import apply_branding

st.set_page_config(
    page_title="ANAC Appalti · Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_branding(
    repo_name="appalti-pubblici",
    repo_url="https://github.com/dataciviclab/appalti-pubblici",
)

pages = {
    "": [
        st.Page("pages/01_Panoramica.py", title="Panoramica", icon="📊", default=True),
    ],
    "Analisi": [
        st.Page("pages/02_Bandi.py", title="Bandi di Gara", icon="📋"),
        st.Page("pages/03_Aggiudicazioni.py", title="Aggiudicazioni", icon="🏆"),
        st.Page("pages/06_Ritardi.py", title="Ritardi e Monitoraggio", icon="⏱️"),
    ],
    "Strumenti": [
        st.Page("pages/04_Scheda_CIG.py", title="Scheda CIG", icon="🔍"),
        st.Page("pages/05_SQL.py", title="Query SQL", icon="🧪"),
    ],
}

pg = st.navigation(pages, position="sidebar")
pg.run()
