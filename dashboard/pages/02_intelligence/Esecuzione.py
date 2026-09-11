"""Esecuzione -- Funnel, ritardi SAL, monitoraggio esecuzione appalti."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from lab_connectors.formatters import fmt_num
from sources import (
    load_mart_ritardi_per_sa,
    load_mart_sal,
    load_compose_panoramica_annuale,
    YEARS_BANDI,
    fmt_eur_short,
    query_duckdb,
    _clean_path,
    _latest_year,
)

st.title("Esecuzione -- Dal bando al collaudo")

# -- Funnel appalti -------------------------------------------------------------
st.subheader("Funnel: quanti bandi diventano lavori?")

bandi_year = _latest_year("anac_bandi_gara", 2025)
bandi_p = _clean_path("anac_bandi_gara", bandi_year)
sal_p = _clean_path("anac_stati_avanzamento", _latest_year("anac_stati_avanzamento", 2026))

if bandi_p and sal_p:
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
              AND EXTRACT(YEAR FROM data_emissione_sal) = {bandi_year}
        )
        SELECT * FROM bandi, sal
    """)
    if not funnel.empty:
        f = funnel.iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(
            f"Pubblicati ({bandi_year})",
            f"{fmt_num(int(f['n_bandi']))} bandi",
            f"EUR {f['importo_mld']} mld",
        )
        col2.metric(
            "Aggiudicati",
            f"{fmt_num(int(f['n_aggiudicati']))}",
            f"EUR {f['importo_agg_mld']} mld",
        )
        col3.metric(
            "In esecuzione (SAL)",
            f"{fmt_num(int(f['n_sal']))}",
            f"EUR {f['importo_sal_mld']} mld",
        )
        col4.metric(
            "SAL in ritardo",
            f"{fmt_num(int(f['n_ritardi']))}",
            f"EUR {f['importo_ritardi_mld']} mld",
        )

        fig = go.Figure()
        stages = ["Pubblicati", "Aggiudicati", "In esecuzione", "In ritardo"]
        values_n = [int(f['n_bandi']), int(f['n_aggiudicati']), int(f['n_sal']), int(f['n_ritardi'])]
        values_eur = [f['importo_mld'], f['importo_agg_mld'], f['importo_sal_mld'], f['importo_ritardi_mld']]
        colors = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444"]

        fig.add_trace(go.Bar(
            x=stages, y=values_n,
            text=[f"{fmt_num(v)}<br>EUR {e} mld" for v, e in zip(values_n, values_eur)],
            textposition="outside",
            marker_color=colors,
        ))
        fig.update_layout(title=f"Funnel appalti {bandi_year}", yaxis_title="Numero", height=400)
        st.plotly_chart(fig, use_container_width=True, key="esecuzione_funnel")

        gap = int(f['n_aggiudicati']) - int(f['n_sal'])
        st.info(
            f"**Gap esecuzione**: {fmt_num(gap)} appalti aggiudicati non hanno ancora SAL attivi. "
            f"Possono essere in attesa di avvio, bloccati, o troppo recenti."
        )

# -- Trend ritardi nel tempo ----------------------------------------------------
st.subheader("Trend ritardi SAL nel tempo")
sal = load_mart_sal()
if not sal.empty:
    sal_ritardo = sal[sal["flag_ritardo"] == "IN RITARDO"]
    trend = (
        sal.groupby("anno")
        .agg(totale=("n_sal", "sum"))
        .reset_index()
    )
    ritardi_per_anno = (
        sal_ritardo.groupby("anno")
        .agg(in_ritardo=("n_sal", "sum"))
        .reset_index()
    )
    trend = trend.merge(ritardi_per_anno, on="anno", how="left").fillna(0)
    trend["in_ritardo"] = trend["in_ritardo"].astype(int)
    trend["pct_ritardo"] = (trend["in_ritardo"] / trend["totale"] * 100).round(1)
    trend = trend[trend["anno"] >= 2008]

    col_a, col_b = st.columns(2)
    with col_a:
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=trend["anno"], y=trend["in_ritardo"],
            name="In ritardo", marker_color="#ef4444"
        ))
        fig2.add_trace(go.Bar(
            x=trend["anno"], y=trend["totale"] - trend["in_ritardo"],
            name="In linea", marker_color="#22c55e"
        ))
        fig2.update_layout(barmode="stack", title="SAL totali vs in ritardo",
                          xaxis=dict(dtick=2), height=350)
        st.plotly_chart(fig2, use_container_width=True, key="esecuzione_ritardi_stacked")
    with col_b:
        fig3 = px.line(
            trend, x="anno", y="pct_ritardo",
            title="% SAL in ritardo per anno",
            labels={"pct_ritardo": "% in ritardo", "anno": "Anno"},
            markers=True,
        )
        fig3.update_layout(yaxis=dict(range=[0, trend["pct_ritardo"].max() * 1.2]),
                           xaxis=dict(dtick=2), height=350)
        st.plotly_chart(fig3, use_container_width=True, key="esecuzione_ritardi_pct")

# -- Ritardi per SA (compose) ---------------------------------------------------
st.subheader("Dove ci sono problemi? -- Ritardi per SA")
ritardi_sa = load_mart_ritardi_per_sa()
if not ritardi_sa.empty:
    col1, col2 = st.columns(2)
    with col1:
        top_sa = ritardi_sa.nlargest(20, "n_ritardi")
        fig4 = px.bar(
            top_sa, x="n_ritardi", y="sa", orientation="h",
            title="Top 20 SA per numero ritardi",
            labels={"sa": "Stazione Appaltante", "n_ritardi": "Ritardi"},
        )
        fig4.update_layout(yaxis={"categoryorder": "total ascending"}, height=600)
        st.plotly_chart(fig4, use_container_width=True, key="esecuzione_sa_ritardi")
    with col2:
        st.dataframe(
            top_sa[["sa", "settore", "n_ritardi", "n_cig_ritardo", "max_gg_ritardo", "importo_ritardo_totale"]],
            use_container_width=True, hide_index=True,
            column_config={
                "max_gg_ritardo": st.column_config.NumberColumn("Max ritardo (gg)"),
                "importo_ritardo_totale": st.column_config.NumberColumn("Importo SAL ritardo", format="€%.0f"),
            },
        )

    st.subheader("Ritardi per settore")
    ritardi_settore = (
        ritardi_sa.groupby("settore")
        .agg(n_ritardi=("n_ritardi", "sum"), importo=("importo_ritardo_totale", "sum"))
        .reset_index()
        .sort_values("n_ritardi", ascending=False)
    )
    col1, col2 = st.columns(2)
    with col1:
        fig5 = px.bar(
            ritardi_settore.head(10), x="n_ritardi", y="settore", orientation="h",
            title="Top 10 settori per ritardi",
            labels={"settore": "Settore", "n_ritardi": "Ritardi"},
        )
        fig5.update_layout(yaxis={"categoryorder": "total ascending"}, height=400)
        st.plotly_chart(fig5, use_container_width=True, key="esecuzione_settori_ritardi_n")
    with col2:
        fig6 = px.bar(
            ritardi_settore.head(10), x="importo", y="settore", orientation="h",
            title="Top 10 settori per importo ritardo",
            labels={"settore": "Settore", "importo": "Importo (EUR)"},
        )
        fig6.update_layout(yaxis={"categoryorder": "total ascending"}, height=400)
        st.plotly_chart(fig6, use_container_width=True, key="esecuzione_settori_ritardi_eur")

st.caption("Dati: ANAC (dati.anticorruzione.it) -- CC BY 4.0")
