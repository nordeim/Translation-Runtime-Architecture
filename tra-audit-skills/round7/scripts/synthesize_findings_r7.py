"""Round 7 audit — synthesize the master findings register.

Reads the 7 per-track findings files (track_{r7,a7,b7,c7,d7,e7,f7}_findings.md),
deduplicates findings that cite the same root issue across tracks, and writes:

  - master_findings_register_r7.json   (machine-readable single source of truth)
  - summary.json / summary.txt          (counts by severity / track / category)

Output dir: /home/z/my-project/Translation-Runtime-Architecture/docs/audit/round7/
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROUND7_DIR = Path(
    "/home/z/my-project/Translation-Runtime-Architecture/docs/audit/round7"
)
TRACKS = ["r7", "a7", "b7", "c7", "d7", "e7", "f7"]


def parse_findings(track: str, md_text: str) -> list[dict]:
    """Parse `### TRA-<X7>-NNN: <title>` blocks from a track's findings file."""
    findings: list[dict] = []
    # Match each finding block: starts at ### TRA- header, ends at next ### or ## header
    # R7: supports both "### TRA-A7-001: title" and "### A7-001 — title" forms
    pattern = re.compile(
        r"^### (?:TRA-)?([A-Z]?\d+-\d+|TRA-\d+)[^\n]*$\n((?:(?!^##? ).)*?)(?=^### |^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    for m in pattern.finditer(md_text):
        raw_id = m.group(1).strip()
        # Normalize ID to TRA- prefix
        if raw_id.startswith("TRA-"):
            finding_id = raw_id
        else:
            finding_id = f"TRA-{raw_id}"
        # Skip probe headers (not findings)
        if "Probe" in finding_id or finding_id.startswith("TRA-Probe"):
            continue
        body = m.group(2)
        severity = _extract_field(body, "Severity") or "INFO"
        category = _extract_field(body, "Category") or "Uncategorized"
        evidence = _extract_field(body, "Evidence") or ""
        detail = _extract_field(body, "Detail") or ""
        suggested_fix = _extract_field(body, "Suggested fix") or ""
        round6_status = (
            _extract_field(body, "Round 6 status")
            or _extract_field(body, "Round 5 status")
            or ""
        )
        finding_type = _extract_field(body, "Finding type") or "issue"
        # Pull title directly from header line
        header_match = re.search(
            rf"^### (?:TRA-)?{re.escape(raw_id)}[^\n]*?\n",
            md_text,
            re.MULTILINE,
        )
        title = ""
        if header_match:
            header_line = header_match.group(0).rstrip("\n")
            # Strip leading "### " + optional "TRA-" + ID + optional ":"/"—" + spaces
            title = re.sub(
                rf"^### (?:TRA-)?{re.escape(raw_id)}\s*[:—-]\s*", "", header_line
            )
            title = title.strip()
        findings.append(
            {
                "id": finding_id,
                "track": track.upper(),
                "title": title,
                "severity": severity,
                "category": category,
                "evidence": evidence,
                "detail": detail,
                "suggested_fix": suggested_fix,
                "round6_status": round6_status,
                "finding_type": finding_type,
                "source_findings": [finding_id],
            }
        )
    return findings


def _extract_field(body: str, field_name: str) -> str | None:
    """Extract `- **<field_name>:** <value>` (value may span multiple lines)."""
    pattern = re.compile(
        rf"- \*\*{re.escape(field_name)}[^:]*:\*\*\s*(.+?)(?=\n- \*\*|\Z)",
        re.DOTALL,
    )
    m = pattern.search(body)
    if not m:
        return None
    value = m.group(1).strip()
    value = re.sub(r"\s+", " ", value)
    return value


def dedupe_findings(all_findings: list[dict]) -> list[dict]:
    """Merge findings that reference the same root finding ID (e.g., TRA-001)."""
    groups: dict[str, list[dict]] = {}
    for f in all_findings:
        root_match = re.search(r"TRA-(\d{3})", f["title"] + " " + f["detail"])
        if root_match:
            root_id = f"TRA-{root_match.group(1)}"
        else:
            root_id = f["id"]
        groups.setdefault(root_id, []).append(f)

    merged: list[dict] = []
    for root_id, group in groups.items():
        if len(group) == 1:
            f = dict(group[0])
            f["root_id"] = root_id
            merged.append(f)
        else:
            severity_rank = {"BLOCKING": 0, "WARNING": 1, "INFO": 2}
            group_sorted = sorted(
                group, key=lambda x: severity_rank.get(x["severity"], 3)
            )
            primary = dict(group_sorted[0])
            primary["root_id"] = root_id
            primary["track"] = ",".join(sorted({g["track"] for g in group}))
            primary["source_findings"] = [g["id"] for g in group]
            cross_refs = [
                f"Also cited by {g['id']} ({g['track']}): {g['title']}"
                for g in group[1:]
            ]
            if cross_refs:
                primary["detail"] = primary["detail"] + " || " + " | ".join(cross_refs)
            merged.append(primary)

    severity_rank = {"BLOCKING": 0, "WARNING": 1, "INFO": 2}
    merged.sort(
        key=lambda x: (severity_rank.get(x["severity"], 3), x["root_id"])
    )
    return merged


def build_summary(master: list[dict]) -> dict:
    by_severity = {"BLOCKING": 0, "WARNING": 0, "INFO": 0}
    by_track: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_round7_status: dict[str, int] = {}
    by_finding_type: dict[str, int] = {}
    for f in master:
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
        for t in f["track"].split(","):
            by_track[t] = by_track.get(t, 0) + 1
        by_category[f["category"]] = by_category.get(f["category"], 0) + 1
        status = f.get("round6_status") or "new"
        by_round7_status[status] = by_round7_status.get(status, 0) + 1
        ftype = f.get("finding_type", "issue")
        by_finding_type[ftype] = by_finding_type.get(ftype, 0) + 1
    return {
        "total": len(master),
        "by_severity": by_severity,
        "by_track": by_track,
        "by_category": dict(sorted(by_category.items(), key=lambda x: -x[1])),
        "by_round7_status": by_round7_status,
        "by_finding_type": by_finding_type,
    }


def main() -> None:
    all_findings: list[dict] = []
    for track in TRACKS:
        # R7 baseline file is named track_r7_baseline.md (not _findings.md)
        if track == "r7":
            path = ROUND7_DIR / "track_r7_baseline.md"
        else:
            path = ROUND7_DIR / f"track_{track}_findings.md"
        if not path.exists():
            print(f"WARN: {path} not found, skipping")
            continue
        md = path.read_text(encoding="utf-8")
        track_findings = parse_findings(track, md)
        print(f"{track}: parsed {len(track_findings)} findings")
        all_findings.extend(track_findings)

    print(f"\nTotal raw findings: {len(all_findings)}")
    master = dedupe_findings(all_findings)
    print(f"After dedup: {len(master)}")

    summary = build_summary(master)
    print(f"\nSummary:")
    print(f"  By severity: {summary['by_severity']}")
    print(f"  By track: {summary['by_track']}")
    print(f"  By Round 6 status: {summary['by_round7_status']}")
    print(f"  By finding type: {summary['by_finding_type']}")

    master_path = ROUND7_DIR / "master_findings_register_r7.json"
    master_path.write_text(
        json.dumps(master, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nWrote: {master_path}")

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


if __name__ == "__main__":
    main()
