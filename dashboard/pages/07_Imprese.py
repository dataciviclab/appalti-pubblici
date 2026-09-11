"""Imprese — Chi vince le gare, chi partecipa, chi fa subappalti.

Include: raggruppamenti (RTI), catene di subappalto, profilo impresa.
"""

import streamlit as st
import plotly.express as px
from lab_connectors.formatters import fmt_num
from sources import load_mart_imprese, query_duckdb, _clean_path

st.title("🏢 Imprese")
st.markdown(
    "Profilo delle imprese nei mercati ANAC: chi vince, chi partecipa, "
    "chi fa subappalti, come si organizzano i raggruppamenti."
)

imprese = load_mart_imprese()
if imprese.empty:
    st.warning("Nessun dato impresa disponibile.")
    st.stop()

# ── KPI generali ─────────────────────────────────────────────────────────────
st.subheader("Panoramica imprese")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Imprese totali", fmt_num(len(imprese)))
c2.metric("Aggiudicatari", fmt_num(int((imprese["n_aggiudicazioni"] > 0).sum())))
c3.metric("Partecipanti", fmt_num(int((imprese["n_gare_partecipate"] > 0).sum())))
c4.metric("Subappaltanti", fmt_num(int((imprese["n_subappalti"] > 0).sum())))

# ── Distribuzione ruolo prevalente ────────────────────────────────────────────
st.subheader("Ruolo prevalente")
ruolo_dist = imprese["ruolo_prevalente"].value_counts().reset_index()
ruolo_dist.columns = ["ruolo", "n_imprese"]
fig = px.pie(ruolo_dist, values="n_imprese", names="ruolo", title="Distribuzione ruolo prevalente")
st.plotly_chart(fig, use_container_width=True)

# ── Top imprese per attività ──────────────────────────────────────────────────
st.subheader("Top imprese per attività totale")
n_top = st.slider("Numero di imprese", 5, 50, 20, key="n_top_imprese")
top = imprese.nlargest(n_top, "totale_attivita")

st.dataframe(
    top[["denominazione", "tipo_soggetto", "ruolo_prevalente",
         "n_aggiudicazioni", "n_gare_partecipate", "n_subappalti", "totale_attivita"]],
    use_container_width=True, hide_index=True,
    column_config={
        "denominazione": st.column_config.TextColumn("Impresa", width="large"),
        "totale_attivita": st.column_config.NumberColumn("Totale attività"),
    },
)

fig = px.bar(
    top, x="totale_attivita", y="denominazione", orientation="h",
    color="ruolo_prevalente",
    title=f"Top {n_top} imprese per attività",
    labels={"denominazione": "Impresa", "totale_attivita": "Totale attività"},
)
fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=max(300, n_top * 25))
st.plotly_chart(fig, use_container_width=True)


# ── Helper functions (cross-dataset queries) ──────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _duckdb_rti():
    """RTI: mandataria + mandanti per CIG."""
    part_p = _clean_path("anac_partecipanti", 2026)
    return query_duckdb(f"""
        SELECT
            p1.cig,
            p1.codice_fiscale AS cf_mandataria,
            MAX(p1.denominazione) AS mandataria,
            COUNT(DISTINCT p2.codice_fiscale) AS n_mandanti,
            STRING_AGG(DISTINCT p2.denominazione, ' | ' ORDER BY p2.denominazione) AS mandanti
        FROM read_parquet('{part_p}') p1
        JOIN read_parquet('{part_p}') p2
            ON p1.cig = p2.cig AND p2.ruolo = 'MANDANTE'
        WHERE p1.ruolo = 'MANDATARIA'
        GROUP BY p1.cig, p1.codice_fiscale
        HAVING COUNT(DISTINCT p2.codice_fiscale) >= 2
        ORDER BY n_mandanti DESC
    """)


@st.cache_data(ttl=3600, show_spinner=False)
def _duckdb_subappalti():
    """Subappalti: imprese che ricevono subappalti."""
    sub_p = _clean_path("anac_subappalti", 2026)
    return query_duckdb(f"""
        SELECT
            denominazione,
            COUNT(*) AS n_subappalti,
            COUNT(DISTINCT cig) AS n_cig,
            COUNT(DISTINCT codice_fiscale) AS n_imprese_committenti
        FROM read_parquet('{sub_p}')
        WHERE denominazione IS NOT NULL AND denominazione != ''
        GROUP BY denominazione
        ORDER BY n_subappalti DESC
    """)

# ── Raggruppamenti (RTI) ─────────────────────────────────────────────────────
st.subheader("Raggruppamenti (RTI)")
st.markdown(
    "Come si organizzano le imprese: mandataria (capogruppo) + mandanti (membri)."
)

rti_data = _duckdb_rti()

if not rti_data.empty:
    c1, c2 = st.columns(2)
    c1.metric("CIG con RTI (≥2 mandanti)", fmt_num(len(rti_data)))

    max_mandanti = int(rti_data["n_mandanti"].max())
    c2.metric("Max mandanti in un RTI", fmt_num(max_mandanti))

    st.dataframe(
        rti_data[["mandataria", "n_mandanti", "mandanti"]].head(10),
        use_container_width=True, hide_index=True,
        column_config={
            "mandataria": st.column_config.TextColumn("Mandataria", width="large"),
            "mandanti": st.column_config.TextColumn("Mandanti", width="xlarge"),
        },
    )
else:
    st.info("Nessun RTI trovato nei dati.")

# ── Catene di subappalto ──────────────────────────────────────────────────────
st.subheader("Catene di subappalto")
st.markdown(
    "Chi riceve i subappalti: imprese che lavorano per conto di altre."
)

sub_data = _duckdb_subappalti()

if not sub_data.empty:
    c1, c2 = st.columns(2)
    c1.metric("Imprese che ricevono subappalti", fmt_num(len(sub_data)))
    c2.metric("Top subappaltatrice", sub_data.iloc[0]["denominazione"][:40])

    fig = px.bar(
        sub_data.head(15), x="n_subappalti", y="denominazione", orientation="h",
        title="Top 15 imprese per subappalti ricevuti",
        labels={"denominazione": "Impresa", "n_subappalti": "Subappalti"},
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        sub_data[["denominazione", "n_subappalti", "n_cig", "n_imprese_committenti"]],
        use_container_width=True, hide_index=True,
        column_config={
            "denominazione": st.column_config.TextColumn("Impresa", width="large"),
        },
    )

# ── Filtro per ruolo ─────────────────────────────────────────────────────────
st.subheader("Cerca per ruolo")
ruolo_filter = st.selectbox("Filtra per ruolo", ["Tutti", "aggiudicatario", "partecipante", "subappaltante", "sconosciuto"])

if ruolo_filter != "Tutti":
    filtered = imprese[imprese["ruolo_prevalente"] == ruolo_filter]
else:
    filtered = imprese

st.dataframe(
    filtered[["denominazione", "tipo_soggetto", "ruolo_prevalente",
              "n_aggiudicazioni", "n_gare_partecipate", "n_subappalti", "totale_attivita"]]
    .sort_values("totale_attivita", ascending=False).head(100),
    use_container_width=True, hide_index=True,
    column_config={
        "denominazione": st.column_config.TextColumn("Impresa", width="large"),
        "totale_attivita": st.column_config.NumberColumn("Totale attività"),
    },
)

st.caption("Dati: ANAC (dati.anticorruzione.it) · CC BY 4.0")
