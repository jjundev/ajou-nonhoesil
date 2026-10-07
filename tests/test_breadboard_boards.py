"""주차 결선 파일(`보고서/실험NN/결선도/배치.py`)의 로더·일괄 렌더.

설계: docs/plans/2026-09-15-결선도-엔진-주차분리-설계.md
"""
import ast
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

from PIL import Image

from scripts.lab import config
from tests._boards import engine_files, experiment_numbers, per_experiment

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude/skills/breadboard-diagram/scripts/render_breadboard.py"
FIXTURE = ROOT / "tests/fixtures/board_min/배치.py"


def _load(name="render_breadboard"):
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Loader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_주차_파일은_불러온_엔진의_클래스를_쓴다(self):
        """테스트 스파이가 `mod.BreadboardRenderer` 에 걸리려면 같은 객체여야 한다."""
        board = self.mod.load_board_file(FIXTURE)
        self.assertIs(board.BreadboardRenderer, self.mod.BreadboardRenderer)
        other = _load("rb_other")
        self.assertIsNot(other.BreadboardRenderer, self.mod.BreadboardRenderer)
        self.assertIs(other.load_board_file(FIXTURE).BreadboardRenderer, other.BreadboardRenderer)

    def test_불러온_뒤_sys_modules_를_되돌린다(self):
        before = sys.modules.get("render_breadboard")
        self.mod.load_board_file(FIXTURE)
        self.assertIs(sys.modules.get("render_breadboard"), before)

    def test_바이트코드를_남기지_않는다(self):
        """보고서 폴더에 `__pycache__` 가 생기면 안 된다."""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "배치.py"
            p.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
            self.mod.load_board_file(p)
            self.assertFalse((Path(d) / "__pycache__").exists())

    def test_board_path_는_config_의_실험_폴더를_따른다(self):
        self.assertEqual(Path(self.mod.board_path(3)),
                         ROOT / config.experiment_dir(3) / "결선도" / "배치.py")

    def test_board_numbers_는_실험_폴더_이름을_config_로_되돌려_센다(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / config.EXPERIMENT_BASE
            for name in (config.experiment_folder_name(4), config.experiment_folder_name(2),
                         "실험4", "메모", "실험99"):
                (base / name / "결선도").mkdir(parents=True)
                (base / name / "결선도" / "배치.py").write_text("", encoding="utf-8")
            self.assertEqual(self.mod.board_numbers(root=d), [2, 4])


class BuildAll(unittest.TestCase):
    def test_사슬과_완성본을_전부_뽑는다(self):
        mod = _load()
        with tempfile.TemporaryDirectory() as d:
            made = mod.build_all(mod.load_board_file(FIXTURE), d)
            self.assertEqual(sorted(made), ["min.png", "min_1단계_잭.png"])
            # PNG 마다 사이드카 JSON 이 붙는다(2026-09-28)
            self.assertEqual(sorted(os.listdir(d)), ["min.json", "min.png",
                                                     "min_1단계_잭.json", "min_1단계_잭.png"])

    def test_빌더가_None을_돌려주면_알아볼_수_있는_TypeError를_던진다(self):
        """`return bb` 를 빠뜨린 빌더는 `'NoneType' object has no attribute
        'snapshot'` 같은 알아볼 수 없는 오류로 죽는다 — 문구를 준다(M1)."""
        mod = _load()

        def none_builder(path, template_path=None, stage=None, baseline=None):
            return None

        board = types.SimpleNamespace(BOARDS=[("x.png", none_builder, None)], FINALS=[])
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(TypeError) as cm:
                mod.build_all(board, d)
            self.assertIn("x.png", str(cm.exception))
            self.assertIn("none_builder", str(cm.exception))
            self.assertIn("return bb", str(cm.exception))

    def test_팔레트를_넘는_단계는_멈춘다(self):
        mod = _load()

        def eleven(path, template_path=None, stage=None, baseline=None):
            bb = mod.BreadboardRenderer(template_path, baseline=baseline, palette=True, board='v1')
            bb.enable_steps()
            bb.connect_jacks()
            c = bb.cols['left']
            for i in range(11):
                bb.step_wire([(c['a'], bb.r_y(5 + 2 * i)), (c['a'], bb.r_y(6 + 2 * i))], 'sig', f'신호 {i}')
            return bb

        board = types.SimpleNamespace(BOARD='v1', BOARDS=[("x.png", eleven, 1)], FINALS=[])
        with tempfile.TemporaryDirectory() as d, \
                self.assertRaisesRegex(ValueError, r'x\.png.*11.*10.*쪼갠다'):
            mod.build_all(board, d)


class RealBoards(unittest.TestCase):
    """세 주차의 결선이 실험 폴더로 옮겨 갔고, 엔진에는 주차 이름이 없다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_세_주차의_결선_파일이_있다(self):
        self.assertTrue({1, 2, 3} <= set(self.mod.board_numbers()), self.mod.board_numbers())

    def test_주차_파일은_BOARDS_와_FINALS_를_낸다(self):
        for n in self.mod.board_numbers():
            with self.subTest(실험=n):
                board = self.mod.load_board(n)
                self.assertTrue(all(len(t) == 3 for t in board.BOARDS), board.BOARDS)
                self.assertTrue(all(len(t) == 2 for t in board.FINALS), board.FINALS)

    def test_엔진은_주차_결선을_정의하지_않는다(self):
        names = []
        for p in engine_files():
            tree = ast.parse(p.read_text(encoding="utf-8"))
            names += [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
            names += [t.id for n in tree.body if isinstance(n, ast.Assign)
                      for t in n.targets if isinstance(t, ast.Name)]
        bad = [n for n in names if n.startswith("build_e") or re.match(r"_e\d+_", n)
               or n[:1] == "E" and n[1:2].isdigit()]
        self.assertEqual(bad, [])


class Cli(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args],
                              capture_output=True, text=True, cwd=ROOT)

    def test_experiment_로_그_주차를_전부_뽑는다(self):
        board = _load().load_board(2)
        pngs = [n for n, _f, _s in board.BOARDS] + [n for n, _f in board.FINALS]
        want = sorted(pngs + [n[:-len(".png")] + ".json" for n in pngs])   # 사이드카 쌍
        with tempfile.TemporaryDirectory() as d:
            r = self._run("--experiment", "2", "--output", d)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(sorted(os.listdir(d)), want)

    def test_circuit_는_없다(self):
        r = self._run("--circuit", "e3_all", "--output", tempfile.gettempdir())
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_결선_파일이_없는_실험은_거절한다(self):
        free = sorted(set(range(1, config.EXPERIMENT_COUNT + 1)) - set(_load().board_numbers()))
        if not free:
            self.skipTest("모든 실험에 결선 파일이 있다")
        r = self._run("--experiment", str(free[-1]))
        self.assertEqual(r.returncode, 2)
        self.assertIn("주차 결선 파일이 없다", r.stderr)

    def test_범위_밖_실험_번호는_트레이스백_없이_거절한다(self):
        r = self._run("--experiment", "0")
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertNotIn("Traceback", r.stderr)


class Stamp(unittest.TestCase):
    """도장 = 그림이 **무엇을** 싣는가의 해시. 글꼴·줄바꿈은 들지 않는다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def _render_final(self, mod):
        name, fn = mod.load_board(3).FINALS[0]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, name)
            bb = fn(p, None)
            return bb, mod.read_stamp(p), Path(p).read_bytes()

    def test_PNG_에_도장이_찍힌다(self):
        bb, got, _png = self._render_final(self.mod)
        self.assertRegex(got, r"^v2:[0-9a-f]{64}$")
        self.assertEqual(got, bb.stamp())

    def test_글꼴이_달라도_도장은_같다(self):
        """커밋된 실험01 PNG 는 다른 기계의 글꼴로 뽑혀 바이트가 달랐다 — 선은 같았다."""
        other = _load("rb_font")
        other._font = lambda kind, size: other.ImageFont.load_default(size)
        _bb1, s1, png1 = self._render_final(self.mod)
        _bb2, s2, png2 = self._render_final(other)
        self.assertNotEqual(png1, png2, "글꼴이 실제로 바뀌지 않았다")
        self.assertEqual(s1, s2)

    def test_주석이_바뀌면_도장이_바뀐다(self):
        bb, got, _png = self._render_final(self.mod)
        bb.notes.append("새 주석")
        self.assertNotEqual(bb.stamp(), got)

    def test_도장_없는_PNG_는_None(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.png")
            Image.new("RGB", (4, 4)).save(p)
            self.assertIsNone(self.mod.read_stamp(p))

    def test_PNG_가_아닌_이미지는_AttributeError_없이_None(self):
        """`im.text` 는 PNG 전용 속성이다 — JPEG 등은 없어서 `.get()` 이 바로
        `AttributeError` 로 죽는다(미룬 지적 3)."""
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.jpg")
            Image.new("RGB", (4, 4)).save(p, format="JPEG")
            self.assertIsNone(self.mod.read_stamp(p))

    def test_build_all_은_파일명마다_도장을_돌려준다(self):
        with tempfile.TemporaryDirectory() as d:
            made = self.mod.build_all(self.mod.load_board_file(FIXTURE), d)
            self.assertEqual(list(made), ["min_1단계_잭.png", "min.png"])
            for name, s in made.items():
                self.assertEqual(self.mod.read_stamp(os.path.join(d, name)), s)


class FreshBoard(unittest.TestCase):
    """`rebuild: true` 회로의 첫 보드 — 앞 회로를 전부 걷으므로 기준선을 잇지 않는다.
    이으면 앞 회로 배선이 전부 '걷는다' 로 잡혀 단계 보드가 선을 걷게 된다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_기준선을_버리고_부른다(self):
        seen = {}

        def build(output_path, template_path=None, stage=None, baseline=None):
            seen.update(out=output_path, stage=stage, baseline=baseline)
            return 'bb'

        fresh = self.mod.fresh_board(build)
        self.assertEqual(fresh('x.png', None, stage=1, baseline={'wires': 1}), 'bb')
        self.assertEqual(seen, {'out': 'x.png', 'stage': 1, 'baseline': None})


class StageBudget(unittest.TestCase):
    """단계 하나가 꽂는 새 신호선 수. 2026-09-20 단계 세분화: 확인이 실패했을 때
    용의자가 '방금 꽂은 셋' 으로 줄어드는 것이 이 수의 존재 이유다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_예산_상수가_셋이다(self):
        self.assertEqual(self.mod.STAGE_WIRE_BUDGET, 3)

    def test_주차_예외가_없으면_기본_예산이다(self):
        self.assertEqual(self.mod.stage_budget(types.ModuleType('board')), 3)

    def test_주차_예외는_이유와_함께_쓴다(self):
        """실험04: 4입력 NAND 출력 하나를 보려면 입력 넷과 관측선 하나가 한꺼번에
        있어야 한다 — 셋으로는 관측 노드 하나를 세울 수 없다(2026-09-27 결정)."""
        board = types.ModuleType('board')
        board.STAGE_WIRE_BUDGET = 5
        board.STAGE_WIRE_BUDGET_REASON = '4입력 NAND = 입력 4 + 관측선 1'
        self.assertEqual(self.mod.stage_budget(board), 5)

    def test_이유_없는_예외는_거절한다(self):
        """이유 없이 숫자만 올리면 예산이 조용히 풀린다."""
        board = types.ModuleType('board')
        board.STAGE_WIRE_BUDGET = 5
        with self.assertRaises(ValueError):
            self.mod.stage_budget(board)

    def test_양의_정수가_아닌_예외는_거절한다(self):
        for bad in (0, -1, 2.5, '5'):
            board = types.ModuleType('board')
            board.STAGE_WIRE_BUDGET = bad
            board.STAGE_WIRE_BUDGET_REASON = '이유'
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.mod.stage_budget(board)

    def test_전원과_LED_사슬은_예산에_들지_않는다(self):
        """기반 배선이다 — 회로가 바뀌어도 그대로 있고 첫 단계에 한꺼번에 꽂는다."""
        bb = self.mod.BreadboardRenderer()
        bb.enable_steps()
        c = bb.cols['left']
        bb.connect_power(7, gnd_col='b')
        self.assertEqual(bb.new_signal, [])
        bb.step_wire([(c['b'], bb.r_y(7)), (c['b'], bb.r_y(9))], 'sig', '신호 한 가닥')
        bb.step_wire([(c['c'], bb.r_y(7)), (c['c'], bb.r_y(9))], 'mid', '중간 한 가닥')
        self.assertEqual(len(bb.new_signal), 2)

    def test_기준선에_있던_신호선은_새_선이_아니다(self):
        """회색으로 그려지는 선은 실험실에서 손대지 않는다 — 용의자가 아니다."""
        first = self.mod.BreadboardRenderer()
        first.enable_steps()
        c = first.cols['left']
        first.step_wire([(c['b'], first.r_y(7)), (c['b'], first.r_y(9))], 'sig', '신호 한 가닥')
        second = self.mod.BreadboardRenderer(baseline=first.snapshot())
        second.enable_steps()
        c2 = second.cols['left']
        second.step_wire([(c2['b'], second.r_y(7)), (c2['b'], second.r_y(9))], 'sig', '신호 한 가닥')
        self.assertEqual(second.new_signal, [])

    def test_도장에는_들어가지_않는다(self):
        """들어가면 실험01·02·03 PNG 스물두 장이 전부 stale 이 된다."""
        bb = self.mod.BreadboardRenderer()
        self.assertNotIn('new_signal', bb.content())

    # 옛 규약("칩 하나 = 단계 하나")으로 그린 승인본. 다시 쪼개면 PNG 열여섯 장과
    # 손그림 전사 기준이 움직인다 — 소급 적용하지 않는다(2026-09-20 설계 결정 10).
    LEGACY_BOARDS = (1, 2)


class StageBoards(unittest.TestCase):
    """실험 하나의 절차 보드를 차례로 그려 본다. 실험마다 클래스가 하나씩 생긴다
    (`per_experiment`) — xdist 가 실험을 워커에 나눠 그리게 하려는 것이다(2026-09-29)."""
    experiment = None

    @classmethod
    def setUpClass(cls):
        if cls.experiment in StageBudget.LEGACY_BOARDS:
            raise unittest.SkipTest(f"실험{cls.experiment:02d} 는 옛 규약 승인본이라 면제다")
        cls.mod = _load()
        cls.board = cls.mod.load_board(cls.experiment)

    def test_절차_보드는_새_신호선이_예산_안이다(self):
        board = self.board
        budget = self.mod.stage_budget(board)
        with tempfile.TemporaryDirectory() as d:
            base = None
            for name, fn, stage in board.BOARDS:
                bb = fn(os.path.join(d, name), stage=stage, baseline=base)
                with self.subTest(board=name):
                    self.assertLessEqual(
                        len(bb.new_signal), budget,
                        f"{name}: 새 신호선 {len(bb.new_signal)} 가닥 — "
                        f"{[k[1:] for k in bb.new_signal]}")
                base = bb.snapshot()

    def test_단계_보드는_아무것도_걷지_않는다(self):
        """뽑는 자리는 전용 걷기 보드다 (2026-09-20). 단계 보드가 선을 걷으면 그
        지시는 footer 표의 글 한 줄뿐이고, 2026-09-18 실험03 실험실에서 바로 그
        글이 건너뛰어졌다 — 걷기 보드를 만든 근거가 그것이다.

        `stage is None` 인 보드가 걷기 보드다(`removal_board` 클로저는 stage 를
        거절한다). 실험01·02 는 옛 규약 승인본이라 면제다."""
        with tempfile.TemporaryDirectory() as d:
            base = None
            for name, fn, stage in self.board.BOARDS:
                bb = fn(os.path.join(d, name), stage=stage, baseline=base)
                if stage is not None:
                    with self.subTest(board=name):
                        self.assertEqual(
                            [r['addr'] for r in bb.removals()], [],
                            f"{name}: 단계 보드가 선을 걷는다 — 그 전환 앞에 "
                            f"removal_board 를 끼운다")
                base = bb.snapshot()


per_experiment(StageBoards, globals())

class CommittedPngs(unittest.TestCase):
    """커밋된 결선도 PNG 가 지금 `배치.py` 에서 나온 것인가 — 도장으로 본다.
    글꼴이 다른 기계에서도 선·문구가 같으면 통과한다. 실험마다 클래스가 하나씩
    생긴다(`per_experiment`)."""
    experiment = None

    def test_결선도_폴더가_코드와_같다(self):
        mod, n = _load(), self.experiment
        folder = Path(mod.board_path(n)).parent
        with tempfile.TemporaryDirectory() as d:
            made = mod.build_all(mod.load_board(n), d)
            self.assertEqual({p.name for p in folder.glob("*.png")}, set(made),
                             "결선도 폴더의 PNG 와 배치.py 의 BOARDS·FINALS 가 다르다")
            stale = sorted(f for f, s in made.items() if mod.read_stamp(folder / f) != s)
            self.assertEqual(stale, [], "코드와 어긋난 PNG — "
                             f"`render_breadboard.py --experiment {n}` 으로 다시 뽑는다")
            # 체크리스트의 결선 순서는 사이드카에서만 온다 — PNG 도장이 맞아도 JSON 이 옛것이면
            # 틀린 순서가 인쇄된다(2026-09-28 최종 리뷰: 병합 충돌·이름 바꾸기)
            sides = {f[:-len(".png")] + ".json" for f in made}
            self.assertEqual({p.name for p in folder.glob("*.json")}, sides,
                             "결선도 폴더의 JSON 이 PNG 와 쌍이 아니다")
            stale = sorted(f for f in sides
                           if (folder / f).read_bytes() != (Path(d) / f).read_bytes())
            self.assertEqual(stale, [], "코드와 어긋난 사이드카 — "
                             f"`render_breadboard.py --experiment {n}` 으로 다시 뽑는다")


per_experiment(CommittedPngs, globals())


class ExperimentNumbers(unittest.TestCase):
    def test_실험별_클래스의_번호가_엔진과_같다(self):
        """실험별 클래스 이름은 폴더 이름(`experiment_numbers`)에서 나온다."""
        nums = _load().board_numbers()
        self.assertTrue({1, 2, 3} <= set(nums), nums)
        self.assertEqual(experiment_numbers(), nums)

class TestE4MuxFinalOneLed(unittest.TestCase):
    """실험04 C1(4x1 MUX) 완성본은 출력이 Y 하나라 LED 사슬도 하나다(2026-09-28 사용자).

    손으로 따라 그려 제출하는 원도라, 네 사슬이면 출력이 넷인 회로로 읽힌다. 2026-09-29
    부터는 **보드도 같다** — 8걷기가 LED2~4 사슬을 뽑아 8단계 절차 그림도 사슬 하나다.
    7단계까지는 중간 노드를 보느라 네 사슬이 다 있다.
    """

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.board = cls.mod.load_board_file(cls.mod.board_path(4))

    def _chains(self, stage):
        with tempfile.TemporaryDirectory() as d:
            bb = self.board.build_e4_mux(os.path.join(d, "x.png"), stage=stage)
        return sorted(ch["tag"] for ch in bb.wiring()["chains"])

    def test_완성본은_Y_사슬_하나다(self):
        self.assertEqual(self._chains(None), ["Y"])

    def test_7단계_절차_그림은_네_사슬이다(self):
        self.assertEqual(self._chains(7), ["L2", "L3", "L4", "Y"])

    def test_8단계_절차_그림은_Y_사슬_하나다(self):
        self.assertEqual(self._chains(8), ["Y"])

    def test_8걷기는_뽑는_사슬을_번호_없는_줄로_낸다(self):
        """사슬째 뽑는 LED·저항은 GND 선만 번호를 받는다. 부품은 빨간 점선 상자로 그리고
        순서표에는 번호 없는 줄로 낸다 — 그림이 회색이면 "부품은 둔다" 로 읽힌다."""
        name, fn, _stage = next(b for b in self.board.BOARDS if "8걷기" in b[0])
        with tempfile.TemporaryDirectory() as d:
            bb = fn(os.path.join(d, name))
        self.assertEqual(sorted(bb.ghost["chains"].values()), ["L2", "L3", "L4"])
        self.assertEqual(bb.ghost_chains_drawn, set(bb.ghost["chains"]))
        lines = [r["text"] for r in bb.sidecar()["removals"] if r["n"] is None]
        self.assertEqual(len(lines), 3)
        self.assertTrue(all("LED·330Ω 을 뽑는다" in t for t in lines), lines)

    def test_5걷기는_사슬을_뽑지_않는다(self):
        """선만 뽑는 걷기 보드에는 `chains` 키가 없다 — 옛 걷기 보드 도장이 그대로다."""
        name, fn, _stage = next(b for b in self.board.BOARDS if "5걷기" in b[0])
        with tempfile.TemporaryDirectory() as d:
            bb = fn(os.path.join(d, name))
        self.assertNotIn("chains", bb.ghost)


if __name__ == "__main__":
    unittest.main()
