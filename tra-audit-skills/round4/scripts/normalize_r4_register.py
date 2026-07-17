"""Normalize severities in the master register and rebuild summary.

Some findings have severity values like 'INFO (positive confirmation)' etc.
Normalize them to the canonical BLOCKING / WARNING / INFO values, then
rebuild the summary statistics.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

MASTER_PATH = Path(
    "/home/z/my-project/Translation-Runtime-Architecture/docs/audit/round4/master_findings_register_r4.json"
)


def normalize_severity(s: str) -> str:
    """Map messy severity values to canonical BLOCKING/WARNING/INFO."""
    s = s.strip().upper()
    if s.startswith("BLOCKING"):
        return "BLOCKING"
    if s.startswith("WARNING"):
        return "WARNING"
    # Everything else (INFO, INFO (positive confirmation), etc.) → INFO
    return "INFO"


def categorize_finding(f: dict) -> str:
    """Classify each finding as positive (verification holding) or negative (issue)."""
    title = f["title"].lower()
    detail = f["detail"].lower() if f["detail"] else ""
    positive_markers = [
        "verified holding",
        "verified safe",
        "verified fixed",
        "fixed —",
        "fixed and-verified",
        "fixed-and-verified",
        "verified —",
        "confirmed",
        "byte-reproducibility confirmed",
        "all 9 runtime artifacts",
        "all gates green",
        "now fixed",
        "fully resolved",
        "positive",
    ]
    for marker in positive_markers:
        if marker in title or marker in detail:
            return "positive_verification"
    return "issue"


def main() -> None:
    master = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(master)} findings")

    # Normalize severity
    for f in master:
        f["severity"] = normalize_severity(f["severity"])
        f["finding_type"] = categorize_finding(f)

    # Rebuild summary
    by_severity = Counter(f["severity"] for f in master)
    by_type = Counter(f["finding_type"] for f in master)
    by_track: dict[str, int] = {}
    for f in master:
        for t in f["track"].split(","):
            by_track[t] = by_track.get(t, 0) + 1
    by_round3_status: dict[str, int] = {}
    for f in master:
        status = f["round3_status"] or "new"
        # Normalize the round3_status to a single token
        status_lower = status.lower()
        if "fixed" in status_lower and "verified" in status_lower:
            key = "fixed-and-verified"
        elif "fixed" in status_lower:
            key = "fixed"
        elif "partial" in status_lower:
            key = "partial"
        elif "persistent" in status_lower:
            key = "persistent"
        elif "new" in status_lower:
            key = "new"
        elif "verified" in status_lower or "safe" in status_lower:
            key = "verified-holding"
        elif "carry" in status_lower:
            key = "carry-over"
        else:
            key = "other"
        by_round3_status[key] = by_round3_status.get(key, 0) + 1

    # Count issues only (exclude positive verifications)
    issue_findings = [f for f in master if f["finding_type"] == "issue"]
    issues_by_severity = Counter(f["severity"] for f in issue_findings)

    summary = {
        "total_findings": len(master),
        "by_severity_all": dict(by_severity),
        "by_finding_type": dict(by_type),
        "issues_only": {
            "count": len(issue_findings),
            "by_severity": dict(issues_by_severity),
        },
        "by_track": dict(sorted(by_track.items())),
        "by_round3_status_normalized": dict(
            sorted(by_round3_status.items(), key=lambda x: -x[1])
        ),
    }

    # Write normalized master
    MASTER_PATH.write_text(
        json.dumps(master, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Normalized master written to: {MASTER_PATH}")

    # Write summary
    summary_path = MASTER_PATH.parent / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Summary written to: {summary_path}")

    # Human-readable summary
    txt_path = MASTER_PATH.parent / "summary.txt"
    with txt_path.open("w", encoding="utf-8") as fh:
        fh.write("TRA Round 4 Audit — Master Findings Register Summary\n")
        fh.write("=" * 60 + "\n\n")
        fh.write(f"HEAD audited: 805a8f8\n")
        fh.write(f"Total findings (deduplicated): {summary['total_findings']}\n\n")
        fh.write("By severity (all findings, including positive verifications):\n")
        for sev in ["BLOCKING", "WARNING", "INFO"]:
            fh.write(f"  {sev:10s}: {summary['by_severity_all'].get(sev, 0)}\n")
        fh.write("\nBy finding type:\n")
        for t, n in summary["by_finding_type"].items():
            fh.write(f"  {t:25s}: {n}\n")
        fh.write("\nIssues only (excluding positive verifications):\n")
        fh.write(f"  Total issues: {summary['issues_only']['count']}\n")
        for sev in ["BLOCKING", "WARNING", "INFO"]:
            fh.write(
                f"  {sev:10s}: {summary['issues_only']['by_severity'].get(sev, 0)}\n"
            )
        fh.write("\nBy track:\n")
        for t, n in summary["by_track"].items():
            fh.write(f"  {t}: {n}\n")
        fh.write("\nBy Round 3 status (normalized):\n")
        for s, n in summary["by_round3_status_normalized"].items():
            fh.write(f"  {s:25s}: {n}\n")
    print(f"Human-readable summary: {txt_path}")

    # Print headline
    print("\n" + "=" * 60)
    print("HEADLINE COUNTS (issues only):")
    print(
        f"  BLOCKING: {summary['issues_only']['by_severity'].get('BLOCKING', 0)}"
    )
    print(
        f"  WARNING:  {summary['issues_only']['by_severity'].get('WARNING', 0)}"
    )
    print(
        f"  INFO:     {summary['issues_only']['by_severity'].get('INFO', 0)}"
    )
    print(f"  TOTAL:    {summary['issues_only']['count']}")
    print(
        f"\nPositive verifications (invariants holding, fixes confirmed): "
        f"{summary['by_finding_type'].get('positive_verification', 0)}"
    )


if __name__ == "__main__":
    main()
