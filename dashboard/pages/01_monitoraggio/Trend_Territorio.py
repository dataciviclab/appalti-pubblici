"""Trend Territorio -- Competitivita per regione nel tempo."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from lab_connectors.formatters import fmt_num
from sources import load_mart_competitivita, fmt_eur_short

st.title("Trend Territorio")

comp = load_mart_competitivita()
if comp.empty:
    st.warning("Nessun dato di competitivita disponibile.")
    st.stop()

# -- Pulizia nomi regioni -------------------------------------------------------
comp["regione_short"] = (
    comp["regione"]
    .str.replace(r"^SEZIONE REGIONALE\s+", "", regex=True)
    .str.strip()
)

# -- Filtro: escludi CENTRALE e NON CLASSIFICATO --------------------------------
exclude_special = st.checkbox(
    "Escludi 'Centrale' e 'Non classificato'",
    value=True,
    help="'Centrale' = enti nazionali (RFI, CONSIP, INPS...). 'Non classificato' = senza regione.",
)
if exclude_special:
    comp = comp[~comp["regione_short"].isin(["CENTRALE", "NON CLASSIFICATO"])]

if comp.empty:
    st.warning("Nessun dato dopo i filtri.")
    st.stop()

# -- Filtro anno ----------------------------------------------------------------
year = st.selectbox("Anno", sorted(comp["anno"].unique(), reverse=True))

comp_year = comp[comp["anno"] == year]
if comp_year.empty:
    st.warning(f"Nessun dato per l'anno {year}.")
    st.stop()

# -- Top 10 regioni per importo -------------------------------------------------
st.subheader(f"Top 10 regioni per importo -- {year}")
col1, col2 = st.columns(2)
with col1:
    top_regioni = comp_year.nlargest(10, "importo_totale")
    fig = px.bar(
        top_regioni, x="importo_totale", y="regione_short", orientation="h",
        title=f"Top 10 regioni -- {year}",
        labels={"regione_short": "Regione", "importo_totale": "Importo (EUR)"},
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=400)
    st.plotly_chart(fig, use_container_width=True, key="territorio_top_regioni")
with col2:
    st.dataframe(
        comp_year[["regione_short", "n_bandi", "importo_totale", "n_aggiudicati",
                    "offerenti_medi", "tasso_aggiudicazione_pct"]]
        .sort_values("importo_totale", ascending=False).head(15)
        .rename(columns={"regione_short": "Regione"}),
        use_container_width=True, hide_index=True,
        column_config={
            "tasso_aggiudicazione_pct": st.column_config.NumberColumn("Tasso agg. %", format="%.1f"),
            "offerenti_medi": st.column_config.NumberColumn("Offerenti medi", format="%.1f"),
            "importo_totale": st.column_config.NumberColumn("Importo", format="€%.0f"),
        },
    )

# -- Trend multi-anno per regione -----------------------------------------------
st.subheader("Evoluzione regionale nel tempo")
regioni_top = comp.groupby("regione_short")["importo_totale"].sum().nlargest(5).index.tolist()
comp_top = comp[comp["regione_short"].isin(regioni_top)]

fig2 = px.line(
    comp_top, x="anno", y="importo_totale", color="regione_short",
    title="Top 5 regioni: trend importi 2016-2025",
    labels={"importo_totale": "Importo (EUR)", "anno": "Anno", "regione_short": "Regione"},
    markers=True,
)
fig2.update_layout(height=400)
st.plotly_chart(fig2, use_container_width=True, key="territorio_trend_regioni")

# -- Heatmap regioni x anni -----------------------------------------------------
st.subheader("Heatmap: importo per regione x anno")
pivot = comp.pivot_table(
    index="regione_short", columns="anno", values="importo_totale", aggfunc="sum"
).fillna(0)

fig3 = px.imshow(
    pivot.values,
    labels=dict(x="Anno", y="Regione", color="Importo (EUR)"),
    y=pivot.index.tolist(),
    x=pivot.columns.tolist(),
    color_continuous_scale="Blues",
    aspect="auto",
)
fig3.update_layout(height=max(400, len(pivot) * 25))
st.plotly_chart(fig3, use_container_width=True, key="territorio_heatmap")

st.caption("Dati: ANAC (dati.anticorruzione.it) -- CC BY 4.0")
