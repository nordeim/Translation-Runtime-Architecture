"""Normalize the Round 7 master findings register.

Re-reads master_findings_register_r7.json, normalizes severities to the
canonical {BLOCKING, WARNING, INFO} set, rebuilds summary.json/summary.txt,
and reports any anomalies (missing fields, unknown severities, etc.).
"""
from __future__ import annotations

import json
from pathlib import Path

ROUND7_DIR = Path(
    "/home/z/my-project/Translation-Runtime-Architecture/docs/audit/round7"
)
REGISTER = ROUND7_DIR / "master_findings_register_r7.json"
VALID_SEVERITIES = {"BLOCKING", "WARNING", "INFO"}
VALID_TYPES = {"issue", "positive_verification"}


def normalize(f: dict) -> dict:
    sev = f.get("severity", "INFO").upper().strip()
    # R7 baseline uses status-qualified severities like "BLOCKING → fixed",
    # "WARNING → partial", "WARNING (still open)". Parse out the canonical
    # severity (the leftmost token) and preserve the status in a separate field.
    if sev not in VALID_SEVERITIES:
        # Extract the canonical severity from the first token
        first_token = sev.split()[0].split("→")[0].strip("(").strip()
        if first_token in VALID_SEVERITIES:
            f["round6_status_detail"] = sev
            sev = first_token
        else:
            print(f"  WARN: {f['id']} has unknown severity {sev!r}; defaulting to INFO")
            sev = "INFO"
    f["severity"] = sev

    ftype = f.get("finding_type", "issue").lower().strip()
    # R7 uses qualified types like "issue (partial-fix)", "positive_verification (partial)".
    # Extract the canonical type (the first token).
    if ftype not in VALID_TYPES:
        first_token = ftype.split()[0].split("(")[0].strip()
        if first_token in VALID_TYPES:
            f["finding_type_detail"] = ftype
            ftype = first_token
        else:
            print(f"  WARN: {f['id']} has unknown finding_type {ftype!r}; defaulting to issue")
            ftype = "issue"
    f["finding_type"] = ftype

    f.setdefault("category", "Uncategorized")
    f.setdefault("evidence", "")
    f.setdefault("detail", "")
    f.setdefault("suggested_fix", "")
    f.setdefault("round6_status", "")
    f.setdefault("root_id", f["id"])
    f.setdefault("source_findings", [f["id"]])
    return f


def build_summary(master: list[dict]) -> dict:
    by_severity = {"BLOCKING": 0, "WARNING": 0, "INFO": 0}
    by_track: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for f in master:
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
        for t in f["track"].split(","):
            by_track[t] = by_track.get(t, 0) + 1
        by_category[f["category"]] = by_category.get(f["category"], 0) + 1
        s = f.get("round6_status") or "new"
        by_status[s] = by_status.get(s, 0) + 1
        ft = f.get("finding_type", "issue")
        by_type[ft] = by_type.get(ft, 0) + 1
    return {
        "total": len(master),
        "by_severity": by_severity,
        "by_track": by_track,
        "by_category": dict(sorted(by_category.items(), key=lambda x: -x[1])),
        "by_round7_status": by_status,
        "by_finding_type": by_type,
    }


def main() -> None:
    if not REGISTER.exists():
        print(f"ERROR: {REGISTER} not found")
        return
    master = json.loads(REGISTER.read_text(encoding="utf-8"))
    print(f"Loaded {len(master)} findings")

    master = [normalize(f) for f in master]

    REGISTER.write_text(
        json.dumps(master, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Normalized + wrote: {REGISTER}")

    summary = build_summary(master)
    summary_path = ROUND7_DIR / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Wrote: {summary_path}")

    txt_path = ROUND7_DIR / "summary.txt"
    with txt_path.open("w", encoding="utf-8") as fh:
        fh.write("TRA Round 7 Audit — Master Findings Register Summary\n")
        fh.write("=" * 60 + "\n\n")
        fh.write("HEAD audited: 6d3144a\n")
        fh.write(f"Total findings (deduplicated): {summary['total']}\n\n")
        fh.write("By severity:\n")
        for sev in ["BLOCKING", "WARNING", "INFO"]:
            fh.write(f"  {sev:10s}: {summary['by_severity'].get(sev, 0)}\n")
        fh.write("\nBy finding type:\n")
        for ft, n in sorted(summary["by_finding_type"].items()):
            fh.write(f"  {ft:25s}: {n}\n")
        fh.write("\nBy track:\n")
        for t, n in sorted(summary["by_track"].items()):
            fh.write(f"  {t}: {n}\n")
        fh.write("\nBy Round 6 status:\n")
        for s, n in sorted(summary["by_round7_status"].items()):
            fh.write(f"  {s}: {n}\n")
        fh.write("\nBy category (top 10):\n")
        for c, n in list(summary["by_category"].items())[:10]:
            fh.write(f"  {n:3d}  {c}\n")
    print(f"Wrote: {txt_path}")

    print("\nFinal counts:")
    print(f"  Total: {summary['total']}")
    print(f"  By severity: {summary['by_severity']}")
    print(f"  By type: {summary['by_finding_type']}")


if __name__ == "__main__":
    main()
