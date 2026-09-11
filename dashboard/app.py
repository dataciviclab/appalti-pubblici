#!/usr/bin/env python3
"""ANAC Appalti Pubblici -- Dashboard Streamlit"""

import streamlit as st
from lab_connectors.branding import apply_branding

st.set_page_config(
    page_title="ANAC Appalti -- Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_branding(
    repo_name="appalti-pubblici",
    repo_url="https://github.com/dataciviclab/appalti-pubblici",
)

pages = {
    "Monitoraggio": [
        st.Page("pages/01_monitoraggio/Panoramica.py", title="Panoramica", icon="📊", default=True),
        st.Page("pages/01_monitoraggio/Trend_Territorio.py", title="Trend Territorio", icon="🌍"),
    ],
    "Intelligence": [
        st.Page("pages/02_intelligence/Trasparenza.py", title="Trasparenza", icon="🛡️"),
        st.Page("pages/02_intelligence/Esecuzione.py", title="Esecuzione", icon="⏱️"),
        st.Page("pages/02_intelligence/Imprese.py", title="Imprese", icon="🏢"),
    ],
    "Esplorazione": [
        st.Page("pages/03_esplorazione/Scheda_CIG.py", title="Scheda CIG", icon="🔍"),
        st.Page("pages/03_esplorazione/Scheda_SA.py", title="Scheda SA", icon="🏛️"),
        st.Page("pages/03_esplorazione/SQL.py", title="Query SQL", icon="🧪"),
    ],
}

pg = st.navigation(pages, position="sidebar")
pg.run()
