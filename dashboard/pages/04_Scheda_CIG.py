"""Scheda CIG — Cerca e esplora CIG nei dataset ANAC."""

import streamlit as st
import pandas as pd
from lab_connectors.formatters import fmt_num
from sources import search_cig, search_by_sa, top_cig_by_importo

st.title("🔍 Scheda CIG")

# ── Tabs principali ───────────────────────────────────────────────────────────
tab_direct, tab_sa, tab_top = st.tabs(["Cerca per CIG", "Cerca per SA", "Top CIG"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: Ricerca diretta CIG
# ══════════════════════════════════════════════════════════════════════════════
with tab_direct:
    cig_input = st.text_input(
        "CIG",
        placeholder="es. B3F52D2",
        help="Codice Identificativo di Gara. Case-insensitive.",
        key="cig_direct",
    )

    if cig_input:
        cig = cig_input.strip().upper()
        with st.spinner(f"Ricerca `{cig}` in 8 dataset…"):
            results = search_cig(cig)

        if not results:
            st.warning(f"CIG `{cig}` non trovato in nessun dataset.")
        else:
            st.success(f"CIG `{cig}` trovato in {len(results)} dataset")

            order = [
                ("anac_bandi_gara", "📋 Bandi di Gara"),
                ("anac_aggiudicazioni", "🏆 Aggiudicazioni"),
                ("anac_aggiudicatari", "👥 Aggiudicatari"),
                ("anac_cup", "🔗 CUP"),
                ("anac_partecipanti", "🤝 Partecipanti"),
                ("anac_collaudo", "✅ Collaudo"),
                ("anac_stati_avanzamento", "📊 SAL"),
                ("anac_subappalti", "📋 Subappalti"),
            ]

            for key, label in order:
                if key in results:
                    df = results[key]
                    with st.expander(f"{label} — {len(df)} righe", expanded=(key == "anac_bandi_gara")):
                        st.dataframe(df, use_container_width=True, hide_index=True)

            cols = st.columns(min(len(results), 4))
            for i, (key, label) in enumerate(order):
                if key in results:
                    with cols[i % len(cols)]:
                        st.metric(label.split("—")[0].strip(), f"{len(results[key])} righe")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: Ricerca per SA
# ══════════════════════════════════════════════════════════════════════════════
with tab_sa:
    st.markdown("Cerca per nome stazione appaltante per trovare CIG correlati.")

    sa_input = st.text_input(
        "Nome SA",
        placeholder="es. CONSIP, ARIS, RFI, INPS…",
        help="Ricerca parziale case-insensitive sul nome della stazione appaltante.",
        key="sa_search",
    )

    if sa_input:
        with st.spinner(f"Ricerca SA `{sa_input}` nei bandi…"):
            df_sa = search_by_sa(sa_input, limit=50)

        if df_sa.empty:
            st.warning(f"Nessun bando trovato per SA contenente `{sa_input}`.")
        else:
            st.success(f"Trovati {len(df_sa)} bandi")

            # Riepilogo
            k1, k2, k3 = st.columns(3)
            k1.metric("CIG trovati", fmt_num(df_sa["cig"].nunique()))
            k2.metric("Importo totale", f"€ {fmt_num(df_sa['importo_lotto'].sum())}")
            k3.metric("Anni coperti", f"{df_sa['anno'].min()}–{df_sa['anno'].max()}")

            # Tabella CIG cliccabili
            st.dataframe(
                df_sa[["cig", "sa", "oggetto_gara", "importo_lotto", "anno"]],
                use_container_width=True, hide_index=True,
                column_config={
                    "importo_lotto": st.column_config.NumberColumn("Importo", format="€%.0f"),
                    "cig": st.column_config.TextColumn("CIG", width="medium"),
                },
            )

            # Prompt per cercare un CIG trovato
            st.info("💡 Copia un CIG dalla tabella e incollalo nel tab 'Cerca per CIG' per il dettaglio completo.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: Top CIG per importo
# ══════════════════════════════════════════════════════════════════════════════
with tab_top:
    st.markdown("I bandi con gli importi piu' alti.")

    n_top = st.slider("Numero di CIG", 5, 50, 20, key="n_top_cig")

    with st.spinner("Caricamento top CIG…"):
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

        # Bar chart importi
        import plotly.express as px
        fig = px.bar(
            df_top.head(15), x="importo_lotto", y="cig",
            orientation="h",
            title=f"Top {min(15, len(df_top))} CIG per importo",
            labels={"importo_lotto": "Importo (€)", "cig": "CIG"},
            hover_data=["sa", "oggetto_gara"],
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=400)
        st.plotly_chart(fig, use_container_width=True)

st.caption("Dati: ANAC (dati.anticorruzione.it) · CC BY 4.0")
