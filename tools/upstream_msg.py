#!/usr/bin/env python3
"""Rewrite imported commit messages into upstream Mutter form (subjects, package references)."""
import re, sys
m = sys.stdin.read()
subjects = {
 "backends/native: support native DisplayID RGB BT.2020 PQ on eDP": "backends/native: Support native DisplayID RGB BT.2020 PQ on eDP",
 "fix(color): separate native HDR target luminance from encoding": "backends/color: Separate the native target luminance from the encoding",
 "test(color): cover native target policy and immutable Wayland feedback": "tests/native-hdr: Cover native target policy and immutable Wayland feedback",
 "fix(color): refresh preferred targets after output topology changes": "backends/color: Refresh preferred targets after output topology changes",
 "test(color): account for global force HDR output changes": "tests/color-management: Account for global forced HDR output changes",
 "fix(color): dispose Wayland target records before output teardown": "wayland/color-management: Dispose target records before output teardown",
 "test(color): retain native fixture mode during forced policy comparison": "tests/native-hdr: Keep the native fixture mode during the forced policy comparison",
 "color: publish native target primaries independently of encoding": "backends/color: Publish native target primaries independently of the encoding",
 "test: cover native target primaries and their Wayland feedback": "tests/native-hdr: Cover native target primaries and their Wayland feedback",
 "test: run target-volume cases in separate test invocations": "tests: Run target-volume cases in separate test invocations",
 "color: Publish encoding and fallback target primaries with one conversion": "backends/color: Publish encoding and fallback target primaries with one conversion",
 "color-device: Validate EDID primaries before using them for native SDR": "backends/color: Validate EDID primaries before using them for native SDR",
}
first, _, rest = m.partition("\n")
first = subjects.get(first, first)
m = first + "\n" + rest
subs = [
 (r"Validation on the Ubuntu 51\.0 source adaptation: a normal", "Validation: a normal"),
 (r"A private real-panel\s+probe", "A real-panel probe"),
 (r"Require the additive hdr8 chromaticity API at configure/link time and\s+record the nativehdr4 packaging metadata\.", "Require the additive libdisplay-info chromaticity API at configure/link\ntime."),
 (r"\(published to Wayland\s+since nativehdr4\)", "(already published to Wayland)"),
 (r"\(since\s+nativehdr4\), and since nativehdr6 renders for the declared target peak,\s+but rendering never saw the primaries: nativehdr6 deliberately left\s+them off",
  "(already),\nand rendering already blends for the declared target peak, but\nrendering never saw the primaries: the target peak change deliberately\nleft them off"),
 (r"the notion nativehdr6 uses for the peak", "the notion highlight mapping uses for the peak"),
 (r"keeps the nativehdr6 rule,", "keeps the existing rule,"),
 (r"which the nativehdr6\s+acceptance rule takes", "which the mastering\n   acceptance rule takes"),
 (r"The nativehdr4 target-primaries fixture", "The earlier target-primaries fixture"),
 (r"Since nativehdr7, declared mastering primaries", "Since gamut compression was added, declared mastering primaries"),
 (r"\s+It is\s+listed in the symbols file\.", ""),
 (r"; added to the symbols\s+file\)", ")"),
 (r"\s+and\s+(?:listed in|added to)\s+the\s+symbols\s+file(?:\s+at\s+\S+?)?(?=[.:](?:\s|$))", ""),
]
for a, b in subs:
    m = re.sub(a, b, m)
for bad in ("nativehdr", "symbols file", "ubuntu", "hdr8 "):
    if bad in m.lower():
        sys.stderr.write("LEFTOVER %r in: %s\n" % (bad, first))
sys.stdout.write(m)
