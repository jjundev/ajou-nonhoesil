import os
import tempfile
import unittest
from pathlib import Path

from scripts.cleanup_archive import plan, promotion_target, verify, manifest


class TestCleanupArchive(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.arc = self.root / "_원천_아카이브"
        self.cur = self.root / "정리"
        (self.arc / "깊은/경로").mkdir(parents=True)
        (self.cur / "퀴즈/실험3").mkdir(parents=True)
        (self.cur / "강의노트").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path: Path, data: bytes):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def reasons(self, p):
        return {path.name: reason for path, reason, _ in p["deletions"]}

    def test_junk_is_deleted(self):
        self.write(self.arc / "~$실험5_예상.docx", b"lock")
        self.write(self.arc / "datasheet.pdf.03ujqxr.partial.pdf", b"half")
        p = plan(self.arc, self.cur)
        r = self.reasons(p)
        self.assertEqual(len(r), 2)
        self.assertTrue(all("쓰레기" in v for v in r.values()))

    def test_curated_duplicate_is_deleted_but_unique_is_kept(self):
        self.write(self.cur / "퀴즈/실험3/사본.pdf", b"same-bytes")
        self.write(self.arc / "깊은/사본.pdf", b"same-bytes")
        self.write(self.arc / "깊은/고유.pdf", b"only-here")
        r = self.reasons(plan(self.arc, self.cur))
        self.assertIn("사본.pdf", r)
        self.assertIn("동일본", r["사본.pdf"])
        self.assertNotIn("고유.pdf", r)

    def test_internal_duplicate_keeps_shallowest_copy(self):
        self.write(self.arc / "얕은.docx", b"dup")
        self.write(self.arc / "깊은/경로/얕은.docx", b"dup")
        p = plan(self.arc, self.cur)
        deleted = [path for path, _, _ in p["deletions"]]
        self.assertEqual(len(deleted), 1)
        self.assertEqual(deleted[0].parent.name, "경로")

    def test_promotion_routes_by_kind(self):
        t = promotion_target(Path("a/실험3퀴즈_문제.docx"), self.cur)
        self.assertEqual(t.parent, self.cur / "퀴즈/실험3/원본_docx")
        t = promotion_target(Path("a/실험4.ppt"), self.cur)
        self.assertEqual(t.parent, self.cur / "강의노트/원본_PPT")
        # 보고서는 퀴즈보다 먼저 판정되어야 한다
        t = promotion_target(Path("a/실험6 예비보고서.hwp"), self.cur)
        self.assertEqual(t.parent, self.cur / "예비보고서/실험6/원본_hwp")
        self.assertIsNone(promotion_target(Path("a/무관한파일.zip"), self.cur))

    def test_verify_detects_loss_and_honors_intended(self):
        a = self.write(self.arc / "지켜야할.pdf", b"keep-me")
        before = manifest(self.arc)
        h = next(iter(before))
        a.unlink()
        self.assertEqual(verify(before, self.arc), [h])
        self.assertEqual(verify(before, self.arc, intended={h}), [])

    def test_plan_does_not_touch_filesystem(self):
        f = self.write(self.arc / "~$임시.docx", b"lock")
        plan(self.arc, self.cur)
        self.assertTrue(f.exists())


if __name__ == "__main__":
    unittest.main()
