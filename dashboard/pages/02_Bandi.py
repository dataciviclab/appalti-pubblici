"""Bandi di Gara — Trend, SA, territorio, competitivita."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from lab_connectors.formatters import fmt_num, fmt_eur
from sources import (
    load_mart_annuale_bandi, load_mart_sa_profilo,
    load_mart_trend_pnrr, load_mart_esiti_procedura,
    load_mart_competitivita, YEARS_BANDI, fmt_eur_short,
)

st.title("📋 Bandi di Gara")

# ── Filtro anno ───────────────────────────────────────────────────────────────
year = st.selectbox("Anno", YEARS_BANDI, index=len(YEARS_BANDI) - 1)

# ── Trend multi-anno ─────────────────────────────────────────────────────────
st.subheader("Trend annuale")
ann = load_mart_annuale_bandi()
if not ann.empty:
    col1, col2, col3, col4 = st.columns(4)
    r = ann[ann["anno"] == year]
    if not r.empty:
        r = r.iloc[0]
        col1.metric("CIG", fmt_num(int(r["n_cig"])))
        col2.metric("Importo", fmt_eur_short(r['importo_totale']))
        col3.metric("PNRR", fmt_num(int(r["n_pnrr"])))
        col4.metric("Importo medio", fmt_eur_short(r['importo_medio']))

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

# ── Competitivita per regione ────────────────────────────────────────────────
st.subheader("Competitività per regione")
comp = load_mart_competitivita()
if not comp.empty:
    comp_year = comp[comp["anno"] == year]
    if not comp_year.empty:
        col1, col2 = st.columns(2)
        with col1:
            top_regioni = comp_year.nlargest(10, "importo_totale")
            fig = px.bar(
                top_regioni, x="importo_totale", y="regione", orientation="h",
                title=f"Top 10 regioni per importo — {year}",
                labels={"regione": "Regione", "importo_totale": "Importo (€)"},
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=400)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.dataframe(
                comp_year[["regione", "n_bandi", "importo_totale", "n_aggiudicati", "offerenti_medi",
                           "tasso_aggiudicazione_pct"]].sort_values("importo_totale", ascending=False).head(15),
                use_container_width=True, hide_index=True,
                column_config={
                    "tasso_aggiudicazione_pct": st.column_config.NumberColumn("Tasso agg. %", format="%.1f"),
                    "offerenti_medi": st.column_config.NumberColumn("Offerenti medi", format="%.1f"),
                },
            )

# ── Trend PNRR ────────────────────────────────────────────────────────────────
trend_pnrr = load_mart_trend_pnrr(year)
if not trend_pnrr.empty:
    st.subheader(f"Trend PNRR — {year}")
    st.dataframe(trend_pnrr, use_container_width=True, hide_index=True)

# ── Esiti per procedura ──────────────────────────────────────────────────────
esiti = load_mart_esiti_procedura(year)
if not esiti.empty:
    st.subheader(f"Esiti per procedura — {year}")
    st.dataframe(esiti, use_container_width=True, hide_index=True)

st.caption("Dati: ANAC (dati.anticorruzione.it) · CC BY 4.0")
