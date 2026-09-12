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


class Filenames(unittest.TestCase):
    SUBS = {"1-1", "1-2", "2-1", "2-2", "3"}

    def test_netlist_에서_소단원_토큰을_뽑는다(self):
        self.assertEqual(bc.sub_items(NETLIST), self.SUBS)

    def test_승인본_13장은_전부_합격이다(self):
        for p in sorted(PNG_DIR.glob("*.png")):
            self.assertEqual(bc.check_filename(p.name, self.SUBS), "", p.name)

    def test_어긋난_이름은_이유를_낸다(self):
        for bad in ("실험1-1_결선도_AND.png", "실험01_1-1_AND.png", "실험01_9_결선도_AND.png",
                    "실험01_2-1_결선도_NAND_단계1.png", "e1_and.png"):
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
