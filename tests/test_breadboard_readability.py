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
import importlib.util
import os
import tempfile
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / ".claude/skills/breadboard-diagram/scripts/render_breadboard.py"

# 보드 안쪽 x 범위. 이 밖에 앉는 배지는 여백이라 홀을 가리지 않는다
BOARD_L, BOARD_R = 149, 877

# 그림 한 장의 보드 위 배지 상한. 신호 이름(입력 A·B·C, 출력 L1·L2·X·Y·Z)만 남긴
# 결과가 한 장에 0~5 개다. 문구를 다시 얹기 시작하면 여기서 걸린다
MAX_ON_BOARD_LABELS = 8


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


def _module():
    spec = importlib.util.spec_from_file_location("render_breadboard", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _circuit_builders(mod):
    """`--circuit` 이 부르는 빌더. `*_all` 은 이들을 묶기만 한다."""
    import inspect
    out = {}
    for name, fn in vars(mod).items():
        if (name.startswith("build_") and not name.endswith("_all")
                and inspect.isfunction(fn)):
            out[name] = fn
    return out


class BuilderApiContract(unittest.TestCase):
    """소스를 ast 로 읽어 옛 API 로 새는지 본다."""

    @staticmethod
    def _builder_like(tree):
        for n in tree.body:
            if isinstance(n, ast.FunctionDef) and (
                    n.name.startswith("build_") or n.name.startswith("_build_")
                    or n.name.startswith("_e1_") or n.name.startswith("_e2_")
                    or n.name.startswith("_e3_")):
                yield n

    def _calls(self, node, attr):
        return [c for c in ast.walk(node)
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)
                and c.func.attr == attr]

    def test_빌더가_번호_없는_배선을_그리지_않는다(self):
        tree = ast.parse(SRC.read_text(encoding="utf-8"))
        bad = [n.name for n in self._builder_like(tree) if self._calls(n, "draw_wire")]
        self.assertEqual(bad, [], f"{bad}: draw_wire 는 번호도 순서표도 남기지 않는다. "
                                  "step_wire 를 쓴다")

    def test_빌더가_보드_위에_배지를_직접_그리지_않는다(self):
        tree = ast.parse(SRC.read_text(encoding="utf-8"))
        bad = [n.name for n in self._builder_like(tree) if self._calls(n, "draw_badge")]
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

    def _render(self, fn):
        # 그림 한 장만 센다. 단계 그림은 기준선을 얻으려고 앞 보드를 한 번 더
        # 그리는데, 그 배지까지 합치면 한 장에 5개인 그림이 10개로 잡힌다
        counted = {}
        mod = self.mod
        orig_badge = mod.BreadboardRenderer.draw_badge
        captured = {}

        def spy_badge(self_, x, y, text, *a, **k):
            if BOARD_L < x < BOARD_R:
                counted[self_] = counted.get(self_, 0) + 1
            return orig_badge(self_, x, y, text, *a, **k)

        orig_export = mod.BreadboardRenderer.export

        def spy_export(self_, *a, **k):
            captured['bb'] = self_
            return orig_export(self_, *a, **k)

        mod.BreadboardRenderer.draw_badge = spy_badge
        mod.BreadboardRenderer.export = spy_export
        try:
            with tempfile.TemporaryDirectory() as d:
                fn(os.path.join(d, 'x.png'))
        finally:
            mod.BreadboardRenderer.draw_badge = orig_badge
            mod.BreadboardRenderer.export = orig_export
        bb = captured['bb']
        return bb, counted.get(bb, 0)

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
                    labels, MAX_ON_BOARD_LABELS,
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
        bb, _ = self._render(self.mod.build_e3_hs)
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
                bb, _ = self._render(getattr(self.mod, name))
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
