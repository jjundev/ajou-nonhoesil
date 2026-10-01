"""결선도의 **두 층 계약**을 강제한다.

이 그림은 제출물이 아니다. 운영계획서 3.2 6) 이 "직접 손으로 작성한 회로
결선도"를 요구하므로, 렌더 결과물은 조원이 **따라 그릴 원도**다. 그래서
무엇이 그림 위에 있어야 하고 무엇이 있으면 안 되는지가 갈린다.

  · 보드 위  — 손으로 옮겨 그릴 것 (배선, 칩, 핀 번호, 신호 이름 배지)
  · 보드 밖  — 옮겨 그릴 수 없는 것 (미사용핀을 접지하는 *이유*, 계측 지시)

2026-09 이전 판은 이 둘을 섞어 보드 위에 라벨 박스를 30개 넘게 얹었다. 그중
절반은 손으로 옮길 것이 하나도 없는 문구인데 하필 **따라 그릴 홀을 덮었다.**
같은 내용이 예비보고서 본문에 이미 문장으로 있었다.

문서로만 적어 두면 다음 주차 빌더가 조용히 옛 방식으로 돌아간다 — 옛 함수
(`draw_wire`, `draw_badge`)가 그대로 살아 있고 더 짧기 때문이다. 그래서 센다.
"""
import ast
import copy
import importlib.util
import re
import unittest
from collections import Counter
from pathlib import Path

from tests._boards import all_builders, board_files
from tests._renders import BOARD_L, BOARD_R, render

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / ".claude/skills/breadboard-diagram/scripts/render_breadboard.py"

# 보드 안쪽 x 범위. 이 밖에 앉는 배지는 여백이라 홀을 가리지 않는다

# 그림 한 장의 보드 위 배지 상한. 신호 이름(입력 A·B·C, 출력 L1·L2·X·Y·Z)만 남긴
# 결과가 한 장에 0~5 개다. 문구를 다시 얹기 시작하면 여기서 걸린다
MAX_ON_BOARD_LABELS = 8
# 신호 이름만으로 상한을 넘는 회로. 이름은 `test_신호_이름이_보드_안에_있다` 가 요구하므로
# 뺄 수 없다 — 문구 배지가 아니라 이름 개수가 넘는 경우만 여기 적는다.
#  · `build_e4_mux` 와 그 단계 래퍼(`build_e4_mux_s*`): 입력 7(E·S1·S0·D0~D3) + LED 4
#    (Y·L2·L3·L4) = 11 (2026-09-28). 키는 빌더 이름의 앞머리다
LABEL_EXCEPTIONS = {'build_e4_mux': 11}


def _label_cap(name):
    return next((v for k, v in LABEL_EXCEPTIONS.items() if name.startswith(k)), MAX_ON_BOARD_LABELS)


def _inter(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _badge_hits(bb, box, seg):
    """신호 이름 배지 상자가 가리는 것 — 번호 원, 꽂힌 홀, 자기 것이 아닌 배선, 다른 배지."""
    hits = [f'번호 원 {m}' for m in bb.marker_boxes if _inter(box, m)]
    for (hx, hr), what in bb._leads.items():
        if box[0] <= hx <= box[2] and box[1] <= bb.r_y(hr) <= box[3]:
            hits.append(f'홀 {what}')
    for j, (_kind, pts, desc) in enumerate(bb._segments):
        if j == seg:
            continue
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            n = int(max(abs(bx - ax), abs(by - ay)) / 2) + 1
            if any(box[0] < ax + (bx - ax) * k / n < box[2]
                   and box[1] < ay + (by - ay) * k / n < box[3] for k in range(n + 1)):
                hits.append(f'배선 {desc}')
                break
    hits += [f'배지 {n}' for n, b, _s in bb.tag_boxes if b is not box and _inter(box, b)]
    return hits


# 이미 맞닿아 있던 번호 원 — 새 겹침만 막고 이건 그대로 둔다. 빌더의 `marker_at` 을
# 옮기면 커밋된 PNG 도장이 바뀌어 `tests/test_breadboard_boards.py` 가 깨진다
# (2026-09-20 발견). 둘 다 별건으로 다룬다.
#
#  · `build_e3_fs` ⑲(좌 c19 → 우 a10)·㉒(좌 c11 → 우 a14) — 중심 (426,468)·(431,472),
#    거리 6.4px. 반지름 합 16px 안이라 **원이 실제로 포개진다.** 진짜 겹침이다.
#  · `build_e1_nand`·`build_e1_nor`·`build_e1_comb` ⑥(좌 d13 → 좌 GND레일13행)·
#    ⑭(좌 a9 → 좌 a18) — 중심 (231,457)·(219,468), 거리 16.3px. 반지름 합을 0.3px
#    넘겨 원끼리는 안 닿고 외접 상자 모서리만 겹친다. 아슬아슬하지만 읽힌다.
KNOWN_MARKER_OVERLAPS = {
    'build_e3_fs': [((418, 460, 434, 476), (423, 464, 439, 480))],
    'build_e1_nand': [((223, 449, 239, 465), (211, 460, 227, 476))],
    'build_e1_nor': [((223, 449, 239, 465), (211, 460, 227, 476))],
    'build_e1_comb': [((223, 449, 239, 465), (211, 460, 227, 476))],
}


def _module():
    spec = importlib.util.spec_from_file_location("render_breadboard", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _circuit_builders(mod):
    """모든 주차 `배치.py` 의 빌더 — 엔진 `mod` 로 불러 스파이가 그 클래스에 걸린다."""
    return all_builders(mod)


class BuilderApiContract(unittest.TestCase):
    """소스를 ast 로 읽어 옛 API 로 새는지 본다."""

    @staticmethod
    def _builder_like(tree):
        for n in tree.body:
            if isinstance(n, ast.FunctionDef) and (
                    n.name.startswith("build_") or n.name.startswith("_build_")
                    or re.match(r"_e\d+_", n.name)):
                yield n

    def _calls(self, node, attr):
        return [c for c in ast.walk(node)
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                and c.func.attr == attr]

    @staticmethod
    def _trees():
        """엔진과 주차 `배치.py` 전부 — 빌더는 주차 파일에, 헬퍼 일부는 엔진에 있다."""
        return [ast.parse(p.read_text(encoding="utf-8")) for p in [SRC, *board_files()]]

    def test_빌더가_번호_없는_배선을_그리지_않는다(self):
        bad = [n.name for t in self._trees() for n in self._builder_like(t)
               if self._calls(n, "draw_wire")]
        self.assertEqual(bad, [], f"{bad}: draw_wire 는 번호도 순서표도 남기지 않는다. "
                                  "step_wire 를 쓴다")

    def test_빌더가_보드_위에_배지를_직접_그리지_않는다(self):
        bad = [n.name for t in self._trees() for n in self._builder_like(t)
               if self._calls(n, "draw_badge")]
        self.assertEqual(bad, [], f"{bad}: 신호 이름은 signal_tag() 로(_input_jumper·draw_led 가 "
                                  "부른다), 꽂을 자리는 _tag() 로, 설명은 note() 로 보드 밖에 낸다")


def _missing_signal_names(bb):
    """보드 안 배지에 없는 신호 이름 — 개수로 센다.

    입력은 점퍼마다가 아니라 이름마다 배지가 하나라(e3 는 입력마다 좌·우 블록 점퍼가
    둘) 이름으로 중복을 지우고, LED 꼬리표는 그대로 센다. 실험3 반감산기는 입력 B 와
    출력 B 가 같은 글자라 집합으로 보면 둘째 B 배지가 빠져도 통과한다(2026-09-14
    패치 재현).
    """
    want = Counter(list(dict.fromkeys(i['name'] for i in bb.inputs))
                   + [ch['tag'] for ch in bb.led_chains]
                   + list(dict.fromkeys(p['name'] for p in bb.probes if p.get('name'))))
    got = Counter(n for n, box, _s in bb.tag_boxes
                  if BOARD_L < box[0] and box[2] < BOARD_R)
    return want - got


class RenderedContract(unittest.TestCase):
    """실제로 그려 보고 센다. ast 로는 위임을 못 따라간다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _module()
        cls.b1, cls.b2, cls.b3 = (cls.mod.load_board(n) for n in (1, 2, 3))

    def _render(self, fn):
        """`(렌더러, 보드 위 배지 수)` — 프로세스에서 한 번만 그린다(`tests/_renders.py`)."""
        return render(self.mod, fn)

    def test_모든_회로가_결선_순서표를_낸다(self):
        """번호와 순서표가 없으면 조원은 30가닥을 동시에 봐야 한다."""
        for name, fn in _circuit_builders(self.mod).items():
            with self.subTest(회로=name):
                bb, _ = self._render(fn)
                self.assertTrue(bb.numbered, f"{name}: enable_steps() 를 안 불렀다")
                self.assertGreater(len(bb.steps), 0, f"{name}: 결선 순서표가 비었다")

    def test_보드_위_꼬리표가_적다(self):
        for name, fn in _circuit_builders(self.mod).items():
            with self.subTest(회로=name):
                _, labels = self._render(fn)
                self.assertLessEqual(
                    labels, _label_cap(name),
                    f"{name}: 보드 위 라벨 {labels}개. 손으로 옮겨 그릴 것이 아니면 "
                    "note() 로 보드 밖에 낸다")

    def test_신호_이름이_보드_안에_있다(self):
        """2026-09 실험01 예보 조교 감점(-1): 손그림 결선도에 입력 A·B·C 위치 표기가
        없었다. 원도가 입력 이름을 보드 밖(x=12) 꼬리표에만 적었고, 학생은 보드
        판형 위만 따라 그려 그 글자가 옮겨지지 않았다."""
        for name, fn in _circuit_builders(self.mod).items():
            with self.subTest(회로=name):
                bb, _ = self._render(fn)
                self.assertEqual(_missing_signal_names(bb), Counter(),
                                 f"{name}: 보드 안에 없는 신호 이름")

    def test_둘째_B_배지가_빠지면_잡는다(self):
        """위 단언이 같은 글자를 개수로 세는지 — 반감산기 LED2 의 B 배지를 지워 본다."""
        bb, _ = self._render(self.b3.build_e3_hs)
        bb = copy.copy(bb)   # 나눠 쓰는 렌더러라 원본은 건드리지 않는다
        drop = max(k for k, (n, _b, _s) in enumerate(bb.tag_boxes) if n == 'B')
        bb.tag_boxes = [t for k, t in enumerate(bb.tag_boxes) if k != drop]
        self.assertEqual(_missing_signal_names(bb), Counter({'B': 1}))

    def test_실험02_계측_지점은_강의노트_이름을_단다(self):
        """실험02 는 입력 점퍼도 LED 도 없어 위 검사가 빈 집합으로 통과했다 — 신호원·
        채널 이름이 보드 밖 꼬리표에만 있었다(2026-09-14 실험02 pre_review_round3).
        이름은 교안 그대로다: p10·p11 회로도의 `VIN`·`VOUT`, p12 회로도의 `VIN` 과
        본문 "CH1에 U1의 4번 핀을, CH2에 U1의 8번 핀을"."""
        cases = {'build_e2_inv': ['VIN', 'VOUT'],
                 'build_e2_schmitt': ['VIN', 'VOUT'],
                 'build_e2_tpd': ['VIN', 'CH1', 'CH2']}
        for name, want in cases.items():
            with self.subTest(회로=name):
                bb, _ = self._render(getattr(self.b2, name))
                self.assertEqual([p['name'] for p in bb.probes if p.get('name')], want)
                got = [n for n, box, _s in bb.tag_boxes
                       if BOARD_L < box[0] and box[2] < BOARD_R]
                self.assertEqual(sorted(got), sorted(want))

    def test_신호_이름_배지가_번호_원_배선_홀을_가리지_않는다(self):
        for name, fn in _circuit_builders(self.mod).items():
            with self.subTest(회로=name):
                bb, _ = self._render(fn)
                for tag, box, seg in bb.tag_boxes:
                    self.assertEqual(_badge_hits(bb, box, seg), [], f"{name}: {tag}")

    def test_번호_원끼리_겹치지_않는다(self):
        """번호 원 둘이 포개지면 아래 번호를 읽을 수 없다 — 따라 그리는 사람이 그
        차례를 건너뛴다. 배지 검사(`_badge_hits`)는 배지 대 번호 원만 보고 번호 원
        끼리는 아무도 안 봤다.

        `marker_boxes` 항목은 원에 **외접**하는 상자다(`_marker`: `(x-8, y-8, x+8,
        y+8)`). 엔진도 걷기 번호 자리를 잡을 때 같은 상자끼리 `_boxes_touch` 로 보니
        (`_ghost_wire`) 여기서도 상자로 본다 — 원이 안 닿아도 상자가 겹치면 두 원이
        16px 안에 붙어 있다는 뜻이라 붙잡을 값은 한다.

        이미 맞닿아 있던 자리는 `KNOWN_MARKER_OVERLAPS` 에 실측값으로 적어 두고 새
        겹침만 막는다 — 승인본 PNG 를 바꿀 수 없어서다(그 주석에 쌍마다 근거).
        """
        for name, fn in _circuit_builders(self.mod).items():
            with self.subTest(회로=name):
                bb, _ = self._render(fn)
                bad = [(a, b) for i, a in enumerate(bb.marker_boxes)
                       for b in bb.marker_boxes[i + 1:] if _inter(a, b)]
                self.assertEqual(bad, KNOWN_MARKER_OVERLAPS.get(name, []),
                                 f'{name}: 번호 원이 겹친다 {bad}')

    def test_보드_밖_입력_꼬리표끼리_겹치지_않는다(self):
        """2026-09-28 실험04 C2: `S1`(우 a31)과 `D`(우 j31)가 같은 행이라 `입력 D → 우 j31`
        꼬리표가 `입력 S1 → 우 a31` 을 정확히 덮었다 — 여백에서 S1 을 어디 꽂는지 사라졌다."""
        for name, fn in _circuit_builders(self.mod).items():
            with self.subTest(회로=name):
                bb, _ = self._render(fn)
                boxes = bb.margin_tag_boxes
                bad = [(a[0], b[0]) for i, a in enumerate(boxes)
                       for b in boxes[i + 1:] if _inter(a[1], b[1])]
                self.assertEqual(bad, [], f'{name}: 보드 밖 꼬리표가 겹친다')

    def test_같은_행에_좌_f쪽과_우_a쪽_입력을_넣으면_번호_원이_겹친다(self):
        """위 검사가 무엇을 막는지 — 중앙 레일쌍 사이 여백(좌 중앙 VCC 484 ~ 우 중앙
        GND 542)은 `_input_jumper` 의 배지와 번호 원 자리를 한 번에 **입력 한 행**만
        받는다. 같은 행에 좌 f 쪽과 우 a 쪽 입력을 넣으면 기본 자리가 같아 번호 원
        둘이 정확히 포개진다 — 상자가 같으니 원도 같은 자리다."""
        bb = self.mod.BreadboardRenderer()
        bb.enable_steps()
        bb.draw_chip('74HC08', 7)
        bb.draw_chip('74HC08', 7, block='right')
        bb.partial = True
        self.mod._input_jumper(bb, bb.cols['left'], 11, 'A', '74HC08 pin 10', side='f')
        self.mod._input_jumper(bb, bb.cols['right'], 11, 'B', '74HC08 pin 1')
        self.assertEqual(len(bb.marker_boxes), 2)
        self.assertEqual(bb.marker_boxes[0], bb.marker_boxes[1])
        self.assertTrue(_inter(*bb.marker_boxes))

    def test_배선_색이_넷을_넘지_않는다(self):
        """이전 판은 한 장에 16색을 썼고 그중 눈으로 구분 안 되는 쌍이 여럿이었다.
        따라 그리는 사람 손에 있는 펜도 네 자루다."""
        self.assertEqual(set(self.mod.WIRE), {'vcc', 'gnd', 'sig', 'mid'})
        self.assertEqual(len(set(self.mod.WIRE.values())), 4, '색이 겹친다')

    def test_계측기는_배선_색을_쓰지_않는다(self):
        """프로브는 점퍼로 꽂는 게 아니라 문다. 색을 섞으면 조원이 프로브 자리에
        점퍼선을 찾는다."""
        self.assertNotIn(self.mod.PROBE, set(self.mod.WIRE.values()))


if __name__ == '__main__':
    unittest.main()
