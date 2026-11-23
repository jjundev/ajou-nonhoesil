"""설계 계획서 그림 세 장(블록다이어그램, 상태도, 키배치)의 SVG 를 만들고 PNG 로 바꾼다.

저장소 루트에서 `python 보고서/프로젝트/그림/make_figures.py` 로 실행한다.
노션 PDF 는 그림을 본문 폭(약 165mm)에 맞추므로, 가장 작은 글자가 폭의 1.4% 이상이
되게 한다(tests/test_fpga_plan_doc.py::test_figure_text_legible).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from scripts.lab.svg_png import render_svg  # noqa: E402

FONT = "Malgun Gothic, sans-serif"
DEFS = ('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
        'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#000"/></marker></defs>')


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'font-family="{FONT}">\n{DEFS}\n<rect width="{w}" height="{h}" fill="#fff"/>\n'
            + "\n".join(body) + "\n</svg>\n")


def t(x, y, s, size, anchor="middle", weight="normal"):
    return f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}">{s}</text>'


def line(x1, y1, x2, y2, arrow=True):
    m = ' marker-end="url(#a)"' if arrow else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#000" stroke-width="2"{m}/>'


def path(d, arrow=True):
    m = ' marker-end="url(#a)"' if arrow else ""
    return f'<path d="{d}" fill="none" stroke="#000" stroke-width="2"{m}/>'


def box(x, y, w, h, name, lines, size=15):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#fff" stroke="#000" stroke-width="2"/>',
           t(x + w / 2, y + 32, name, 21, weight="bold")]
    for i, s in enumerate(lines):
        out.append(t(x + w / 2, y + 58 + 21 * i, s, size))
    return out


# ---------------------------------------------------------------- 블록 다이어그램
def block():
    """ㄷ자 흐름: 위 줄 key_input → key_decode → door_fsm, 아래 줄 display_ctrl → seg_driver → 출력."""
    b, W, H, L = [], 200, 104, 15
    A, B, C = 60, 300, 500          # 줄 y
    x1, x2, x3 = 120, 430, 740      # 열 x
    b += box(x1, A, W, H, "key_input", ["반전, 2FF 동기화", "10ms 디바운스, 엣지"])
    b += box(x2, A, W, H, "key_decode", ["pb 번호를", "숫자·기능 키로"])
    b += box(x3, A, W, H, "door_fsm", ["상태, 입력 버퍼", "비밀번호, 실패, 잠금"])
    b += box(x3, B, W, H, "display_ctrl", ["상태를", "여섯 글자로"])
    b += box(x2, B, W, H, "seg_driver", ["글자를 세그먼트로", "6자리 스캔, 블랭킹"])
    b += box(x1, C, 380, 120, "tick_gen", ["clock_50m에서", "1클록짜리 enable 틱 생성"])
    b += box(560, C, 380, 120, "por", ["전원을 넣은 뒤 일정 클록 동안", "rst 유지 → 나머지 모듈 초기화"])
    ma, mb = A + H / 2, B + H / 2
    # 입력
    b += [t(20, ma - 10, "pb[15:0]", L, "start"), line(20, ma, x1 - 2, ma)]
    b += [t(20, C + 50, "clock_50m", L, "start"), line(20, C + 60, x1 - 2, C + 60)]
    # 위 줄
    b += [line(x1 + W, ma, x2 - 2, ma), t((x1 + W + x2) / 2, ma - 30, "key_valid", L), t((x1 + W + x2) / 2, ma - 10, "key_code", L)]
    b += [line(x2 + W, ma, x3 - 2, ma), t((x2 + W + x3) / 2, ma - 30, "key_valid", L), t((x2 + W + x3) / 2, ma - 10, "키 종류", L)]
    # 위 → 아래
    cx = x3 + W / 2
    b += [line(cx, A + H, cx, B - 2), t(cx - 12, (A + H + B) / 2 - 2, "상태, 메시지,", L, "end"), t(cx - 12, (A + H + B) / 2 + 18, "입력, 남은 초", L, "end")]
    # 아래 줄 (오른쪽 → 왼쪽)
    b += [line(x3, mb, x2 + W + 2, mb), t((x2 + W + x3) / 2, mb - 10, "글자 6개", L)]
    # 출력
    b += [line(x2, mb - 20, 250, mb - 20), t((250 + x2) / 2, mb - 28, "fnd_s[5:0]", L)]
    b += [line(x2, mb + 22, 250, mb + 22), t((250 + x2) / 2, mb + 14, "fnd_d[7:0]", L)]
    b += [t(242, mb - 4, "7", L, "end"), t(242, mb + 16, "Segment", L, "end")]
    # 틱, 리셋, 클록
    b += [line(150, C, 150, A + H + 2), t(160, 240, "10ms 틱", L, "start")]
    b += [line(480, C, 480, B + H + 2), t(490, 456, "1kHz 틱", L, "start")]
    b += [line(940, C + 60, 988, C + 60), t(962, C + 48, "rst", L)]
    b += [t(500, 655, "clock_50m은 모든 모듈, rst는 por를 뺀 모든 모듈에 들어간다.", L)]
    return svg(1000, 675, b)


# ---------------------------------------------------------------- 상태도
def state():
    b, L = [], 17
    S = {  # 이름: (cx, cy, rx, 표시)
        "IDLE": (150, 330, 95, "------"),
        "CHECK": (450, 330, 95, "비교 (1클록)"),
        "OPEN": (760, 170, 90, "OPEn"),
        "NEW_PW": (1060, 170, 100, "nEW"),
        "NEW_CONFIRM": (1060, 420, 125, "AGAIn"),
        "MSG": (760, 540, 150, "Error, nonE, donE, InIt"),
        "LOCK": (450, 600, 115, "LOCK + 남은 초"),
    }
    for n, (x, y, rx, disp) in S.items():
        b.append(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="38" fill="#fff" stroke="#000" stroke-width="2"/>')
        b.append(t(x, y - 3, n, 21, weight="bold"))
        b.append(t(x, y + 22, disp, L))
    b += [line(245, 330, 353, 330), t(300, 318, "OK", L)]
    b += [line(510, 300, 685, 196), t(585, 235, "일치", L, "end")]
    b += [path("M 680,150 Q 330,10 175,291"), t(370, 84, "OK (문 닫힘)", L)]
    b += [line(450, 368, 450, 560), t(462, 470, "3회째 오답", L, "start")]
    b += [line(370, 575, 195, 364), t(268, 480, "시간 만료", L, "end")]
    b += [line(515, 356, 650, 512), t(594, 405, "오답 1, 2회째", L, "start"), t(594, 427, "(빈 입력 포함)", L, "start")]
    b += [path("M 760,578 L 760,730 L 90,730 L 90,362"), t(430, 720, "1.5초 (그 밖의 메시지)", L)]
    b += [line(740, 208, 740, 500), t(730, 350, "RST", L, "end")]
    b += [line(782, 501, 782, 209), t(792, 350, "1.5초", L, "start"), t(792, 372, "(변경 실패)", L, "start")]
    b += [line(850, 170, 958, 170), t(905, 158, "CHG", L)]
    b += [line(1060, 208, 1060, 380), t(1072, 290, "OK", L, "start"), t(1072, 312, "4~6자리", L, "start")]
    b += [line(1000, 200, 850, 509), t(960, 262, "OK, 0~3자리", L, "end")]
    b += [line(990, 452, 900, 520), t(935, 512, "OK (같음 donE, 다름 Error)", L, "start")]
    return svg(1200, 760, b)


# ---------------------------------------------------------------- 키 배치
def keys():
    b = []
    layout = [
        [("1", ""), ("2", ""), ("3", ""), ("CHG", "변경")],
        [("4", ""), ("5", ""), ("6", ""), ("RST", "초기화")],
        [("7", ""), ("8", ""), ("9", ""), ("", "예비")],
        [("OK", "확인"), ("0", ""), ("BS", "지우기"), ("CLR", "전체 지우기")],
    ]
    for r, row in enumerate(layout):
        for c, (label, ko) in enumerate(row):
            n = 4 * r + c
            x, y = 120 + 120 * c, 110 + 120 * r
            fill = "#fff" if label.isdigit() else "#e6e6e6"
            b.append(f'<circle cx="{x}" cy="{y}" r="52" fill="{fill}" stroke="#000" stroke-width="2"/>')
            if label.isdigit():
                b.append(t(x, y + 6, label, 26, weight="bold"))
                b.append(t(x, y + 34, f"pb{n}", 11))
            else:
                if label:
                    b.append(t(x, y - 2, label, 20, weight="bold"))
                b.append(t(x, y + 20, ko, 11))
                b.append(t(x, y + 36, f"pb{n}", 11))
    b.append(t(300, 590, "회색은 기능 키, pb11은 쓰지 않는다.", 13))
    return svg(600, 610, b)


if __name__ == "__main__":
    for name, make in [("블록다이어그램", block), ("상태도", state), ("키배치", keys)]:
        (HERE / f"{name}.svg").write_text(make(), encoding="utf-8")
        render_svg(HERE / f"{name}.svg", HERE / f"{name}.png")
        print(name)
