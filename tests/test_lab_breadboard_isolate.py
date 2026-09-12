"""렌더러에서 실험01 빌더 구간을 걷어내는 계약.

파일을 통째로 지우면 시험할 도구(렌더러 본체·verify()·기준선)가 없고, 통째로
두면 답안(E1_SLOTS·빌더)이 있다. 구간만 걷어낸 사본이 `ast.parse` 되고, 실험02
빌더는 남고, 실험01 토큰은 하나도 없어야 한다.
"""

import ast
import importlib.util
import tempfile
import unittest
from pathlib import Path

from scripts.lab.breadboard_isolate import (E1_MARKER, RENDERER, strip_cli, strip_e1,
                                            strip_e1_file, strip_section)

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / RENDERER).read_text(encoding="utf-8")

FAKE = (
    "import os\n"
    "\n"
    "# ---------------------------------------------------------------------------\n"
    "# 실험 1 · 가짜\n"
    "E1_X = 1\n"
    "def build_e1_a(p): return 1\n"
    "\n"
    "# ---------------------------------------------------------------------------\n"
    "# 실험 2 · 가짜\n"
    "def build_e2_a(p): return 2\n"
    "\n"
    "def main():\n"
    "    parser.add_argument('--circuit', choices=[\n"
    '        "e1_a", "e1_all",\n'
    '        "e2_a", "e2_all"\n'
    "    ])\n"
    "    dispatch = {\n"
    '        "e1_a": build_e1_a,\n'
    '        "e1_all": build_e1_all,\n'
    '        "e2_a": build_e2_a,\n'
    "    }\n"
)


class StripSection(unittest.TestCase):
    def test_머리_앞_경계부터_다음_경계_직전까지_걷어낸다(self):
        out = strip_section(FAKE, "# 실험 1 ·")
        self.assertNotIn("E1_X", out)
        self.assertNotIn("build_e1_a(p)", out)
        self.assertIn("# 실험 2 · 가짜", out)
        self.assertIn("def build_e2_a", out)
        self.assertIn("import os", out)

    def test_머리가_없으면_예외다(self):
        with self.assertRaises(ValueError):
            strip_section(FAKE, "# 실험 9 ·")

    def test_머리_앞줄이_경계가_아니면_예외다(self):
        # 첫 경계 줄(실험 1 바로 앞)만 무너뜨린다
        src = FAKE.replace("# ----", "# xxxx", 1)
        with self.assertRaises(ValueError):
            strip_section(src, "# 실험 1 ·")


class StripCli(unittest.TestCase):
    def test_choices_와_dispatch_에서_접두사_항목을_뺀다(self):
        out = strip_cli(FAKE, "e1_")
        self.assertNotIn('"e1_', out)
        self.assertIn('"e2_a", "e2_all"', out)
        self.assertIn('"e2_a": build_e2_a,', out)
        # 토큰을 뺀 뒤 공백만 남은 줄이 없다
        self.assertNotIn("\n        \n", out)


class RealRenderer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = strip_e1(SRC)

    def test_원본에는_실험01_구간이_있다(self):
        self.assertIn(E1_MARKER, SRC)
        self.assertIn("E1_SLOTS", SRC)

    def test_실험01_토큰이_하나도_없다(self):
        for tok in ("E1_SLOTS", "E1_BOARDS", "E1_FINALS", "_e1_", "build_e1", '"e1_', "_E1_"):
            self.assertNotIn(tok, self.out, tok)

    def test_렌더러_본체와_실험02는_남는다(self):
        for tok in ("class BreadboardRenderer", "def snapshot", "def removed", "def verify",
                    "def mark_unused_inputs", "def build_e2_inv", "def build_e2_all",
                    '"e2_all": build_e2_all', "def main"):
            self.assertIn(tok, self.out, tok)

    def test_파싱된다(self):
        ast.parse(self.out)

    def test_걷어낸_사본이_import_되고_실험02_빌더가_돈다(self):
        d = Path(tempfile.mkdtemp())
        p = d / "render_breadboard.py"
        p.write_text(self.out, encoding="utf-8")
        spec = importlib.util.spec_from_file_location("render_breadboard_stripped", str(p))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertFalse(hasattr(mod, "build_e1_and"))
        bb = mod.build_e2_inv(str(d / "inv.png"),
                              template_path=str(ROOT / ".claude/assets/Breadboard.jpg"))
        self.assertTrue((d / "inv.png").exists())

    def test_strip_e1_file_은_제자리에서_고친다(self):
        d = Path(tempfile.mkdtemp())
        p = d / "render_breadboard.py"
        p.write_text(SRC, encoding="utf-8")
        strip_e1_file(p)
        self.assertNotIn("E1_SLOTS", p.read_text(encoding="utf-8"))
