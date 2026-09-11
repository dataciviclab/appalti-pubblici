"""Bandi di Gara — Trend, PNRR, top stazioni, esiti."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from lab_connectors.formatters import fmt_num
from sources import (
    load_mart_annuale_bandi, load_mart_top_stazioni, load_mart_trend_pnrr,
    load_mart_esiti_procedura, load_mart_trend_settore, ALL_YEARS,
)

st.title("📋 Bandi di Gara")

# ── Filtro anno ───────────────────────────────────────────────────────────────
year = st.selectbox("Anno", ALL_YEARS, index=len(ALL_YEARS) - 1)

# ── Caricamento dati ──────────────────────────────────────────────────────────
try:
    top_stazioni = load_mart_top_stazioni(year)
    trend_pnrr = load_mart_trend_pnrr(year)
    esiti = load_mart_esiti_procedura(year)
    trend_settore = load_mart_trend_settore(year)
except Exception as e:
    st.error(f"Errore caricamento: {e}")
    st.stop()

# ── Trend multi-anno (da mart_annuale) ───────────────────────────────────────
st.subheader("Trend annuale")
ann = load_mart_annuale_bandi()
if not ann.empty:
    col1, col2, col3, col4 = st.columns(4)
    r = ann[ann["anno"] == year]
    if not r.empty:
        r = r.iloc[0]
        col1.metric("CIG", fmt_num(int(r["n_cig"])))
        col2.metric("Importo", f"€ {fmt_num(r['importo_totale'])}")
        col3.metric("PNRR", fmt_num(int(r["n_pnrr"])))
        col4.metric("Importo medio", f"€ {fmt_num(r['importo_medio'])}")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=ann["anno"], y=ann["n_cig"], name="CIG"))
    fig.add_trace(go.Scatter(x=ann["anno"], y=ann["importo_pnrr"],
                             name="Importo PNRR", yaxis="y2", mode="lines+markers"))
    fig.update_layout(
        title="CIG totali vs importo PNRR",
        yaxis=dict(title="N° CIG"),
        yaxis2=dict(title="Importo PNRR (€)", overlaying="y", side="right"),
        xaxis=dict(dtick=1), height=300,
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Top stazioni appaltanti ───────────────────────────────────────────────────
st.subheader(f"Top stazioni appaltanti — {year}")
if not top_stazioni.empty:
    cols = st.columns(2)
    with cols[0]:
        top10 = top_stazioni.head(10)
        fig = px.bar(
            top10, x="importo_totale", y="denominazione_amministrazione_appaltante",
            orientation="h", title="Top 10 per importo",
            labels={"denominazione_amministrazione_appaltante": "SA", "importo_totale": "Importo (€)"},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=400)
        st.plotly_chart(fig, use_container_width=True)
    with cols[1]:
        st.dataframe(
            top_stazioni[["denominazione_amministrazione_appaltante", "n_gare",
                          "importo_totale", "lotti_medi_per_gara", "rank_per_anno"]].head(20),
            use_container_width=True, hide_index=True,
        )
else:
    st.info(f"Nessun dato per {year}.")

# ── Trend PNRR ────────────────────────────────────────────────────────────────
if not trend_pnrr.empty:
    st.subheader(f"Trend PNRR — {year}")
    st.dataframe(trend_pnrr, use_container_width=True, hide_index=True)

# ── Esiti per procedura ───────────────────────────────────────────────────────
if not esiti.empty:
    st.subheader(f"Esiti per procedura — {year}")
    st.dataframe(esiti, use_container_width=True, hide_index=True)

# ── Trend settore ─────────────────────────────────────────────────────────────
if not trend_settore.empty:
    st.subheader(f"Trend settore — {year}")
    st.dataframe(trend_settore.head(30), use_container_width=True, hide_index=True)

st.caption("Dati: ANAC (dati.anticorruzione.it) · CC BY 4.0")
