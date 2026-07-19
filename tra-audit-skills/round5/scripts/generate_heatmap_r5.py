"""Generate severity heatmap PNG for Round 5 audit.

Output: /home/z/my-project/Translation-Runtime-Architecture/docs/audit/round5/TRA_audit_severity_heatmap_r5.png
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np

# Font setup for CJK + Latin (per Rule 7 in the system prompt)
fm.fontManager.addfont(
    "/usr/share/fonts/truetype/noto-serif-sc/NotoSerifSC-Regular.ttf"
)
fm.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
plt.rcParams["font.sans-serif"] = ["Noto Serif SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

REGISTER = Path(
    "/home/z/my-project/Translation-Runtime-Architecture/docs/audit/round5/master_findings_register_r5.json"
)
OUT = Path(
    "/home/z/my-project/Translation-Runtime-Architecture/docs/audit/round5/TRA_audit_severity_heatmap_r5.png"
)


def main() -> None:
    findings = json.loads(REGISTER.read_text(encoding="utf-8"))

    # Split findings by type: issues vs positive verifications
    issues = [f for f in findings if f.get("finding_type") == "issue"]
    positives = [f for f in findings if f.get("finding_type") == "positive_verification"]

    tracks = ["A5", "B5", "C5", "D5", "E5", "F5"]
    severities = ["BLOCKING", "WARNING", "INFO"]

    # Build matrix [track][severity] for ISSUES ONLY
    matrix = np.zeros((len(tracks), len(severities)), dtype=int)
    for f in issues:
        track = f["track"].split(",")[0]
        if track not in tracks:
            continue
        ti = tracks.index(track)
        si = severities.index(f["severity"])
        matrix[ti][si] += 1

    # Headline counts
    issue_counts = {
        sev: sum(1 for f in issues if f["severity"] == sev) for sev in severities
    }
    total_issues = len(issues)
    total_positives = len(positives)

    fig, ax = plt.subplots(figsize=(10, 5.5), constrained_layout=True)
    im = ax.imshow(
        matrix,
        cmap="YlOrRd",
        aspect="auto",
        vmin=0,
        vmax=max(matrix.max(), 1),
    )
    ax.set_xticks(range(len(severities)))
    ax.set_xticklabels(severities, fontsize=11)
    ax.set_yticks(range(len(tracks)))
    ax.set_yticklabels(tracks, fontsize=11)
    ax.set_title(
        f"TRA Round 5 Audit — Severity by Track (Issues Only)\n"
        f"{total_issues} issues: "
        f"{issue_counts['BLOCKING']} BLOCKING / "
        f"{issue_counts['WARNING']} WARNING / "
        f"{issue_counts['INFO']} INFO  "
        f"({total_positives} positive verifications not shown)",
        fontsize=12,
        fontweight="bold",
        pad=12,
    )
    # Annotate cells
    for i in range(len(tracks)):
        for j in range(len(severities)):
            val = matrix[i][j]
            if val > 0:
                color = "white" if val > matrix.max() * 0.6 else "black"
                ax.text(
                    j,
                    i,
                    str(val),
                    ha="center",
                    va="center",
                    fontsize=14,
                    fontweight="bold",
                    color=color,
                )
    # Grid
    ax.set_xticks(np.arange(-0.5, len(severities), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(tracks), 1), minor=True)
    ax.grid(which="minor", color="gray", linestyle="-", linewidth=0.5)
    ax.tick_params(which="minor", bottom=False, left=False)
    # Colorbar
    _ = fig.colorbar(im, ax=ax, shrink=0.8, label="Finding count")

    # Add track scope annotations on the right
    track_scopes = {
        "A5": "Spec conformance",
        "B5": "Code quality & security",
        "C5": "Doc-vs-code consistency",
        "D5": "Test suite",
        "E5": "Forensic L4 e2e",
        "F5": "Stub-module conformance",
    }
    for i, t in enumerate(tracks):
        ax.text(
            len(severities) - 0.4,
            i,
            track_scopes.get(t, ""),
            ha="left",
            va="center",
            fontsize=9,
            color="dimgray",
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print(f"Wrote {OUT}")
    print(f"Issues matrix:\n{matrix}")
    print(
        f"Totals: {issue_counts['BLOCKING']}B / "
        f"{issue_counts['WARNING']}W / {issue_counts['INFO']}I  "
        f"({total_positives} positive verifications excluded)"
    )


if __name__ == "__main__":
    main()
