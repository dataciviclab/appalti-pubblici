"""Ritardi e Monitoraggio — Analisi dei ritardi negli appalti pubblici.

Usa mart_ritardi_per_sa (compose) per analisi SA × settore.
Usa mart_sal (singolo) per trend temporale.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from lab_connectors.formatters import fmt_num, fmt_eur
from sources import load_mart_ritardi_per_sa, load_mart_sal, _years_for, fmt_eur_short

st.title("⏱️ Ritardi e Monitoraggio")
st.markdown(
    "Analisi dei ritardi SAL (Stati di Avanzamento) negli appalti pubblici. "
    "Un SAL in ritardo indica che il progetto sta slittando rispetto alla programmazione."
)

# ── KPI trend ritardi ────────────────────────────────────────────────────────
st.subheader("Trend ritardi nel tempo")
sal = load_mart_sal()
if not sal.empty:
    trend = (
        sal.groupby("anno")
        .agg(
            totale=("n_sal", "sum"),
            in_ritardo=("n_sal", lambda x: x[sal.loc[x.index, "flag_ritardo"] == "IN RITARDO"].sum()),
        )
        .reset_index()
    )
    trend["pct_ritardo"] = (trend["in_ritardo"] / trend["totale"] * 100).round(1)
    trend = trend[trend["anno"] >= 2008]

    col_a, col_b = st.columns(2)
    with col_a:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=trend["anno"], y=trend["in_ritardo"],
            name="In ritardo", marker_color="#ef4444"
        ))
        fig.add_trace(go.Bar(
            x=trend["anno"], y=trend["totale"] - trend["in_ritardo"],
            name="In linea", marker_color="#22c55e"
        ))
        fig.update_layout(barmode="stack", title="SAL totali vs in ritardo",
                          xaxis=dict(dtick=2), height=350)
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        fig2 = px.line(
            trend, x="anno", y="pct_ritardo",
            title="% SAL in ritardo per anno",
            labels={"pct_ritardo": "% in ritardo", "anno": "Anno"},
            markers=True,
        )
        fig2.update_layout(yaxis=dict(range=[0, trend["pct_ritardo"].max() * 1.2]),
                           xaxis=dict(dtick=2), height=350)
        st.plotly_chart(fig2, use_container_width=True)

# ── Ritardi per SA (compose) ─────────────────────────────────────────────────
st.subheader("Dove ci sono problemi? — Ritardi per SA")
ritardi_sa = load_mart_ritardi_per_sa()
if not ritardi_sa.empty:
    col1, col2 = st.columns(2)
    with col1:
        top_sa = ritardi_sa.nlargest(20, "n_ritardi")
        fig = px.bar(
            top_sa, x="n_ritardi", y="sa", orientation="h",
            title="Top 20 SA per numero ritardi",
            labels={"sa": "Stazione Appaltante", "n_ritardi": "Ritardi"},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=600)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.dataframe(
            top_sa[["sa", "settore", "n_ritardi", "n_cig_ritardo", "max_gg_ritardo", "importo_ritardo_totale"]],
            use_container_width=True, hide_index=True,
            column_config={
                "max_gg_ritardo": st.column_config.NumberColumn("Max ritardo (gg)"),
                "importo_ritardo_totale": st.column_config.NumberColumn("Importo SAL ritardo", format="€%.0f"),
            },
        )

    # Ritardi per settore
    st.subheader("Ritardi per settore")
    ritardi_settore = (
        ritardi_sa.groupby("settore")
        .agg(n_ritardi=("n_ritardi", "sum"), importo=("importo_ritardo_totale", "sum"))
        .reset_index()
        .sort_values("n_ritardi", ascending=False)
    )
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            ritardi_settore.head(10), x="n_ritardi", y="settore", orientation="h",
            title="Top 10 settori per ritardi",
            labels={"settore": "Settore", "n_ritardi": "Ritardi"},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=400)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.bar(
            ritardi_settore.head(10), x="importo", y="settore", orientation="h",
            title="Top 10 settori per importo ritardo",
            labels={"settore": "Settore", "importo": "Importo (€)"},
        )
        fig2.update_layout(yaxis={"categoryorder": "total ascending"}, height=400)
        st.plotly_chart(fig2, use_container_width=True)

st.caption("Dati: ANAC (dati.anticorruzione.it) · CC BY 4.0")
