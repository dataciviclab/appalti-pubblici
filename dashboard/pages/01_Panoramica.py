"""Panoramica — Visione d'insieme degli appalti pubblici ANAC."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from lab_connectors.formatters import fmt_num, fmt_pct
from sources import (
    load_mart_annuale_bandi, load_compose_panoramica_annuale,
    load_mart_sa_profilo, load_mart_competitivita,
    load_mart_cup, load_mart_sal, load_mart_collaudo,
    fmt_eur_short, query_duckdb, _clean_path, _years_for,
)

st.title("📊 Panoramica — ANAC Appalti Pubblici")

# ── Caricamento dati ──────────────────────────────────────────────────────────
try:
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

# ── Funnel appalti ───────────────────────────────────────────────────────────
st.subheader("🔄 Funnel Appalti")
st.markdown("Dal bando alla conclusione: quanti bandi diventano lavori?")

bandi_years = _years_for("anac_bandi_gara")
latest_year = max(bandi_years) if bandi_years else 2025
bandi_p = _clean_path("anac_bandi_gara", latest_year)
sal_p = _clean_path("anac_stati_avanzamento", 2026)

funnel = query_duckdb(f"""
    WITH bandi AS (
        SELECT
            COUNT(*) AS n_bandi,
            ROUND(SUM(importo_lotto)/1e9, 1) AS importo_mld,
            SUM(CASE WHEN esito = 'AGGIUDICATA' THEN 1 ELSE 0 END) AS n_aggiudicati,
            ROUND(SUM(CASE WHEN esito = 'AGGIUDICATA' THEN importo_lotto ELSE 0 END)/1e9, 1) AS importo_agg_mld,
            SUM(CASE WHEN esito IS NULL OR esito = '' THEN 1 ELSE 0 END) AS n_senza_esito
        FROM read_parquet('{bandi_p}')
        WHERE stato = 'ATTIVO'
    ),
    sal AS (
        SELECT
            COUNT(*) AS n_sal,
            ROUND(SUM(importo_sal)/1e9, 1) AS importo_sal_mld,
            SUM(CASE WHEN flag_ritardo = 'IN RITARDO' THEN 1 ELSE 0 END) AS n_ritardi,
            ROUND(SUM(CASE WHEN flag_ritardo = 'IN RITARDO' THEN importo_sal ELSE 0 END)/1e9, 1) AS importo_ritardi_mld
        FROM read_parquet('{sal_p}')
        WHERE data_emissione_sal IS NOT NULL
          AND EXTRACT(YEAR FROM data_emissione_sal) = {latest_year}
    )
    SELECT * FROM bandi, sal
""")

if not funnel.empty:
    f = funnel.iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        f"📋 Pubblicati ({latest_year})",
        f"{fmt_num(int(f['n_bandi']))} bandi",
        f"€ {f['importo_mld']} mld",
    )
    col2.metric(
        "🏆 Aggiudicati",
        f"{fmt_num(int(f['n_aggiudicati']))}",
        f"€ {f['importo_agg_mld']} mld",
    )
    col3.metric(
        "⚙️ In esecuzione (SAL)",
        f"{fmt_num(int(f['n_sal']))}",
        f"€ {f['importo_sal_mld']} mld",
    )
    col4.metric(
        "⏱️ SAL in ritardo",
        f"{fmt_num(int(f['n_ritardi']))}",
        f"€ {f['importo_ritardi_mld']} mld",
    )

    # Bar chart funnel
    fig = go.Figure()
    stages = ["Pubblicati", "Aggiudicati", "In esecuzione", "In ritardo"]
    values_n = [int(f['n_bandi']), int(f['n_aggiudicati']), int(f['n_sal']), int(f['n_ritardi'])]
    values_eur = [f['importo_mld'], f['importo_agg_mld'], f['importo_sal_mld'], f['importo_ritardi_mld']]
    colors = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444"]

    fig.add_trace(go.Bar(
        x=stages, y=values_n,
        text=[f"{fmt_num(v)}<br>€ {e} mld" for v, e in zip(values_n, values_eur)],
        textposition="outside",
        marker_color=colors,
    ))
    fig.update_layout(
        title=f"Funnel appalti {latest_year}",
        yaxis_title="Numero",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Gap analysis
    gap = int(f['n_aggiudicati']) - int(f['n_sal'])
    st.info(
        f"**Gap esecuzione**: {fmt_num(gap)} appalti aggiudicati non hanno ancora SAL attivi. "
        f"Possono essere in attesa di avvio, bloccati, o troppo recenti."
    )

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

    col1, col2, col3 = st.columns(3)
    col1.metric("SA totali (≥10 bandi)", fmt_num(len(sa_profilo)))
    col2.metric("SA con PNRR", fmt_num(int((sa_profilo["n_pnrr"] > 0).sum())))
    top3 = sa_profilo.head(3)
    col3.metric("Top 3", f"{top3['denominazione_sa'].iloc[0][:30]}...")

st.caption("Dati: ANAC (dati.anticorruzione.it) · CC BY 4.0")
