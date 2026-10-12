#!/usr/bin/env python3
"""Decode chioff_tommygun.h the way displayDrawBitmap() would, and diff it against
the generator's own mask. Catches packing errors before they reach the radio."""
import re, os, sys
sys.argv = [sys.argv[0]]                 # don't re-trigger --emit-header
sys.path.insert(0, os.path.expanduser("~/src/opengd77-mods/tools"))
import importlib.util
spec = importlib.util.spec_from_file_location("g", os.path.expanduser(
    "~/src/opengd77-mods/tools/gen_tommygun.py"))
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)

H = open(os.path.expanduser("~/src/opengd77-mods/out/chioff_tommygun.h")).read()
def arr(name):
    m = re.search(r"\b" + name + r"\s*\[\s*\d+\s*\]\s*=\s*\{(.*?)\};", H, re.S)
    return [int(x, 16) for x in re.findall(r"0x([0-9A-Fa-f]{2})", m.group(1))]

def unpack(data, w, h):
    """Mirror of HX8353E_display.c displayDrawBitmap()."""
    bw = (w + 7)//8
    out = [[0]*w for _ in range(h)]
    for j in range(h):
        byte = 0
        for i in range(w):
            if i & 7: byte = (byte << 1) & 0xFF
            else:     byte = data[j*bw + i//8]
            if byte & 0x80: out[j][i] = 1
    return out

gun = unpack(arr("tgGun"), g.GUN_W if hasattr(g,"GUN_W") else 120, 40)
diff = sum(1 for y in range(40) for x in range(120) if gun[y][x] != g.GUN[y][x])
lit  = sum(sum(r) for r in g.GUN)
print(f"gun: {lit} lit px in source mask, {sum(sum(r) for r in gun)} decoded, DIFF={diff}")
assert diff == 0, "PACKING MISMATCH"

for s in (1,2,3):
    w = int(re.search(rf"TG_FLASH{s}_W (\d+)", H).group(1))
    h = int(re.search(rf"TG_FLASH{s}_H (\d+)", H).group(1))
    d = unpack(arr(f"tgFlash{s}"), w, h)
    print(f"  flash{s}: {w}x{h}, {sum(sum(r) for r in d)} lit px decoded")

n = len(re.findall(r"\{\s*-?\d+,\s*-?\d+,\s*\d+\s*\},", H))
print(f"shell records in header: {n}")
print("ROUND-TRIP OK - header matches the generator mask exactly")

from PIL import Image
im = Image.new("RGB",(120,40),(0,0,0))
for y in range(40):
    for x in range(120):
        if gun[y][x]: im.putpixel((x,y),(0,0xE5,0xFF))
im.resize((480,160), Image.NEAREST).save(os.path.expanduser(
    "~/.openclaw/workspace/agents/chioff/preview/tommygun/decoded_from_header.png"))
print("wrote decoded_from_header.png")
