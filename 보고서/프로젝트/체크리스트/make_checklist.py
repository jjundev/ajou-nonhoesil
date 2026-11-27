"""11/27 FPGA 설계과제 체크리스트(HTML·PDF·기록.md)를 만든다.

저장소 루트에서 `python 보고서/프로젝트/체크리스트/make_checklist.py` 로 실행한다.
양식은 prep-lab-checklist 의 template.html 과 fit_pages 를 그대로 쓴다. 실험용 렌더러는
실험 번호·칩·홀을 요구해서 여기서는 쓰지 않는다.
"""
import html
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(HERE)]
import checks  # noqa: E402
import figures  # noqa: E402
from scripts.lab import config, validate  # noqa: E402
from scripts.lab.fit_pages import FIT_PLAIN, fit_pages  # noqa: E402
from scripts.lab.html2pdf import DEFAULT_CHROME, html_to_pdf  # noqa: E402
from scripts.lab.record import RecordExistsError, write_record  # noqa: E402

STEM = "FPGA_1주차"
TITLE = "FPGA 설계 1주차 체크리스트 (11/27)"
CIRCUITS = ("C0", "C1", "C2", "C3")
SOF_DIR = "보고서\\프로젝트\\FPGA\\quartus\\output_files"
EXAMPLE_DIR = "강의노트\\설계과제\\설계 자료(26-2)"
RED = "#dc0000"
NOWRAP = " style=\"white-space:nowrap\""
E = html.escape
EXTRA = """<style>
  .seg { vertical-align: middle; }
  .shots { display: flex; flex-wrap: wrap; align-items: center; gap: 1mm 1.5mm; }
  .shots + small { display: block; margin-top: .8mm; font-size: 8.5pt; color: var(--muted); }
  .comparison-table td.photo-name { font-size: 8pt; white-space: normal; }
  .comparison-table td.item { text-align: center; }
  .comparison-table td.do { font-weight: 700; text-align: left; }
  .comparison-table td.shotcell { text-align: left; }
  .step .route { white-space: normal; }
  .pair { display: flex; gap: 3mm; align-items: center; }
  .pair img { width: 50%; min-width: 0; }
  .sketch-key { display: block; width: 58%; margin: 2mm auto; }
  .fix td { text-align: left; vertical-align: top; }
</style>
"""


def trail(cur):
    return '<div class="trail">1주차: ' + " › ".join(
        f"<b>{c}</b>" if c == cur else c for c in CIRCUITS) + "</div>"


def head(cur, title, banner):
    return f'{trail(cur)}<h2>{cur} · {E(title)}</h2><div class="banner">{E(banner)}</div>'


def steps(rows):
    """(큰 글씨, 보조 설명[, 번호, 번호 원 색])"""
    out = ['<ol class="steps">']
    for i, (route, desc, *rest) in enumerate(rows, 1):
        n, color = rest if rest else (i, "#111")
        out.append(f'<li class="step"><span class="box"></span><span class="n" style="background:{color}">{n}</span>'
                   f'<span class="route">{E(route)}</span><span class="desc">{E(desc)}</span></li>')
    return "".join(out) + "</ol>"


def stage(title, body, check="", banner="", operation=""):
    return (f'<div class="stage"><h3>{E(title)}</h3>'
            + (f'<p class="banner">{E(banner)}</p>' if banner else "")
            + (f'<p class="operation">{E(operation)}</p>' if operation else "") + body
            + (f'<p><span class="box"></span><b>확인:</b> {E(check)}</p>' if check else "") + "</div>")


def board(name):
    return f'<figure class="board"><img src="그림/{name}.png" style="width:100%"></figure>'


def table(t, g):
    cols = ["순서"] + (["항목"] if t.has_item else []) + ["누를 키", "예상 화면", "실제 결과", "사진 파일명"]
    width = [6, 7, 22, 36, 16, 13] if t.has_item else [9, 25, 33, 18, 15]
    out = [f'<h3>{t.id} · {E(t.title)}</h3><p>{E(t.purpose)}</p><p class="operation"><b>준비</b> {E(t.setup)}</p>'
           '<table class="comparison-table"><colgroup>' + "".join(f'<col style="width:{w}%">' for w in width)
           + "</colgroup><thead><tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr></thead><tbody>"]
    for r in t.rows:
        shots = "<span>→</span>".join(figures.screen(s, g, .62) for s in r.show)
        cell = f'<div class="shots">{shots}</div><small>{E(r.note)}</small>' if shots else f"<b>{E(r.note)}</b>"
        item = f'<td class="item">{E(r.item).replace(" ", "<br>")}</td>' if t.has_item else ""
        out.append(f'<tr><td>{E(r.no)}</td>{item}<td class="do">{E(r.do)}</td><td class="shotcell">{cell}</td>'
                   f'<td class="actual"></td><td class="photo-name">{E(r.photo)}</td></tr>')
    return "".join(out) + "</tbody></table>"


def pin_table(p):
    def vec(n, hi):
        return ", ".join(p[f"{n}[{i}]"] for i in range(hi, -1, -1))
    rows = [("clock_50m", "입력", "50MHz 클록", p["clock_50m"]),
            ("pb[15:0]", "입력", "키패드 · 누르면 0", vec("pb", 15)),
            ("fnd_s[5:0]", "출력", "자리 선택 · 0이 켜짐 · [5]가 맨 왼쪽", vec("fnd_s", 5)),
            ("fnd_d[7:0]", "출력", "획 dp g f e d c b a · 1이 켜짐", vec("fnd_d", 7))]
    return ('<div class="tblock"><h2>참조 핀아웃 · EP4CE22F17C6</h2><table><thead><tr><th>신호</th><th style="white-space:nowrap">방향</th><th>기능</th>'
            '<th>FPGA 핀(높은 비트부터)</th></tr></thead><tbody>'
            + "".join("<tr>" + "".join(f"<td{NOWRAP * (i < 2)}>{E(c)}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows)
            + "</tbody></table></div>")


def load_steps(sof):
    """두 번째 파일부터: 앞 파일을 지우고 새 파일을 넣는다."""
    return board("Programmer_6_파일교체") + steps([
        ("앞에 넣은 파일 줄 클릭", "", "A", RED),
        ("Delete 클릭", "", "B", RED),
        ("Add File → 파일 고르기 → 열기", f"{SOF_DIR}\\{sof}", "C", RED),
        ("Program/Configure 체크 → Start → 100%", "C1 단계 4의 7~9와 같아요", "D", RED)])


def programmer_stages():
    """Programmer 화면 그대로. 빨간 사각형이 누르는 곳이고 번호가 목록과 같다."""
    return [
        stage("단계 4 준비 ① · USB-Blaster 고르기", board("Programmer_1_HardwareSetup")
              + board("Programmer_2_Hardware선택") + steps([
                  ("Hardware Setup 클릭", "Quartus Programmer 바로가기로 열어요 · 보고서\\프로젝트", 1, RED),
                  ("USB-Blaster [USB-0] 고르기", "그림은 키트를 꽂지 않아 No Hardware예요", 2, RED),
                  ("Close 클릭", "Mode는 JTAG 그대로", 3, RED)]),
              "Hardware Setup 옆 칸이 USB-Blaster로 바뀌었나요?"),
        stage("단계 4 준비 ② · 파일 넣기", board("Programmer_3_AddFile") + board("Programmer_4_파일선택") + steps([
            ("Add File 클릭", "", 4, RED),
            ("example.sof 고르기", f"{EXAMPLE_DIR} · 그림은 door_lock.sof를 고른 화면", 5, RED),
            ("열기 클릭", "", 6, RED)]), "목록에 파일 한 줄과 EP4CE22F17이 보이나요?"),
        stage("단계 4 · 보드에 쓰기", board("Programmer_5_Start") + steps([
            ("Program/Configure 체크 확인", "파일을 넣으면 자동으로 체크돼요", 7, RED),
            ("Start 클릭", "그림은 키트가 없어 흐려요 · 연결되면 눌려요", 8, RED),
            ("100% (Successful) 확인", "전원을 끄면 지워지므로 다시 넣어요", 9, RED)]), "Successful이 떴나요?")]


MEMO = '<div class="circuit-notes"><b>메모</b></div>'


def record_page(t, g):
    return FIT_PLAIN + table(t, g) + MEMO + "</div>"


FIX = [("장치 관리자에 USB-Blaster가 없음", "케이블과 USB 포트 → 키트 전원 → 드라이버 → 조교님"),
       ("Programmer에 No Hardware", "Hardware Setup에서 USB-Blaster 선택 → 다시 꽂고 Programmer를 다시 열기"),
       ("Add File 또는 컴파일 오류", "sof는 C:\\FPGA_Project에, 컴파일은 FPGA 폴더를 통째로 C:\\FPGA_Project에 복사해 다시 · 한글 경로 문제일 수 있음"),
       ("누른 키보다 8 크거나 작은 pb 번호", "③과 ④ 케이블이 서로 바뀌었는지"),
       ("키가 모두 또는 8개 안 먹음", "③ ④ 케이블 끝까지, 홈 방향"),
       ("화면이 꺼졌거나 획·자리가 빠짐", "① ② 케이블 끝까지, 서로 바뀌었는지"),
       ("한 번 눌렀는데 두 번 셈", "pb 번호와 10번 중 횟수 → 영상 · 12/4 전에 key_input 조정"),
       ("옆 자리 글자가 비침", "어느 글자·자리인지 → 사진 · 12/4 전에 BLANK_CLK 조정"),
       ("예제는 되는데 우리 코드만 안 됨", "파일 이름 → 핀 → 코드 순서로 확인")]


def body(g, p):
    c = {n: v[1] for n, v in figures.CABLES.items()}
    o = []
    # C0
    o.append('<section class="circuit">' + FIT_PLAIN + f"<h1>{TITLE}</h1>" + pin_table(p)
             + head("C0", "출발 전", "준비 — 파일 확인, 챙길 것")
             + '<img class="schematic" src="../그림/블록다이어그램.png"></div>')
    o.append(stage("단계 1 · 파일 확인", steps([
        ("door_lock.sof · board_check.sof", SOF_DIR),
        ("example.sof", EXAMPLE_DIR),
        ("Quartus에서 door_lock.qpf 열어 보기", "보고서\\프로젝트\\FPGA\\quartus"),
        ("run_sim.ps1 실행 → ALL PASS", "보고서\\프로젝트\\FPGA · 화면 저장")]),
        "노트북에 파일이 모두 있나요?"))
    o.append(stage("단계 2 · 챙길 것", steps([
        ("노트북·충전기", "Quartus 22.1 설치된 것"), ("태블릿·펜", "이 체크리스트"),
        ("USB 케이블(미니 B)", "키트에 있는지 모르니 있으면 챙겨요"), ("휴대폰", "사진과 초시계")])))
    o.append("</section>")
    # C1
    o.append('<section class="circuit">' + FIT_PLAIN
             + head("C1", "키트 결선과 예제 · 기록: T1", "준비 — 키트, 리본 케이블 4개")
             + '<img class="schematic" style="max-height:none" src="그림/키트_p3.png"></div>')
    o.append(stage("단계 1 · 7-SEG 케이블", board("결선_1_7SEG") + steps([
        ("FPGA 아래쪽 1번째 → 7-SEG 왼쪽", "빨강 원 · 왼쪽부터 셈", 1, c[1]),
        ("FPGA 아래쪽 2번째 → 7-SEG 오른쪽", "초록 원", 2, c[2])]),
        "커넥터 홈이 맞고 끝까지 들어갔나요?", "키트 전원 OFF · USB 뽑음"))
    o.append(stage("단계 2 · Keypad 케이블", board("결선_2_Keypad") + steps([
        ("FPGA 위쪽 3번째 → Keypad 왼쪽", "하늘색 네모 · 왼쪽부터 셈", 3, c[3]),
        ("FPGA 위쪽 4번째 → Keypad 오른쪽", "보라 네모", 4, c[4])]),
        "커넥터 홈이 맞고 끝까지 들어갔나요?", "키트 전원 OFF · USB 뽑음"))
    o.append(FIT_PLAIN + '<div class="wirebox"><h3>완성본</h3><div class="pair"><img src="그림/결선_완성본.png">'
             '<img src="그림/키트_p3.png"></div><p><span class="box"></span><b>확인:</b> 같은 색 표시끼리 이어졌나요? '
             "사진을 찍어요: 1주차 C1 결선.jpg</p></div></div>")
    o.append(stage("단계 3 · 전원과 USB", steps([
        ("키트 전원 연결", "방법은 조교님 안내를 따라요"),
        ("FPGA 보드 USB를 노트북에 연결", "보드 왼쪽 미니 B"),
        ("장치 관리자에서 USB-Blaster 확인", "느낌표가 있으면 다음 줄"),
        ("드라이버 업데이트", "C:\\intelFPGA_lite\\22.1std\\quartus\\drivers · 실습 자료 p20~23")]),
        "장치 관리자의 USB-Blaster에 느낌표가 없나요?"))
    o += programmer_stages()
    o.append(record_page(checks.T1, g) + "</section>")
    # C2
    o.append('<section class="circuit">' + FIT_PLAIN + head("C2", "보드 점검 · 기록: T2, T3", "준비 — board_check.sof")
             + '<img class="sketch-key" src="그림/키패드_pb번호.png">'
             '<p><span class="box"></span><b>확인:</b> 키는 그림의 위치로 찾아요. 기판 글자가 PB1부터면 '
             "pb번호 = 기판 번호 − 1 이에요. 왼쪽 위 키의 기판 글자: ________</p></div>")
    o.append(stage("단계 1 · board_check.sof", load_steps("board_check.sof"), "여섯 자리에 가운데 획이 떴나요?"))
    o.append(record_page(checks.T2, g) + record_page(checks.T3, g) + "</section>")
    # C3
    o.append('<section class="circuit">' + FIT_PLAIN
             + head("C3", "도어락 점검 · 기록: T4, T5, T6, T7", "준비 — door_lock.sof · 시간이 모자라면 12/4에 이어서")
             + '<img class="sketch-key" src="../그림/키배치.png"></div>')
    o.append(stage("단계 1 · door_lock.sof", load_steps("door_lock.sof"), "여섯 자리에 가운데 획이 떴나요?"))
    o += [record_page(t, g) for t in (checks.T4, checks.T5, checks.T6, checks.T7)]
    o.append(stage("단계 2 · 마치기 전", steps([
        ("어긋난 행 다시 보기", "표·순서·누른 키·실제 화면을 메모에 적어요"),
        ("사진·영상 옮기기", "사진 파일명대로 저장"),
        ("고친 파일 확인", "다른 곳에 복사해 고쳤으면 프로젝트 폴더에도 옮겨요"),
        ("키트 정리해서 반납", "실험실 밖으로 가져갈 수 없어요")]), "조교님께 확인받았나요?"))
    o.append("</section>")
    o.append('<div class="stage"><h2>부록 · 문제가 있을 때만 하는 확인</h2><table class="fix"><thead><tr><th></th><th>증상</th>'
             "<th>차례로 볼 것</th></tr></thead><tbody>"
             + "".join(f'<tr><td><span class="box"></span></td><td><b>{E(a)}</b></td><td>{E(b)}</td></tr>' for a, b in FIX)
             + "</tbody></table></div>")
    return "\n".join(o)


def record():
    lines = ["---", "schema: project-record/v1", "project: FPGA 디지털 도어락 1주차 (2026-11-27)",
             "filled_by: ~       # hand | vision | 미기입", "---", "", f"# {STEM.replace('_', ' ')} 기록", "",
             "> 실제 결과: 맞으면 ✓, 다르면 실제 화면, 안 본 행은 비워 둔다.", ""]
    for t in checks.TABLES:
        lines += [f"### {t.id} · {t.title}", "", f"> {t.purpose}", ""]
        cols = ["순서"] + (["항목"] if t.has_item else []) + ["누를 키", "예상 화면", "실제 결과", "사진 파일명"]
        lines += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for r in t.rows:
            want = " → ".join(f'"{s}"' for s in r.show)
            want = f"{want} ({r.note})" if want and r.note else want or r.note
            lines.append("| " + " | ".join([r.no] + ([r.item] if t.has_item else []) + [r.do, want, "", r.photo]) + " |")
        lines += ["", "- 메모:", ""]
    return "\n".join(lines)


def main():
    checks.check_sof()
    p, g = checks.pins(), checks.glyphs()
    if "--skip-sim" not in sys.argv:
        print(checks.simulate())
    figures.build()
    chrome = config.load_course_info(ROOT).get("chrome") or DEFAULT_CHROME
    tmpl = (ROOT / ".claude/skills/prep-lab-checklist/template.html").read_text(encoding="utf-8")
    out = HERE / f"{STEM}_체크리스트.html"
    page = EXTRA + tmpl.replace("{{TITLE}}", TITLE).replace("{{COMMON}}", "").replace("{{CLOSING}}", "")
    out.write_text(page.replace("{{CIRCUITS}}", body(g, p)), encoding="utf-8")
    fit_pages(out, chrome=chrome)
    found = validate.check_rendered_html(out) + validate.check_embedded_images(out)
    if found:
        raise SystemExit("\n".join(map(str, found)))
    html_to_pdf(out, out.with_suffix(".pdf"), chrome=chrome)
    try:
        print("기록:", write_record(HERE / f"{STEM}_기록.md", record())["status"])
    except RecordExistsError as e:
        print(e)


if __name__ == "__main__":
    main()
