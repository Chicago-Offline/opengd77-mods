#!/usr/bin/env python3
"""Trace Eric's reference Thompson PNG into a 1-bit sprite for the power-off screen.

Hand-plotting rectangles produced a ray gun (v1/v2, rejected). This instead
grayscale-thresholds the real reference art, autocrops, scales, and re-thresholds
- the same pipeline as the boot-splash work.
"""
import os
from PIL import Image

REF = os.path.expanduser("~/.openclaw/workspace/agents/chioff/media/inbound/"
                         "openclaw-staged-4d02df8c-0949-40a4-ba99-a3fec838c4cc/"
                         "input-b236e24d-97e9-477d-bc31-d8559a99d060.png")
OUT = os.path.expanduser("~/src/opengd77-mods/preview")
os.makedirs(OUT, exist_ok=True)

im = Image.open(REF).convert("L")
print("source size:", im.size, "min/max:", im.getextrema())

# gun is DARK on light -> lit pixel = dark pixel
THRESH = 128
bw = im.point(lambda p: 255 if p < THRESH else 0, mode="L")

bbox = bw.getbbox()
print("bbox:", bbox)
crop = bw.crop(bbox)
print("cropped:", crop.size, "aspect %.2f" % (crop.size[0]/crop.size[1]))

for TW in (112, 120, 128, 136, 144):
    th = max(1, round(TW * crop.size[1] / crop.size[0]))
    sm = crop.resize((TW, th), Image.LANCZOS)
    for T in (96, 112, 128, 144):
        b = sm.point(lambda p: 1 if p > T else 0)
        on = sum(b.getdata())
        print(f"  W={TW} H={th} thresh={T}: {on} lit px ({100*on/(TW*th):.0f}% fill)")
    sm.point(lambda p: 255 if p > 128 else 0).resize((TW*4, th*4), Image.NEAREST)\
      .save(f"{OUT}/trace_w{TW}.png")
print("wrote trace_w*.png to", OUT)
