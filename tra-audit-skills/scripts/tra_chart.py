"""Generate the TRA audit severity heatmap chart.

A grouped bar chart showing finding counts by category, stacked by severity
(BLOCKING / WARNING / INFO). Uses the charts skill's matplotlib routing with
the Business Cool palette and constrained_layout.
"""

from __future__ import annotations

import sys

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np

# Add scripts dir to import the findings register
sys.path.insert(0, "/home/z/my-project/scripts")
from tra_findings import FINDINGS, by_category  # noqa: E402

# Font setup per skill rules — English-only chart, use DejaVu Sans (always available)
fm.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
fm.fontManager.addfont("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# Business Cool palette (per charts skill)
PRIMARY = "#243447"
ACCENT = "#4C6EF5"
BG = "#F8FAFC"
BLOCKING_COLOR = "#C92A2A"  # muted red
WARNING_COLOR = "#F08C00"   # muted amber
INFO_COLOR = "#1C7ED6"      # muted blue
NEUTRAL = "#E9EEF3"

cat_data = by_category()
categories = list(cat_data.keys())
blocking = [cat_data[c]["BLOCKING"] for c in categories]
warning = [cat_data[c]["WARNING"] for c in categories]
info = [cat_data[c]["INFO"] for c in categories]

# Shorten category labels for readability
short_labels = {
    "Spec Conformance": "Spec\nConformance",
    "Code Quality": "Code\nQuality",
    "Security": "Security",
    "Doc Consistency": "Doc\nConsistency",
    "Test Suite": "Test\nSuite",
}
labels = [short_labels.get(c, c) for c in categories]

fig, ax = plt.subplots(figsize=(11, 6.5), constrained_layout=True)
fig.patch.set_facecolor("white")
ax.set_facecolor(BG)

x = np.arange(len(categories))
width = 0.62

# Stacked bars: BLOCKING at bottom (most urgent), WARNING middle, INFO top
bars_b = ax.bar(x, blocking, width, label="BLOCKING", color=BLOCKING_COLOR, edgecolor="white", linewidth=1.2)
bars_w = ax.bar(x, warning, width, bottom=blocking, label="WARNING", color=WARNING_COLOR, edgecolor="white", linewidth=1.2)
bars_i = ax.bar(
    x,
    info,
    width,
    bottom=[b + w for b, w in zip(blocking, warning, strict=True)],
    label="INFO",
    color=INFO_COLOR,
    edgecolor="white",
    linewidth=1.2,
)

# Total label on top of each bar
totals = [b + w + i for b, w, i in zip(blocking, warning, info, strict=True)]
for i, total in enumerate(totals):
    ax.text(i, total + 0.18, str(total), ha="center", va="bottom", fontsize=12, fontweight="bold", color=PRIMARY)

# Per-segment count labels (only if segment > 0)
for bars, vals, bottoms in [
    (bars_b, blocking, [0] * len(blocking)),
    (bars_w, warning, blocking),
    (bars_i, info, [b + w for b, w in zip(blocking, warning, strict=True)]),
]:
    for bar, val, bottom in zip(bars, vals, bottoms, strict=True):
        if val > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bottom + val / 2,
                str(val),
                ha="center",
                va="center",
                fontsize=10,
                fontweight="bold",
                color="white",
            )

ax.set_ylabel("Finding Count", fontsize=12, color=PRIMARY, fontweight="bold")
ax.set_title(
    "TRA Prototype Audit — Findings by Category & Severity",
    fontsize=15,
    color=PRIMARY,
    fontweight="bold",
    pad=14,
)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=10.5, color=PRIMARY)
ax.set_ylim(0, max(totals) * 1.22)

# Clean axes per skill rules
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_color(NEUTRAL)
ax.spines["bottom"].set_color(NEUTRAL)
ax.tick_params(axis="y", colors=PRIMARY, labelsize=9)
ax.tick_params(axis="x", length=0)
ax.yaxis.grid(True, color=NEUTRAL, alpha=0.6, linewidth=0.8)
ax.set_axisbelow(True)

# Legend outside top-right
legend = ax.legend(
    loc="upper right",
    bbox_to_anchor=(1.0, 1.0),
    frameon=False,
    fontsize=10,
    labelcolor=PRIMARY,
    ncol=3,
)

# Subtitle / caption
fig.text(
    0.01,
    -0.02,
    f"35 findings total — 11 BLOCKING / 22 WARNING / 2 INFO  ·  Audit performed 2026-07-13  ·  Severity lexicon per TRA-SPECIFICATION.md §7",
    fontsize=8.5,
    color="#5B6B7D",
    ha="left",
)

out_path = "/home/z/my-project/download/TRA_audit_severity_heatmap.png"
plt.savefig(out_path, dpi=200, facecolor="white")
plt.close()
print(f"Chart saved to {out_path}")
