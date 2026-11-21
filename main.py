# Passport spread of the Republic of Talvaria, a country that isn't there.
# Draws one open passport spread (data page + visas page) as a PNG.
# Pure stdlib: pixels are rasterised by hand and encoded with zlib.
# No network, no dependencies, deterministic output.
import os
import struct
import zlib

W, H = 1024, 700
OUT = os.environ.get("ENTRY_OUTPUT", "/output/entry.png")

# ---- palette: a working document, not a poster -------------------------------
PAPER   = (242, 236, 220)   # cream security paper
PAPER2  = (236, 229, 210)   # slightly darker cream
INK     = (28, 43, 74)      # navy document ink
INK_SOFT= (74, 84, 110)     # secondary ink
GREY    = (120, 116, 104)   # small-print grey
RULE    = (28, 43, 74)
BURG    = (122, 31, 47)     # burgundy accent (cover colour of the republic)
GOLD    = (176, 141, 63)    # seal gold
STAMP_B = (31, 74, 158)     # entry-stamp blue
STAMP_P = (104, 52, 138)    # visa purple
STAMP_R = (150, 52, 36)     # exit-stamp red brown
STAMP_G = (34, 110, 66)     # fee-stamp green
PHOTO_BG= (196, 205, 212)
SKIN    = (216, 169, 134)
SKIN_D  = (198, 148, 112)
HAIR    = (58, 38, 26)
JACKET  = (38, 52, 86)
SHIRT   = (244, 242, 236)
VISA_BG = (214, 230, 205)

# ---- tiny canvas ------------------------------------------------------------
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def fill(self, x, y, w, h, c):
        x0, y0 = max(x, 0), max(y, 0)
        x1, y1 = min(x + w, self.w), min(y + h, self.h)
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def rect(self, x, y, w, h, c, t=1):
        self.fill(x, y, w, t, c)
        self.fill(x, y + h - t, w, t, c)
        self.fill(x, y, t, h, c)
        self.fill(x + w - t, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.fill(x0 - t // 2, y0 - t // 2, t, t, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c, t=1, filled=False):
        x, y, d = 0, r, 3 - 2 * r
        def plot(px, py):
            if filled:
                self.fill(cx - px, py, 2 * px + 1, 1, c)
            else:
                for _ in range(t):
                    self.set(cx + px, py, c)
                    self.set(cx - px, py, c)
                    self.set(cx + px, py, c)
        while x <= y:
            for sx, sy in ((x, y), (y, x)):
                plot(sx, cy + sy)
                plot(sx, cy - sy)
                plot(-sx, cy + sy)
                plot(-sx, cy - sy)
            if d < 0:
                d += 4 * x + 6
            else:
                d += 4 * (x - y) + 10
                y -= 1
            x += 1

    def ellipse(self, cx, cy, rx, ry, c, filled=True):
        for yy in range(-ry, ry + 1):
            t = 1 - (yy * yy) / (ry * ry)
            if t < 0:
                continue
            dx = int(rx * (t ** 0.5))
            if filled:
                self.fill(cx - dx, cy + yy, 2 * dx + 1, 1, c)
            else:
                self.set(cx - dx, cy + yy, c)
                self.set(cx + dx, cy + yy, c)

    def blit(self, src, dx, dy):
        for yy in range(src.h):
            for xx in range(src.w):
                i = (yy * src.w + xx) * 3
                self.set(dx + xx, dy + yy, tuple(src.px[i:i + 3]))

# ---- 5x7 bitmap font (own glyphs, uppercase + digits + punctuation) ---------
FONT = {
 'A': [".###.","#...#","#...#","#####","#...#","#...#","#...#"],
 'B': ["####.","#...#","#...#","####.","#...#","#...#","####."],
 'C': [".####","#....","#....","#....","#....","#....",".####"],
 'D': ["####.","#...#","#...#","#...#","#...#","#...#","####."],
 'E': ["#####","#....","#....","####.","#....","#....","#####"],
 'F': ["#####","#....","#....","####.","#....","#....","#...."],
 'G': [".####","#....","#....","#.###","#...#","#...#",".###."],
 'H': ["#...#","#...#","#...#","#####","#...#","#...#","#...#"],
 'I': [".###.","..#..","..#..","..#..","..#..","..#..",".###."],
 'J': ["..###","...#.","...#.","...#.","...#.","#..#.",".##.."],
 'K': ["#...#","#..#.","#.#..","##...","#.#..","#..#.","#...#"],
 'L': ["#....","#....","#....","#....","#....","#....","#####"],
 'M': ["#...#","##.##","#.#.#","#.#.#","#...#","#...#","#...#"],
 'N': ["#...#","##..#","##..#","#.#.#","#..##","#..##","#...#"],
 'O': [".###.","#...#","#...#","#...#","#...#","#...#",".###."],
 'P': ["####.","#...#","#...#","####.","#....","#....","#...."],
 'Q': [".###.","#...#","#...#","#...#","#.#.#","#..#.",".##.#"],
 'R': ["####.","#...#","#...#","####.","#.#..","#..#.","#...#"],
 'S': [".####","#....","#....",".###.","....#","....#","####."],
 'T': ["#####","..#..","..#..","..#..","..#..","..#..","..#.."],
 'U': ["#...#","#...#","#...#","#...#","#...#","#...#",".###."],
 'V': ["#...#","#...#","#...#","#...#","#...#",".#.#.","..#.."],
 'W': ["#...#","#...#","#...#","#.#.#","#.#.#","##.##","#...#"],
 'X': ["#...#","#...#",".#.#.","..#..",".#.#.","#...#","#...#"],
 'Y': ["#...#","#...#",".#.#.","..#..","..#..","..#..","..#.."],
 'Z': ["#####","....#","...#.","..#..",".#...","#....","#####"],
 '0': [".###.","#..##","#.#.#","##..#","#...#","#...#",".###."],
 '1': ["..#..",".##..","..#..","..#..","..#..","..#..",".###."],
 '2': [".###.","#...#","....#","..##.",".#...","#....","#####"],
 '3': ["####.","....#","....#",".###.","....#","....#","####."],
 '4': ["...#.","..##.",".#.#.","#..#.","#####","...#.","...#."],
 '5': ["#####","#....","####.","....#","....#","#...#",".###."],
 '6': [".###.","#....","#....","####.","#...#","#...#",".###."],
 '7': ["#####","....#","...#.","..#..","..#..","..#..","..#.."],
 '8': [".###.","#...#","#...#",".###.","#...#","#...#",".###."],
 '9': [".###.","#...#","#...#",".####","....#","....#",".###."],
 ' ': [".....",".....",".....",".....",".....",".....","....."],
 '.': [".....",".....",".....",".....",".....",".##..",".##.."],
 ',': [".....",".....",".....",".....",".##..",".##..",".#..."],
 '-': [".....",".....",".....",".###.",".....",".....","....."],
 '/': ["....#","...#.","...#.","..#..",".#...",".#...","#...."],
 '<': ["...#.","..#..",".#...","#....",".#...","..#..","...#."],
 '>': [".#...","..#..","...#.","....#","...#.","..#..",".#..."],
 '(': ["...#.","..#..",".#...",".#...",".#...","..#..","...#."],
 ')': [".#...","..#..","...#.","...#.","...#.","..#..",".#..."],
 ':': [".....",".##..",".##..",".....",".##..",".##..","....."],
 '+': [".....","..#..","..#..",".###.","..#..","..#..","....."],
 "'": ["..#..","..#..",".....",".....",".....",".....","....."],
 '&': [".##..","#..#.","#.#..",".#...","#.#.#","#..#.",".##.#"],
 '=': [".....",".....",".###.",".....",".###.",".....","....."],
 'N': ["#...#","##..#","##..#","#.#.#","#..##","#..##","#...#"],
}

def text_width(s, scale, spacing=1):
    return len(s) * (5 * scale + spacing) - spacing

def draw_text(cv, s, x, y, scale, color, spacing=1):
    cx = x
    for ch in s.upper():
        g = FONT.get(ch, FONT[' '])
        for r in range(7):
            for col in range(5):
                if g[r][col] == '#':
                    cv.fill(cx + col * scale, y + r * scale, scale, scale, color)
        cx += 5 * scale + spacing
    return cx

def draw_text_center(cv, s, cx, y, scale, color, spacing=1):
    draw_text(cv, s, cx - text_width(s, scale, spacing) // 2, y, scale, color, spacing)

def wrap_text(cv, s, x, y, maxw, scale, color, spacing=1, leading=4):
    words = s.split()
    line, cy = "", y
    for w in words:
        trial = (line + " " + w).strip()
        if text_width(trial, scale, spacing) > maxw and line:
            draw_text(cv, line, x, cy, scale, color, spacing)
            cy += 7 * scale + leading
            line = w
        else:
            line = trial
    if line:
        draw_text(cv, line, x, cy, scale, color, spacing)
    return cy + 7 * scale

# ---- ICAO MRZ check digits (weights 7,3,1; A=10 .. Z=35, '<'=0) -------------
def mrz_check(s):
    total = 0
    for i, ch in enumerate(s):
        if ch.isdigit():
            v = int(ch)
        elif 'A' <= ch <= 'Z':
            v = ord(ch) - 55
        else:
            v = 0
        total += v * (7, 3, 1)[i % 3]
    return str(total % 10)

def mrz_line1():
    base = "P<TVA" + "MEREN<<ALYSSE<KARA"
    return (base + "<" * (44 - len(base)))[:44]

def mrz_line2():
    doc = "TV7845123"
    dob = "910414"
    exp = "330314"
    pers = "VELDARA1987"
    l2 = (doc + mrz_check(doc) + "TVA" + dob + mrz_check(dob) + "F"
          + exp + mrz_check(exp) + pers + mrz_check(pers))
    return (l2 + "<" * (44 - len(l2)))[:44]

# ---- the portrait: a flat-document likeness, drawn, not pasted -------------
def make_portrait():
    p = Canvas(150, 185, PHOTO_BG)
    # faint studio backdrop
    p.fill(0, 0, 150, 60, (206, 213, 219))
    p.fill(0, 60, 150, 125, (188, 197, 205))
    # shoulders / jacket
    p.ellipse(75, 235, 72, 62, JACKET)
    p.fill(0, 185, 150, 1, JACKET)
    # shirt V and collar
    p.fill(63, 168, 24, 17, SHIRT)
    p.line(63, 168, 75, 185, SHIRT, 3)
    p.line(87, 168, 75, 185, SHIRT, 3)
    # small republic pin on the lapel
    p.circle(104, 172, 4, GOLD, 1, filled=True)
    # neck
    p.fill(64, 138, 22, 34, SKIN_D)
    p.fill(64, 138, 22, 6, (176, 128, 96))
    # head
    p.ellipse(75, 88, 44, 54, SKIN)
    # hair: dark mass over the crown, parted, with side strands
    p.ellipse(75, 52, 46, 34, HAIR)
    p.ellipse(75, 78, 47, 26, HAIR)
    p.ellipse(75, 88, 44, 54, SKIN)          # face again over the hair mass
    p.ellipse(75, 46, 40, 22, HAIR)          # crown
    p.fill(30, 60, 10, 62, HAIR)             # left strand
    p.fill(110, 60, 10, 62, HAIR)            # right strand
    p.ellipse(75, 44, 34, 12, HAIR)
    # ears
    p.ellipse(31, 92, 5, 9, SKIN)
    p.ellipse(119, 92, 5, 9, SKIN)
    # brows
    p.line(50, 76, 66, 74, HAIR, 2)
    p.line(84, 74, 100, 76, HAIR, 2)
    # eyes
    p.ellipse(58, 84, 6, 3, (250, 250, 246))
    p.ellipse(92, 84, 6, 3, (250, 250, 246))
    p.ellipse(58, 84, 3, 3, (32, 26, 22))
    p.ellipse(92, 84, 3, 3, (32, 26, 22))
    # nose
    p.line(75, 86, 73, 102, SKIN_D, 2)
    p.line(73, 102, 78, 104, SKIN_D, 2)
    # mouth, closed, steady
    p.line(64, 118, 86, 118, (150, 82, 70), 2)
    p.fill(68, 119, 14, 2, (168, 96, 82))
    # cheek shade, jaw line
    p.ellipse(52, 102, 8, 5, (206, 156, 122))
    p.ellipse(98, 102, 8, 5, (206, 156, 122))
    return p

# ---- stamps ------------------------------------------------------------------
def round_stamp(cv, cx, cy, r, color, top, mid, bottom, sub=""):
    cv.circle(cx, cy, r, color, 2)
    cv.circle(cx, cy, r - 6, color, 1)
    draw_text_center(cv, top, cx, cy - r + 9, 1, color)
    draw_text_center(cv, mid, cx, cy - 4, 1, color)
    draw_text_center(cv, bottom, cx, cy + 8, 1, color)
    if sub:
        draw_text_center(cv, sub, cx, cy + r - 14, 1, color)

def rect_stamp(cv, x, y, w, h, color, lines):
    cv.rect(x, y, w, h, color, 2)
    cv.rect(x + 4, y + 4, w - 8, h - 8, color, 1)
    yy = y + 10
    for ln in lines:
        draw_text_center(cv, ln, x + w // 2, yy, 1, color)
        yy += 11

# ---- the spread ---------------------------------------------------------------
def build():
    cv = Canvas(W, H, PAPER)
    # paper tone blocks + faint guilloche arcs on the data page
    cv.fill(16, 16, 488, 668, PAPER2)
    cv.fill(520, 16, 488, 668, PAPER2)
    for r in range(60, 420, 18):
        cv.circle(260, 640, r, (226, 218, 196), 1)
    # outer double border
    cv.rect(8, 8, W - 16, H - 16, INK, 2)
    cv.rect(14, 14, W - 28, H - 28, INK, 1)
    # centre gutter
    cv.fill(511, 16, 2, 668, INK)

    # ================= LEFT PAGE: DATA PAGE ===================================
    # coat of arms: shield, star, sprig
    cx = 260
    cv.ellipse(cx, 52, 26, 30, BURG)
    cv.fill(cx - 26, 52, 52, 22, BURG)
    cv.line(cx - 26, 52, cx, 84, BURG, 2)
    cv.line(cx + 26, 52, cx, 84, BURG, 2)
    cv.rect(cx - 24, 30, 48, 22, BURG)
    cv.rect(cx - 24, 30, 48, 22, GOLD, 1)
    draw_text_center(cv, "*", cx, 34, 2, GOLD)
    draw_text_center(cv, "T", cx, 52, 2, GOLD)
    draw_text_center(cv, "REPUBLIC OF TALVARIA", cx, 96, 2, INK)
    draw_text_center(cv, "PASSPORT - PASSEPORT", cx, 120, 1, INK_SOFT)
    cv.fill(56, 140, 392, 2, RULE)

    # portrait, framed
    cv.rect(56, 152, 152, 187, INK, 2)
    cv.blit(make_portrait(), 57, 153)
    draw_text_center(cv, "PHOTOGRAPH", 132, 344, 1, GREY)

    # personal data, right of the portrait
    fx, fy = 232, 158
    fields = [
        ("SURNAME", "MEREN"),
        ("GIVEN NAMES", "ALYSSE KARA"),
        ("NATIONALITY", "TALVARIAN"),
        ("DATE OF BIRTH", "14 APR 1991"),
        ("PLACE OF BIRTH", "VELDARA"),
        ("SEX", "F"),
        ("DOCUMENT NO.", "TV7845123"),
        ("DATE OF ISSUE", "14 MAR 2023"),
        ("DATE OF EXPIRY", "14 MAR 2033"),
        ("AUTHORITY", "MINISTRY OF THE INTERIOR"),
    ]
    y = fy
    for label, value in fields:
        draw_text(cv, label, fx, y, 1, GREY)
        draw_text(cv, value, fx, y + 10, 2, INK)
        y += 30
    # signature
    cv.line(56, 372, 208, 372, INK, 1)
    cv.line(70, 366, 96, 356, INK, 2)
    cv.line(96, 356, 112, 368, INK, 2)
    cv.line(112, 368, 140, 358, INK, 2)
    cv.line(140, 358, 158, 366, INK, 2)
    cv.line(158, 366, 190, 360, INK, 2)
    draw_text_center(cv, "HOLDER'S SIGNATURE", 132, 378, 1, GREY)
    # note under the data, kept clear of the seal
    draw_text(cv, "BEARER IS A CITIZEN OF", 232, 452, 1, INK_SOFT)
    draw_text(cv, "THE REPUBLIC OF TALVARIA.", 232, 464, 1, INK_SOFT)
    # small seal, clear of the data rows above and the MRZ rule below
    cv.circle(440, 474, 22, BURG, 2)
    cv.circle(440, 474, 18, BURG, 1)
    draw_text_center(cv, "TAL", 440, 463, 1, BURG)
    draw_text_center(cv, "VARIA", 440, 474, 1, BURG)
    draw_text_center(cv, "2023", 440, 485, 1, BURG)

    # machine-readable zone
    cv.fill(40, 500, 440, 2, RULE)
    draw_text(cv, mrz_line1(), 44, 516, 2, INK, spacing=0)
    draw_text(cv, mrz_line2(), 44, 538, 2, INK, spacing=0)
    draw_text(cv, "P<TVA MEREN<<ALYSSE<KARA", 44, 566, 1, GREY)
    draw_text(cv, "THIS PASSPORT REMAINS THE PROPERTY OF THE REPUBLIC", 44, 596, 1, GREY)
    draw_text(cv, "OF TALVARIA. IF FOUND, RETURN TO ANY TALVARIAN MISSION.", 44, 608, 1, GREY)
    draw_text(cv, "TYPE P  CODE TVA  NO. TV7845123", 44, 636, 1, INK_SOFT)

    # ================= RIGHT PAGE: VISAS ======================================
    draw_text_center(cv, "VISAS", 764, 40, 2, INK)
    draw_text_center(cv, "VISA - VISA", 764, 64, 1, INK_SOFT)
    cv.fill(560, 84, 408, 2, RULE)

    # visa sticker: Ostara, issued at Veldara, before the travel it permits
    vx, vy, vw, vh = 560, 100, 408, 132
    cv.fill(vx, vy, vw, vh, VISA_BG)
    cv.rect(vx, vy, vw, vh, STAMP_P, 2)
    cv.rect(vx + 4, vy + 4, vw - 8, vh - 8, STAMP_P, 1)
    draw_text(cv, "VISA", vx + 14, vy + 12, 2, STAMP_P)
    draw_text(cv, "OSTARA", vx + 14, vy + 34, 2, INK)
    draw_text(cv, "SINGLE ENTRY - 90 DAYS", vx + 14, vy + 60, 1, INK)
    draw_text(cv, "ISSUED 09 SEP 2024 - VELDARA", vx + 14, vy + 74, 1, INK)
    draw_text(cv, "VALID UNTIL 08 DEC 2024", vx + 14, vy + 88, 1, INK)
    draw_text(cv, "NO. 004821", vx + 14, vy + 104, 1, INK_SOFT)
    # sticker corner motif: three bars of the Ostara flag
    cv.fill(vx + vw - 66, vy + 12, 52, 8, (31, 74, 158))
    cv.fill(vx + vw - 66, vy + 22, 52, 8, (244, 242, 236))
    cv.fill(vx + vw - 66, vy + 32, 52, 8, (150, 52, 36))

    # arrival / departure stamps: one trip, in order, all after issue
    round_stamp(cv, 660, 320, 52, STAMP_B, "KESSAN", "ENTRY", "02 JUN 2023", "POST 7")
    round_stamp(cv, 880, 320, 52, STAMP_R, "KESSAN", "EXIT", "18 JUN 2023", "POST 7")
    round_stamp(cv, 660, 470, 52, STAMP_B, "PORT OF LYS", "ENTRY", "11 OCT 2025", "MERIDIAN UN.")
    # fee stamp: the salt levy, Talvaria's telling paperwork
    rect_stamp(cv, 780, 420, 190, 100, STAMP_G,
               ["SALT LEVY PAID", "12 KORUN", "18 JUN 2023", "KESSAN GATE"])
    # condition of issue: the detail that reveals the place
    bx, by, bw = 560, 548, 408
    cv.rect(bx, by, bw, 104, INK, 2)
    draw_text(cv, "CONDITION OF ISSUE - ART. 9, BORDER RITES ACT", bx + 12, by + 10, 1, BURG)
    wrap_text(cv, "THE BEARER SHALL CARRY A SPRIG OF JUNIPER WHEN CROSSING "
                  "THE KESSAN GATE. A PASSPORT WITHOUT ITS SPRIG IS A "
                  "PASSPORT WITHOUT ITS BEARER.", bx + 12, by + 28, bw - 24, 1, INK)
    draw_text(cv, "PAGES 12-31 RESERVED FOR BORDER STAMPS ONLY.", 560, 668, 1, GREY)
    return cv

# ---- PNG writer (8-bit RGB, filter 0) -----------------------------------------
def write_png(cv, path):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

def main():
    cv = build()
    n = write_png(cv, OUT)
    # loud failure if the gate caps are missed
    assert cv.w <= 1024 and cv.h <= 1024, "image too large"
    assert n <= 1_048_576, f"file too large: {n} bytes"
    print(f"wrote {OUT}: {cv.w}x{cv.h}, {n} bytes")

if __name__ == "__main__":
    main()
