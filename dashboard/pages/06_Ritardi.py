"""Ritardi e Monitoraggio — Analisi dei ritardi negli appalti pubblici."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from lab_connectors.formatters import fmt_num
from sources import YEARS_BANDI, query, _years_for

st.title("⏱️ Ritardi e Monitoraggio")
st.markdown(
    "Analisi dei ritardi SAL (Stati di Avanzamento) negli appalti pubblici. "
    "Un SAL in ritardo indica che il progetto sta slittando rispetto alla programmazione."
)

# ── Caricamento dati ──────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_ritardi_data():
    sal_years = _years_for("anac_stati_avanzamento")
    sal = query(
        "SELECT *, EXTRACT(YEAR FROM data_emissione_sal) AS anno "
        "FROM clean_input WHERE data_emissione_sal IS NOT NULL",
        years=sal_years or [2026], slug="anac_stati_avanzamento",
    )
    bandi = query(
        "SELECT DISTINCT cig, denominazione_amministrazione_appaltante AS sa, "
        "oggetto_principale_contratto AS settore, importo_lotto FROM clean_input",
        years=YEARS_BANDI,
        slug="anac_bandi_gara",
    )
    if sal.empty:
        return sal
    return sal.merge(bandi, on="cig", how="left")


with st.spinner("Caricamento dati SAL + bandi…"):
    df = load_ritardi_data()

if df.empty:
    st.warning("Nessun dato disponibile.")
    st.stop()

# ── KPI ───────────────────────────────────────────────────────────────────────
st.subheader("KPI complessivi")
ritardo = df[df["flag_ritardo"] == "IN RITARDO"]
k1, k2, k3, k4 = st.columns(4)
k1.metric("SAL totali", fmt_num(len(df)))
k2.metric("SAL in ritardo", fmt_num(len(ritardo)))
pct_ritardo = len(ritardo) / len(df) * 100 if len(df) > 0 else 0
k3.metric("% in ritardo", f"{pct_ritardo:.1f}%")
k4.metric("CIG coinvolti", fmt_num(ritardo["cig"].nunique()))

# ── Trend ritardi nel tempo ───────────────────────────────────────────────────
st.subheader("Trend ritardi nel tempo")
trend = (
    df.groupby("anno")
    .agg(
        totale=("flag_ritardo", "count"),
        in_ritardo=("flag_ritardo", lambda x: (x == "IN RITARDO").sum()),
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

# ── Top SA per ritardi ────────────────────────────────────────────────────────
st.subheader("Top SA per ritardi")
ritardo_sa = (
    ritardo[ritardo["sa"].notna() & (ritardo["sa"] != "")]
    .groupby("sa")
    .agg(
        n_ritardi=("flag_ritardo", "count"),
        n_cig=("cig", "nunique"),
        max_gg=("n_giorni_scostamento", "max"),
        importo_ritardo=("importo_sal", "sum"),
        importo_lotto=("importo_lotto", "first"),
    )
    .reset_index()
    .sort_values("n_ritardi", ascending=False)
)

if not ritardo_sa.empty:
    col1, col2 = st.columns(2)
    with col1:
        top20 = ritardo_sa.head(20)
        fig = px.bar(
            top20, x="n_ritardi", y="sa", orientation="h",
            title="Top 20 SA per numero SAL in ritardo",
            labels={"sa": "Stazione Appaltante", "n_ritardi": "SAL in ritardo"},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.dataframe(
            ritardo_sa[["sa", "n_ritardi", "n_cig", "max_gg", "importo_ritardo"]].head(20),
            use_container_width=True, hide_index=True,
            column_config={
                "importo_ritardo": st.column_config.NumberColumn("Importo SAL ritardo", format="€%.0f"),
                "max_gg": st.column_config.NumberColumn("Max gg ritardo"),
            },
        )

# ── Ritardi per settore ───────────────────────────────────────────────────────
st.subheader("Ritardi per settore")
ritardo_settore = (
    ritardo[ritardo["settore"].notna() & (ritardo["settore"] != "")]
    .groupby("settore")
    .agg(
        n_ritardi=("flag_ritardo", "count"),
        n_cig=("cig", "nunique"),
        importo=("importo_sal", "sum"),
    )
    .reset_index()
    .sort_values("n_ritardi", ascending=False)
)

if not ritardo_settore.empty:
    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            ritardo_settore.head(10), x="n_ritardi", y="settore", orientation="h",
            title="Top 10 settori per SAL in ritardo",
            labels={"settore": "Settore", "n_ritardi": "SAL in ritardo"},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=400)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.bar(
            ritardo_settore.head(10), x="importo", y="settore", orientation="h",
            title="Top 10 settori per importo SAL in ritardo",
            labels={"settore": "Settore", "importo": "Importo SAL (€)"},
        )
        fig2.update_layout(yaxis={"categoryorder": "total ascending"}, height=400)
        st.plotly_chart(fig2, use_container_width=True)

# ── Correlazione ritardi × importo ────────────────────────────────────────────
st.subheader("Correlazione ritardi × importo")
ritardo_validi = ritardo[
    (ritardo["importo_lotto"].notna()) &
    (ritardo["importo_lotto"] > 0) &
    (ritardo["n_giorni_scostamento"].notna()) &
    (ritardo["n_giorni_scostamento"] > 0) &
    (ritardo["n_giorni_scostamento"] < 5000)
]
if not ritardo_validi.empty:
    fig = px.scatter(
        ritardo_validi, x="n_giorni_scostamento", y="importo_lotto",
        color="settore", hover_data=["cig", "sa"],
        title="Giorni di ritardo vs Importo lotto",
        labels={"n_giorni_scostamento": "Giorni ritardo", "importo_lotto": "Importo lotto (€)"},
        opacity=0.4,
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

# ── Top CIG piu in ritardo ────────────────────────────────────────────────────
st.subheader("Top CIG piu in ritardo")
top_cig = (
    ritardo.groupby(["cig", "sa", "settore"])
    .agg(
        max_gg=("n_giorni_scostamento", "max"),
        n_ritardi=("flag_ritardo", "count"),
        n_sal=("flag_ritardo", "count"),
        importo_lotto=("importo_lotto", "first"),
        periodo_min=("data_emissione_sal", "min"),
        periodo_max=("data_emissione_sal", "max"),
    )
    .reset_index()
    .sort_values("max_gg", ascending=False)
)
top_cig = top_cig[top_cig["max_gg"] > 200]

if not top_cig.empty:
    st.dataframe(
        top_cig[["cig", "sa", "settore", "max_gg", "n_ritardi", "importo_lotto",
                  "periodo_min", "periodo_max"]].head(30),
        use_container_width=True, hide_index=True,
        column_config={
            "importo_lotto": st.column_config.NumberColumn("Importo", format="€%.0f"),
            "max_gg": st.column_config.NumberColumn("Max ritardo (gg)"),
            "periodo_min": st.column_config.DateColumn("Primo SAL"),
            "periodo_max": st.column_config.DateColumn("Ultimo SAL"),
        },
    )

st.caption("Dati: ANAC (dati.anticorruzione.it) · CC BY 4.0")
