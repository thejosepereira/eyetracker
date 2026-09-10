"""Turn the phase2_study.js output into a chart + a visual montage.

Run after phase2_study.js:  SCRATCH=/tmp/vc python research/experiments/phase2_report.py
"""
import os, json, csv
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw

SCRATCH = os.environ.get("SCRATCH", "/tmp/vc")
OUT = os.path.join(os.path.dirname(__file__), "..", "test-images")
os.makedirs(OUT, exist_ok=True)

# ---- chart: legibility vs blur, per algorithm, vs OFF ----
rows = list(csv.DictReader(open(f"{SCRATCH}/phase2_study.csv")))
configs = ["wiener_gauss", "tv_gauss", "wiener_disk", "tv_disk", "tv_disk_bandlimit"]
labels = {"wiener_gauss": "Wiener · Gaussian (old default)", "tv_gauss": "TV · Gaussian",
          "wiener_disk": "Wiener · DISK (matched)", "tv_disk": "TV · disk",
          "tv_disk_bandlimit": "TV · disk · band-limited"}
colors = {"wiener_gauss": "#e07a3c", "tv_gauss": "#e0b13c", "wiener_disk": "#3c7ae0",
          "tv_disk": "#37d67a", "tv_disk_bandlimit": "#9a6bff"}

by_cfg = {c: [] for c in configs}
off = []
for r in rows:
    s = float(r["sigma_px"]); leg = float(r["legibility"]); imp = float(r["improve_vs_off"])
    by_cfg[r["config"]].append((s, leg))
    off.append((s, leg - imp))

fig, ax = plt.subplots(figsize=(9, 5.5))
o = sorted(set(off)); ax.plot([p[0] for p in o], [p[1] for p in o], "k--", lw=2, label="correction OFF (uncorrected)")
for c in configs:
    pts = sorted(by_cfg[c])
    ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", color=colors[c], lw=1.8, ms=4, label=labels[c])
ax.set_xlabel("eye blur σ (pixels)  —  bigger = stronger prescription / farther")
ax.set_ylabel("perceived legibility (0–1, higher = clearer)")
ax.set_title("What a bad eye perceives, by correction algorithm\n(vs a physically-correct disk-blur eye)")
ax.grid(alpha=0.2); ax.legend(fontsize=8, loc="upper right")
ax.set_ylim(0, 1.02)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "phase2_study.png"), dpi=110)
print("wrote phase2_study.png")

# ---- montage: the representative case, all views ----
m = json.load(open(f"{SCRATCH}/phase2_montage.json"))
W, H = m["W"], m["H"]; panels = m["panels"]
scale = 2; pad = 10; caph = 26; cols = 4
rows_n = (len(panels) + cols - 1) // cols
tileW, tileH = W * scale, H * scale + caph
grid = Image.new("RGB", (cols * tileW + (cols + 1) * pad, rows_n * tileH + (rows_n + 1) * pad), (24, 27, 34))
d = ImageDraw.Draw(grid)
for i, p in enumerate(panels):
    arr = (np.clip(np.array(p["data"], dtype=np.float64), 0, 1) * 255).astype(np.uint8).reshape(H, W)
    im = Image.fromarray(arr, "L").convert("RGB").resize((tileW, H * scale), Image.NEAREST)
    cx = pad + (i % cols) * (tileW + pad); cy = pad + (i // cols) * (tileH + pad)
    grid.paste(im, (cx, cy))
    d.rectangle([cx, cy + H * scale, cx + tileW, cy + tileH], fill=(20, 20, 20))
    d.text((cx + 6, cy + H * scale + 6), p["label"], fill=(230, 230, 230))
grid.save(os.path.join(OUT, "phase2_montage.png"))
print("wrote phase2_montage.png")
