#!/usr/bin/env python3
"""One mangosteen, split open.

Draws a single perfect mangosteen -- one half the deep-purple rind dome
with its green calyx star, the other half the cut face with six glistening
white segments -- on dark slate under one warm dramatic light.

Stdlib only. Everything is drawn procedurally at runtime (shapes, radial
gradients, highlights, soft shadows, specular droplets) and the PNG is
encoded by hand with zlib + struct. Deterministic: fixed seed, no clock,
no network, no file input.

Usage: python3 main.py  ->  writes /output/entry.png (1024x1024)
"""

import math
import os
import random
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------------------
# Pixel buffer (RGB, row-major bytearray)
# ---------------------------------------------------------------------------
buf = bytearray(W * H * 3)


def blend_px(x, y, r, g, b, a):
    """Blend one pixel with coverage a (0..1)."""
    if 0 <= x < W and 0 <= y < H and a > 0.0:
        i = (y * W + x) * 3
        if a >= 1.0:
            buf[i] = r
            buf[i + 1] = g
            buf[i + 2] = b
        else:
            ia = 1.0 - a
            buf[i] = int(buf[i] * ia + r * a + 0.5)
            buf[i + 1] = int(buf[i + 1] * ia + g * a + 0.5)
            buf[i + 2] = int(buf[i + 2] * ia + b * a + 0.5)


def lerp(a, b, t):
    return a + (b - a) * t


def clamp01(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def smooth(t):
    t = clamp01(t)
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------
def disc(cx, cy, r, color, alpha=1.0):
    """Solid filled circle."""
    r0, g0, b0 = color
    x0 = max(0, int(cx - r))
    x1 = min(W - 1, int(cx + r) + 1)
    y0 = max(0, int(cy - r))
    y1 = min(H - 1, int(cy + r) + 1)
    r2 = r * r
    for y in range(y0, y1 + 1):
        dy = y - cy
        dy2 = dy * dy
        row = y * W * 3
        for x in range(x0, x1 + 1):
            dx = x - cx
            if dx * dx + dy2 <= r2:
                i = row + x * 3
                if alpha >= 1.0:
                    buf[i] = r0
                    buf[i + 1] = g0
                    buf[i + 2] = b0
                else:
                    ia = 1.0 - alpha
                    buf[i] = int(buf[i] * ia + r0 * alpha + 0.5)
                    buf[i + 1] = int(buf[i + 1] * ia + g0 * alpha + 0.5)
                    buf[i + 2] = int(buf[i + 2] * ia + b0 * alpha + 0.5)


def radial_disc(cx, cy, r, inner, outer, alpha=1.0, power=1.0, cx2=None, cy2=None,
                fade=False):
    """Circle centred on (cx, cy), shaded from `inner` at (cx2, cy2) to
    `outer` at the rim. With fade=True the alpha also falls to zero at the
    rim, so overlays (glow, shadow, vignette) leave no hard circular edge.
    Containment is always the circle around (cx, cy); only the shading
    centre is offset -- the two must never be confused."""
    if cx2 is None:
        cx2, cy2 = cx, cy
    ir, ig, ib = inner
    orr, og, ob = outer
    x0 = max(0, int(cx - r))
    x1 = min(W - 1, int(cx + r) + 1)
    y0 = max(0, int(cy - r))
    y1 = min(H - 1, int(cy + r) + 1)
    r2 = r * r
    for y in range(y0, y1 + 1):
        dy = y - cy
        dy2 = dy * dy
        dys = y - cy2
        row = y * W * 3
        for x in range(x0, x1 + 1):
            dx = x - cx
            d2 = dx * dx + dy2
            if d2 <= r2:
                dxs = x - cx2
                ds2 = dxs * dxs + dys * dys
                t = math.sqrt(ds2) / r
                if t > 1.0:
                    t = 1.0
                t = t ** power
                rr = int(lerp(ir, orr, t) + 0.5)
                gg = int(lerp(ig, og, t) + 0.5)
                bb = int(lerp(ib, ob, t) + 0.5)
                a = alpha
                if fade:
                    tg = math.sqrt(d2) / r
                    a = alpha * (1.0 - tg)
                    if a <= 0.0:
                        continue
                i = row + x * 3
                if a >= 1.0:
                    buf[i] = rr
                    buf[i + 1] = gg
                    buf[i + 2] = bb
                else:
                    ia = 1.0 - a
                    buf[i] = int(buf[i] * ia + rr * a + 0.5)
                    buf[i + 1] = int(buf[i + 1] * ia + gg * a + 0.5)
                    buf[i + 2] = int(buf[i + 2] * ia + bb * a + 0.5)


def ellipse(cx, cy, rx, ry, color, alpha=1.0):
    """Solid filled ellipse."""
    r0, g0, b0 = color
    x0 = max(0, int(cx - rx))
    x1 = min(W - 1, int(cx + rx) + 1)
    y0 = max(0, int(cy - ry))
    y1 = min(H - 1, int(cy + ry) + 1)
    for y in range(y0, y1 + 1):
        dy = (y - cy) / ry
        dy2 = dy * dy
        if dy2 > 1.0:
            continue
        half = rx * math.sqrt(1.0 - dy2)
        xa = max(x0, int(cx - half))
        xb = min(x1, int(cx + half))
        row = y * W * 3
        for x in range(xa, xb + 1):
            i = row + x * 3
            if alpha >= 1.0:
                buf[i] = r0
                buf[i + 1] = g0
                buf[i + 2] = b0
            else:
                ia = 1.0 - alpha
                buf[i] = int(buf[i] * ia + r0 * alpha + 0.5)
                buf[i + 1] = int(buf[i + 1] * ia + g0 * alpha + 0.5)
                buf[i + 2] = int(buf[i + 2] * ia + b0 * alpha + 0.5)


def radial_ellipse(cx, cy, rx, ry, inner, outer, alpha=1.0, power=1.0):
    """Ellipse shaded from `inner` at its centre to `outer` at the rim."""
    ir, ig, ib = inner
    orr, og, ob = outer
    x0 = max(0, int(cx - rx))
    x1 = min(W - 1, int(cx + rx) + 1)
    y0 = max(0, int(cy - ry))
    y1 = min(H - 1, int(cy + ry) + 1)
    for y in range(y0, y1 + 1):
        dy = (y - cy) / ry
        dy2 = dy * dy
        if dy2 > 1.0:
            continue
        half = rx * math.sqrt(1.0 - dy2)
        xa = max(x0, int(cx - half))
        xb = min(x1, int(cx + half))
        row = y * W * 3
        for x in range(xa, xb + 1):
            dx = (x - cx) / rx
            d = math.sqrt(dx * dx + dy2)
            t = d ** power
            rr = int(lerp(ir, orr, t) + 0.5)
            gg = int(lerp(ig, og, t) + 0.5)
            bb = int(lerp(ib, ob, t) + 0.5)
            i = row + x * 3
            if alpha >= 1.0:
                buf[i] = rr
                buf[i + 1] = gg
                buf[i + 2] = bb
            else:
                ia = 1.0 - alpha
                buf[i] = int(buf[i] * ia + rr * alpha + 0.5)
                buf[i + 1] = int(buf[i + 1] * ia + gg * alpha + 0.5)
                buf[i + 2] = int(buf[i + 2] * ia + bb * alpha + 0.5)


def poly(points, color, alpha=1.0):
    """Filled polygon (scanline fill)."""
    r0, g0, b0 = color
    ys = [p[1] for p in points]
    y0 = max(0, int(min(ys)))
    y1 = min(H - 1, int(max(ys)) + 1)
    n = len(points)
    for y in range(y0, y1 + 1):
        xs = []
        for k in range(n):
            x1, y1p = points[k]
            x2, y2p = points[(k + 1) % n]
            if (y1p <= y < y2p) or (y2p <= y < y1p):
                t = (y - y1p) / (y2p - y1p)
                xs.append(x1 + t * (x2 - x1))
        if len(xs) < 2:
            continue
        xs.sort()
        for j in range(0, len(xs) - 1, 2):
            xa = max(0, int(xs[j]))
            xb = min(W - 1, int(xs[j + 1]))
            row = y * W * 3
            for x in range(xa, xb + 1):
                i = row + x * 3
                if alpha >= 1.0:
                    buf[i] = r0
                    buf[i + 1] = g0
                    buf[i + 2] = b0
                else:
                    ia = 1.0 - alpha
                    buf[i] = int(buf[i] * ia + r0 * alpha + 0.5)
                    buf[i + 1] = int(buf[i + 1] * ia + g0 * alpha + 0.5)
                    buf[i + 2] = int(buf[i + 2] * ia + b0 * alpha + 0.5)


def thick_line(x1, y1, x2, y2, w, color, alpha=1.0):
    """A tapered line drawn as a thin quad."""
    dx = x2 - x1
    dy = y2 - y1
    ln = math.hypot(dx, dy) or 1.0
    nx = -dy / ln * w / 2.0
    ny = dx / ln * w / 2.0
    poly([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny),
          (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)], color, alpha)


def rotated_ellipse(cx, cy, a, b, ang, inner, outer, alpha=1.0, power=1.0,
                    sector=None):
    """Ellipse rotated by `ang` radians, centre-shaded inner -> outer.
    With sector=(sx, sy, sang, half) only pixels whose angle from (sx, sy)
    lies within half radians of sang are painted -- used to clip each
    mangosteen segment to its own 60-degree wedge so neighbouring lobes
    meet cleanly instead of overlapping into a pinwheel."""
    ir, ig, ib = inner
    orr, og, ob = outer
    ca = math.cos(ang)
    sa = math.sin(ang)
    ext = max(a, b)
    x0 = max(0, int(cx - ext))
    x1 = min(W - 1, int(cx + ext) + 1)
    y0 = max(0, int(cy - ext))
    y1 = min(H - 1, int(cy + ext) + 1)
    if sector is not None:
        scx, scy, sang, half = sector
    for y in range(y0, y1 + 1):
        dy = y - cy
        row = y * W * 3
        for x in range(x0, x1 + 1):
            dx = x - cx
            u = (dx * ca + dy * sa) / a
            v = (-dx * sa + dy * ca) / b
            d2 = u * u + v * v
            if d2 <= 1.0:
                if sector is not None:
                    pa = math.atan2(y - scy, x - scx) - sang
                    while pa > math.pi:
                        pa -= 2 * math.pi
                    while pa < -math.pi:
                        pa += 2 * math.pi
                    if abs(pa) > half:
                        continue
                t = math.sqrt(d2) ** power
                rr = int(lerp(ir, orr, t) + 0.5)
                gg = int(lerp(ig, og, t) + 0.5)
                bb = int(lerp(ib, ob, t) + 0.5)
                i = row + x * 3
                if alpha >= 1.0:
                    buf[i] = rr
                    buf[i + 1] = gg
                    buf[i + 2] = bb
                else:
                    ia = 1.0 - alpha
                    buf[i] = int(buf[i] * ia + rr * alpha + 0.5)
                    buf[i + 1] = int(buf[i + 1] * ia + gg * alpha + 0.5)
                    buf[i + 2] = int(buf[i + 2] * ia + bb * alpha + 0.5)


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------
rng = random.Random(20261123)

# Warm key light comes from the upper left.
LX, LY = -0.55, -0.75  # light direction (unit-ish)


def background():
    # Vertical charcoal gradient, slightly warmer toward the middle.
    top = (16, 16, 21)
    mid = (44, 38, 34)
    bot = (13, 13, 17)
    for y in range(H):
        t = y / (H - 1)
        if t < 0.45:
            k = t / 0.45
            r = int(lerp(top[0], mid[0], k) + 0.5)
            g = int(lerp(top[1], mid[1], k) + 0.5)
            b = int(lerp(top[2], mid[2], k) + 0.5)
        else:
            k = (t - 0.45) / 0.55
            r = int(lerp(mid[0], bot[0], k) + 0.5)
            g = int(lerp(mid[1], bot[1], k) + 0.5)
            b = int(lerp(mid[2], bot[2], k) + 0.5)
        row = y * W * 3
        for x in range(W):
            i = row + x * 3
            buf[i] = r
            buf[i + 1] = g
            buf[i + 2] = b
    # Warm glow behind the fruit, centred upper-middle (faded at the rim
    # so no circular edge shows against the wall).
    radial_disc(560, 350, 520, (96, 74, 52), (16, 16, 21), alpha=0.55,
                power=1.6, fade=True)


def slate():
    # Dark slate plane the fruit rests on.
    for y in range(748, H):
        t = (y - 748) / (H - 748)
        r = int(lerp(38, 18, t) + 0.5)
        g = int(lerp(41, 20, t) + 0.5)
        b = int(lerp(48, 24, t) + 0.5)
        row = y * W * 3
        for x in range(W):
            i = row + x * 3
            buf[i] = r
            buf[i + 1] = g
            buf[i + 2] = b
    # Horizon line where the wall meets the slate.
    thick_line(0, 748, W, 748, 2, (70, 74, 86), 0.35)
    # Warm pool of light on the slate under the fruit.
    radial_ellipse(512, 830, 430, 105, (96, 80, 62), (30, 32, 40),
                   alpha=0.5, power=1.4)
    # Cool sheen streak across the slate.
    radial_ellipse(700, 900, 300, 42, (64, 70, 86), (22, 24, 30),
                   alpha=0.35, power=1.6)


def contact_shadow(cx, cy, rx, ry, strength=0.45):
    # Layered soft shadow: three ellipses, darkest in the middle.
    for s, a in ((1.15, 0.18), (1.0, 0.30), (0.82, 0.42)):
        ellipse(cx, cy, rx * s, ry * s, (0, 0, 0), strength * a / 0.42)


def droplet(cx, cy, r):
    """A glistening water droplet: bright core, pale rim, hot highlight."""
    radial_disc(cx, cy, r, (235, 245, 255), (120, 150, 185),
                alpha=0.85, power=0.7)
    disc(cx, cy, r * 0.92, (200, 220, 240), 0.25)
    disc(cx - r * 0.32, cy - r * 0.36, r * 0.30, (255, 255, 255), 0.95)
    disc(cx + r * 0.28, cy + r * 0.30, r * 0.14, (255, 255, 255), 0.5)


def calyx(cx, cy):
    """The pointed green star on top of the rind dome."""
    # Five pointed leaves radiating upward.
    for k in range(5):
        ang = math.radians(-90 + (k - 2) * 26)
        tipx = cx + math.cos(ang) * 58
        tipy = cy + math.sin(ang) * 58
        px = math.cos(ang + math.pi / 2)
        py = math.sin(ang + math.pi / 2)
        base = 15
        poly([(cx + px * base, cy + py * base),
              (tipx, tipy),
              (cx - px * base, cy - py * base)], (74, 122, 44))
        # Lighter inner vein on each leaf.
        tipx2 = cx + math.cos(ang) * 44
        tipy2 = cy + math.sin(ang) * 44
        poly([(cx + px * 6, cy + py * 6),
              (tipx2, tipy2),
              (cx - px * 6, cy - py * 6)], (122, 170, 80), 0.85)
    # Short woody stem.
    poly([(cx - 7, cy - 26), (cx + 7, cy - 26),
          (cx + 5, cy + 2), (cx - 5, cy + 2)], (88, 66, 38))
    disc(cx, cy, 11, (58, 96, 36))
    disc(cx - 3, cy - 3, 4, (140, 185, 95), 0.9)


def rind_dome(cx, cy, r):
    """Left half: the deep-purple rind dome, lit from the upper left."""
    # Base sphere shading, highlight offset toward the light.
    radial_disc(cx, cy, r, (150, 66, 168), (46, 14, 58),
                alpha=1.0, power=1.15, cx2=cx - 62, cy2=cy - 78)
    # Deep shadow creeping in from the lower right (faded at the rim).
    radial_disc(cx + 78, cy + 88, r * 0.85, (20, 6, 28), (46, 14, 58),
                alpha=0.55, power=1.4, fade=True)
    # Hot specular bloom upper left.
    radial_ellipse(cx - 96, cy - 104, 78, 46, (214, 158, 224), (150, 66, 168),
                   alpha=0.55, power=1.2)
    # Pale rim light along the upper-left edge (dense small dots so the
    # arc reads as a smooth highlight, not a beaded outline).
    for k in range(120):
        a = math.radians(150 + k * 1.0)
        px = cx + math.cos(a) * (r - 4)
        py = cy + math.sin(a) * (r - 4)
        disc(px, py, 4, (196, 150, 208), 0.16)
    # Rind speckle: tiny darker pores, deterministic.
    for _ in range(110):
        a = rng.uniform(0, 2 * math.pi)
        d = math.sqrt(rng.uniform(0, 1)) * (r - 14)
        px = cx + math.cos(a) * d
        py = cy + math.sin(a) * d
        rad = rng.uniform(1.0, 3.2)
        disc(px, py, rad, (30, 8, 40), rng.uniform(0.10, 0.28))
    # A few pale freckles catching the light.
    for _ in range(18):
        a = rng.uniform(0, 2 * math.pi)
        d = math.sqrt(rng.uniform(0, 1)) * (r - 20)
        px = cx + math.cos(a) * d
        py = cy + math.sin(a) * d
        disc(px, py, rng.uniform(0.8, 1.8), (210, 170, 215), 0.30)
    # Thin darker outline to seat the dome on the background.
    for k in range(240):
        a = k / 240.0 * 2 * math.pi
        px = cx + math.cos(a) * (r - 1)
        py = cy + math.sin(a) * (r - 1)
        disc(px, py, 2, (24, 8, 32), 0.5)


def cut_face(cx, cy, r):
    """Right half: the cut face -- lilac rind ring, six white segments."""
    # Outer rind ring (dark purple) and lilac inner ring.
    disc(cx, cy, r, (58, 20, 72))
    radial_disc(cx, cy, r - 8, (132, 74, 150), (74, 30, 88),
                alpha=1.0, power=1.3, cx2=cx - 40, cy2=cy - 52)
    disc(cx, cy, r - 30, (176, 138, 186))          # lilac ring
    disc(cx, cy, r - 44, (196, 162, 204), 0.6)     # lilac inner glow
    # Cream flesh bed.
    radial_disc(cx, cy, r - 52, (252, 240, 224), (226, 204, 182),
                alpha=1.0, power=1.1, cx2=cx - 30, cy2=cy - 40)

    # Six plump segments, each a rotated lobe clipped to its own 60-degree
    # wedge, brightest toward the light. The lobes are big enough to touch
    # each other and the lilac ring, so the flesh reads as one juicy cut
    # face; the wedge clip keeps them meeting cleanly at the centre like
    # real segments instead of overlapping into a pinwheel.
    for k in range(6):
        ang = math.radians(-90 + k * 60)
        scx = cx + math.cos(ang) * 76
        scy = cy + math.sin(ang) * 76
        sector = (cx, cy, ang, math.radians(30))
        # Hairline rim: only 3px larger and barely darker than the flesh.
        rotated_ellipse(scx, scy, 91, 71, ang + math.pi / 2,
                        (228, 208, 188), (222, 200, 178), alpha=1.0,
                        sector=sector)
        # The glistening segment itself.
        rotated_ellipse(scx, scy, 88, 68, ang + math.pi / 2,
                        (255, 252, 246), (234, 214, 190),
                        alpha=1.0, power=0.85, sector=sector)
        # Wet sheen: bright wash toward the upper-left of the lobe.
        radial_disc(scx - 18, scy - 20, 40, (255, 255, 255), (255, 252, 246),
                    alpha=0.45, power=1.2, fade=True)
        # Specular sparkle.
        disc(scx - 26, scy - 26, 5, (255, 255, 255), 0.85)
        disc(scx + 20, scy + 12, 3, (255, 255, 255), 0.6)

    # Creases between segments: short, soft, and low-contrast -- they
    # separate the lobes without drawing a diagram over the flesh.
    for k in range(6):
        ang = math.radians(-60 + k * 60)
        x1 = cx + math.cos(ang) * 34
        y1 = cy + math.sin(ang) * 34
        x2 = cx + math.cos(ang) * (r - 100)
        y2 = cy + math.sin(ang) * (r - 100)
        thick_line(x1, y1, x2, y2, 5, (204, 176, 146), 0.45)
        thick_line(x1, y1, x2, y2, 2, (188, 156, 124), 0.4)

    # Central hub: the pale core the segments grow from.
    radial_disc(cx, cy, 30, (255, 250, 240), (224, 200, 176),
                alpha=1.0, power=1.0)
    disc(cx - 7, cy - 8, 7, (255, 255, 255), 0.8)

    # Rim light on the upper-left of the rind ring (dense, smooth).
    for k in range(100):
        a = math.radians(150 + k * 1.0)
        px = cx + math.cos(a) * (r - 5)
        py = cy + math.sin(a) * (r - 5)
        disc(px, py, 4, (206, 158, 216), 0.18)


def vignette():
    # Darken the four corners so the eye stays on the fruit. Each disc
    # fades to zero alpha at its rim, so no circular edge shows.
    for ccx, ccy in ((0, 0), (W, 0), (0, H), (W, H)):
        for rr, aa in ((560, 0.10), (460, 0.16), (360, 0.20), (260, 0.22)):
            radial_disc(ccx, ccy, rr, (0, 0, 0), (0, 0, 0),
                        alpha=aa, power=1.0, fade=True)


def draw():
    background()
    slate()
    # Shadows first so the fruit sits in them.
    contact_shadow(330, 742, 200, 30)
    contact_shadow(700, 742, 205, 30)
    # Left: whole rind dome with calyx.
    rind_dome(330, 512, 212)
    calyx(330, 296)
    # Right: cut face.
    cut_face(700, 512, 218)
    # Droplets: on the rind, on the cut flesh, on the slate.
    droplet(398, 372, 11)
    droplet(262, 470, 8)
    droplet(428, 648, 9)
    droplet(664, 470, 8)
    droplet(742, 586, 7)
    droplet(196, 884, 9)
    droplet(838, 876, 8)
    vignette()


# ---------------------------------------------------------------------------
# PNG encoder (stdlib only)
# ---------------------------------------------------------------------------
def _chunk(typ, data):
    out = struct.pack(">I", len(data)) + typ + data
    out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return out


def write_png(path):
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += buf[y * W * 3:(y + 1) * W * 3]
    idat = zlib.compress(bytes(raw), 9)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", idat)
    png += _chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    draw()
    size = write_png("/output/entry.png")
    print("wrote /output/entry.png: %dx%d, %d bytes" % (W, H, size))


if __name__ == "__main__":
    main()
