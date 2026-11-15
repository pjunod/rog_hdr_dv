#!/usr/bin/env python3
"""Fixed-ROI comparison of XR30 captures, same method as image-comparison-20261114-r1.

The patch grid is found from the chart geometry only (black/white anchor search near the
r1 rectangles), before any colour errors are computed. Each patch value is the median of its
central 32x32 physical pixels. Windows that are not uniform are listed, with min/max kept.
Optional second argument: the chart's linear BT.2020 reference table, for a comparison with
an independent PQ model as well as between apps. Exit status is 0 only if the grid validates
and every comparison is within 2 codes.

Usage: xr30_fixed_roi.py CAPTURE_DIR [REFERENCE_LINEAR2020_TXT]"""
import json, sys, hashlib, statistics as st
assert sys.byteorder == "little", "XR30 words are little-endian; cast(\"I\") assumes a little-endian host"
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
def validate(ps):
    """Geometry check independent of the colour comparison: neutral patches are neutral and
    ordered black < near-black < gray64 < gray128 < gray192 < white."""
    v = {p["name"]: p["median_rgb10"] for p in ps}
    order = ["black", "near-black", "gray64", "gray128", "gray192", "white"]
    neutral = all(max(v[n]) - min(v[n]) <= 2 for n in order)
    ordered = all(v[a][0] < v[b][0] for a, b in zip(order, order[1:]))
    return neutral and ordered
def pq10(linear, white_nits=203.0):
    """SMPTE ST 2084 full-range 10-bit code for a linear BT.2020 value where 1.0 is SDR white."""
    m1, m2, c1, c2, c3 = 0.1593017578125, 78.84375, 0.8359375, 18.8515625, 18.6875
    y = (max(linear, 0.0) * white_nits / 10000.0) ** m1
    return 1023.0 * ((c1 + c2*y) / (1 + c3*y)) ** m2
def independent(ps, table):
    """Compare each scene with an independent model: per-patch linear BT.2020 values from the
    chart's reference table (8-bit R G B then linear R G B per line), encoded to PQ at 203 nits."""
    rows = [list(map(float, l.split()[3:6])) for l in Path(table).read_text().splitlines() if l.strip()]
    assert len(rows) == len(ps)
    diffs = {p["name"]: max(abs(p["median_rgb10"][k] - pq10(r[k])) for k in range(3)) for p, r in zip(ps, rows)}
    m = max(diffs.values())
    return {"expected_pq10": [[round(pq10(x), 2) for x in r] for r in rows],
            "max_abs_pq10_code_difference": round(m, 2), "per_patch_max": {k: round(v, 2) for k, v in diffs.items()},
            "within_predeclared_2code_diagnostic_bound": m <= 2}
def compare(a, b):
    d = {p["name"]: max(abs(p["median_rgb10"][k]-q["median_rgb10"][k]) for k in range(3))
         for p, q in zip(a, b)}
    allv = [abs(p["median_rgb10"][k]-q["median_rgb10"][k]) for p, q in zip(a, b) for k in range(3)]
    return {"max_abs_pq10_code_difference": max(allv), "mean_abs_pq10_code_difference": sum(allv)/len(allv),
            "per_patch_max": d, "within_predeclared_2code_diagnostic_bound": max(allv) <= 2}
d = Path(sys.argv[1]); res = {"scope": "fixed-ROI diagnostic, same method as image-comparison-20261114-r1; no optical claim",
                              "directory": d.name, "scenes": {}, "comparisons": {}}
for scene in ["loupe-reference", "loupe-original", "web-original"]:
    f = d/f"{scene}.xr30"; m = load(f); x, y, s = register(m, scene.split("-")[0])
    ps = patches(m, x, y, s)
    res["scenes"][scene] = {"capture_sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                            "rectangle": [x, y, 8*s, 2*s], "patches": ps,
                            "grid_validated": validate(ps),
                            "non_uniform_windows": [p["name"] for p in ps if p["minimum"] != p["maximum"]]}
S = res["scenes"]
if len(sys.argv) > 2:
    res["independent_model"] = {"table": Path(sys.argv[2]).name, "white_nits": 203,
                                "scenes": {k: independent(v["patches"], sys.argv[2]) for k, v in S.items()}}
for a, b in [("loupe-original","loupe-reference"),("web-original","loupe-reference"),("web-original","loupe-original")]:
    res["comparisons"][f"{a}__{b}"] = compare(S[a]["patches"], S[b]["patches"])
(d/"fixed-roi-diagnostics.json").write_text(json.dumps(res, indent=1)+"\n")
for k, v in res["comparisons"].items():
    print(k, "max", v["max_abs_pq10_code_difference"], "mean", round(v["mean_abs_pq10_code_difference"],3), "within2", v["within_predeclared_2code_diagnostic_bound"])
for k, v in S.items(): print(k, v["rectangle"], "grid", v["grid_validated"], "non-uniform", v["non_uniform_windows"])
for k, v in res.get("independent_model", {}).get("scenes", {}).items():
    print(k, "vs independent model max", v["max_abs_pq10_code_difference"])
ok = all(v["grid_validated"] for v in S.values()) and \
     all(v["within_predeclared_2code_diagnostic_bound"] for v in res.get("independent_model", {}).get("scenes", {}).values()) and \
     all(c["within_predeclared_2code_diagnostic_bound"] for c in res["comparisons"].values())
sys.exit(0 if ok else 1)
