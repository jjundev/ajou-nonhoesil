"""점검표 데이터 하나와 그 검증.

HTML, 기록.md, Questa 대조가 모두 여기의 표를 쓴다. 행의 동작은 다음 중 하나다.
  ("keys", "1234K")    키를 차례로 누른다. K=OK C=CHG R=RST B=BS X=CLR Z=pb11, 숫자는 숫자 키
  ("see", "OPEn")      화면이 이 여섯 글자여야 한다
  ("msg",)             메시지 1.5초가 끝나기를 기다린다
  ("lock", 10, "5KX")  잠금 10초를 1초씩 확인하고 그동안 키를 누른다. 끝나면 ------
  ("lockhold", 20)     잠금이 풀리기 전에 키 5를 누르고 풀린 뒤까지 쥔다
"""
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

FPGA = Path(__file__).resolve().parents[1] / "FPGA"
QUESTA = Path(r"C:\intelFPGA_lite\22.1std\questa_fse\win64")


@dataclass
class Row:
    no: str
    do: str                 # 인쇄하는 조작
    acts: list              # 시뮬레이션으로 재생하는 조작
    show: list              # 인쇄하는 화면(차례)
    note: str = ""          # 화면 옆 짧은 설명
    item: str = ""          # 평가 항목
    photo: str = ""


@dataclass
class Table:
    id: str
    title: str
    purpose: str
    setup: str
    rows: list
    sim: str = ""           # door | board | "" (시뮬레이션 없음)
    has_item: bool = False
    notes: list = field(default_factory=list)


def K(s): return ("keys", s)
def S(s): return ("see", s)


MSG = ("msg",)
ERR = [S("Error"), MSG, S("------")]
W = [K("9999K"), *ERR]

T1 = Table("T1", "예제 동작 확인", "예제가 OPEN을 띄우는지 보고 키트·케이블·드라이버가 정상인지 확인한다.",
           "example.sof를 넣은 직후", [
               Row("1", "Enter(pb12) → 2 → 5 → 8 → 0 → Enter(pb12)", [], [], "OPEN",
                   photo="1주차 T1 예제 OPEN.jpg")])


def _t2():
    rows = [Row("시작", "아무 키도 누르지 않아요", [S("------")], ["------"])]
    for n in range(16):
        cnt = (n + 1) * 10 % 100
        if n == 11:
            rows.append(Row("pb11", "pb11을 10번 눌러요", [("pb", 11, 10), S("Error")], ["Error"],
                            "누를 때마다 글자 화면이 바뀌고 열 번째가 Error"))
            continue
        scr = f"{n:02d}--{cnt:02d}"
        note = "오른쪽 두 자리가 20 증가(pb11의 10번 포함)" if n == 12 else (
            "99 다음은 00" if n == 9 else "")
        rows.append(Row(f"pb{n}", f"pb{n}을 10번 눌러요", [("pb", n, 10), S(scr)], [scr], note,
                        photo="1주차 T2 pb15.jpg" if n == 15 else ""))
    rows += [
        Row("동시 1", "pb0을 누른 채 있어요", [("down", 0), S("00--61")], ["00--61"]),
        Row("동시 2", "pb0을 쥔 채 pb1을 눌렀다 떼요", [("down", 1), ("up", 1), S("00--61")], ["00--61"],
            "그대로"),
        Row("동시 3", "모두 뗀 뒤 pb1을 한 번 눌러요", [("up", 0), S("00--61"), ("pb", 1, 1), S("01--62")],
            ["01--62"]),
    ]
    return rows


T2 = Table("T2", "키 16개 점검",
           "키마다 번호가 맞는지, 한 번 누를 때 한 번만 세는지 확인한다.",
           "board_check.sof를 넣은 직후 · 키마다 끝날 때 화면을 봐요 · 왼쪽 두 자리는 pb 번호, "
           "오른쪽 두 자리는 누른 횟수 · 도중에 어긋나면 그 키의 앞뒤 차이를 적고 다음 키로 가요",
           _t2(), sim="board")

PAGES = ["OPEn", "Error", "nonE", "donE", "InIt", "nEW", "AGAIn", "LOCK09"]
T3 = Table("T3", "글자 8장 점검",
           "도어락에서 쓰는 글자를 모두 읽을 수 있고 잔상이 없는지 확인한다.",
           "T2에 이어서 · pb0을 한 번 누른 다음 pb11을 눌러요 · 못 읽는 글자와 비치는 자리를 적어요",
           [Row(str(i + 1), ("pb0 한 번 → " if i == 0 else "") + "pb11",
                ([("pb", 0, 1)] if i == 0 else []) + [("pb", 11, 1), S(p)], [p],
                {"nEW": "W를 읽을 수 있나요?", "AGAIn": "G를 6과 구별할 수 있나요?",
                 "LOCK09": "K를 읽을 수 있나요?"}.get(p, ""),
                photo=f"1주차 T3 {p}.jpg" if p in ("nEW", "AGAIn", "LOCK09") else "")
            for i, p in enumerate(PAGES)], sim="board")

T4 = Table("T4", "입력·정답·오답", "숫자 입력과 지우기, 정답·오답·빈 입력, 6자리 초과를 확인한다.",
           "door_lock.sof를 넣은 직후", sim="door", has_item=True, rows=[
               Row("1", "아무 키도 누르지 않아요", [S("------")], ["------"]),
               Row("2", "1 → 2", [K("12"), S("12----")], ["12----"]),
               Row("3", "pb11", [K("Z"), S("12----")], ["12----"], "그대로"),
               Row("4", "3 → 4 → 5 → 6 → 7", [K("34567"), S("234567")], ["234567"],
                   "마지막 여섯 숫자만", "E8", "1주차 T4 E8.jpg"),
               Row("5", "OK", [K("K"), *ERR], ["Error", "------"], "1.5초 뒤 ------", "E1 E8",
                   "1주차 T4 E1 Error.jpg"),
               Row("6", "1 → 2 → 3 → BS", [K("123B"), S("12----")], ["12----"], "", "A1", "1주차 T4 A1.jpg"),
               Row("7", "CLR → BS", [K("X"), S("------"), K("B"), S("------")], ["------"], "", "A1"),
               Row("8", "1 → 2 → 3 → 4 → OK", [K("1234K"), S("OPEn")], ["OPEn"], "", "E1",
                   "1주차 T4 E1 OPEN.jpg"),
               Row("9", "5 → BS → CLR", [K("5BX"), S("OPEn")], ["OPEn"], "그대로"),
               Row("10", "OK", [K("K"), S("------")], ["------"], "문 닫힘"),
               Row("11", "CHG → RST", [K("CR"), S("------")], ["------"], "그대로"),
               Row("12", "OK", [K("K"), S("nonE"), MSG, S("------")], ["nonE", "------"],
                   "1.5초 뒤 ------", "E5", "1주차 T4 E5.jpg"),
               Row("13", "1 → 2 → 3 → 4 → OK → OK", [K("1234K"), S("OPEn"), K("K"), S("------")],
                   ["OPEn", "------"], "열고 닫아 오답 횟수를 0으로"),
           ])

T5 = Table("T5", "LOCK", "세 번 틀리면 잠기고, 잠금 중에는 키가 안 먹고, 풀린 직후 입력되는지 확인한다.",
           "T4에 이어서(비밀번호 1234, 오답 0회) · 잠금 시간은 휴대폰 초시계로도 재서 실제 결과에 적어요",
           sim="door", has_item=True, rows=[
               Row("1", "9 → 9 → 9 → 9 → OK", W, ["Error", "------"], "오답 1회", "E2"),
               Row("2", "9 → 9 → 9 → 9 → OK", W, ["Error", "------"], "오답 2회", "E2"),
               Row("3", "9 → 9 → 9 → 9 → OK, 잠긴 동안 5·OK·CLR", [K("9999K"), ("lock", 10, "5KX")],
                   ["LOCK10", "LOCK01", "------"], "Error 없이 바로 · 키는 무반응 · 10초", "E2 E9",
                   "1주차 T5 E2.jpg"),
               Row("4", "OK를 세 번(nonE가 사라진 뒤 다음)",
                   [K("K"), S("nonE"), MSG, S("------"), K("K"), S("nonE"), MSG, S("------"),
                    K("K"), ("lockhold", 20)],
                   ["nonE", "nonE", "LOCK20"], "빈 입력도 오답 · 20초", "E3 E5 A2", "1주차 T5 E3.jpg"),
               Row("5", "LOCK03쯤 5를 누르고 풀린 뒤까지 쥐어요 → 떼요", [S("------")], ["------"],
                   "5가 입력되지 않음", "E9", "1주차 T5 E9.jpg"),
               Row("6", "9999 OK를 세 번(Error가 사라진 뒤 다음)", [*W, *W, K("9999K"), ("lock", 40, "")],
                   ["LOCK40", "------"], "40초", "A2", "1주차 T5 A2.jpg"),
               Row("7", "9999 OK를 세 번", [*W, *W, K("9999K"), ("lock", 40, "")],
                   ["LOCK40", "------"], "더 늘지 않고 40초", "A2"),
               Row("8", "1 → 2 → 3 → 4 → OK → OK", [K("1234K"), S("OPEn"), K("K"), S("------")],
                   ["OPEn", "------"], "맞히면 잠금 시간 초기화", "A2"),
               Row("9", "9999 OK를 세 번", [*W, *W, K("9999K"), ("lock", 10, "")],
                   ["LOCK10", "------"], "10초로 복귀", "A2"),
               Row("10", "풀리자마자 1 → 2 → 3 → 4 → OK → OK", [K("1234K"), S("OPEn"), K("K"), S("------")],
                   ["OPEn", "------"], "", "E9"),
           ])

T6 = Table("T6", "비밀번호 변경·초기화", "변경의 예외 처리와 변경 뒤 이전 비밀번호, 초기화를 확인한다.",
           "T5에 이어서(비밀번호 1234, 문 닫힘)", sim="door", has_item=True, rows=[
               Row("1", "1 → 2 → 3 → 4 → OK → CHG", [K("1234K"), S("OPEn"), K("C"), S("nEW")],
                   ["OPEn", "nEW"]),
               Row("2", "OK", [K("K"), S("Error"), MSG, S("OPEn")], ["Error", "OPEn"], "1.5초 뒤 OPEn", "E6",
                   "1주차 T6 E6.jpg"),
               Row("3", "CHG → 1 → 2 → 3 → OK", [K("C123"), S("123---"), K("K"), S("Error"), MSG, S("OPEn")],
                   ["Error", "OPEn"], "3자리라 거부", "E6"),
               Row("4", "CHG → 5678 → OK → 5679 → OK",
                   [K("C5678K"), S("AGAIn"), K("5679K"), S("Error"), MSG, S("OPEn")],
                   ["AGAIn", "Error", "OPEn"], "두 입력이 달라 거부", "A3", "1주차 T6 A3.jpg"),
               Row("5", "OK → 1 → 2 → 3 → 4 → OK", [K("K"), S("------"), K("1234K"), S("OPEn")],
                   ["------", "OPEn"], "이전 비밀번호 그대로", "A3"),
               Row("6", "CHG → 5678 → OK → 5678 → OK",
                   [K("C5678K"), S("AGAIn"), K("5678K"), S("donE"), MSG, S("------")],
                   ["AGAIn", "donE", "------"], "변경하고 문 닫힘", "E4", "1주차 T6 E4 donE.jpg"),
               Row("7", "CHG", [K("C"), S("------")], ["------"], "닫힌 상태라 무시", "E10"),
               Row("8", "1 → 2 → 3 → 4 → OK", [K("1234K"), *ERR], ["Error", "------"], "이전 비밀번호 거부", "E4"),
               Row("9", "5 → 6 → 7 → 8 → OK", [K("5678K"), S("OPEn")], ["OPEn"], "틀린 뒤에도 열림", "E10"),
               Row("10", "CHG → 4321 → OK → 4322 → OK",
                   [K("C4321K"), S("AGAIn"), K("4322K"), S("Error"), MSG, S("OPEn")],
                   ["AGAIn", "Error", "OPEn"], "", "E10"),
               Row("11", "CHG → 4321 → OK → 4321 → OK",
                   [K("C4321K"), S("AGAIn"), K("4321K"), S("donE"), MSG, S("------")],
                   ["AGAIn", "donE", "------"], "바로 다시 변경", "E10", "1주차 T6 E10.jpg"),
               Row("12", "4 → 3 → 2 → 1 → OK", [K("4321K"), S("OPEn")], ["OPEn"], "", "E10"),
               Row("13", "RST", [K("R"), S("InIt"), MSG, S("------")], ["InIt", "------"],
                   "1234로 복원하고 문 닫힘", "E7", "1주차 T6 E7.jpg"),
               Row("14", "4 → 3 → 2 → 1 → OK", [K("4321K"), *ERR], ["Error", "------"], "", "E7"),
               Row("15", "1 → 2 → 3 → 4 → OK → OK", [K("1234K"), S("OPEn"), K("K"), S("------")],
                   ["OPEn", "------"], "", "E7"),
           ])

TABLES = [T1, T2, T3, T4, T5, T6]


# ---------------------------------------------------------------- 7 Segment 글자
def glyphs() -> dict:
    """글자 → 세그먼트 값. rtl/glyphs.vh 와 rtl/seg_driver.v 를 읽는다."""
    names = dict(re.findall(r"G_(\w+)\s*=\s*5'd(\d+)", (FPGA / "rtl/glyphs.vh").read_text(encoding="utf-8")))
    src = (FPGA / "rtl/seg_driver.v").read_text(encoding="utf-8")
    out = {d: int(h, 16) for d, h in re.findall(r"5'd(\d):\s*seg = 8'h([0-9A-F]{2})", src)}
    for n, h in re.findall(r"G_(\w+):\s*seg = 8'h([0-9A-F]{2})", src):
        out["-" if n == "DASH" else n] = int(h, 16)
    out["O"] = out[names["O"]]
    out[" "] = 0
    return out


def pad(s: str) -> str:
    return s.ljust(6)


# ---------------------------------------------------------------- Questa 대조
_KEYPB = {"1": 0, "2": 1, "3": 2, "C": 3, "4": 4, "5": 5, "6": 6, "R": 7, "7": 8, "8": 9, "9": 10,
          "Z": 11, "K": 12, "0": 13, "B": 14, "X": 15}


def _hex(s, g):
    return "48'h" + "".join(f"{g[c]:02X}" for c in pad(s))


def _tb(kind, tables, g) -> tuple[str, int]:
    body, checks = [], 0
    for t in tables:
        for r in t.rows:
            tag = f"{t.id}-{r.no}"
            if not set(r.show) <= {a[1] for a in r.acts if a[0] == "see"} | {
                    f"LOCK{a[1]:02d}" for a in r.acts if a[0] in ("lock", "lockhold")} | {
                    x for a in r.acts if a[0] == "lock" for x in ("LOCK01", "------")}:
                raise ValueError(f"{tag}: 인쇄하는 화면이 재생에 없다")
            def see(s):
                nonlocal checks
                checks += 1
                body.append(f'    chk({_hex(s, g)}, "{tag.replace("시작", "s").replace("동시 ", "d")}");')
            for a in r.acts:
                if a[0] == "keys":
                    body += [f"    press({_KEYPB[c]});" for c in a[1]]
                elif a[0] == "pb":
                    body.append(f"    repeat ({a[2]}) press({a[1]});")
                elif a[0] in ("down", "up"):
                    body.append(f"    pb[{a[1]}] = {int(a[0] == 'up')}; w(4*T);")
                elif a[0] == "msg":
                    body.append("    w(CPS + CPS/2);")
                elif a[0] == "see":
                    see(a[1])
                elif a[0] == "lock":
                    for i, sec in enumerate(range(a[1], 0, -1)):
                        see(f"LOCK{sec:02d}")
                        key = a[2][i % len(a[2])] if a[2] else None
                        if key:
                            body.append(f"    press({_KEYPB[key]});")
                            see(f"LOCK{sec:02d}")
                        body.append(f"    w(CPS{' - 8*T' if key else ''});")
                    see("------")
                elif a[0] == "lockhold":
                    see(f"LOCK{a[1]:02d}")
                    body.append(f"    w({a[1] - 3}*CPS);")
                    see("LOCK03")
                    body.append("    pb[5] = 0; w(4*CPS);")
                    see("------")
                    body.append("    pb[5] = 1; w(4*T);")
                    see("------")
    top = "door_lock" if kind == "door" else "board_check"
    extra = ", .LOCK_SEC(10)" if kind == "door" else ""
    return f"""`timescale 1ns/1ps
module tb_check_{kind};
  localparam CPS = 20000, T = CPS/100;
  reg clk = 0; reg [15:0] pb = 16'hFFFF;
  wire [5:0] fnd_s; wire [7:0] fnd_d;
  reg [47:0] shown = 0; integer errors = 0, checks = 0, m;
  always #10 clk = ~clk;
  {top} #(.CLK_PER_SEC(CPS), .POR_CYCLES(50), .BLANK_CLK(1){extra}) dut (
    .clock_50m(clk), .pb(pb), .fnd_s(fnd_s), .fnd_d(fnd_d));
  always @(negedge clk) for (m = 0; m < 6; m = m + 1) if (fnd_s[m] === 1'b0) shown[m*8 +: 8] = fnd_d;
  task w(input integer c); begin repeat (c) @(posedge clk); #1; end endtask
  task press(input integer n); begin pb[n] = 0; w(4*T); pb[n] = 1; w(4*T); end endtask
  task chk(input [47:0] e, input [8*8-1:0] tag); begin
    checks = checks + 1;
    if (shown !== e) begin errors = errors + 1;
      $display("FAIL %0s want %h got %h", tag, e, shown); end end endtask
  initial begin
    w(10*T);
""" + "\n".join(body) + f"""
    $display("RESULT %0s tb_check_{kind} checks=%0d errors=%0d", errors ? "FAIL" : "PASS", checks, errors);
    $finish;
  end
endmodule
""", checks


def simulate() -> str:
    """표의 모든 행을 RTL 에서 재생한다. 하나라도 다르면 멈춘다."""
    g, report = glyphs(), []
    work = Path(tempfile.mkdtemp(prefix="doorlock_check_"))   # vopt 는 한글 경로를 못 읽는다
    try:
        shutil.copytree(FPGA / "rtl", work / "rtl")
        counts = {}
        for kind in ("board", "door"):
            text, counts[kind] = _tb(kind, [t for t in TABLES if t.sim == kind], g)
            (work / f"tb_check_{kind}.v").write_text(text, encoding="ascii")
        run = lambda *a: subprocess.run([str(QUESTA / a[0]), *a[1:]], cwd=work, capture_output=True,
                                        text=True, errors="replace", timeout=900).stdout
        run("vlib.exe", "work")
        out = run("vlog.exe", "-quiet", "-vlog01compat", "+incdir+rtl", "-work", "work",
                  *[f"rtl/{p.name}" for p in sorted((work / "rtl").glob("*.v"))],
                  "tb_check_board.v", "tb_check_door.v")
        if "Error" in out:
            raise SystemExit("Questa 컴파일 실패\n" + out)
        for kind, n in counts.items():
            for _ in range(60):     # Questa Starter 는 한 번에 하나만 돈다. 다른 작업이 쓰면 기다린다
                if "vsimk.exe" not in subprocess.run(["tasklist"], capture_output=True, text=True, errors="replace").stdout:
                    out = run("vsim.exe", "-c", "-lib", "work", f"tb_check_{kind}", "-do", "run 60 sec; quit -f")
                    if "License checkout" not in out:
                        break
                time.sleep(5)
            else:
                raise SystemExit("Questa 를 다른 작업이 쓰고 있다")
            want = f"RESULT PASS tb_check_{kind} checks={n} errors=0"
            if want not in out:
                raise SystemExit(f"{kind}: 예상 화면이 RTL 과 다르다\n" + "\n".join(
                    x for x in out.splitlines() if re.search(r"FAIL|RESULT|Error|Fatal", x)))
            report.append(f"{kind} 화면 {n}번 대조 일치")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return " · ".join(report)


# ---------------------------------------------------------------- 핀·sof
def check_sof() -> None:
    for top in ("board_check", "door_lock"):
        qsf = (FPGA / f"quartus/{top}.qsf").read_text(encoding="utf-8")
        files = [FPGA / "quartus" / p for p in re.findall(r"VERILOG_FILE\s+(\S+)", qsf)]
        files += list((FPGA / "rtl").glob("*.vh"))
        sof = FPGA / f"quartus/output_files/{top}.sof"
        old = [f.name for f in files if f.stat().st_mtime > sof.stat().st_mtime]
        # 공용 .vh 는 쓰지 않는 쪽에도 걸리지만 다시 컴파일하면 그만이다
        if top == "board_check":
            old = [n for n in old if n != "door_defs.vh"]
        if old:
            raise SystemExit(f"{top}.sof 가 {old} 보다 오래됐다. Quartus 로 다시 컴파일한다")


def pins() -> dict:
    import openpyxl
    book = FPGA.parents[2] / "강의노트/설계과제/설계 자료(26-2)/FPGA pin map.xlsx"
    want = {r[0]: r[1] for r in openpyxl.load_workbook(book).active.iter_rows(values_only=True) if r[0]}
    for top in ("board_check", "door_lock"):
        qsf = (FPGA / f"quartus/{top}.qsf").read_text(encoding="utf-8")
        got = {n: p for p, n in re.findall(r"set_location_assignment (\S+) -to (\S+)", qsf)}
        if got != want:
            raise SystemExit(f"{top}.qsf 핀이 핀맵과 다르다: "
                             f"{sorted(set(got.items()) ^ set(want.items()))}")
    return {k: v.replace("PIN_", "") for k, v in want.items()}


if __name__ == "__main__":
    check_sof()
    print(len(pins()), "핀 일치")
    print(simulate())
