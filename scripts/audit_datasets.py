#!/usr/bin/env python3
"""Quadratura dei dataset ANAC: chiavi, date, schema per anno, freschezza.

I controlli derivano dal Manuale open data ANAC v1.4:
- §4 chiavi primarie ufficiali per dataset;
- §5 politica di aggiornamento (FULL mensile vs FULL + DELTA).

Uso:
    python scripts/audit_datasets.py                 # legge out/data
    python scripts/audit_datasets.py --root out/data
    python scripts/audit_datasets.py --json
    python scripts/audit_datasets.py --max-age-days 60

Esce con codice 1 solo sugli **errori**; gli **avvisi** non fanno fallire:

- errore: `cig` vuoto; chiave duplicata **dentro la stessa partizione anno**;
  date con anno < `MIN_YEAR`; schema diverso tra le partizioni anno.
- avviso: stessa chiave presente in **piu' anni** (nei bandi e' strutturale: il
  delta del 2026 puo' ripubblicare un CIG del 2025); date con anno maggiore di
  quello corrente (refusi plausibili, es. 2062 al posto di 2026, che la macro
  `safe_date` non intercetta perche' formalmente valide); clean piu' vecchio di
  `--max-age-days`.

Nota sulla finestra delle date: `MIN_YEAR` e' l'attesa del **dominio** (ANAC dal
2005), piu' stretta della macro `safe_date`, che scarta solo cio' che e'
fisicamente impossibile (1800-2100). Se una data ante-1990 arriva in un clean,
qui e' un errore: e' il controllo che la macro, per costruzione, non puo' fare.
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
    # Chiave dal Manuale v1.4 §4 (pag. 17): "stazioni-appaltanti -> codice_fiscale".
    "anac_stazioni_appaltanti": {"key": ["codice_fiscale"], "dates": ["data_inizio"]},
    "anac_stati_avanzamento": {"key": ["cig", "id_aggiudicazione", "progressivo_sal"], "dates": ["data_emissione_sal", "data_cert_pagamento"]},
    "anac_subappalti": {"key": ["cig", "id_subappalto", "cod_categoria", "codice_fiscale"], "dates": ["data_autorizzazione"]},
    "anac_varianti": {"key": ["cig", "id_aggiudicazione", "id_variante", "cod_motivo_variante", "data_approvazione_variante"], "dates": ["data_approvazione_variante"]},
}

# La macro `safe_date` del toolkit scarta solo cio' che e' fisicamente
# impossibile (1800-2100). Qui la finestra e' piu' stretta perche' e' l'attesa
# del dominio: un appalto anteriore al 1990 in un dataset che parte dal 2007 e'
# un errore di compilazione della stazione appaltante, e va visto.
MIN_YEAR = 1990


def _partitions(base: Path) -> list[tuple[int, str]]:
    """(anno, path) per ogni partizione anno del clean."""
    out: list[tuple[int, str]] = []
    for path in sorted(base.glob("*/*.parquet")):
        try:
            out.append((int(path.parent.name), str(path)))
        except ValueError:
            continue
    return out


def _schema(con: duckdb.DuckDBPyConnection, path: str) -> list[tuple[str, str]]:
    rows = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path}')").fetchall()
    return [(r[0], r[1]) for r in rows]


def _freshness(base: Path) -> tuple[str | None, int | None]:
    """Ultimo `timestamp_utc` dei metadata delle partizioni + eta' in giorni."""
    last: dt.datetime | None = None
    for meta in base.glob("*/metadata.json"):
        try:
            payload = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        raw = payload.get("timestamp_utc")
        if not raw:
            continue
        try:
            ts = dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        if last is None or ts > last:
            last = ts
    if last is None:
        return None, None
    age = (dt.datetime.now(dt.timezone.utc) - last).days
    return last.isoformat(timespec="seconds"), age


def audit(
    slug: str,
    spec: dict,
    con: duckdb.DuckDBPyConnection,
    root: Path,
    max_age_days: int = 40,
) -> dict:
    base = root / "clean" / slug
    result: dict = {
        "dataset": slug,
        "righe": 0,
        "anni": [],
        "errori": [],
        "avvisi": [],
        "note": [],
        "date": {},
        "schema": {},
    }
    parts = _partitions(base) if base.is_dir() else []
    if not parts:
        result["note"].append("clean locale assente")
        return result

    result["anni"] = [year for year, _ in parts]
    files = [path for _, path in parts]
    src = f"read_parquet({files!r})"
    cols = {c[0] for c in con.execute(f"SELECT * FROM {src} LIMIT 0").description}
    result["righe"] = con.execute(f"SELECT count(*) FROM {src}").fetchone()[0]

    # ── schema: le partizioni anno devono avere lo stesso schema ─────────────
    reference_year, reference_path = parts[0]
    reference = _schema(con, reference_path)
    schema_drift: dict[str, list[str]] = {}
    for year, path in parts[1:]:
        current = _schema(con, path)
        if current != reference:
            ref_map, cur_map = dict(reference), dict(current)
            diffs = [
                f"{col}: {ref_map.get(col, 'assente')} -> {cur_map.get(col, 'assente')}"
                for col in sorted(set(ref_map) | set(cur_map))
                if ref_map.get(col) != cur_map.get(col)
            ]
            schema_drift[str(year)] = diffs
    result["schema"] = {
        "riferimento": reference_year,
        "deriva": schema_drift,
    }
    if schema_drift:
        esempio = next(iter(schema_drift.items()))
        result["errori"].append(
            f"schema diverso in {len(schema_drift)} partizioni rispetto al "
            f"{reference_year} (es. {esempio[0]}: {esempio[1][0]})"
        )

    if "cig" in cols:
        nulli = con.execute(f"SELECT count(*) FROM {src} WHERE cig IS NULL OR trim(cig) = ''").fetchone()[0]
        if nulli:
            result["errori"].append(f"{nulli} righe con cig vuoto")

    # ── chiavi: duplicati dentro l'anno = errore, fra anni = avviso ──────────
    key = spec.get("key")
    if key and all(k in cols for k in key):
        kexpr = ", ".join(key)
        dup_anno = 0
        for year, path in parts:
            dup_anno += con.execute(
                f"SELECT count(*) FROM (SELECT {kexpr} FROM read_parquet('{path}') "
                f"GROUP BY ALL HAVING count(*) > 1)"
            ).fetchone()[0]
        if dup_anno:
            result["errori"].append(
                f"{dup_anno} chiavi duplicate entro la stessa partizione anno su ({', '.join(key)})"
            )

        dup_cross = con.execute(
            f"""
            SELECT count(*) FROM (
                SELECT {kexpr} FROM {src}
                GROUP BY ALL
                HAVING count(DISTINCT {'anno_pubblicazione' if 'anno_pubblicazione' in cols else '1'}) > 1
            )
            """
        ).fetchone()[0] if "anno_pubblicazione" in cols else 0
        if dup_cross:
            result["avvisi"].append(
                f"{dup_cross} chiavi ({', '.join(key)}) presenti in piu' di un anno "
                "(il delta puo' ripubblicare un record cambiando anno)"
            )

    # ── date: sopra MIN_YEAR errore, sopra l'anno corrente avviso ────────────
    current_year = dt.date.today().year
    for col in spec.get("dates", []):
        if col not in cols:
            continue
        max_data, antiche, future = con.execute(
            f"""
            SELECT max({col}),
                   count(*) FILTER (WHERE year({col}) < {MIN_YEAR}),
                   count(*) FILTER (WHERE year({col}) > {current_year})
            FROM {src}
            """
        ).fetchone()
        result["date"][col] = {
            "max": str(max_data) if max_data else None,
            "ante_1990": antiche,
            "future": future,
        }
        if antiche:
            result["errori"].append(f"{antiche} date con anno < {MIN_YEAR} in {col}")
        if future:
            result["avvisi"].append(
                f"{future} date con anno > {current_year} in {col} (max {max_data})"
            )

    # ── freschezza: eta' dell'ultimo clean ───────────────────────────────────
    last_ts, age = _freshness(base)
    result["freshness"] = {"ultimo_clean": last_ts, "giorni": age}
    if age is not None and age > max_age_days:
        result["avvisi"].append(f"clean fermo da {age} giorni (soglia {max_age_days})")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Quadratura dataset ANAC")
    parser.add_argument("--root", default="out/data", help="radice dei layer (default: out/data)")
    parser.add_argument("--json", action="store_true", help="output JSON")
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=40,
        help="eta' massima del clean prima di un avviso di freschezza (default: 40)",
    )
    args = parser.parse_args()

    root = Path(args.root)
    con = duckdb.connect()
    report = [audit(slug, spec, con, root, args.max_age_days) for slug, spec in DATASETS.items()]

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"{'dataset':26s} {'righe':>10s} {'anni':>10s}  esito")
        for r in report:
            messaggi = r["errori"] + r["avvisi"]
            if r["errori"]:
                esito = "ERRORI: " + "; ".join(messaggi)
            elif r["avvisi"]:
                esito = "avvisi: " + "; ".join(messaggi)
            else:
                esito = "OK"
            anni = f"{r['anni'][0]}-{r['anni'][-1]}" if r["anni"] else "-"
            print(f"{r['dataset']:26s} {r['righe']:>10,d} {anni:>10s}  {esito}")

    return 1 if any(r["errori"] for r in report) else 0


if __name__ == "__main__":
    sys.exit(main())
