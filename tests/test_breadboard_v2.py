"""브레드보드 v2 판형 — 판형 산출물·사양·가운데 레일 공유·블록 역할(R9·R10)·계약·연기 시험.

설계: docs/plans/2026-10-02-브레드보드-v2-구조-설계.md
구현계획: docs/plans/2026-10-03-브레드보드-v2-구현계획.md
v1(실험01~04)이 바이트 하나 안 바뀌는 것은 기존 테스트(`test_breadboard_boards` 의 도장·사이드카
대조)가 지킨다. 여기는 v2 와, v1·v2 가 갈리는 자리를 본다.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
import types
import unittest
from dataclasses import replace
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude/skills/breadboard-diagram/scripts/render_breadboard.py"
V2_DIR = ROOT / ".claude/assets/breadboard_v2"
GEOMETRY = V2_DIR / "geometry.json"
SMOKE = ROOT / "tests/fixtures/board_v2/배치.py"


def _load(name="render_breadboard"):
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class V2Template(unittest.TestCase):
    """판형 산출물 — 1배 PNG, 해시, 잭 글자 자리. 판형을 다시 뽑으면 여기서 걸린다."""

    def setUp(self):
        self.g = json.loads(GEOMETRY.read_text(encoding="utf-8"))
        self.png = V2_DIR / self.g["png"]

    def test_PNG_는_1배다(self):
        """2배로 뽑으면 레일 극성선이 4px 가 되어 손그림 검토가 레일 열을 6.5px 밀어 잡는다."""
        with Image.open(self.png) as im:
            self.assertEqual(im.size, (1200, 1600))
        self.assertEqual(self.g["export_scale"], 1)

    def test_해시가_geometry_와_같다(self):
        self.assertEqual(hashlib.sha256(self.png.read_bytes()).hexdigest(), self.g["png_sha256"])

    def test_잭_글자는_잭_왼쪽에_있고_아래는_비어_있다(self):
        """잭 전원선은 잭 아래로 곧장 내려간다 — 글자가 아래 있으면 선이 덮는다(2026-10-03 사용자)."""
        with Image.open(self.png) as im:
            im = im.convert("RGB")
            bg = im.getpixel((5, 5))
            for j in self.g["jacks"]:
                if j["name"] == "yellow":
                    continue
                cx, cy, bottom = j["center_x"], j["center_y"], j["bottom_y"]
                r = bottom - cy
                below = [im.getpixel((x, y)) for x in range(cx - 20, cx + 21)
                         for y in range(bottom + 4, bottom + 41)]
                self.assertTrue(all(p == bg for p in below), f"{j['name']} 잭 아래에 그림이 있다")
                left = [im.getpixel((x, y)) for x in range(cx - r - 60, cx - r - 3)
                        for y in range(cy - 10, cy + 11)]
                self.assertTrue(any(sum(p) < 300 for p in left), f"{j['name']} 글자가 잭 왼쪽에 없다")


class V1Spec(unittest.TestCase):
    """v1 사양은 옛 모듈 상수 그대로다 — 실험01~04 PNG 가 바이트 하나 안 바뀌는 근거."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_v1_사양은_모듈_상수와_같다(self):
        m, s = self.mod, self.mod.board_spec('v1')
        self.assertEqual((s.name, s.size, s.row0, s.row_pitch),
                         ('v1', m.TEMPLATE_SIZE, m.ROW0, m.ROW_PITCH))
        self.assertEqual((s.board_left, s.board_right), (m.BOARD_LEFT, m.BOARD_RIGHT))
        self.assertEqual((s.jacks, s.jack_bottom), (m.JACKS, m.JACK_BOTTOM))
        self.assertEqual((s.jack_y_max, s.jack_route_y, s.jack_marker_y), (240, (250, 258), 118))
        self.assertEqual(s.mid_badge_x, 513.0)
        self.assertEqual((s.chip_blocks, s.led_only_blocks, s.sha256), (('left', 'right'), (), None))

    def test_렌더러는_기본이_v1_이다(self):
        bb = self.mod.BreadboardRenderer()
        self.assertEqual(bb.board, 'v1')
        self.assertIs(bb.spec, self.mod.board_spec('v1'))
        self.assertEqual(bb.cols, self.mod.board_spec('v1').cols)
        self.assertIsNot(bb.cols, self.mod.board_spec('v1').cols)   # 사본 — 빌더가 고쳐도 사양은 그대로

    def test_v1_열_표는_28열이고_겹치는_x_가_없다(self):
        self.assertEqual(len(self.mod.column_table('v1')), 28)
        self.assertEqual(self.mod.board_spec('v1').cols['left']['mid_gnd'], 468)

    def test_잭_판정은_사양을_따른다(self):
        bb = self.mod.BreadboardRenderer()
        self.assertEqual(bb._jack_at(439, 160), 'red')
        self.assertEqual(bb._jack_at(766, 200), 'gray')
        self.assertIsNone(bb._jack_at(439, 245))      # 보드 위 테두리(242) 아래
        self.assertIsNone(bb._jack_at(520, 160))      # 잭 x 30px 밖

    def test_모르는_판형은_거절한다(self):
        with self.assertRaises(ValueError):
            self.mod.board_spec('v3')


class V2Spec(unittest.TestCase):
    """v2 사양은 geometry.json 에서만 나온다. 양식이 없거나 바뀌었으면 v1 로 넘어가지 않고 멈춘다."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load()
        cls.g = json.loads(GEOMETRY.read_text(encoding="utf-8"))
        cls.spec = cls.mod.board_spec('v2')

    def test_열_표의_순서와_이름이_geometry_와_같다(self):
        got = []
        for x, (block, key) in sorted(self.mod.column_table('v2').items()):
            got.append((f"mid.{key[4:]}" if key.startswith("mid_") else f"{block}.{key}", x))
        self.assertEqual(got, [(c["name"], c["x"]) for c in self.g["columns"]])

    def test_가운데_레일은_두_블록이_같은_x_다(self):
        L, R = self.spec.cols['left'], self.spec.cols['right']
        self.assertEqual((L['mid_gnd'], L['mid_vcc']), (R['mid_gnd'], R['mid_vcc']))

    def test_칩_몸통은_e_f_안쪽_5px(self):
        for blk in self.spec.cols.values():
            self.assertEqual((blk['chip_x1'], blk['chip_x2']), (blk['e'] + 5, blk['f'] - 5))

    def test_행과_잭은_geometry_를_따른다(self):
        g, s = self.g, self.spec
        self.assertEqual((s.size, s.row0, s.row_pitch),
                         ((g["image"]["width"], g["image"]["height"]), g["row1_center_y"], g["row_pitch"]))
        jx = {j["name"]: j["center_x"] for j in g["jacks"]}
        self.assertEqual(s.jacks, {'red': jx['+5V'], 'yellow': jx['yellow'], 'gray': jx['0V']})
        top = g["border"]["top"]
        self.assertEqual((s.jack_bottom, s.jack_y_max, s.jack_route_y, s.jack_marker_y),
                         (g["jacks"][0]["bottom_y"], top, (top + 8, top + 16), g["jacks"][0]["center_y"]))
        self.assertEqual(s.mid_badge_x, (s.cols['left']['mid_vcc'] + s.cols['right']['a']) / 2)
        self.assertEqual((s.chip_blocks, s.led_only_blocks, s.sha256),
                         (('left',), ('right',), g["png_sha256"]))

    def test_v2_렌더러가_v2_양식을_쓴다(self):
        bb = self.mod.BreadboardRenderer(board='v2')
        self.assertEqual(bb.base_im.size, (1200, 1600))
        self.assertEqual((bb.r_y(1), bb.r_y(63)),
                         (self.g["row1_center_y"], self.g["row1_center_y"] + 62 * self.g["row_pitch"]))

    def test_양식_후보가_없으면_v1_로_넘어가지_않는다(self):
        spec = replace(self.spec, template=(str(ROOT / "없는폴더/Breadboard_v2.png"),))
        with self.assertRaisesRegex(FileNotFoundError, "v2"):
            self.mod._default_template(spec)

    def test_geometry_가_없으면_멈춘다(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                self.mod._spec_from_geometry(os.path.join(d, "geometry.json"))

    def test_geometry_의_행이_렌더러와_다르면_멈춘다(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "geometry.json"
            p.write_text(json.dumps(dict(self.g, rows=62)), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "행"):
                self.mod._spec_from_geometry(str(p))

    def test_다시_뽑은_PNG_는_해시로_잡는다(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "Breadboard_v2.png"
            with Image.open(V2_DIR / "Breadboard_v2.png") as im:
                im = im.convert("RGB")
                im.putpixel((0, 0), (0, 0, 0))
                im.save(p)
            with self.assertRaisesRegex(ValueError, "png_sha256"):
                self.mod.BreadboardRenderer(str(p), board='v2')

    def test_v1_양식을_v2_로_넘기면_크기로_잡는다(self):
        """Review Focus 2 — `--template <v1 jpg>` 를 v2 주차에 넘긴 경우."""
        with self.assertRaisesRegex(ValueError, "1200x1600"):
            self.mod.BreadboardRenderer(self.mod._default_template(), board='v2')

    def test_잭_선이_v2_에서도_그림대로_꽂힌다(self):
        bb = self.mod.BreadboardRenderer(board='v2')
        bb.enable_steps()
        bb.connect_jacks()
        bb.verify()
        self.assertEqual([(s['frm'], s['to']) for s in bb.steps],
                         [('전원잭', '좌 VCC레일3행'), ('전원잭', '좌 GND레일4행')])
        red = bb._segments[0][1]
        self.assertEqual(red[0], (self.spec.jacks['red'], self.spec.jack_bottom))
        self.assertEqual(red[1][1], self.spec.jack_route_y[0])


if __name__ == "__main__":
    unittest.main()
