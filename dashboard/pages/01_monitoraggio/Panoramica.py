"""Panoramica -- Visione d'insieme degli appalti pubblici ANAC."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from lab_connectors.formatters import fmt_num
from sources import (
    load_compose_panoramica_annuale,
    load_mart_sa_profilo,
    fmt_eur_short,
)

st.title("Panoramica -- ANAC Appalti Pubblici")

try:
    ann_compose = load_compose_panoramica_annuale()
    sa_profilo = load_mart_sa_profilo()
except Exception as e:
    st.error(f"Errore caricamento dati: {e}")
    st.stop()

if ann_compose.empty:
    st.warning("Nessun dato disponibile.")
    st.stop()

# -- KPI ultimo anno -----------------------------------------------------------
st.subheader("KPI Principali (ultimo anno disponibile)")
latest = ann_compose.iloc[-1]
k1, k2, k3, k4 = st.columns(4)
k1.metric("CIG pubblicati", fmt_num(int(latest["n_cig"])))
k2.metric("Importo totale", fmt_eur_short(latest['importo_totale']))
k3.metric("SA attive", fmt_num(int(latest["n_stazioni_appaltanti"])))
k4.metric("PNRR", fmt_num(int(latest['n_pnrr'])))

k5, k6, k7, k8 = st.columns(4)
k5.metric("Aggiudicati", fmt_num(int(latest['n_aggiudicati'])))
k6.metric("Importo aggiudicati", fmt_eur_short(latest['importo_aggiudicati']))
k7.metric("Settori", fmt_num(int(latest['n_settori'])))
tasso = latest['n_aggiudicati'] * 100 / latest['n_lotti'] if latest['n_lotti'] > 0 else 0
k8.metric("Tasso aggiudicazione", f"{tasso:.1f}%")

# -- Trend bandi 2016-2025 -----------------------------------------------------
st.subheader("Trend bandi pubblicati (2016-2025)")
col_a, col_b = st.columns(2)
with col_a:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=ann_compose["anno"], y=ann_compose["n_lotti"],
        name="N Lotti", marker_color="#6366f1"
    ))
    fig.add_trace(go.Scatter(
        x=ann_compose["anno"], y=ann_compose["importo_totale"],
        name="Importo (EUR)", yaxis="y2", mode="lines+markers",
        line=dict(color="#f59e0b", width=2)
    ))
    fig.update_layout(
        title="Lotti e importi per anno",
        yaxis=dict(title="N Lotti"),
        yaxis2=dict(title="Importo (EUR)", overlaying="y", side="right"),
        xaxis=dict(title="Anno", dtick=1),
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True, key="panoramica_lotti_importi")
with col_b:
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=ann_compose["anno"], y=ann_compose["n_aggiudicati"],
        name="Aggiudicati", marker_color="#22c55e"
    ))
    fig2.update_layout(
        title="Aggiudicati per anno",
        xaxis=dict(title="Anno", dtick=1), height=350,
    )
    st.plotly_chart(fig2, use_container_width=True, key="panoramica_aggiudicati")

# -- Trend affidamenti diretti vs gara -----------------------------------------
st.subheader("Affidamenti diretti vs gara (trend)")
col_c, col_d = st.columns(2)
with col_c:
    fig3 = go.Figure()
    pct_diretto = (ann_compose["n_aggiudicati"] * 0.51).astype(float)
    fig3.add_trace(go.Bar(
        x=ann_compose["anno"], y=pct_diretto,
        name="Affidamenti diretti", marker_color="#ef4444"
    ))
    fig3.add_trace(go.Bar(
        x=ann_compose["anno"], y=ann_compose["n_aggiudicati"] - pct_diretto,
        name="Gara pubblica", marker_color="#3b82f6"
    ))
    fig3.update_layout(
        barmode="stack",
        title="Stima: diretti (~51%) vs gara",
        xaxis=dict(title="Anno", dtick=1), height=350,
    )
    st.plotly_chart(fig3, use_container_width=True, key="panoramica_diretti_gara")
with col_d:
    if not sa_profilo.empty:
        top_sa = sa_profilo.head(15)
        fig4 = px.bar(
            top_sa, x="importo_totale", y="denominazione_sa",
            orientation="h", title="Top 15 SA per importo bandi",
            labels={"denominazione_sa": "Stazione Appaltante", "importo_totale": "Importo (EUR)"},
        )
        fig4.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
        st.plotly_chart(fig4, use_container_width=True, key="panoramica_top_sa")

st.caption("Dati: ANAC (dati.anticorruzione.it) -- CC BY 4.0")
