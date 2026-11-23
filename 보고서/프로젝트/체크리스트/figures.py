"""체크리스트 그림: 키트 결선 3장, pb 번호 키패드, 화면(7 Segment) 조각.

결선 그림의 단자 위치는 과제 PDF p3 사진을 따른다. 사진 사본도 여기서 만든다.
"""
import html
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from scripts.lab.svg_png import render_svg  # noqa: E402

FIG = HERE / "그림"
PDF = ROOT / "강의노트/설계과제/26-2_논리회로실험_설계과제.pdf"
FONT = "Malgun Gothic, sans-serif"
INK, GREY, LIGHT = "#111", "#9a9a9a", "#d9d9d9"

# 번호: (이름, 색, 표시 모양, FPGA 쪽 단자 x, 모듈 쪽 단자 x)
CABLES = {
    1: ("빨강 원", "#c81e1e", "o", 225, 890),
    2: ("초록 원", "#14823c", "o", 335, 1000),
    3: ("하늘색 네모", "#0e8fc8", "s", 440, 1240),
    4: ("보라 네모", "#8f2a91", "s", 550, 1350),
}
TOP, BOT, SEG_Y, KEY_Y = 150, 640, 640, 660     # 단자 중심 y


def t(x, y, s, size=18, color=INK, anchor="middle", weight="normal"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}" '
            f'font-weight="{weight}">{html.escape(s)}</text>')


def rect(x, y, w, h, fill="#fff", stroke=INK, sw=2, rx=6, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}"{d}/>')


def conn(x, y, color=None):
    """10핀 박스 단자. 쓰지 않는 단자는 흐리게."""
    out = [rect(x - 42, y - 19, 84, 38, "#fff" if color else "#f4f4f4", color or GREY, 4 if color else 1.5, 4)]
    for i in range(5):
        for dy in (-7, 7):
            out.append(f'<circle cx="{x - 24 + 12 * i}" cy="{y + dy}" r="2.6" fill="{color or GREY}"/>')
    return out


def badge(x, y, n, color, shape):
    body = (f'<circle cx="{x}" cy="{y}" r="17" fill="{color}"/>' if shape == "o"
            else f'<rect x="{x - 16}" y="{y - 16}" width="32" height="32" fill="{color}"/>')
    return body + t(x, y + 7, str(n), 20, "#fff", weight="bold")


def cable(n, color):
    x1, x2 = CABLES[n][3], CABLES[n][4]
    if n == 1:
        d = f"M{x1},{BOT + 19} V800 H{x2} V{SEG_Y + 19}"
    elif n == 2:
        d = f"M{x1},{BOT + 19} V765 H{x2} V{SEG_Y + 19}"
    elif n == 3:
        d = f"M{x1},{TOP - 19} V55 H1145 V765 H{x2} V{KEY_Y + 19}"
    else:
        d = f"M{x1},{TOP - 19} V90 H1114 V800 H{x2} V{KEY_Y + 19}"
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="9" stroke-linejoin="round"/>'


def kit(new, done=()):
    b = [rect(60, 20, 1400, 720, "#fafafa", LIGHT, 2, 10), rect(90, 105, 560, 590, "#f2f6fa", INK, 2, 10),
         t(370, 490 + 52, "FPGA 보드 (DE0-Nano)", 22, weight="bold")]
    b += [rect(195, 225, 350, 290, "#fff", INK, 2, 8), rect(390, 320, 100, 100, "#e6e6e6", INK),
          t(440, 377, "Cyclone IV", 15)]
    b += [rect(195, 290, 70, 46, "#fff", INK), t(230, 319, "USB", 16, weight="bold"),
          t(203, 358, "미니 B", 14, "#555", "start")]
    b += [rect(104, 205, 72, 46, "#e6e6e6", INK), t(140, 234, "DC +5V", 14)]
    b += [rect(190, 188, 360, 18, "#cfcfcf", GREY, 1, 2), rect(190, 575, 360, 18, "#cfcfcf", GREY, 1, 2)]
    for x in (225, 335, 440, 550):
        b += conn(x, TOP) + conn(x, BOT)
    for y, name in ((270, "J13"), (380, "J14"), (490, "J15")):
        b += [rect(590, y - 40, 34, 80, "#f4f4f4", GREY, 1.5, 4), t(607, y + 58, name, 14, "#666")]
    b += [t(440, BOT + 40, "J10", 14, "#666"), t(550, BOT + 40, "J9", 14, "#666")]

    b += [rect(690, 130, 750, 580, "none", GREY, 2, 4), t(850, 170, "Application Bench", 18, "#666")]
    b += [rect(800, 410, 290, 275, "#fff", INK, 2, 8), t(945, 446, "7-SEG 모듈", 22, weight="bold")]
    b += [rect(825, 470, 240, 90, "#222", INK, 1, 4)]
    for i in range(6):
        b.append(t(847 + 39 * i, 535, "8", 50, "#777", weight="bold"))
    b += [rect(1165, 310, 260, 395, "#fff", INK, 2, 8), t(1295, 346, "Keypad 모듈", 22, weight="bold")]
    for r in range(4):
        for c in range(4):
            x, y = 1205 + 52 * c, 368 + 58 * r
            b += [rect(x, y, 40, 40, "#eee", INK, 1.5, 4), f'<circle cx="{x + 20}" cy="{y + 20}" r="10" fill="#333"/>']
    for n in (1, 2):
        b += conn(CABLES[n][4], SEG_Y)
    for n in (3, 4):
        b += conn(CABLES[n][4], KEY_Y)

    for n in done:
        b.append(cable(n, "#b5b5b5"))
    for n in new:
        b.append(cable(n, CABLES[n][1]))
    for n in (*done, *new):
        _, color, shape, x1, x2 = CABLES[n]
        color = color if n in new else "#8a8a8a"
        y1, y2 = (BOT, SEG_Y) if n < 3 else (TOP, KEY_Y)
        b += conn(x1, y1, color) + conn(x2, y2, color)
        s = -1 if n > 2 else 1
        b += [badge(x1, y1 + 42 * s, n, color, shape), badge(x2, y2 + 42, n, color, shape)]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1520 830" width="1520" height="830" '
            f'font-family="{FONT}">\n<rect width="1520" height="830" fill="#fff"/>\n' + "\n".join(b) + "\n</svg>\n")


def keypad():
    b = []
    for n in range(16):
        x, y = 130 + 150 * (n % 4), 90 + 125 * (n // 4)
        b += [rect(x - 62, y - 50, 124, 100, "#fff", INK, 2, 10), t(x, y + 12, f"pb{n}", 34, weight="bold")]
    b += [t(355, 560, "케이블 커넥터", 18, "#555"), rect(120, 530, 470, 46, "none", GREY, 1.5, 4, "6 4")]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 710 600" width="710" height="600" '
            f'font-family="{FONT}">\n<rect width="710" height="600" fill="#fff"/>\n' + "\n".join(b) + "\n</svg>\n")


def photo():
    import pymupdf
    page = pymupdf.open(PDF)[2]
    clip = page.get_image_rects(page.get_images(full=True)[0][0])[0]
    page.get_pixmap(dpi=200, clip=clip).save(FIG / "키트_p3.png")


_SEG = [  # a b c d e f g — 자리 폭 20, 높이 34
    "M5,3 H15", "M17,5 V15", "M17,19 V29", "M5,31 H15", "M3,19 V29", "M3,5 V15", "M5,17 H15"]


def screen(text, g, scale=1.0):
    """화면 여섯 자리 인라인 SVG. g 는 checks.glyphs()."""
    parts = []
    for i, ch in enumerate(text.ljust(6)):
        for bit, d in enumerate(_SEG):
            on = g[ch] >> bit & 1
            parts.append(f'<path transform="translate({i * 25 + 6},5)" d="{d}" stroke="{"#111" if on else "#e8e8e8"}" '
                         f'stroke-width="{3.4 if on else 2}" stroke-linecap="round"/>')
    w = 156 * scale
    return (f'<svg class="seg" viewBox="0 0 156 44" width="{w:.0f}" height="{44 * scale:.0f}" role="img" '
            f'aria-label="{html.escape(text)}"><rect x=".5" y=".5" width="155" height="43" rx="3" fill="#fff" '
            f'stroke="#777"/>' + "".join(parts) + "</svg>")


def build():
    FIG.mkdir(exist_ok=True)
    for name, text in [("결선_1_7SEG", kit([1, 2])), ("결선_2_Keypad", kit([3, 4], [1, 2])),
                       ("결선_완성본", kit([1, 2, 3, 4])), ("키패드_pb번호", keypad())]:
        (FIG / f"{name}.svg").write_text(text, encoding="utf-8")
        render_svg(FIG / f"{name}.svg", FIG / f"{name}.png")
    photo()


if __name__ == "__main__":
    build()
