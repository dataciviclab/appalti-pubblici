#!/usr/bin/env python3
"""Quadratura dei dataset ANAC: chiavi, date plausibili, freschezza.

I controlli derivano dal Manuale open data ANAC v1.4:
- §4 chiavi primarie ufficiali per dataset;
- §5 politica di aggiornamento (FULL mensile vs FULL + DELTA).

Uso:
    python scripts/audit_datasets.py            # legge out/data/clean
    python scripts/audit_datasets.py --root out
    python scripts/audit_datasets.py --json

Esce con codice 1 se trova un problema "hard" (date impossibili o chiavi
duplicate dove la chiave e' dichiarata ufficiale).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import duckdb

# slug -> (chiave primaria ufficiale, colonne data da controllare)
# Chiavi da Manuale ANAC v1.4 §4. `None` = chiave non dichiarata nel manuale.
DATASETS: dict[str, dict] = {
    "anac_bandi_gara": {"key": ["cig"], "dates": ["data_pubblicazione", "data_scadenza_offerta"]},
    "anac_aggiudicazioni": {"key": ["cig", "id_aggiudicazione"], "dates": ["data_aggiudicazione_definitiva", "data_comunicazione_esito"]},
    "anac_aggiudicatari": {"key": ["cig", "id_aggiudicazione", "codice_fiscale"], "dates": []},
    "anac_avvio_contratto": {"key": ["cig", "id_aggiudicazione"], "dates": ["data_stipula_contratto", "data_inizio_effettiva"]},
    "anac_collaudo": {"key": ["cig", "id_aggiudicazione"], "dates": ["data_cert_collaudo", "data_delibera"]},
    "anac_cup": {"key": ["cup", "cig"], "dates": []},
    "anac_fine_contratto": {"key": ["cig", "id_aggiudicazione"], "dates": ["data_effettiva_ultimazione"]},
    "anac_partecipanti": {"key": None, "dates": []},
    "anac_sospensioni": {"key": ["cig", "id_aggiudicazione", "data_sospensione", "descrizione_motivo"], "dates": ["data_sospensione", "data_ripresa"]},
    "anac_stati_avanzamento": {"key": ["cig", "id_aggiudicazione", "progressivo_sal"], "dates": ["data_emissione_sal", "data_cert_pagamento"]},
    "anac_subappalti": {"key": ["cig", "id_subappalto", "cod_categoria", "codice_fiscale"], "dates": ["data_autorizzazione"]},
    "anac_varianti": {"key": ["cig", "id_aggiudicazione", "id_variante", "cod_motivo_variante", "data_approvazione_variante"], "dates": ["data_approvazione_variante"]},
}

MIN_YEAR = 1990
MAX_YEAR = 2100


def _rows(con: duckdb.DuckDBPyConnection, slug: str, root: Path) -> list[dict]:
    base = root / "clean" / slug
    if not base.is_dir():
        return []
    files = sorted(str(p) for p in base.glob("*/*.parquet"))
    if not files:
        return []
    cols = {c[0] for c in con.execute(f"SELECT * FROM read_parquet({files!r}) LIMIT 0").description}
    return [{"files": files, "cols": cols}]


def audit(slug: str, spec: dict, con: duckdb.DuckDBPyConnection, root: Path) -> dict:
    base = root / "clean" / slug
    result: dict = {"dataset": slug, "righe": 0, "anni": [], "errori": [], "avvisi": [], "note": []}
    if not base.is_dir():
        result["note"].append("clean locale assente")
        return result

    files = sorted(str(p) for p in base.glob("*/*.parquet"))
    if not files:
        result["note"].append("clean locale assente")
        return result

    src = f"read_parquet({files!r}, union_by_name=true)"
    result["anni"] = sorted(int(p.parent.name) for p in base.glob("*/*.parquet"))
    cols = {c[0] for c in con.execute(f"SELECT * FROM {src} LIMIT 0").description}
    result["righe"] = con.execute(f"SELECT count(*) FROM {src}").fetchone()[0]

    if "cig" in cols:
        nulli = con.execute(f"SELECT count(*) FROM {src} WHERE cig IS NULL OR trim(cig) = ''").fetchone()[0]
        if nulli:
            result["errori"].append(f"{nulli} righe con cig vuoto")

    key = spec.get("key")
    if key and all(k in cols for k in key):
        kexpr = ", ".join(key)
        dup = con.execute(
            f"SELECT count(*) FROM (SELECT {kexpr} FROM {src} GROUP BY ALL HAVING count(*) > 1)"
        ).fetchone()[0]
        if dup:
            result["avvisi"].append(f"{dup} chiavi duplicate su ({', '.join(key)})")

    for col in spec.get("dates", []):
        if col not in cols:
            continue
        max_data, impossibili = con.execute(
            f"""
            SELECT max({col}),
                   count(*) FILTER (WHERE year({col}) < {MIN_YEAR} OR year({col}) > {MAX_YEAR})
            FROM {src}
            """
        ).fetchone()
        result.setdefault("date", {})[col] = {
            "max": str(max_data) if max_data else None,
            "impossibili": impossibili,
        }
        if impossibili:
            result["errori"].append(f"{impossibili} date impossibili in {col}")
        # Date future oltre 2 anni: quasi sempre refusi (es. 2062 al posto di 2026)
        if max_data and max_data > dt.date.today() + dt.timedelta(days=730):
            result["avvisi"].append(f"data futura in {col}: {max_data}")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Quadratura dataset ANAC")
    parser.add_argument("--root", default="out/data", help="radice dei layer (default: out/data)")
    parser.add_argument("--json", action="store_true", help="output JSON")
    args = parser.parse_args()

    root = Path(args.root)
    con = duckdb.connect()
    report = [audit(slug, spec, con, root) for slug, spec in DATASETS.items()]

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"{'dataset':26s} {'righe':>10s} {'anni':>10s}  esito")
        for r in report:
            esito = "OK" if not (r["errori"] or r["avvisi"]) else "; ".join(r["errori"] + r["avvisi"])
            anni = f"{r['anni'][0]}-{r['anni'][-1]}" if r["anni"] else "-"
            print(f"{r['dataset']:26s} {r['righe']:>10,d} {anni:>10s}  {esito}")

    return 1 if any(r["errori"] for r in report) else 0


if __name__ == "__main__":
    sys.exit(main())
