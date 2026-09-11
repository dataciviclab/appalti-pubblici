"""Panoramica — Visione d'insieme degli appalti pubblici ANAC."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from lab_connectors.formatters import fmt_num, fmt_eur, fmt_pct
from sources import (
    load_mart_annuale_bandi, load_compose_panoramica_annuale,
    load_mart_sa_profilo, load_mart_competitivita,
    load_mart_cup, load_mart_sal, load_mart_collaudo,
    fmt_eur_short,
)

st.title("📊 Panoramica — ANAC Appalti Pubblici")

# ── Caricamento dati ──────────────────────────────────────────────────────────
try:
    ann_bandi = load_mart_annuale_bandi()
    ann_compose = load_compose_panoramica_annuale()
    sa_profilo = load_mart_sa_profilo()
except Exception as e:
    st.error(f"Errore caricamento dati: {e}")
    st.stop()

if ann_compose.empty:
    st.warning("Nessun dato disponibile.")
    st.stop()

# ── KPI ultimo anno ───────────────────────────────────────────────────────────
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
k8.metric("Tasso aggiudicazione", fmt_pct(tasso / 100 if tasso else 0))

# ── Trend bandi 2016-2025 ────────────────────────────────────────────────────
st.subheader("Trend bandi pubblicati (2016-2025)")
col_a, col_b = st.columns(2)
with col_a:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=ann_compose["anno"], y=ann_compose["n_lotti"],
        name="N° Lotti", marker_color="#6366f1"
    ))
    fig.add_trace(go.Scatter(
        x=ann_compose["anno"], y=ann_compose["importo_totale"],
        name="Importo (€)", yaxis="y2", mode="lines+markers",
        line=dict(color="#f59e0b", width=2)
    ))
    fig.update_layout(
        title="Lotti e importi per anno",
        yaxis=dict(title="N° Lotti"),
        yaxis2=dict(title="Importo (€)", overlaying="y", side="right"),
        xaxis=dict(title="Anno", dtick=1),
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)
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
    st.plotly_chart(fig2, use_container_width=True)

# ── Top SA per importo ───────────────────────────────────────────────────────
st.subheader("Chi compra di più?")
if not sa_profilo.empty:
    top_sa = sa_profilo.head(15)
    fig = px.bar(
        top_sa, x="importo_totale", y="denominazione_sa",
        orientation="h", title="Top 15 SA per importo bandi",
        labels={"denominazione_sa": "Stazione Appaltante", "importo_totale": "Importo (€)"},
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
    st.plotly_chart(fig, use_container_width=True)

    # KPI SA
    col1, col2, col3 = st.columns(3)
    col1.metric("SA totali (≥10 bandi)", fmt_num(len(sa_profilo)))
    col2.metric("SA con PNRR", fmt_num(int((sa_profilo["n_pnrr"] > 0).sum())))
    top3 = sa_profilo.head(3)
    col3.metric("Top 3", f"{top3['denominazione_sa'].iloc[0][:30]}...")

# ── Copertura dataset ANAC ────────────────────────────────────────────────────
st.subheader("Copertura dataset ANAC")
cup = load_mart_cup()
sal = load_mart_sal()
collaudo = load_mart_collaudo()

col1, col2, col3 = st.columns(3)
with col1:
    if not cup.empty:
        st.metric("CIG-CUP mappati", fmt_num(int(cup["n_cig_distinti"].sum())))
with col2:
    if not collaudo.empty:
        st.metric("Collaudi", fmt_num(int(collaudo["n_collaudi"].sum())))
with col3:
    if not sal.empty:
        n_ritardi = int(sal[sal["flag_ritardo"] == "IN RITARDO"]["n_sal"].sum())
        st.metric("SAL in ritardo", fmt_num(n_ritardi))

st.caption("Dati: ANAC (dati.anticorruzione.it) · CC BY 4.0")
