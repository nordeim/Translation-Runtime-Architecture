"""Generate the severity heatmap PNG for Round 2 audit."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np

# Font setup for any CJK characters in finding titles
try:
    fm.fontManager.addfont("/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf")
except Exception:
    pass
try:
    fm.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
except Exception:
    pass
plt.rcParams["font.sans-serif"] = ["Noto Sans SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

REGISTER_PATH = Path("/home/z/my-project/audit-ctx/master_findings_register.json")
OUT_PATH = Path("/home/z/my-project/download/TRA_audit_severity_heatmap_r2.png")

# Severity numeric mapping for the heatmap
SEVERITY_WEIGHT = {"BLOCKING": 3, "WARNING": 2, "INFO": 1}


def main() -> None:
    findings = json.loads(REGISTER_PATH.read_text(encoding="utf-8"))

    # Group by track and category-prefix
    # Tracks: A, B, C, D, E, R (carry-over marked as A/E for cross-cutting)
    tracks = ["A", "B", "C", "D", "E"]
    severities = ["BLOCKING", "WARNING", "INFO"]

    # Build matrix: rows = tracks, cols = severities, values = count
    matrix = np.zeros((len(tracks), len(severities)), dtype=int)
    for f in findings:
        # A finding can belong to multiple tracks (e.g., "A,E"); count each
        for t in f["track"].split(","):
            t = t.strip()
            if t in tracks:
                matrix[tracks.index(t), severities.index(f["severity"])] += 1

    fig, ax = plt.subplots(figsize=(10, 6), constrained_layout=True)

    # Use a custom colormap: light yellow → orange → red
    cmap = plt.cm.YlOrRd
    im = ax.imshow(matrix, cmap=cmap, aspect="auto", vmin=0, vmax=max(matrix.max(), 1))

    # Tick labels
    ax.set_xticks(range(len(severities)))
    ax.set_xticklabels(severities, fontsize=12, fontweight="bold")
    ax.set_yticks(range(len(tracks)))
    ax.set_yticklabels(
        [f"Track {t}\n({{'A':'Spec Conformance','B':'Code Quality','C':'Doc Consistency','D':'Test Suite','E':'Forensic L4'}}[t])"
         for t in tracks],
        fontsize=11,
    )

    # Annotate each cell with the count
    for i in range(len(tracks)):
        for j in range(len(severities)):
            count = matrix[i, j]
            color = "white" if count >= matrix.max() * 0.6 else "black"
            ax.text(j, i, str(count), ha="center", va="center",
                    color=color, fontsize=14, fontweight="bold")

    # Title and labels
    ax.set_title(
        f"TRA Prototype Audit Round 2 — Severity Heatmap\n"
        f"({len(findings)} findings: {sum(matrix[:,0])} BLOCKING / {sum(matrix[:,1])} WARNING / {sum(matrix[:,2])} INFO)",
        fontsize=13, fontweight="bold", pad=12,
    )
    ax.set_xlabel("Severity", fontsize=12, fontweight="bold")
    ax.set_ylabel("Audit Track", fontsize=12, fontweight="bold")

    # Colorbar
    cbar = fig.colorbar(im, ax=ax, shrink=0.7)
    cbar.set_label("Finding count", fontsize=11)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PATH, dpi=150, facecolor="white")
    plt.close(fig)
    print(f"Wrote {OUT_PATH}")
    print(f"Matrix:\n{matrix}")
    print(f"Per-track totals: {[matrix[i].sum() for i in range(len(tracks))]}")


if __name__ == "__main__":
    main()
