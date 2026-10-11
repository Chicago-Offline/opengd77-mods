
import re
from PIL import Image

CH = "/Users/muehlbucks/src/opengd77-R20260131/OpenGD77_MDUV380_DM1701_20260130/OpenGD77_MDUV380_DM1701_20260130/MDUV380_firmware/application/include/hardware/HX8353E_charset.h"
raw = open(CH, encoding="utf-8", errors="replace").read()
src = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
src = re.sub(r"//[^\n]*", "", src)
def grab(n):
    m = re.search(r"\b"+n+r"\s*\[\s*\]\s*=\s*\{(.*?)\}\s*;", src, re.S)
    v = re.findall(r"0[xX][0-9a-fA-F]+|\b\d+\b", m.group(1))
    return [int(x,16) if x.lower().startswith("0x") else int(x) for x in v]
class Font:
    def __init__(s,n):
        d=grab(n); s.start=d[2]; s.end=d[3]; s.w=d[4]; s.h=d[5]; s.bpc=d[7]; s.data=d[8:]
    def glyph(s,c):
        o=ord(c)-s.start
        if o<0 or o>s.end-s.start: o=ord('?')-s.start
        return s.data[o*s.bpc:o*s.bpc+s.bpc]
F={n:Font(n) for n in ["font_6x8","font_8x16","font_16x32"]}

W,H = 160,128
GROUND = 119
BAND_TOP = 62
BH = GROUND-BAND_TOP+1
STRIP = 240

CYAN=(0x00,0xE5,0xFF); AMBER=(0xFF,0xB3,0x00); WHITE=(0xFF,0xFF,0xFF)
DEEP=(0x00,0x3A,0x44); BG=(0,0,0)

mask=[[False]*STRIP for _ in range(BH)]
def mset(x,y):
    if 0<=x<STRIP and 0<=y<BH: mask[y][x]=True
def box(x,w,h):
    for yy in range(BH-h,BH):
        for xx in range(x,x+w): mset(xx,yy)
def ant(x,h,top):
    for yy in range(BH-top-h,BH-top): mset(x,yy)

builds=[(2,12,18,'p'),(16,9,26,'p'),(27,16,32,'s'),(46,9,27,'c'),(57,9,27,'c'),
        (70,11,20,'p'),(84,24,48,'w'),(111,10,22,'p'),(124,14,40,'t'),(141,9,24,'p'),
        (153,12,44,'r'),(168,10,20,'p'),(180,14,30,'s'),(197,8,22,'p'),(208,12,26,'p'),
        (223,13,34,'s')]
willis_ant=[]
for (x,w,h,st) in builds:
    if st=='p': box(x,w,h)
    elif st=='s':
        box(x,w,int(h*0.7)); box(x+3,w-6,h)
    elif st=='c':
        box(x,w,h-4)
        r=w//2
        for yy in range(BH-h,BH-h+5):
            for xx in range(x,x+w):
                dx=(xx-(x+r))/max(r,1); dy=(yy-(BH-h+5))/5.0
                if dx*dx+dy*dy<=1.15: mset(xx,yy)
    elif st=='w':  # Willis: stepped setbacks + twin antennas
        box(x,w,int(h*0.55)); box(x+4,w-8,int(h*0.78)); box(x+8,w-16,h)
        ant(x+9,13,h); ant(x+13,13,h)
        willis_ant=[(x+9,BH-h-13),(x+13,BH-h-13)]
    elif st=='t':  # Hancock taper
        for i in range(h):
            inset=int(i*2.2/h*2)
            for xx in range(x+inset,x+w-inset): mset(xx,BH-1-i)
        ant(x+4,11,h); ant(x+w-5,11,h)
    elif st=='r':  # Trump spire
        box(x,w,int(h*0.72)); box(x+2,w-5,h); ant(x+4,14,h)

wins=[]
for (x,w,h,st) in builds:
    for yy in range(BH-h+4, BH-3, 4):
        for xx in range(x+2, x+w-1, 3):
            if 0<=yy<BH and mask[yy][xx] and mask[yy][xx-1]:
                wins.append((xx,yy,(xx*7+yy*13)%11))

def put(buf,x,y,c):
    if 0<=x<W and 0<=y<H:
        i=(y*W+x)*3; buf[i]=c[0]; buf[i+1]=c[1]; buf[i+2]=c[2]
def text(buf,x,y,msg,fn,c,center=False):
    f=F[fn]
    if center: x=(W-f.w*len(msg))//2
    for i,ch in enumerate(msg):
        if ch==' ': continue
        g=f.glyph(ch)
        for gx in range(f.w):
            for gy in range(f.h):
                k=gx+(gy//8)*f.w
                if k<len(g) and (g[k]>>(gy%8))&1: put(buf,x+gx+i*f.w,y+gy,c)

base=bytearray(W*H*3)
text(base,0,6,"CHICAGO",'font_16x32',CYAN,center=True)
text(base,0,42,"OFFLINE",'font_8x16',WHITE,center=True)
for x in range(W): put(base,x,GROUND+1,DEEP)

FRAMES=40; SPEED=6
frames=[]
for fr in range(FRAMES):
    buf=bytearray(base); off=(fr*SPEED)%STRIP
    for sx in range(W):
        mx=(sx+off)%STRIP
        for by in range(BH):
            if mask[by][mx]: put(buf,sx,BAND_TOP+by,DEEP)
    for (wx,wy,ph) in wins:
        sx=(wx-off)%STRIP
        if sx<W and ((fr//5+ph)%9)!=0: put(buf,sx,BAND_TOP+wy,AMBER)
    for (ax,ay) in willis_ant:
        sx=(ax-off)%STRIP
        if sx<W and (fr//4)%2==0: put(buf,sx,BAND_TOP+ay,AMBER)
    frames.append(Image.frombytes("RGB",(W,H),bytes(buf)))

OUT="/Users/muehlbucks/.openclaw/workspace/agents/chioff/mockups/opengd77/"
big=[f.resize((W*5,H*5),Image.NEAREST) for f in frames]
big[0].save(OUT+"boot_skyline.gif",save_all=True,append_images=big[1:],duration=90,loop=0)
frames[0].save(OUT+"boot_skyline_1x.gif",save_all=True,append_images=frames[1:],duration=90,loop=0)
big[0].save(OUT+"boot_skyline_still.png")
print("frames",len(frames),"windows",len(wins),"strip",STRIP)

