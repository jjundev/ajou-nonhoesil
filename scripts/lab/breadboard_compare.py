"""결선도 격리 재생성물을 승인본과 대조한다.

**넷으로 본다, 홀로 보지 않는다** — `hand_compare` 와 같은 이유. 재생성 빌더가
칩을 한 행 위에 놓아도 넷이 같으면 그림은 유효하고, 그 좌표 차이는 H9·H10
(표기) 로만 나온다. 치명·기능이 나오면 넷이 다른 것이다.

네 축을 잰다.

1. 넷 — 보드마다 `hand_compare.compare(ref, hand)` (H1~H10·H14; 손그림 서류
   규칙 H11~H13 은 뺀다)
2. 자리 — 빌더가 실제로 앉힌 칩 자리 vs netlist `kind: layout` 표
3. 전환 — 보드 사슬을 기준선으로 이어 그렸을 때 `steps`·`kept`·`removed()`·
   `swaps` 수
4. 파일명 — `실험NN_<소단원>_결선도_<회로명>[_<k>단계_<이름>].png`

승인본 쪽 값도 **같은 함수로** 잰다 — 설계 문서의 표를 베끼면 표가 낡았을 때
도구가 그것을 못 본다. 승인본·재생성 `배치.py` 는 저장소 엔진 하나
(`hand_grid.load_renderer()`)로 이름을 달리해 따로 로드한다.

판정은 사람이 한다. `judge()` 는 셀 수 있는 것만 세고 「사람이 볼 것」 으로 끝난다.
"""

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import md
from .hand_compare import BLOCKING, _from_wiring, compare
from .hand_grid import load_renderer
from .netlist_parser import parse_netlist

PAPERWORK = ("H11", "H12", "H13")   # 제목·서명·전사 불확실 — 손그림에만 있는 것
_SEAT = re.compile(r"(좌|우)\s*(\d+)행")
_BLOCK = {"좌": "left", "우": "right"}
STAGE_RE = re.compile(r"^실험(\d{2})_(\d+(?:-\d+)?)_결선도_(.+)_(\d+)단계_([^_]+)\.png$")
FINAL_RE = re.compile(r"^실험(\d{2})_(\d+(?:-\d+)?)_결선도_(.+)\.png$")


def load_board_at(path, name):
    """주차 결선 파일(`배치.py`)을 경로에서 로드한다. `name` 은 모듈마다 달라야 한다."""
    return load_renderer().load_board_file(path, name)


@dataclass
class Board:
    name: str        # PNG 파일명
    cid: str         # 빌더 이름에서 `build_` 를 뗀 것 — hand_compare 의 회로 ID 자리
    stage: object    # None 이면 완성 상태
    bb: object       # 렌더러 (export 까지 마쳐 overlaps 가 차 있다). 죽었으면 None
    error: str       # 빌더가 죽었으면 그 메시지

    def __str__(self):
        return f"{self.name} ({self.cid}, stage={self.stage}){' ✗ ' + self.error if self.error else ''}"


def _cid(fn):
    return getattr(fn, "__name__", "?").removeprefix("build_")


def _call(fn, path, template_path, stage, baseline):
    """빌더를 규약 시그니처로 부른다. 시그니처가 다르면 위치 인자 둘로 한 번 더 —
    그것도 죽으면 오류 문자열. 어느 쪽이었는지는 오류 문자열에 남긴다.

    TypeError 라고 다 시그니처 문제는 아니다 — 빌더 안쪽(예: `stage` 분기)에서
    난 TypeError 도 여기로 온다. 그걸 시그니처 불일치로 오인해 `(path,
    template_path)` 로 다시 부르면 stage 없는 완성 보드가 조용히 그 자리를
    대신한다. `e.__traceback__.tb_next` 로 가른다 — 인자 바인딩 실패는 호출
    프레임에서 바로 나서 다음 프레임이 없고, 빌더 내부 실패는 있다."""
    try:
        return fn(path, template_path, stage=stage, baseline=baseline), ""
    except TypeError as e:
        if e.__traceback__.tb_next is not None:   # 빌더 안쪽에서 난 TypeError — 시그니처 문제가 아니다
            return None, f"TypeError: {e}"
        try:
            return fn(path, template_path), f"stage/baseline 인자를 안 받는다 ({e})"
        except Exception as e2:  # noqa: BLE001 — 판정 재료다
            return None, f"{type(e2).__name__}: {e2}"
    except Exception as e:  # noqa: BLE001 — verify() 의 AssertionError 가 여기로 온다
        return None, f"{type(e).__name__}: {e}"


def render_chain(boards, out_dir, template_path=None):
    """`EN_BOARDS` 모양의 [(파일명, 빌더, stage)] 를 앞 보드를 기준선으로 이어 그린다.

    빌더가 죽으면 그 보드는 `error` 를 갖고 다음 보드는 기준선 없이 간다 —
    한 장이 죽었다고 사슬 전체를 못 보는 것보다 낫다.
    """
    os.makedirs(out_dir, exist_ok=True)
    out, base = [], None
    for name, fn, stage in boards:
        bb, err = _call(fn, os.path.join(out_dir, name), template_path, stage, base)
        if bb is None and not err:
            err = "빌더가 렌더러를 돌려주지 않는다 — 끝에 `return bb` 가 없다"
        board = Board(name, _cid(fn), stage, bb, err)
        out.append(board)
        base = None
        if bb is not None:
            try:
                base = bb.snapshot()
            except Exception as e:  # noqa: BLE001 — 판정 재료다. snapshot() 도 죽을 수 있다 —
                # 이 보드는 그렸지만 기준선을 못 낸다. `error` 에 적고 다음 보드는
                # 기준선 없이 간다(빌더가 죽었을 때와 같은 계약).
                msg = f"snapshot() 실패: {type(e).__name__}: {e}"
                board.error = f"{board.error} · {msg}" if board.error else msg
    return out


def render_finals(finals, out_dir, template_path=None):
    """완성본 — 기준선 없이."""
    os.makedirs(out_dir, exist_ok=True)
    out = []
    for name, fn in finals:
        bb, err = _call(fn, os.path.join(out_dir, name), template_path, None, None)
        if bb is None and not err:
            err = "빌더가 렌더러를 돌려주지 않는다 — 끝에 `return bb` 가 없다"
        out.append(Board(name, _cid(fn), None, bb, err))
    return out


def pair_boards(ref, new):
    """이름이 같은 것끼리 먼저, 남은 것끼리는 순서로. 남는 쪽은 None 짝.

    같은 이름이 둘이면(재생성이 한 파일명에 두 장을 썼다 — 이 도구가 잡아야 할
    결함이다) 큐로 하나씩 소비한다 — dict 로 접으면 앞 장이 조용히 사라진다.
    """
    from collections import defaultdict, deque
    queue = defaultdict(deque)
    for b in new:
        queue[b.name].append(b)
    pairs = []
    for r in ref:
        pairs.append([r, queue[r.name].popleft() if queue[r.name] else None])
    ids = {id(p[1]) for p in pairs}
    rest = [b for b in new if id(b) not in ids]
    for p in pairs:
        if p[1] is None and rest:
            p[1] = rest.pop(0)
    return [tuple(p) for p in pairs] + [(None, b) for b in rest]


def _compare_diagrams(ref_d, new_d):
    new_d.signed = True
    new_d.title = ref_d.circuit
    return [f for f in compare(ref_d, new_d) if f.rule not in PAPERWORK]


def net_findings(ref, new):
    """승인본 보드 vs 재생성 보드. 어느 쪽이든 못 그렸으면 빈 목록 — 그 사실은
    `error` 가 따로 말한다."""
    if ref is None or new is None or ref.bb is None or new.bb is None:
        return []
    return _compare_diagrams(_from_wiring(ref.bb.wiring(), ref.cid),
                             _from_wiring(new.bb.wiring(), ref.cid))


def layout_slots(netlist_path):
    """netlist `kind: layout` 표 → {'S1': ('left', 7), …}. 절이 없으면 빈 dict."""
    layouts = parse_netlist(Path(netlist_path)).of_kind("layout")
    if not layouts:
        return {}
    slots = {}
    for row in md.parse_tables(layouts[0].body)[0].rows:
        m = _SEAT.search(row[1])
        if m:
            slots[row[0].strip()] = (_BLOCK[m.group(1)], int(m.group(2)))
    return slots


def seats(boards):
    """보드들이 실제로 앉힌 (block, pin1_row) → 그 자리에 앉았던 칩 라벨 집합."""
    out = {}
    for b in boards:
        if b.bb is None:
            continue
        for ch in b.bb.wiring()["chips"]:
            out.setdefault((ch["block"], ch["pin1_row"]), set()).add(ch["label"])
    return out


def transition(board):
    """보드 하나의 전환 수치 다섯 개: `steps`(번호 받은 줄) · `kept`(회색으로 남긴 것) ·
    `removed`(걷는다 표에 올라간 것) · `swaps`(칩 교체·삽입) · `partial`(단계가 회로
    전체를 다 그리지 못했는지). 빌더가 죽어 `board.bb` 가 없으면(또는 `board` 자체가
    None, 즉 짝이 없으면) 다섯 값 모두 `None` — 「0」 이 아니다, 재지 못했다는 뜻이다."""
    if board is None or board.bb is None:
        return {"name": board.name if board else "—", "steps": None, "kept": None,
                "removed": None, "swaps": None, "partial": None,
                "error": board.error if board else "짝 없음"}
    bb = board.bb
    return {"name": board.name, "steps": len(bb.steps), "kept": len(bb.kept),
            "removed": len(bb.removed()), "swaps": len(bb.swaps),
            "partial": bool(bb.partial), "error": board.error}


def sub_items(netlist_path):
    """회로 절의 `item`(`E1.P1-1`) 에서 `P` 뒤 토큰 — 파일명의 <소단원> 후보."""
    out = set()
    for sec in parse_netlist(Path(netlist_path)).of_kind("circuit"):
        if sec.item and ".P" in sec.item:
            out.add(sec.item.split(".P", 1)[1])
    return out


def check_filename(name, subs):
    """규칙에 맞으면 ''. 아니면 이유 한 줄."""
    m = STAGE_RE.match(name) or FINAL_RE.match(name)
    if not m:
        return "틀이 `실험NN_<소단원>_결선도_<회로명>[_<k>단계_<이름>].png` 가 아니다"
    if m.group(2) not in subs:
        return f"<소단원> `{m.group(2)}` 이 명세 항목에 없다 (후보: {', '.join(sorted(subs))})"
    if not STAGE_RE.match(name) and "단계" in m.group(3):
        return "단계 표기가 `_<k>단계_<이름>` 순서가 아니거나 회로명이 없다"
    return ""


def _grade_counts(findings):
    c = {"치명": 0, "기능": 0, "표기": 0, "보류": 0}
    for f in findings:
        c[f.grade] = c.get(f.grade, 0) + 1
    return c


def _pair_table(pairs, title):
    L = [f"### {title}", "", "| 승인본 | 재생성 | 치명 | 기능 | 표기 | 빌더 오류 |", "|---|---|---|---|---|---|"]
    detail, every = [], []
    for ref, new in pairs:
        fs = net_findings(ref, new)
        every += fs
        c = _grade_counts(fs)
        err = (ref.error if ref else "") or (new.error if new else "")
        L.append(f"| {ref.name if ref else '—'} | {new.name if new else '—'} | "
                 f"{c['치명']} | {c['기능']} | {c['표기']} | {err} |")
        for f in fs:
            detail.append(f"- {ref.name if ref else new.name} · {f.rule} {f.grade} · {f.where}: {f.message}")
    total = _grade_counts(every)
    L += ["", f"합계 치명 {total['치명']} · 기능 {total['기능']} · 표기 {total['표기']}", ""]
    L += detail + [""]
    return L


def judge(experiment, approved_board, regen_board, netlist_path, regen_png_dir,
          template_path, leak_hits=(), agent_report=""):
    """판정 초안. 셀 수 있는 것만 센다 — 갈린 자리에 규칙이 있었는지는 사람이
    SKILL.md 와 에이전트 보고를 놓고 가른다. 두 인자는 승인본·재생성 `배치.py` 경로다."""
    ref_mod = load_board_at(approved_board, f"board_approved_e{experiment}")
    new_mod = load_board_at(regen_board, f"board_regen_e{experiment}")
    boards_attr, finals_attr = "BOARDS", "FINALS"
    slots = layout_slots(netlist_path)
    subs = sub_items(netlist_path)
    regen_pngs = sorted(p.name for p in Path(regen_png_dir).glob("*.png"))

    with tempfile.TemporaryDirectory() as d:
        ref_b = render_chain(getattr(ref_mod, boards_attr), os.path.join(d, "ra"), template_path)
        ref_f = render_finals(getattr(ref_mod, finals_attr), os.path.join(d, "rf"), template_path)
        new_boards = getattr(new_mod, boards_attr, None)
        new_finals = getattr(new_mod, finals_attr, None)
        new_b = render_chain(new_boards, os.path.join(d, "na"), template_path) if new_boards else []
        new_f = render_finals(new_finals, os.path.join(d, "nf"), template_path) if new_finals else []

        L = [f"# 실험{experiment} breadboard-diagram 격리 재생성 판정 초안", "",
             "이 회차는 세션 메모리 주입 아래서 돌았다(verify-draft-lab-spec §절대 규칙 7).", "",
             f"## 1. 구조적 누출 {len(leak_hits)}건", ""]
        L += [f"- {h}" for h in leak_hits] + [""]

        nb = f"{len(new_b)}장" if new_boards else f"`{boards_attr}` 없음"
        nf = f"{len(new_f)}장" if new_finals else f"`{finals_attr}` 없음"
        L += [f"## 2. 보드 사슬 — 승인본 {len(ref_b)}장+완성본 {len(ref_f)}장 / 재생성 {nb}+완성본 {nf}", ""]
        L += [f"- 재생성 {b}" for b in new_b + new_f] + [""]

        bp = pair_boards(ref_b, new_b)
        fp = pair_boards(ref_f, new_f)
        L += ["## 3. 절차 그림 넷 대조 (H1~H10·H14 — 홀이 달라도 넷이 같으면 표기만 난다)", ""]
        L += _pair_table(bp, "절차 그림")
        L += ["## 4. 완성본 넷 대조", ""]
        L += _pair_table(fp, "완성본")

        used = seats(new_b + new_f)
        L += ["## 5. 칩 자리 — netlist `kind: layout` vs 재생성 보드가 앉힌 자리", "",
              "| 슬롯 | 자리표 | 재생성이 그 자리에 앉힌 칩 |", "|---|---|---|"]
        for s, seat in slots.items():
            L.append(f"| {s} | {seat[0]} {seat[1]} | {', '.join(sorted(used.get(seat, set()))) or '—'} |")
        extra = {k: v for k, v in used.items() if k not in set(slots.values())}
        L += [""] + [f"- 자리표 밖 자리: {k[0]} {k[1]} ← {', '.join(sorted(v))}" for k, v in extra.items()] + [""]

        L += ["## 6. 전환 수치 (steps = 번호 받은 줄 · kept = 회색 · removed = 걷는다 표 · swaps = 칩 교체/삽입)", "",
              "| 승인본 | steps | kept | removed | swaps | partial | 재생성 | steps | kept | removed | swaps | partial |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for ref, new in bp:
            a, b = transition(ref), transition(new)
            L.append(f"| {a['name']} | {a['steps']} | {a['kept']} | {a['removed']} | {a['swaps']} | {a['partial']} "
                     f"| {b['name']} | {b['steps']} | {b['kept']} | {b['removed']} | {b['swaps']} | {b['partial']} |")
        L.append("")

        bad = [(n, check_filename(n, subs)) for n in regen_pngs]
        bad = [(n, why) for n, why in bad if why]
        L += [f"## 7. 파일명 {len(regen_pngs)}장 중 규칙 위반 {len(bad)}건", ""]
        L += [f"- {n}: {why}" for n, why in bad]
        L += [f"- (전체) {n}" for n in regen_pngs] + [""]

        L += ["## 8. 에이전트 보고 (원문)", "", agent_report or "(없음)", ""]
        L += ["## 9. 사람이 볼 것",
              "- 3·4절의 치명·기능마다: SKILL.md 에 그 넷을 정하는 문장이 **있었는가**(있는데 안 읽힘) / **없었는가**(규칙 없음). 8절 3항의 첫 렌더 결과로 verify() 가 잡았는지도 가른다.",
              "- 5절: 자리가 다르면 「슬롯」 문단이 자리 **선택**을 지시하는지 본다 — 자리표는 netlist 가 주므로 여기서 갈리면 netlist 를 안 읽은 것이다.",
              "- 6절: 재생성 kept 가 승인본보다 작으면 공통 배선을 같은 헬퍼·같은 순서로 안 그린 것(「기준선」 문단). removed 가 다르면 단계 분해가 다른 것.",
              "- 도구의 사각지대: 아무것도 꽂히지 않은 레일 구간의 브리지가 빠진 것은 넷 차이로 안 보인다(hand_compare 가 부착물 있는 넷만 본다). 실물 보드에서는 레일이 끊기므로 PNG 를 볼 때 브리지 수를 센다.",
              "- 7절: 파일명 갈림은 「파일명 규칙」 문단이 <소단원>·<이름> 을 어디서 가져오라 했는지 본다.",
              "- 1절의 누출 자리와 일치하는 것은 합격 근거로 세지 않는다.",
              "", "> 치명 0 은 넷이 같다는 뜻이고, 그림이 따라 그리기 좋다는 뜻이 아니다. PNG 는 눈으로 한 번 본다.", ""]
    return "\n".join(L)
