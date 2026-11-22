#!/usr/bin/env python3
"""One mangosteen, split open — procedural renderer (Python stdlib only).

Draws a single perfect mangosteen, split into two halves, on dark slate
under one dramatic light. No image data is embedded; every pixel is
computed from shapes, gradients and highlights at runtime.

Output: /output/entry.png — 1024x1024 PNG, deterministic.
"""
import math
import os
import struct
import zlib

W = H = 1024
OUT = "/output/entry.png"

buf = bytearray(W * H * 3)


# ---------------------------------------------------------------- helpers
def _clamp255(v):
    return 0 if v < 0 else (255 if v > 255 else v)


def lerp3(c0, c1, t):
    return (
        int(c0[0] + (c1[0] - c0[0]) * t),
        int(c0[1] + (c1[1] - c0[1]) * t),
        int(c0[2] + (c1[2] - c0[2]) * t),
    )


def grad_table(c0, c1, n=256):
    return [lerp3(c0, c1, i / (n - 1)) for i in range(n)]


def glow_table(n=256, power=1.6):
    """0..255 falloff: 255 at centre, 0 at edge."""
    return [int(255 * (1.0 - i / (n - 1)) ** power) for i in range(n)]


def ellipse_grad_fill(cx, cy, rx, ry, table, hx, hy):
    """Filled ellipse, radial gradient indexed by squared distance from (hx, hy)."""
    r2 = max(rx, ry) ** 2
    inv = 255.0 / r2
    y0 = max(0, cy - ry)
    y1 = min(H - 1, cy + ry)
    for y in range(y0, y1 + 1):
        ny = (y - cy) / ry
        rest = 1.0 - ny * ny
        if rest <= 0:
            continue
        dx = int(rx * math.sqrt(rest))
        x0 = max(0, cx - dx)
        x1 = min(W - 1, cx + dx)
        i = (y * W + x0) * 3
        ddy = y - hy
        ddy2 = ddy * ddy
        for x in range(x0, x1 + 1):
            ddx = x - hx
            t = int((ddx * ddx + ddy2) * inv)
            if t > 255:
                t = 255
            c = table[t]
            buf[i] = c[0]
            buf[i + 1] = c[1]
            buf[i + 2] = c[2]
            i += 3


def disc_grad(cx, cy, r, table, hx, hy):
    """Filled disc, radial gradient indexed by squared distance from (hx, hy)."""
    r2 = r * r
    inv = 255.0 / r2
    y0 = max(0, cy - r)
    y1 = min(H - 1, cy + r)
    for y in range(y0, y1 + 1):
        dy = y - cy
        rest = r2 - dy * dy
        if rest < 0:
            continue
        dx = int(math.sqrt(rest))
        x0 = max(0, cx - dx)
        x1 = min(W - 1, cx + dx)
        i = (y * W + x0) * 3
        ddy = y - hy
        ddy2 = ddy * ddy
        for x in range(x0, x1 + 1):
            ddx = x - hx
            t = int((ddx * ddx + ddy2) * inv)
            if t > 255:
                t = 255
            c = table[t]
            buf[i] = c[0]
            buf[i + 1] = c[1]
            buf[i + 2] = c[2]
            i += 3


def disc_soft(cx, cy, rx, ry, color, a0, a1):
    """Elliptical soft blob: alpha falls from a0 (centre) to a1 (edge)."""
    cr, cg, cb = color
    y0 = max(0, cy - ry)
    y1 = min(H - 1, cy + ry)
    for y in range(y0, y1 + 1):
        ny = (y - cy) / ry
        rest = 1.0 - ny * ny
        if rest <= 0:
            continue
        dx = int(rx * math.sqrt(rest))
        x0 = max(0, cx - dx)
        x1 = min(W - 1, cx + dx)
        i = (y * W + x0) * 3
        for x in range(x0, x1 + 1):
            nx = (x - cx) / rx
            v = nx * nx + ny * ny
            if v > 1.0:
                continue
            a = a0 + (a1 - a0) * v
            if a <= 0.003:
                i += 3
                continue
            buf[i] = int(buf[i] + (cr - buf[i]) * a)
            buf[i + 1] = int(buf[i + 1] + (cg - buf[i + 1]) * a)
            buf[i + 2] = int(buf[i + 2] + (cb - buf[i + 2]) * a)
            i += 3


def ring_band(cx, cy, r0, r1, color, alpha, ang0=None, ang1=None):
    """Blend a ring (optionally restricted to an angle range, degrees,
    0 = east, 90 = north, screen y down)."""
    cr, cg, cb = color
    r0sq = r0 * r0
    r1sq = r1 * r1
    y0 = max(0, cy - r1)
    y1 = min(H - 1, cy + r1)
    for y in range(y0, y1 + 1):
        dy = y - cy
        x0 = max(0, cx - r1)
        x1 = min(W - 1, cx + r1)
        i = (y * W + x0) * 3
        for x in range(x0, x1 + 1):
            dx = x - cx
            d2 = dx * dx + dy * dy
            if d2 < r0sq or d2 > r1sq:
                i += 3
                continue
            if ang0 is not None:
                ang = math.degrees(math.atan2(-dy, dx)) % 360.0
                if not (ang0 <= ang <= ang1):
                    i += 3
                    continue
            buf[i] = int(buf[i] + (cr - buf[i]) * alpha)
            buf[i + 1] = int(buf[i + 1] + (cg - buf[i + 1]) * alpha)
            buf[i + 2] = int(buf[i + 2] + (cb - buf[i + 2]) * alpha)
            i += 3


def fill_poly(points, color):
    """Scanline fill of a convex polygon."""
    cr, cg, cb = color
    ys = [p[1] for p in points]
    y0 = max(0, int(min(ys)))
    y1 = min(H - 1, int(max(ys)))
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
        xa, xb = int(min(xs)), int(max(xs))
        xa = max(0, xa)
        xb = min(W - 1, xb)
        i = (y * W + xa) * 3
        for _ in range(xa, xb + 1):
            buf[i] = cr
            buf[i + 1] = cg
            buf[i + 2] = cb
            i += 3


def ellipse_grad(cx, cy, a, b, ang_deg, c_top, c_bot, c_edge):
    """Rotated ellipse petal: vertical gradient + darker rim near edge."""
    ang = math.radians(-ang_deg)
    ca = math.cos(ang)
    sa = math.sin(ang)
    y0 = max(0, int(cy - max(a, b) - 2))
    y1 = min(H - 1, int(cy + max(a, b) + 2))
    x0 = max(0, int(cx - max(a, b) - 2))
    x1 = min(W - 1, int(cx + max(a, b) + 2))
    ia = 1.0 / a
    ib = 1.0 / b
    for y in range(y0, y1 + 1):
        dy = y - cy
        i = (y * W + x0) * 3
        for x in range(x0, x1 + 1):
            dx = x - cx
            rx = dx * ca - dy * sa
            ry = dx * sa + dy * ca
            u = rx * ia
            v = ry * ib
            q = u * u + v * v
            if q > 1.0:
                i += 3
                continue
            # vertical shading: top lighter, bottom warmer/darker
            t = 0.5 + 0.5 * v
            r = int(c_top[0] + (c_bot[0] - c_top[0]) * t)
            g = int(c_top[1] + (c_bot[1] - c_top[1]) * t)
            bl = int(c_top[2] + (c_bot[2] - c_top[2]) * t)
            # darken toward the rim (stronger: segments must read individually)
            edge = q * q * 0.55
            r = int(r + (c_edge[0] - r) * edge)
            g = int(g + (c_edge[1] - g) * edge)
            bl = int(bl + (c_edge[2] - bl) * edge)
            buf[i] = r
            buf[i + 1] = g
            buf[i + 2] = bl
            i += 3


def droplet(cx, cy, r):
    """A bright water droplet: pale body, bright specular dot, dark base."""
    # body: pale blue-white, semi-transparent look via soft alpha
    disc_soft(cx, cy, r, r, (205, 228, 245), 0.72, 0.18)
    # lower shade
    disc_soft(cx, cy + r // 3, int(r * 0.7), int(r * 0.55),
              (90, 120, 150), 0.28, 0.0)
    # specular highlight
    disc_soft(cx - r // 3, cy - r // 3, max(2, r // 3), max(2, r // 3),
              (255, 255, 255), 0.95, 0.0)
    # thin bright rim on the upper-left arc
    ring_band(cx, cy, int(r * 0.78), r, (255, 255, 255), 0.35, 80, 190)


# ---------------------------------------------------------------- scene
def draw_background():
    top = (11, 13, 20)
    bottom = (26, 28, 38)
    glow = glow_table()
    # spotlight centre and radius
    sx, sy, sr = 512, 360, 600
    inv = 255.0 / (sr * sr)
    warm = (232, 214, 176)
    for y in range(H):
        t = y / (H - 1)
        br = int(top[0] + (bottom[0] - top[0]) * t)
        bg = int(top[1] + (bottom[1] - top[1]) * t)
        bb = int(top[2] + (bottom[2] - top[2]) * t)
        dy = y - sy
        dy2 = dy * dy
        i = (y * W) * 3
        for x in range(W):
            dx = x - sx
            g = int((dx * dx + dy2) * inv)
            if g > 255:
                g = 255
            gl = glow[g]
            if gl:
                f = gl / 255.0 * 0.42
                buf[i] = int(br + (warm[0] - br) * f)
                buf[i + 1] = int(bg + (warm[1] - bg) * f)
                buf[i + 2] = int(bb + (warm[2] - bb) * f)
            else:
                buf[i] = br
                buf[i + 1] = bg
                buf[i + 2] = bb
            i += 3


def draw_slate():
    # a low tabletop plane: only the top of a wide ellipse shows,
    # so it reads as a surface with a horizon, not a floating disc
    ellipse_grad_fill(512, 1030, 600, 280,
                      grad_table((52, 55, 68), (18, 20, 28)),
                      512, 800)
    # subtle sheen where the light pools on the slate
    disc_soft(512, 800, 330, 70, (130, 140, 160), 0.10, 0.0)


def draw_rind_half(cx, cy, r):
    """Left half: the outer purple rind dome, with calyx on top."""
    # dark outer rim
    disc_grad(cx, cy, r, grad_table((58, 22, 66), (38, 14, 44)), cx - 40, cy - 60)
    # main body gradient: light from upper-left, deeper moodier purple
    disc_grad(cx, cy, r - 6,
              grad_table((128, 62, 138), (44, 16, 52)),
              cx - 70, cy - 80)
    # deep shadow toward lower-right
    disc_soft(cx + 70, cy + 80, r // 2, r // 2, (20, 6, 26), 0.38, 0.0)
    # glossy highlight upper-left: tighter, crescent-like (not a smudge)
    disc_soft(cx - 95, cy - 105, 58, 30, (198, 142, 208), 0.16, 0.0)
    disc_soft(cx - 110, cy - 120, 34, 20, (228, 192, 232), 0.26, 0.0)
    # bright rim light along the top-left edge
    ring_band(cx, cy, r - 9, r - 2, (196, 140, 205), 0.55, 75, 185)
    # faint rim light lower-right (bounce)
    ring_band(cx, cy, r - 7, r - 2, (120, 70, 130), 0.25, 285, 345)
    # deterministic mottling: tiny darker speckles on the rind
    seed = 1234567
    for _ in range(46):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        ang = (seed % 360) * math.pi / 180.0
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        rr = (seed % 82 + 8) / 100.0 * (r - 18)
        px = int(cx + math.cos(ang) * rr)
        py = int(cy + math.sin(ang) * rr * 0.92)
        pr = 2 + (seed % 4)
        disc_soft(px, py, pr, pr, (30, 10, 36), 0.30, 0.0)
    # calyx: four pointed leaves in a star + short stem (classic mangosteen top)
    cal_y = cy - r + 6
    disc_soft(cx, cal_y - 24, 12, 30, (58, 92, 40), 0.9, 0.0)  # stem base
    for k, ang_deg in enumerate((-58, -20, 20, 58)):
        a = math.radians(ang_deg)
        tipx = cx + int(math.sin(a) * 52)
        tipy = cal_y - 6 - int(math.cos(a) * 44)
        # leaf as a pointed triangle, base straddling the centre
        px = math.cos(a)
        py = -math.sin(a)
        bx, by = cx, cal_y - 4
        leaf = (110, 158, 76) if k % 2 == 0 else (88, 136, 60)
        fill_poly([
            (tipx, tipy),
            (int(bx + px * 13 - py * 0 + math.sin(a) * 0), int(by + py * 13)),
            (int(bx - px * 13), int(by - py * 13)),
        ], leaf)
    disc_grad(cx, cal_y - 4, 11, grad_table((96, 140, 66), (52, 84, 36)),
              cx, cal_y - 8)


def draw_flesh_half(cx, cy, r):
    """Right half: the cut face — white segments inside a purple rind ring."""
    # contact shadow cast onto the rind half (drawn before this disc)
    disc_soft(cx - 150, cy + 10, r, r, (10, 6, 12), 0.30, 0.0)
    # rind ring
    disc_grad(cx, cy, r, grad_table((140, 76, 148), (50, 20, 58)),
              cx - 70, cy - 80)
    ring_band(cx, cy, r - 8, r - 2, (190, 132, 198), 0.45, 60, 170)
    # cut-edge ring: paler lilac-pink where the rind was sliced
    disc_grad(cx, cy, r - 14, grad_table((168, 108, 158), (120, 66, 116)),
              cx - 40, cy - 50)
    # white flesh base
    flesh_r = r - 34
    disc_grad(cx, cy, flesh_r,
              grad_table((255, 250, 242), (238, 222, 200)),
              cx - 30, cy - 40)
    # six segments as glossy petals
    n_seg = 6
    for k in range(n_seg):
        ang = -90 + k * (360.0 / n_seg)
        a = math.radians(ang)
        pcx = cx + int(math.cos(a) * flesh_r * 0.48)
        pcy = cy + int(math.sin(a) * flesh_r * 0.48)
        ellipse_grad(pcx, pcy, int(flesh_r * 0.66), int(flesh_r * 0.38),
                     ang + 90,
                     (255, 253, 247), (240, 224, 200), (196, 168, 138))
    # faint pink blush just inside the flesh edge
    ring_band(cx, cy, flesh_r - 16, flesh_r - 2, (232, 198, 186), 0.16)
    # separators: thin pale lines radiating between segments
    for k in range(n_seg):
        ang = -90 + (k + 0.5) * (360.0 / n_seg)
        a = math.radians(ang)
        ex = cx + int(math.cos(a) * (flesh_r - 4))
        ey = cy + int(math.sin(a) * (flesh_r - 4))
        # wedge: two offset lines meeting near the centre
        px = math.cos(a + math.pi / 2)
        py = math.sin(a + math.pi / 2)
        fill_poly([
            (cx + int(px * 6), cy + int(py * 6)),
            (cx - int(px * 6), cy - int(py * 6)),
            (ex - int(px * 3), ey - int(py * 3)),
            (ex + int(px * 3), ey + int(py * 3)),
        ], (196, 170, 140))
    # centre core where segments meet
    disc_grad(cx, cy, 20, grad_table((250, 238, 222), (226, 204, 182)),
              cx - 4, cy - 5)
    disc_soft(cx, cy, 7, 7, (196, 168, 142), 0.5, 0.0)
    # gloss: soft light sweeping the upper segments
    disc_soft(cx - 55, cy - 75, 110, 60, (255, 255, 255), 0.22, 0.0)
    disc_soft(cx + 70, cy - 40, 60, 34, (255, 255, 255), 0.14, 0.0)
    # specular sparkles on the flesh
    for sx, sy, sr in ((cx - 88, cy - 62, 7), (cx + 30, cy - 96, 5),
                       (cx + 96, cy + 18, 6), (cx - 20, cy + 88, 5)):
        disc_soft(sx, sy, sr, sr, (255, 255, 255), 0.85, 0.0)


def draw_droplets():
    # on the rind
    droplet(268, 428, 10)
    droplet(392, 318, 8)
    droplet(452, 668, 9)
    # on the white flesh
    droplet(668, 428, 9)
    droplet(742, 560, 7)
    # on the slate beside the fruit (must sit below the slate horizon ~y800)
    droplet(845, 862, 8)
    droplet(205, 868, 7)


def vignette():
    table = [int(255 * (1.0 - 0.42 * (i / 255.0) ** 1.7)) for i in range(256)]
    maxd2 = 512 * 512 + 512 * 512
    inv = 255.0 / maxd2
    for y in range(H):
        dy = y - 512
        dy2 = dy * dy
        i = (y * W) * 3
        for x in range(W):
            dx = x - 512
            t = int((dx * dx + dy2) * inv)
            f = table[t]
            if f != 255:
                buf[i] = (buf[i] * f) >> 8
                buf[i + 1] = (buf[i + 1] * f) >> 8
                buf[i + 2] = (buf[i + 2] * f) >> 8
            i += 3


def render():
    draw_background()
    draw_slate()
    # soft shadow pooling under the fruit
    disc_soft(512, 838, 360, 70, (0, 0, 0), 0.55, 0.0)
    draw_rind_half(330, 520, 232)
    draw_flesh_half(700, 520, 232)
    draw_droplets()
    vignette()


# ---------------------------------------------------------------- PNG out
def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += buf[y * W * 3:(y + 1) * W * 3]
    comp = zlib.compress(bytes(raw), 6)

    def chunk(typ, data):
        out = struct.pack(">I", len(data)) + typ + data
        out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    render()
    n = write_png(OUT)
    print(f"wrote {OUT}: {W}x{H}, {n} bytes")


if __name__ == "__main__":
    main()
