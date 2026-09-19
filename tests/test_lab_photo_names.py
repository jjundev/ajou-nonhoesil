"""사진 파일명 규칙 — 인쇄본(render)과 시트(contact_sheet)가 같은 규칙을 읽는다.

2026-09-19 전까지 인쇄본은 옛 관례 `T<n> row<m>.jpg` 를 찍고 시트 엔진은
`<항목> <입력비트>.jpg` 를 읽었다. 실험실에서 인쇄본대로 찍으면 시트가 전부
"규칙 밖" 으로 거절했다.
"""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts.lab import contact_sheet
from scripts.lab.photo_names import FILE, SIDE, item_token, photo_name


class TestPhotoNames(unittest.TestCase):
    def test_항목_토큰은_제목의_실험_번호다(self):
        self.assertEqual(item_token("실험 1-2) 전가산기"), "1-2")
        self.assertEqual(item_token("실험 3) 복합 논리회로"), "3")
        self.assertIsNone(item_token("FPGA 프로젝트"))
        self.assertIsNone(item_token(""))

    def test_조립한_이름을_시트_규칙이_그대로_읽는다(self):
        name = photo_name("1-2", "000")
        self.assertEqual(name, "1-2 000.jpg")
        m = FILE.match(name)
        self.assertEqual((m.group("item"), m.group("bits")), ("1-2", "000"))

    def test_스텝표_파형_사진은_SIDE_로만_잡힌다(self):
        for name in ("1-1 T1 xy.jpg", "2-1 T3 s4.jpg", "1-1 T1.png"):
            with self.subTest(name=name):
                self.assertIsNotNone(SIDE.match(name))
                self.assertIsNone(FILE.match(name))

    def test_접두어나_옛_관례는_어느_규칙에도_안_맞는다(self):
        for name in ("실험02 1-1 T1 xy.jpg", "실험03 1-2 000.jpg", "T1 row3.jpg"):
            with self.subTest(name=name):
                self.assertIsNone(SIDE.match(name))
                self.assertIsNone(FILE.match(name))


class TestContactSheetSidePhotos(unittest.TestCase):
    """`plan()` 은 사진 파일을 열지 않고 이름만 본다 — 빈 파일로 충분하다.
    기록은 실험03 실물 `기록.md` 를 읽는다(확인 칸이 전부 ✓)."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        for name in ("1-2 000.jpg", "1-2 T3 근접.jpg", "실험03 1-2 001.jpg"):
            (self.dir / name).write_bytes(b"")

    def test_스텝표_파형_사진은_규칙_밖_문제가_아니다(self):
        plans, loose, skipped = contact_sheet.plan(3, photo_dir=self.dir)
        self.assertEqual([p.token for p in plans], ["1-2"])
        self.assertEqual([p.name for _, p in plans[0].photos], ["1-2 000.jpg"])
        self.assertEqual(len(loose), 1)
        self.assertIn("실험03 1-2 001.jpg", loose[0])
        self.assertEqual(skipped, ["1-2 T3 근접.jpg"])

    def test_check_는_건너뛴_사진_수를_알리고_문제로_세지_않는다(self):
        d = Path(tempfile.mkdtemp())
        for name in ("1-2 000.jpg", "1-1 T1 xy.jpg", "1-2 T3 근접.jpg"):
            (d / name).write_bytes(b"")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = contact_sheet.main(["3", "--check", "--photo-dir", str(d)])
        out = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("건너뜀 (스텝표·파형 사진 — 시트 대상 아님): 2장 — "
                      "1-1 T1 xy.jpg, 1-2 T3 근접.jpg", out)
        self.assertIn("문제 0건", out)

    def test_시트로_묶을_사진이_없으면_그렇게_말한다(self):
        only_side = Path(tempfile.mkdtemp())
        (only_side / "1-1 T1 xy.jpg").write_bytes(b"")
        with self.assertRaisesRegex(contact_sheet.ContactSheetError, "시트로 묶을 사진"):
            contact_sheet.plan(3, photo_dir=only_side)
