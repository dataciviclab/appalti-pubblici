"""Scheda SA -- Profilo di una Stazione Appaltante."""

import streamlit as st
import plotly.express as px
from lab_connectors.formatters import fmt_num
from sources import load_mart_sa_profilo, search_by_sa, fmt_eur_short

st.title("Scheda Stazione Appaltante")

sa_input = st.text_input(
    "Nome SA",
    placeholder="es. CONSIP, RAI, ROMA CAPITALE, ANAS...",
    help="Ricerca parziale case-insensitive.",
    key="sa_search",
)

if sa_input:
    sa_profilo = load_mart_sa_profilo()
    if not sa_profilo.empty:
        mask = sa_profilo["denominazione_sa"].str.contains(sa_input, case=False, na=False)
        matches = sa_profilo[mask]

        if matches.empty:
            st.warning(f"Nessuna SA trovata con nome contenente `{sa_input}`.")
        else:
            st.success(f"Trovate {len(matches)} SA")

            for _, row in matches.head(5).iterrows():
                with st.expander(
                    f"**{row['denominazione_sa']}** -- {fmt_num(row['n_bandi'])} bandi, "
                    f"{fmt_eur_short(row['importo_totale'])}",
                    expanded=(len(matches) == 1),
                ):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Bandi", fmt_num(row['n_bandi']))
                    c2.metric("Importo totale", fmt_eur_short(row['importo_totale']))
                    c3.metric("Settori", fmt_num(row['n_settori']))
                    c4.metric("Regione", row['regione'])

                    c5, c6, c7 = st.columns(3)
                    c5.metric("CIG", fmt_num(row['n_cig']))
                    c6.metric("Importo medio", fmt_eur_short(row['importo_mediano']))
                    c7.metric("PNRR", fmt_num(row['n_pnrr']))

                    st.caption(f"Attiva dal {int(row['anno_primo'])} al {int(row['ultimo_anno'])}")

                    # Top bandi della SA
                    st.subheader("Top bandi per importo")
                    top_bandi = search_by_sa(row["denominazione_sa"], limit=10)
                    if not top_bandi.empty:
                        st.dataframe(
                            top_bandi[["cig", "oggetto_gara", "importo_lotto", "anno"]],
                            use_container_width=True, hide_index=True,
                            column_config={
                                "importo_lotto": st.column_config.NumberColumn("Importo", format="€%.0f"),
                                "cig": st.column_config.TextColumn("CIG", width="medium"),
                                "oggetto_gara": st.column_config.TextColumn("Oggetto", width="xlarge"),
                            },
                        )
    else:
        st.info("Profilo SA non disponibile (serve il mart_sa_profilo).")

st.caption("Dati: ANAC (dati.anticorruzione.it) -- CC BY 4.0")
