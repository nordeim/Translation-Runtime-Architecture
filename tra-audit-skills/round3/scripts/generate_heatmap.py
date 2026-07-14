"""Generate severity heatmap PNG for Round 3 audit."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np

# Font setup for CJK + Latin
fm.fontManager.addfont('/usr/share/fonts/truetype/noto-serif-sc/NotoSerifSC-Regular.ttf')
fm.fontManager.addfont('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
plt.rcParams['font.sans-serif'] = ['Noto Serif SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

REGISTER = Path("/home/z/my-project/download/TRA_Round3/master_findings_register_r3.json")
OUT = Path("/home/z/my-project/download/TRA_Round3/TRA_audit_severity_heatmap_r3.png")


def main() -> None:
    findings = json.loads(REGISTER.read_text(encoding="utf-8"))
    tracks = ["R3", "A3", "B3", "C3", "D3", "E3", "F3"]
    severities = ["BLOCKING", "WARNING", "INFO"]
    # Build matrix [track][severity]
    matrix = np.zeros((len(tracks), len(severities)), dtype=int)
    for f in findings:
        track = f["track"].split(",")[0]  # primary track
        if track not in tracks:
            continue
        ti = tracks.index(track)
        si = severities.index(f["severity"])
        matrix[ti][si] += 1
    # Add Track R3 row from baseline (all 71 findings are regression checks, not new findings)
    # Track R3 didn't produce new findings — it verified Round 2 findings. Represent as 0.
    # Actually, the 12 persistent findings are carry-overs that R3 confirmed.
    # Let's count persistent findings per track for R3.
    for f in findings:
        if f["round2_status"] in ("persistent", "partial"):
            track = f["track"].split(",")[0]
            if track in tracks:
                ti = tracks.index(track)
                # These are already counted above; don't double-count.

    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto', vmin=0, vmax=max(matrix.max(), 1))
    ax.set_xticks(range(len(severities)))
    ax.set_xticklabels(severities, fontsize=11)
    ax.set_yticks(range(len(tracks)))
    ax.set_yticklabels(tracks, fontsize=11)
    ax.set_title('TRA Round 3 Audit — Severity by Track\n(36 findings: 2 BLOCKING / 18 WARNING / 16 INFO)',
                 fontsize=13, fontweight='bold', pad=12)
    # Annotate cells
    for i in range(len(tracks)):
        for j in range(len(severities)):
            val = matrix[i][j]
            if val > 0:
                color = 'white' if val > matrix.max() * 0.6 else 'black'
                ax.text(j, i, str(val), ha='center', va='center',
                        fontsize=14, fontweight='bold', color=color)
    # Grid
    ax.set_xticks(np.arange(-0.5, len(severities), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(tracks), 1), minor=True)
    ax.grid(which='minor', color='gray', linestyle='-', linewidth=0.5)
    ax.tick_params(which='minor', bottom=False, left=False)
    # Colorbar
    cbar = fig.colorbar(im, ax=ax, shrink=0.8, label='Finding count')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print(f"Wrote {OUT}")
    print(f"Matrix:\n{matrix}")


if __name__ == "__main__":
    main()
