"""Panoramica — Visione d'insieme degli appalti pubblici ANAC."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from lab_connectors.formatters import fmt_num
from sources import (
    load_compose_panoramica_annuale,
    load_mart_cup, load_mart_sal, load_mart_collaudo,
    load_mart_top_subappalti,
)

st.title("📊 Panoramica — ANAC Appalti Pubblici")

# ── Caricamento dati ──────────────────────────────────────────────────────────
try:
    ann_bandi = load_compose_panoramica_annuale()
    cup = load_mart_cup()
    sal = load_mart_sal()
    collaudo = load_mart_collaudo()
    subappalti = load_mart_top_subappalti()
except Exception as e:
    st.error(f"Errore caricamento dati: {e}")
    st.stop()

if ann_bandi.empty:
    st.warning("Nessun dato disponibile.")
    st.stop()

# ── KPI ultimi anni ───────────────────────────────────────────────────────────
st.subheader("KPI Principali (ultimo anno disponibile)")
latest = ann_bandi.iloc[-1]
k1, k2, k3, k4 = st.columns(4)
k1.metric("CIG pubblicati", fmt_num(int(latest["n_cig"])))
k2.metric("Importo totale", f"€ {fmt_num(latest['importo_totale'])}")
k3.metric("SA attive", fmt_num(int(latest["n_stazioni_appaltanti"])))
k4.metric("PNRR", fmt_num(int(latest["n_pnrr"])))

k5, k6, k7, k8 = st.columns(4)
k5.metric("Aggiudicati", fmt_num(int(latest["n_aggiudicati"])))
k6.metric("Importo aggiudicati", f"€ {fmt_num(latest['importo_aggiudicati'])}")
k7.metric("Settori", fmt_num(int(latest["n_settori"])))
k8.metric("Tasso aggiudicazione", f"{latest['n_aggiudicati'] * 100 / latest['n_lotti']:.1f}%" if latest['n_lotti'] > 0 else "—")

# ── Trend bandi 2016-2025 ────────────────────────────────────────────────────
st.subheader("Trend bandi pubblicati (2016-2025)")
col_a, col_b = st.columns(2)
with col_a:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=ann_bandi["anno"], y=ann_bandi["n_lotti"],
        name="N° Lotti", marker_color="#6366f1"
    ))
    fig.add_trace(go.Scatter(
        x=ann_bandi["anno"], y=ann_bandi["importo_totale"],
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
        x=ann_bandi["anno"], y=ann_bandi["n_aggiudicati"],
        name="Aggiudicati", marker_color="#22c55e"
    ))
    fig2.update_layout(
        title="Aggiudicati per anno",
        xaxis=dict(title="Anno", dtick=1), height=350,
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── Quote ANAC dataset ────────────────────────────────────────────────────────
st.subheader("Copertura dataset ANAC")
col1, col2, col3 = st.columns(3)
with col1:
    if not cup.empty:
        st.metric("CIG-CUP mappati", fmt_num(int(cup["n_cig_distinti"].sum())))
with col2:
    if not collaudo.empty:
        st.metric("Collaudi", fmt_num(int(collaudo["n_collaudi"].sum())))
with col3:
    if not subappalti.empty:
        st.metric("Subappalti", fmt_num(int(subappalti["n_subappalti"].sum())))

# ── SAL ritardi ───────────────────────────────────────────────────────────────
if not sal.empty:
    st.subheader("Stato SAL")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        fig_sal = px.pie(sal, values="n_sal", names="flag_ritardo",
                         title="Distribuzione SAL per stato")
        st.plotly_chart(fig_sal, use_container_width=True)
    with col_s2:
        st.dataframe(sal, use_container_width=True, hide_index=True)

st.caption("Dati: ANAC (dati.anticorruzione.it) · CC BY 4.0")
