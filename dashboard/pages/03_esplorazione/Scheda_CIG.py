"""Scheda CIG -- Profilo completo di un CIG negli appalti ANAC."""

import streamlit as st
import plotly.express as px
from lab_connectors.formatters import fmt_num
from sources import search_cig, top_cig_by_importo, fmt_eur_short

st.title("Scheda CIG")

# -- Tabs principali ------------------------------------------------------------
tab_cig, tab_cig_top = st.tabs(["Cerca per CIG", "Top CIG"])

# -- Tab 1: Profilo completo CIG ------------------------------------------------
with tab_cig:
    cig_input = st.text_input(
        "CIG",
        placeholder="es. B3F52D2",
        help="Codice Identificativo di Gara. Case-insensitive.",
        key="cig_direct",
    )

    if cig_input:
        cig = cig_input.strip().upper()
        with st.spinner(f"Ricerca `{cig}` in tutti i dataset..."):
            results = search_cig(cig)

        if not results:
            st.warning(f"CIG `{cig}` non trovato in nessun dataset.")
        else:
            st.success(f"CIG `{cig}` trovato in {len(results)} dataset")

            bandi = results.get("anac_bandi_gara")
            if bandi is not None and not bandi.empty:
                st.subheader("Bandi di Gara")
                b = bandi.iloc[0]
                c1, c2, c3 = st.columns(3)
                c1.metric("SA", str(b.get("denominazione_amministrazione_appaltante", "---"))[:40])
                c2.metric("Importo", fmt_eur_short(b.get('importo_lotto', 0)))
                c3.metric("Regione", b.get("sezione_regionale", "---"))
                st.dataframe(bandi, use_container_width=True, hide_index=True)

            order = [
                ("anac_aggiudicazioni", "Aggiudicazioni"),
                ("anac_aggiudicatari", "Aggiudicatari"),
                ("anac_partecipanti", "Partecipanti"),
                ("anac_cup", "CUP"),
                ("anac_stati_avanzamento", "SAL"),
                ("anac_collaudo", "Collaudo"),
                ("anac_subappalti", "Subappalti"),
            ]

            for key, label in order:
                if key in results:
                    df = results[key]
                    with st.expander(f"{label} -- {len(df)} righe"):
                        st.dataframe(df, use_container_width=True, hide_index=True)

# -- Tab 2: Top CIG per importo -------------------------------------------------
with tab_cig_top:
    st.markdown("I bandi con gli importi piu' alti -- per scoprire CIG da esplorare.")

    n_top = st.slider("Numero di CIG", 5, 50, 20, key="n_top_cig")

    with st.spinner("Caricamento top CIG..."):
        df_top = top_cig_by_importo(limit=n_top)

    if df_top.empty:
        st.warning("Nessun dato disponibile.")
    else:
        st.dataframe(
            df_top,
            use_container_width=True, hide_index=True,
            column_config={
                "importo_lotto": st.column_config.NumberColumn("Importo", format="€%.0f"),
                "cig": st.column_config.TextColumn("CIG", width="medium"),
                "sa": st.column_config.TextColumn("SA", width="large"),
                "oggetto_gara": st.column_config.TextColumn("Oggetto", width="xlarge"),
            },
        )

        fig = px.bar(
            df_top.head(15), x="importo_lotto", y="cig",
            orientation="h",
            title=f"Top {min(15, len(df_top))} CIG per importo",
            labels={"importo_lotto": "Importo (EUR)", "cig": "CIG"},
            hover_data=["sa", "oggetto_gara"],
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=400)
        st.plotly_chart(fig, use_container_width=True, key="scheda_cig_top_importo")

st.caption("Dati: ANAC (dati.anticorruzione.it) -- CC BY 4.0")
