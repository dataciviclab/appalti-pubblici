"""Aggiudicazioni — Importi, criteri, competitività."""

import streamlit as st
import plotly.express as px
from lab_connectors.formatters import fmt_num, fmt_eur
from sources import load_mart_annuale_agg

st.title("🏆 Aggiudicazioni")

try:
    ann = load_mart_annuale_agg()
except Exception as e:
    st.error(f"Errore caricamento: {e}")
    st.stop()

if ann.empty:
    st.warning("Nessun dato aggiudicazioni disponibile.")
    st.stop()

# ── KPI ───────────────────────────────────────────────────────────────────────
st.subheader("Riepilogo annuale")
st.dataframe(ann, use_container_width=True, hide_index=True)

# ── Trend importi ─────────────────────────────────────────────────────────────
if "anno_aggiudicazione" in ann.columns and "importo_totale" in ann.columns:
    st.subheader("Trend importi aggiudicazione")
    ann_sorted = ann.sort_values("anno_aggiudicazione")
    fig = px.bar(
        ann_sorted, x="anno_aggiudicazione", y="importo_totale",
        title="Importo totale aggiudicato per anno",
        labels={"anno_aggiudicazione": "Anno", "importo_totale": "Importo (€)"},
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Criteri aggiudicazione ────────────────────────────────────────────────────
if "criterio_aggiudicazione" in ann.columns:
    st.subheader("Criteri di aggiudicazione")
    crit = ann.groupby("criterio_aggiudicazione", dropna=False)["n_aggiudicazioni"].sum().reset_index()
    crit = crit.sort_values("n_aggiudicazioni", ascending=False)
    fig = px.pie(crit, values="n_aggiudicazioni", names="criterio_aggiudicazione",
                 title="Distribuzione criteri")
    st.plotly_chart(fig, use_container_width=True)

st.caption("Dati: ANAC (dati.anticorruzione.it) · CC BY 4.0")
