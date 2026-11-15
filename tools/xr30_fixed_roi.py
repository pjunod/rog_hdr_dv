#!/usr/bin/env python3
"""Fixed-ROI comparison of XR30 captures, same method as image-comparison-20261114-r1.

The patch grid is found from the chart geometry only (black/white anchor search near the
r1 rectangles), before any colour errors are computed. Each patch value is the median of its
central 32x32 physical pixels, which must be uniform."""
import json, sys, hashlib, statistics as st
from pathlib import Path
W, H = 2560, 1600
NAMES = ["black","white","red","green","blue","yellow","magenta","cyan",
         "near-black","gray64","gray128","gray192","orange","green-mid","purple","skin"]
R1 = {"loupe": (1024, 788, 64), "web": (768, 371, 128)}
def load(p):
    b = Path(p).read_bytes(); assert len(b) == W*H*4, len(b)
    return memoryview(b).cast("I")
def px(m, x, y):
    v = m[y*W+x]; return ((v >> 20) & 1023, (v >> 10) & 1023, v & 1023)
def window(m, cx, cy):
    vals = [px(m, x, y) for y in range(cy-16, cy+16) for x in range(cx-16, cx+16)]
    return vals
def patches(m, x0, y0, s):
    out = []
    for i, n in enumerate(NAMES):
        cx = x0 + s*(i % 8) + s//2; cy = y0 + s*(i // 8) + s//2
        w = window(m, cx, cy)
        out.append({"name": n, "center": [cx, cy],
                    "median_rgb10": [st.median(c[k] for c in w) for k in range(3)],
                    "minimum": [min(c[k] for c in w) for k in range(3)],
                    "maximum": [max(c[k] for c in w) for k in range(3)]})
    return out
def register(m, kind):
    """Geometry only: find the black patch (exact 0,0,0) whose neighbour one pitch to the right
    is uniform white, then centre on the midpoint of the black run in both axes. Edges are
    scaled, so blended edge pixels are excluded by requiring exact black."""
    x0, y0, s = R1[kind]
    for dy in range(-240, 241, 4):
        for dx in range(-240, 241, 4):
            cx, cy = x0+dx+s//2, y0+dy+s//2
            if px(m, cx, cy) != (0,0,0): continue
            w = px(m, cx+s, cy)
            if not (w[0] == w[1] == w[2] > 500): continue
            l = cx
            while px(m, l-1, cy) == (0,0,0): l -= 1
            r = cx
            while px(m, r+1, cy) == (0,0,0): r += 1
            t = cy
            while px(m, cx, t-1) == (0,0,0): t -= 1
            bt = cy
            while px(m, cx, bt+1) == (0,0,0): bt += 1
            if not (s-4 <= r-l+1 <= s and s-4 <= bt-t+1 <= s): continue
            return (l+r)//2 - s//2, (t+bt)//2 - s//2, s
    raise SystemExit(f"{kind}: chart not registered")
def compare(a, b):
    d = {p["name"]: max(abs(p["median_rgb10"][k]-q["median_rgb10"][k]) for k in range(3))
         for p, q in zip(a, b)}
    allv = [abs(p["median_rgb10"][k]-q["median_rgb10"][k]) for p, q in zip(a, b) for k in range(3)]
    return {"max_abs_pq10_code_difference": max(allv), "mean_abs_pq10_code_difference": sum(allv)/len(allv),
            "per_patch_max": d, "within_predeclared_2code_diagnostic_bound": max(allv) <= 2}
d = Path(sys.argv[1]); res = {"scope": "fixed-ROI diagnostic, same method as image-comparison-20261114-r1; no optical claim",
                              "directory": str(d), "scenes": {}, "comparisons": {}}
for scene in ["loupe-reference", "loupe-original", "web-original"]:
    f = d/f"{scene}.xr30"; m = load(f); x, y, s = register(m, scene.split("-")[0])
    ps = patches(m, x, y, s)
    res["scenes"][scene] = {"capture_sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                            "rectangle": [x, y, 8*s, 2*s], "patches": ps,
                            "all_windows_uniform": all(p["minimum"] == p["maximum"] for p in ps)}
S = res["scenes"]
for a, b in [("loupe-original","loupe-reference"),("web-original","loupe-reference"),("web-original","loupe-original")]:
    res["comparisons"][f"{a}__{b}"] = compare(S[a]["patches"], S[b]["patches"])
(d/"fixed-roi-diagnostics.json").write_text(json.dumps(res, indent=1)+"\n")
for k, v in res["comparisons"].items():
    print(k, "max", v["max_abs_pq10_code_difference"], "mean", round(v["mean_abs_pq10_code_difference"],3), "within2", v["within_predeclared_2code_diagnostic_bound"])
for k, v in S.items(): print(k, v["rectangle"], "uniform", v["all_windows_uniform"])
