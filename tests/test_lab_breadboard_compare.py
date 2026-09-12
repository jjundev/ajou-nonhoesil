"""결선도 격리 재생성물 대조기의 계약.

승인본을 승인본과 대조하면 치명·기능 0건이어야 한다 — 검사기가 틀린 것을 먼저
가려낸다. 나머지는 자리표·전환 수치·파일명·짝 맺기·빌더 오류 격리.
"""

import os
import tempfile
import unittest
from pathlib import Path

from scripts.lab import config
from scripts.lab import breadboard_compare as bc
from scripts.lab.breadboard_isolate import RENDERER

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = str(ROOT / ".claude/assets/Breadboard.jpg")
NETLIST = ROOT / config.experiment_dir(1) / "결선도/netlist.md"
PNG_DIR = ROOT / config.experiment_dir(1) / "결선도"


class Rendered(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = bc.load_renderer_at(ROOT / RENDERER, "rb_test_approved")
        cls.tmp = tempfile.mkdtemp()
        cls.boards = bc.render_chain(cls.mod.E1_BOARDS, os.path.join(cls.tmp, "a"), TEMPLATE)
        cls.finals = bc.render_finals(cls.mod.E1_FINALS, os.path.join(cls.tmp, "f"), TEMPLATE)

    def test_보드_아홉_완성본_넷이_오류_없이_그려진다(self):
        self.assertEqual([b.error for b in self.boards], [""] * 9)
        self.assertEqual([b.error for b in self.finals], [""] * 4)
        self.assertEqual(self.boards[0].cid, "e1_and")
        self.assertEqual(self.boards[1].stage, None)
        self.assertEqual(self.boards[2].stage, 1)

    def test_자기대조는_치명_기능_0건(self):
        other = bc.load_renderer_at(ROOT / RENDERER, "rb_test_again")
        b2 = bc.render_chain(other.E1_BOARDS, os.path.join(self.tmp, "b"), TEMPLATE)
        for ref, new in zip(self.boards, b2):
            with self.subTest(ref.name):
                bad = [f for f in bc.net_findings(ref, new) if f.grade in bc.BLOCKING]
                self.assertEqual(bad, [], [str(x) for x in bad])

    def test_자기대조는_서류_규칙을_안_낸다(self):
        rules = {f.rule for f in bc.net_findings(self.boards[3], self.boards[3])}
        self.assertFalse(rules & {"H11", "H12", "H13"}, rules)

    def test_자리표는_빌더가_앉힌_자리와_같다(self):
        slots = bc.layout_slots(NETLIST)
        self.assertEqual(slots, self.mod.E1_SLOTS)
        used = set(bc.seats(self.boards + self.finals))
        self.assertEqual(used, set(slots.values()))

    def test_OR_전환은_칩_교체_한_줄_걷는_것_0(self):
        t = bc.transition(self.boards[1])
        self.assertEqual((t["steps"], t["removed"], t["swaps"]), (1, 0, 1))
        self.assertFalse(t["partial"])

    def test_복합_1단계는_partial_이고_걷는_것이_있다(self):
        t = bc.transition(self.boards[6])
        self.assertTrue(t["partial"])
        self.assertGreater(t["removed"], 0)

    def test_다른_회로끼리_대조하면_치명_기능이_난다(self):
        # 자기대조 0건은 대조기가 아무것도 안 봐도 통과한다 — 다른 넷은 잡아야 의미가 있다
        bad = [f for f in bc.net_findings(self.boards[0], self.boards[2]) if f.grade in bc.BLOCKING]
        self.assertTrue(bad, "대조기가 서로 다른 넷을 구별하지 못한다")


class Pairing(unittest.TestCase):
    def _b(self, name, cid="e1_x"):
        return bc.Board(name, cid, None, None, "")

    def test_이름이_같으면_이름으로_짝짓는다(self):
        ref = [self._b("a.png"), self._b("b.png")]
        new = [self._b("b.png"), self._b("a.png")]
        pairs = bc.pair_boards(ref, new)
        self.assertEqual([(r.name, n.name) for r, n in pairs],
                         [("a.png", "a.png"), ("b.png", "b.png")])

    def test_이름이_다르면_남은_것끼리_순서로_짝짓는다(self):
        ref = [self._b("a.png"), self._b("b.png"), self._b("c.png")]
        new = [self._b("x.png"), self._b("b.png"), self._b("y.png")]
        pairs = bc.pair_boards(ref, new)
        self.assertEqual([(r.name, n.name) for r, n in pairs],
                         [("a.png", "x.png"), ("b.png", "b.png"), ("c.png", "y.png")])

    def test_재생성이_모자라거나_남으면_None_으로_보인다(self):
        ref = [self._b("a.png"), self._b("b.png")]
        new = [self._b("a.png"), self._b("b.png"), self._b("z.png")]
        pairs = bc.pair_boards(ref, new)
        self.assertEqual(pairs[-1][0], None)
        self.assertEqual(pairs[-1][1].name, "z.png")
        pairs = bc.pair_boards(ref, new[:1])
        self.assertEqual(pairs[1][1], None)

    def test_같은_이름이_둘이면_둘_다_남는다(self):
        a = self._b("a.png")
        a1, a2 = self._b("a.png"), self._b("a.png")
        pairs = bc.pair_boards([a], [a1, a2])
        self.assertEqual(len(pairs), 2)
        self.assertIs(pairs[0][0], a)
        self.assertIs(pairs[0][1], a1)
        self.assertIsNone(pairs[1][0])
        self.assertIs(pairs[1][1], a2)

    def test_승인본_이름이_겹쳐도_재생성_한_장을_두_번_쓰지_않는다(self):
        a = self._b("a.png")
        a1 = self._b("a.png")
        pairs = bc.pair_boards([a, a], [a1])
        self.assertEqual(len(pairs), 2)
        self.assertIs(pairs[0][0], a)
        self.assertIs(pairs[0][1], a1)
        self.assertIs(pairs[1][0], a)
        self.assertIsNone(pairs[1][1])


class Filenames(unittest.TestCase):
    SUBS = {"1-1", "1-2", "2-1", "2-2", "3"}

    def test_netlist_에서_소단원_토큰을_뽑는다(self):
        self.assertEqual(bc.sub_items(NETLIST), self.SUBS)

    def test_승인본_13장은_전부_합격이다(self):
        for p in sorted(PNG_DIR.glob("*.png")):
            self.assertEqual(bc.check_filename(p.name, self.SUBS), "", p.name)

    def test_어긋난_이름은_이유를_낸다(self):
        for bad in ("실험1-1_결선도_AND.png", "실험01_1-1_AND.png", "실험01_9_결선도_AND.png",
                    "실험01_2-1_결선도_NAND_단계1.png", "e1_and.png",
                    "실험01_1-1_결선도_3단계_이름.png",
                    "실험01_1-1_결선도_AND_2단계_이름_추가.png"):
            self.assertNotEqual(bc.check_filename(bad, self.SUBS), "", bad)


class BrokenBuilder(unittest.TestCase):
    def test_빌더가_죽어도_사슬은_계속되고_오류가_남는다(self):
        def boom(path, template_path=None, stage=None, baseline=None):
            raise AssertionError("R2 한 홀에 리드 둘")

        def none_builder(path, template_path=None, stage=None, baseline=None):
            return None

        mod = bc.load_renderer_at(ROOT / RENDERER, "rb_test_broken")
        boards = bc.render_chain([("x.png", boom, None), ("y.png", none_builder, 1),
                                  mod.E1_BOARDS[0]], tempfile.mkdtemp(), TEMPLATE)
        self.assertIn("R2", boards[0].error)
        self.assertIn("돌려주지 않는다", boards[1].error)
        self.assertEqual(boards[2].error, "")
        t = bc.transition(boards[0])
        self.assertEqual(t["steps"], None)

    def test_snapshot_이_죽어도_사슬은_계속된다(self):
        class DeadSnapshot:
            def snapshot(self):
                raise RuntimeError("스냅샷 붕괴")

        def dead_snapshot_builder(path, template_path=None, stage=None, baseline=None):
            return DeadSnapshot()

        mod = bc.load_renderer_at(ROOT / RENDERER, "rb_test_dead_snapshot")
        boards = bc.render_chain([("x.png", dead_snapshot_builder, None),
                                  mod.E1_BOARDS[0]], tempfile.mkdtemp(), TEMPLATE)
        self.assertIn("snapshot", boards[0].error)
        self.assertEqual(boards[1].error, "")

    def test_빌더_안의_TypeError_는_시그니처_불일치로_보지_않는다(self):
        def fn(path, template_path=None, stage=None, baseline=None):
            if stage is not None:
                raise TypeError("내부 버그")
            return object()

        boards = bc.render_chain([("x.png", fn, 1)], tempfile.mkdtemp(), TEMPLATE)
        self.assertIsNone(boards[0].bb)
        self.assertIn("내부 버그", boards[0].error)
        self.assertNotIn("안 받는다", boards[0].error)

    def test_시그니처가_다른_빌더는_위치_인자로_다시_부른다(self):
        mod = bc.load_renderer_at(ROOT / RENDERER, "rb_test_sig")

        def fn(path, template_path=None):
            return mod.build_e1_and(path, template_path)

        boards = bc.render_chain([("x.png", fn, 1)], tempfile.mkdtemp(), TEMPLATE)
        self.assertIsNotNone(boards[0].bb)
        self.assertIn("안 받는다", boards[0].error)


class Judgment(unittest.TestCase):
    def test_승인본을_승인본과_대조한_판정문(self):
        md = bc.judge(1, ROOT / RENDERER, ROOT / RENDERER, NETLIST, PNG_DIR, TEMPLATE,
                      leak_hits=["a.md:1: E1_SLOTS"], agent_report="3. 첫 렌더 통과")
        for head in ("## 1. 구조적 누출 1건", "## 2. 보드 사슬", "## 3. 절차 그림 넷 대조",
                     "## 4. 완성본 넷 대조", "## 5. 칩 자리", "## 6. 전환 수치",
                     "## 7. 파일명 13", "## 8. 에이전트 보고", "## 9. 사람이 볼 것"):
            self.assertIn(head, md, head)
        self.assertIn("세션 메모리 주입", md)
        self.assertIn("치명 0 · 기능 0", md)
        self.assertIn("첫 렌더 통과", md)
