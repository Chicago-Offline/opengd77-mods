#!/usr/bin/env python3
"""gen_tommygun.py - Thompson firing animation for the OpenGD77 power-off screen.

Art pipeline: trace Eric's reference silhouette (grayscale -> threshold -> autocrop
-> LANCZOS downscale -> re-threshold). Hand-plotting rectangles was tried twice and
read as a sci-fi ray gun; do not go back to it.

Emits preview PNG/GIF now; --emit-header later writes the firmware tables in the
column-major 8-px-page layout:  byte = bmp[(page*W)+x],  pixel = (byte >> (y&7)) & 1
"""
import os, re, math, sys
from PIL import Image

OUT = os.path.expanduser("~/src/opengd77-mods/preview")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- font reader
CH = os.path.expanduser("~/src/opengd77-R20260131/OpenGD77_MDUV380_DM1701_20260130/"
                        "OpenGD77_MDUV380_DM1701_20260130/MDUV380_firmware/application/"
                        "include/hardware/HX8353E_charset.h")
src = re.sub(r"/\*.*?\*/", "", open(CH, encoding="utf-8", errors="replace").read(), flags=re.S)
src = re.sub(r"//[^\n]*", "", src)
def grab(n):
    m = re.search(r"\b" + n + r"\s*\[\s*\]\s*=\s*\{(.*?)\}\s*;", src, re.S)
    v = re.findall(r"0[xX][0-9a-fA-F]+|\b\d+\b", m.group(1))
    return [int(x, 16) if x.lower().startswith("0x") else int(x) for x in v]
class Font:
    def __init__(s, n):
        d = grab(n); s.start=d[2]; s.end=d[3]; s.w=d[4]; s.h=d[5]; s.bpc=d[7]; s.data=d[8:]
    def glyph(s, c):
        if ord(c) < s.start: return [0]*s.bpc        # SPACE has no glyph -> blank
        o = ord(c) - s.start
        if o > s.end - s.start: o = ord('?') - s.start
        return s.data[o*s.bpc : o*s.bpc + s.bpc]
F = {n: Font(n) for n in ["font_6x8", "font_8x16", "font_16x32"]}

def text_mask(txt, font):
    # Glyph bytes are PAGE-MAJOR: pages = bytesPerChar/width, idx = page*width + cx
    f = F[font]; w = f.w * len(txt)
    m = [[0]*w for _ in range(f.h)]
    pages = f.bpc // f.w
    for i, c in enumerate(txt):
        g = f.glyph(c)
        for cx in range(f.w):
            for page in range(pages):
                idx = page*f.w + cx
                if idx >= len(g): continue
                for bit in range(8):
                    y = page*8 + bit
                    if y < f.h and (g[idx] >> bit) & 1: m[y][i*f.w + cx] = 1
    return m, w, f.h

# ---------------------------------------------------------------- traced gun
REF = os.path.expanduser("~/.openclaw/workspace/agents/chioff/media/inbound/"
                         "openclaw-staged-4d02df8c-0949-40a4-ba99-a3fec838c4cc/"
                         "input-b236e24d-97e9-477d-bc31-d8559a99d060.png")
# 120 px: at 128 the stock clipped the left box border on recoil frames and the
# muzzle flash overran the right border. 120 + 22 px of flash + 4 px recoil fits
# the 150 px interior of the stock notification box with room to spare.
GW, GH = 120, 40
TRACE_W, TRACE_THRESH = 120, 128

def build_gun():
    im = Image.open(REF).convert("L")
    bw = im.point(lambda v: 255 if v < 128 else 0, mode="L")   # dark art = lit pixel
    crop = bw.crop(bw.getbbox())
    th = max(1, round(TRACE_W * crop.size[1] / crop.size[0]))
    sm = crop.resize((TRACE_W, th), Image.LANCZOS)
    m = [[0]*GW for _ in range(GH)]
    ytop = (GH - th)//2
    for y in range(th):
        for x in range(TRACE_W):
            if sm.getpixel((x, y)) > TRACE_THRESH: m[ytop+y][x] = 1
    return m, th

GUN, GUN_H = build_gun()

def _muzzle(m):
    for x in range(GW-1, -1, -1):  # noqa
        ys = [y for y in range(GH) if m[y][x]]
        if ys: return x, (min(ys)+max(ys))//2
    return GW-1, GH//2
def _eject(m, xf=0.55):
    x = int(GW*xf)
    ys = [y for y in range(GH) if m[y][x]]
    return x, (min(ys) if ys else GH//2)
MUZZLE_X, MUZZLE_Y = _muzzle(GUN)
EJECT_X,  EJECT_Y  = _eject(GUN)

def blank(w,h): return [[0]*w for _ in range(h)]
def P(m,x,y):
    if 0 <= y < len(m) and 0 <= x < len(m[0]): m[y][x] = 1
def line(m,x0,y0,x1,y1,t=1):
    n = max(abs(x1-x0), abs(y1-y0)) or 1
    for i in range(n+1):
        x = round(x0+(x1-x0)*i/n); y = round(y0+(y1-y0)*i/n)
        for o in range(t): P(m,x,y+o)
def disc(m,cx,cy,r):
    for yy in range(cy-r,cy+r+1):
        for xx in range(cx-r,cx+r+1):
            if (xx-cx)**2+(yy-cy)**2 <= r*r: P(m,xx,yy)

# ---------------------------------------------------------------- muzzle flash
def flash_mask(size):
    fw, fh = 44, 44
    m = blank(fw, fh)
    if size == 0: return m, 0, 0
    cx, cy = 2, fh//2
    reach, spikes = {1:(9,5), 2:(22,9), 3:(15,7)}[size]
    for k in range(spikes):
        a = (k/(spikes-1) - 0.5) * 1.5
        ln = reach * (0.55 + 0.45*math.cos(a*1.4))
        line(m, cx, cy, int(cx+ln*math.cos(a)), int(cy+ln*math.sin(a)), 2)
    disc(m, cx+3, cy, max(2, reach//6))
    return m, cx, cy
FLASH = {s: flash_mask(s) for s in (0,1,2,3)}

# ---------------------------------------------------------------- brass
# Ballistic arc from the ejection port, up and to the right, tumbling.
# Deterministic (no RNG) so the firmware can ship a precomputed table.
# 40 ms (not 80): POWEROFF_DURATION_MILLISECONDS is 500, so a 960 ms loop would be
# cut in half by shutdown. 12 x 40 = 480 ms fits one complete loop inside the stock
# power-off window with zero change to shutdown behaviour.
NFRAMES, FRAME_MS = 12, 40
SHOTS   = [0, 3, 6, 9]                      # frames on which a round fires
SHELL_LIFE = 12
VX = [3.4, 3.0, 3.7, 3.2]                   # slight per-shot spread
VY, GRAV = -6.5, 1.1                        # apex ~19 px above the port at t~6
SPAWN_DY = -2                               # clear the receiver on frame 1

def shells_at(frame):
    """Active shells this frame, as (x, y, tumble) relative to the gun sprite.
       Shots from the previous cycle are included so the loop is seamless."""
    out = []
    for si, s in enumerate(SHOTS):
        for base in (s, s - NFRAMES):
            t = frame - base
            if 0 <= t < SHELL_LIFE:
                x = EJECT_X + VX[si]*t
                y = EJECT_Y + SPAWN_DY + VY*t + 0.5*GRAV*t*t
                ix, iy = int(round(x)), int(round(y))
                # cull once it falls back behind the gun body
                if 0 <= iy < GH and 0 <= ix < GW and GUN[iy][ix]: continue
                out.append((ix, iy, t & 1))
    return out

def shot_age(frame):
    best = 99
    for s in SHOTS:
        for base in (s, s - NFRAMES):
            if frame >= base: best = min(best, frame - base)
    return best

def flash_for(frame):
    return {0:2, 1:3, 2:1}.get(shot_age(frame), 0)
def recoil_for(frame):
    return {0:4, 1:2, 2:1}.get(shot_age(frame), 0)

# ---------------------------------------------------------------- render
W, H = 160, 128
CYAN=(0x00,0xE5,0xFF); AMBER=(0xFF,0xB3,0x00); WHITE=(0xFF,0xFF,0xFF)
DEEP=(0x00,0x3A,0x44); BG=(0,0,0)

def put_mask(img, m, ox, oy, col):
    for y,row in enumerate(m):
        for x,v in enumerate(row):
            if v and 0 <= ox+x < W and 0 <= oy+y < H: img.putpixel((ox+x, oy+y), col)

def put_text(img, txt, font, cy, col):
    m,w,h = text_mask(txt, font)
    put_mask(img, m, (W-w)//2, cy, col)

def round_rect(img,x,y,w,h,r,col,shadow):
    for yy in range(y,y+h):
        for xx in range(x,x+w):
            dx=min(xx-x,x+w-1-xx); dy=min(yy-y,y+h-1-yy)
            if dx<r and dy<r and (r-dx)**2+(r-dy)**2 > r*r: continue
            if dx==0 or dy==0 or (dx<r and dy<r and (r-dx)**2+(r-dy)**2 > (r-1)**2):
                img.putpixel((xx,yy),col)
    for yy in range(y+h,y+h+3):
        for xx in range(x+3,x+w+3):
            if 0<=xx<W and 0<=yy<H: img.putpixel((xx,yy),shadow)
    for xx in range(x+w,x+w+3):
        for yy in range(y+3,y+h+3):
            if 0<=xx<W and 0<=yy<H: img.putpixel((xx,yy),shadow)

SHELL = {0: [[1,1,1],[1,1,1]], 1: [[1,1],[1,1],[1,1]]}   # tumble: flat / on end

def draw_gun_scene(img, gx, gy, frame):
    rec = recoil_for(frame); fsz = flash_for(frame)
    put_mask(img, GUN, gx-rec, gy, CYAN)
    fm, fcx, fcy = FLASH[fsz]
    if fsz: put_mask(img, fm, gx-rec+MUZZLE_X-fcx, gy+MUZZLE_Y-fcy, AMBER)
    for sx, sy, tum in shells_at(frame):
        put_mask(img, SHELL[tum], gx-rec+sx, gy+sy, AMBER)

def render(frame, layout):
    img = Image.new("RGB",(W,H),BG)
    if layout == "A":
        round_rect(img,4,4,152,122,5,CYAN,DEEP)
        put_text(img,"Power Off","font_8x16",14,AMBER)
        # "73" dropped at Eric's request. Remaining space is now text + the
        # gun/brass block; gy picked so that block (gy-16 brass .. gy+36 gun)
        # centres in the area below the text.
        draw_gun_scene(img, 10, 67, frame)
    else:
        put_text(img,"Power Off","font_8x16",14,AMBER)
        draw_gun_scene(img, 14, 68, frame)
    return img

print(f"traced gun {TRACE_W}x{GUN_H}  muzzle=({MUZZLE_X},{MUZZLE_Y})  eject=({EJECT_X},{EJECT_Y})")
print(f"{NFRAMES} frames @ {FRAME_MS}ms = {NFRAMES*FRAME_MS}ms/loop, shots on {SHOTS}")
for f in range(NFRAMES):
    print(f"  f{f:2d} flash={flash_for(f)} recoil={recoil_for(f)} shells={shells_at(f)}")

for layout in ("A","B"):
    frames = [render(i,layout) for i in range(NFRAMES)]
    cols=4; rows=(len(frames)+cols-1)//cols; pad=6
    sheet = Image.new("RGB",(cols*(W*2+pad)+pad, rows*(H*2+pad)+pad),(30,30,30))
    for i,fr in enumerate(frames):
        sheet.paste(fr.resize((W*2,H*2),Image.NEAREST),(pad+(i%cols)*(W*2+pad), pad+(i//cols)*(H*2+pad)))
    sheet.save(f"{OUT}/tommygun_sheet_{layout}.png")
    big=[fr.resize((W*3,H*3),Image.NEAREST) for fr in frames]
    big[0].save(f"{OUT}/tommygun_{layout}.gif",save_all=True,append_images=big[1:],
                duration=FRAME_MS,loop=0)
print("wrote",OUT)


# ---------------------------------------------------------------- C emitter
def pack(m):
    """Row-major, MSB-first, scanlines padded to whole bytes.
       This is what displayDrawBitmap() reads (HX8353E_display.c):
         byteWidth = (w+7)/8;  byte = bitmap[j*byteWidth + i/8];  test byte & 0x80
       NOT the column-major page layout used by the framebuffer/font glyphs."""
    h = len(m); w = len(m[0]); bw = (w + 7)//8
    out = [0]*(bw*h)
    for y in range(h):
        for x in range(w):
            if m[y][x]: out[y*bw + (x >> 3)] |= (0x80 >> (x & 7))
    return out, w, h, bw

def crop(m):
    ys = [y for y,r in enumerate(m) if any(r)]
    xs = [x for x in range(len(m[0])) if any(r[x] for r in m)]
    if not ys: return [[0]], 0, 0
    return [[m[y][x] for x in xs] for y in ys], xs[0], ys[0]

def carr(name, data, per=16):
    s = f"static const uint8_t {name}[{len(data)}] = {{\n"
    for i in range(0, len(data), per):
        s += "\t" + ", ".join(f"0x{b:02X}" for b in data[i:i+per]) + ",\n"
    return s + "};\n"

def emit_header(path):
    L = ["// AUTO-GENERATED by tools/gen_tommygun.py -- DO NOT EDIT BY HAND",
         "// Chicago Offline power-off animation: Thompson + ejecting brass.",
         "// Bitmaps are ROW-MAJOR, MSB-FIRST, scanlines padded to whole bytes,",
         "// i.e. exactly the layout displayDrawBitmap(x,y,bmp,w,h,inv) expects.",
         "#pragma once", "#include <stdint.h>", ""]
    g, gw, gh, gp = pack(GUN)
    L += [f"#define TG_GUN_W {gw}", f"#define TG_GUN_H {gh}",
          f"#define TG_MUZZLE_X {MUZZLE_X}", f"#define TG_MUZZLE_Y {MUZZLE_Y}", "",
          carr("tgGun", g)]
    for s in (1, 2, 3):
        fm, fcx, fcy = FLASH[s]
        cm, ox, oy = crop(fm)
        d, w, h, p = pack(cm)
        L += [f"#define TG_FLASH{s}_W {w}", f"#define TG_FLASH{s}_H {h}",
              f"#define TG_FLASH{s}_DX ({ox - fcx})", f"#define TG_FLASH{s}_DY ({oy - fcy})",
              carr(f"tgFlash{s}", d)]
    # per-frame: recoil, flash size, and the shell list
    shells, idx = [], []
    for f in range(NFRAMES):
        idx.append(len(shells))
        for (sx, sy, t) in shells_at(f): shells.append((sx, sy, t))
    idx.append(len(shells))
    L += [f"#define TG_FRAMES {NFRAMES}", f"#define TG_FRAME_MS {FRAME_MS}",
          f"#define TG_LOOP_MS {NFRAMES*FRAME_MS}", ""]
    L.append("static const uint8_t tgRecoil[TG_FRAMES] = { " +
             ", ".join(str(recoil_for(f)) for f in range(NFRAMES)) + " };")
    L.append("static const uint8_t tgFlashSize[TG_FRAMES] = { " +
             ", ".join(str(flash_for(f)) for f in range(NFRAMES)) + " };")
    L.append("static const uint8_t tgShellIdx[TG_FRAMES + 1] = { " +
             ", ".join(str(i) for i in idx) + " };")
    L.append("typedef struct { int8_t dx; int8_t dy; uint8_t tumble; } tgShell_t;")
    L.append(f"static const tgShell_t tgShells[{len(shells)}] = {{")
    for (sx, sy, t) in shells: L.append(f"\t{{ {sx}, {sy}, {t} }},")
    L.append("};")
    # NOTE: no shell sprite arrays are emitted. The shells are 3x2 / 2x3 solid
    # blocks drawn with displaySetPixel loops in uiPowerOff.c; emitting unused
    # static const arrays in a header trips -Wunused-const-variable.
    open(path, "w").write("\n".join(L) + "\n")
    tot = len(g) + sum(len(pack(crop(FLASH[s][0])[0])[0]) for s in (1,2,3)) + len(shells)*3 + NFRAMES*3
    print(f"wrote {path}\n  gun {gw}x{gh} = {len(g)} B, {len(shells)} shell records, ~{tot} B of .rodata")

if "--emit-header" in sys.argv:
    emit_header(os.path.expanduser("~/src/opengd77-mods/out/chioff_tommygun.h"))
