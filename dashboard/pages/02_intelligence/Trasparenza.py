"""Trasparenza -- Concentrazione mercato, affidamenti diretti, top imprese."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from lab_connectors.formatters import fmt_num
from sources import (
    load_compose_panoramica_annuale,
    load_mart_sa_profilo,
    load_mart_imprese,
    YEARS_BANDI,
    fmt_eur_short,
    query_duckdb,
    _clean_path,
    _latest_year,
)

st.title("Trasparenza -- Chi compra e come?")

try:
    ann_compose = load_compose_panoramica_annuale()
    sa_profilo = load_mart_sa_profilo()
    imprese = load_mart_imprese()
except Exception as e:
    st.error(f"Errore caricamento dati: {e}")
    st.stop()

# -- Concentrazione mercato: top imprese ----------------------------------------
st.subheader("Concentrazione del mercato")
if not imprese.empty:
    top_agg = imprese[imprese["n_aggiudicazioni"] > 0].nlargest(20, "n_aggiudicazioni")
    totale_agg = imprese["n_aggiudicazioni"].sum()
    top_agg["pct_mercato"] = (top_agg["n_aggiudicazioni"] / totale_agg * 100).round(2)
    top_agg["cum_pct"] = top_agg["pct_mercato"].cumsum().round(2)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            top_agg.head(10), x="n_aggiudicazioni", y="denominazione", orientation="h",
            title="Top 10 imprese per numero aggiudicazioni",
            labels={"denominazione": "Impresa", "n_aggiudicazioni": "Aggiudicazioni"},
            text="pct_mercato",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=400)
        st.plotly_chart(fig, use_container_width=True, key="trasparenza_top_imprese")
    with col2:
        st.dataframe(
            top_agg[["denominazione", "n_aggiudicazioni", "pct_mercato", "cum_pct"]].head(10),
            use_container_width=True, hide_index=True,
            column_config={
                "pct_mercato": st.column_config.NumberColumn("% mercato", format="%.2f"),
                "cum_pct": st.column_config.NumberColumn("% cumulato", format="%.2f"),
            },
        )
        st.info(
            f"Le top 10 imprese controllano il **{top_agg['pct_mercato'].head(10).sum():.1f}%** "
            f"delle aggiudicazioni totali ({fmt_num(int(totale_agg))} totale)."
        )

# -- Affidamenti diretti vs gara ------------------------------------------------
st.subheader("Affidamenti diretti vs gara pubblica")
bandi_path = _clean_path("anac_bandi_gara", _latest_year("anac_bandi_gara", 2025))
if bandi_path:
    tipo_dist = query_duckdb(f"""
        SELECT tipo_scelta_contraente AS tipo, COUNT(*) AS n,
               ROUND(SUM(importo_lotto)/1e9,1) AS mld
        FROM read_parquet('{bandi_path}')
        WHERE stato = 'ATTIVO'
        GROUP BY tipo ORDER BY n DESC LIMIT 10
    """)
    if not tipo_dist.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig2 = px.pie(
                tipo_dist.head(5), values="n", names="tipo",
                title="Distribuzione per tipo scelta contraente",
            )
            st.plotly_chart(fig2, use_container_width=True, key="trasparenza_tipo_scelta")
        with col2:
            st.dataframe(
                tipo_dist, use_container_width=True, hide_index=True,
                column_config={
                    "n": st.column_config.NumberColumn("N bandi"),
                    "mld": st.column_config.NumberColumn("Importo (mld)", format="%.1f"),
                },
            )

# -- SA che comprano di piu' ----------------------------------------------------
st.subheader("Chi compra di piu'?")
if not sa_profilo.empty:
    top_sa = sa_profilo.head(15)
    fig3 = px.bar(
        top_sa, x="importo_totale", y="denominazione_sa", orientation="h",
        title="Top 15 SA per importo bandi",
        labels={"denominazione_sa": "Stazione Appaltante", "importo_totale": "Importo (EUR)"},
    )
    fig3.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
    st.plotly_chart(fig3, use_container_width=True, key="trasparenza_top_sa")

    col1, col2, col3 = st.columns(3)
    col1.metric("SA totali (>=10 bandi)", fmt_num(len(sa_profilo)))
    col2.metric("SA con PNRR", fmt_num(int((sa_profilo["n_pnrr"] > 0).sum())))
    top3 = sa_profilo.head(3)
    col3.metric("Top 3", f"{top3['denominazione_sa'].iloc[0][:30]}...")

st.caption("Dati: ANAC (dati.anticorruzione.it) -- CC BY 4.0")
