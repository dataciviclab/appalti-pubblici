"""Query SQL — Interroga direttamente i dati ANAC.

Template predefiniti + editor SQL libero.
"""

import time

import streamlit as st
from sources import DATASETS, _years_for, query

st.title("🧪 Query SQL")
st.markdown(
    "Interroga direttamente i dati ANAC. "
    "Seleziona un dataset, poi scrivi SQL su ``clean_input``."
)

# ── Template predefiniti ──────────────────────────────────────────────────────
TEMPLATES = {
    "Seleziona un template...": None,
    "📊 Conta righe": "SELECT COUNT(*) AS n FROM clean_input",
    "📋 Preview (10 righe)": "SELECT * FROM clean_input LIMIT 10",
    "📊 Colonne disponibili": "DESCRIBE SELECT * FROM clean_input",
    "🏆 Top SA per importo": (
        "SELECT denominazione_amministrazione_appaltante AS sa, "
        "COUNT(*) AS n_bandi, ROUND(SUM(importo_lotto), 0) AS importo_totale "
        "FROM clean_input "
        "WHERE cf_amministrazione_appaltante IS NOT NULL "
        "GROUP BY sa ORDER BY importo_totale DESC LIMIT 20"
    ),
    "📈 Trend annuale": (
        "SELECT anno_pubblicazione AS anno, COUNT(*) AS n_bandi, "
        "ROUND(SUM(importo_lotto), 0) AS importo_totale "
        "FROM clean_input GROUP BY anno ORDER BY anno"
    ),
    "🔍 CIG con un solo offerente": (
        "SELECT cig, importo_aggiudicazione, num_imprese_offerenti "
        "FROM clean_input WHERE num_imprese_offerenti = 1 "
        "AND importo_aggiudicazione > 1000000 "
        "ORDER BY importo_aggiudicazione DESC LIMIT 20"
    ),
    "⏱️ SAL in ritardo": (
        "SELECT cig, n_giorni_scostamento, importo_sal "
        "FROM clean_input WHERE flag_ritardo = 'IN RITARDO' "
        "ORDER BY n_giorni_scostamento DESC LIMIT 20"
    ),
}

template = st.selectbox("Template", list(TEMPLATES.keys()))
default_sql = TEMPLATES.get(template, "SELECT * FROM clean_input LIMIT 10") or "SELECT * FROM clean_input LIMIT 10"

# ── Selezione dataset ─────────────────────────────────────────────────────────
dataset_keys = list(DATASETS.keys())
labels = [f"{k} — {DATASETS[k]['label']}" for k in dataset_keys]

selected_idx = st.selectbox(
    "📋 Dataset",
    range(len(labels)),
    format_func=lambda i: labels[i],
)
selected_slug = dataset_keys[selected_idx]
ds_info = DATASETS[selected_slug]

ds_years = _years_for(selected_slug)
if not ds_years:
    ds_years = [2026]
if len(ds_years) > 1:
    year_range = st.slider(
        "Anni", min(ds_years), max(ds_years),
        (min(ds_years), max(ds_years)),
    )
    selected_years = list(range(year_range[0], year_range[1] + 1))
else:
    selected_years = ds_years

st.caption(
    f"Dataset: ``{selected_slug}`` · Anni: {selected_years[0]}–{selected_years[-1]} "
    f"({len(selected_years)} file Parquet)"
)

# ── Editor SQL ────────────────────────────────────────────────────────────────
sql = st.text_area(
    "SQL",
    value=st.session_state.get("sql_query_sql", default_sql),
    height=150,
    key="sql_query_sql",
    label_visibility="collapsed",
    help="Usa 'clean_input' come tabella virtuale.",
)

# ── Pulsanti ──────────────────────────────────────────────────────────────────
col_exec, col_hist = st.columns([3, 1])
with col_exec:
    execute = st.button("▶️ Esegui", type="primary", use_container_width=True)
with col_hist:
    show_hist = st.button("📜 Storico", use_container_width=True)

# ── Storico ───────────────────────────────────────────────────────────────────
history = st.session_state.setdefault("sql_history", [])

if show_hist and history:
    st.subheader("📜 Storico")
    for i, entry in enumerate(reversed(history[-8:])):
        label = entry["sql"][:60].replace("\n", " ")
        if len(entry["sql"]) > 60:
            label += "…"
        col_a, col_b = st.columns([6, 1])
        with col_a:
            if st.button(
                f"`{entry['slug']}` {label}",
                key=f"hist_{i}",
                help=f"{entry['rows']} righe · {entry['time']}",
            ):
                st.session_state.sql_query_sql = entry["sql"]
                st.rerun()
        with col_b:
            st.caption(f"{entry['rows']} rows")
    if st.button("Svuota storico", key="clear_hist"):
        st.session_state.sql_history = []
        st.rerun()

# ── Esecuzione ────────────────────────────────────────────────────────────────
if execute:
    with st.spinner(f"Esecuzione su `{selected_slug}`…"):
        try:
            q = sql.strip().rstrip(";")
            if "LIMIT" not in q.upper():
                q += " LIMIT 1000"

            t0 = time.perf_counter()
            df = query(q, years=selected_years, slug=selected_slug)
            elapsed = time.perf_counter() - t0

            n_rows = len(df)
            is_truncated = n_rows >= 1000

            m1, m2, m3 = st.columns(3)
            m1.metric("Righe", f"{n_rows:,}")
            m2.metric("Tempo", f"{elapsed:.2f}s")
            m3.metric("Parquet", f"{len(selected_years)} file")

            if is_truncated:
                st.info(f"Troncato a 1000 righe. Aggiungi LIMIT.")

            if n_rows > 0:
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    ":material/download: CSV", csv,
                    file_name=f"{selected_slug}_{int(time.time())}.csv",
                    mime="text/csv",
                )

            st.session_state.sql_history.append({
                "slug": selected_slug, "sql": sql,
                "rows": n_rows, "time": f"{elapsed:.2f}s",
            })

            with st.expander("SQL eseguita", expanded=False):
                st.code(q, language="sql")

        except Exception as e:
            st.error(f"Errore: {e}")

st.caption("Dati: ANAC (dati.anticorruzione.it) · CC BY 4.0")
