"""렌더러가 이 머신의 폰트로 뜨는지 본다.

2026-09-12 까지 `BreadboardRenderer.__init__` 은 macOS 경로
(`/System/Library/Fonts/AppleSDGothicNeo.ttc`)를 박아 두어 Windows 에서는
`OSError: cannot open resource` 로 렌더러 테스트 165건이 통째로 죽었다.

2026-09-19 에는 더 조용한 사고가 있었다 — Windows 에서 고른 맑은 고딕에 U+2295 `⊕`
가 없어 결선도 부제가 `(A□B)·Ci` 로 나갔다. 터지지 않으니 테스트도 몰랐다. 그래서
"뜨는가" 만이 아니라 "필요한 글자를 그리는가" 까지 여기서 본다.

다만 글리프 검사가 **전부 아니면 죽음**이면 더 나쁘다 — 맑은 고딕밖에 없는 보통의
Windows 에서는 렌더러가 통째로 안 떴다. 그래서 글리프를 하드(없으면 후보를 버린다)와
소프트(없으면 경고만 하고 쓴다)로 가른다. 여기서 그 둘을 다 본다.
"""
import contextlib
import importlib.util
import io
import os
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, '.claude', 'skills', 'breadboard-diagram',
                      'scripts', 'render_breadboard.py')


def _load():
    spec = importlib.util.spec_from_file_location('render_breadboard', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Fonts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_한글_영문_후보가_있다(self):
        # 'hand' 는 손그림 모사 전용 손글씨 후보(2026-10-12) — 못 찾아도 렌더러는 산다
        self.assertEqual(set(self.mod.FONT_CANDIDATES), {'kr', 'en', 'hand'})

    def test_font_path_는_실재하는_파일을_준다(self):
        for kind in ('kr', 'en'):
            with self.subTest(kind=kind):
                self.assertTrue(os.path.exists(self.mod.font_path(kind)))

    def test_모르는_kind_는_거절한다(self):
        with self.assertRaises(KeyError):
            self.mod.font_path('emoji')

    def test_렌더러가_이_머신에서_뜬다(self):
        bb = self.mod.BreadboardRenderer()
        self.assertIsNotNone(bb.font_title)

    @contextlib.contextmanager
    def candidates(self, kind, paths):
        """`FONT_CANDIDATES[kind]` 를 잠깐 갈아끼우고 경고 기억도 비운다."""
        old = self.mod.FONT_CANDIDATES[kind]
        self.mod.FONT_CANDIDATES[kind] = tuple(paths)
        self.mod._SOFT_WARNED.clear()
        try:
            yield
        finally:
            self.mod.FONT_CANDIDATES[kind] = old
            self.mod._SOFT_WARNED.clear()

    def test_하드_글리프와_소프트_글리프가_갈려_있다(self):
        """☐ 는 소프트다 — 이게 하드면 맑은 고딕뿐인 Windows 에서 렌더러가 통째로 죽는다."""
        self.assertEqual(self.mod.REQUIRED_GLYPHS, {'kr': '⊕→·※', 'en': '', 'hand': "0123456789ABCDEHLSYΩ'·"})
        self.assertEqual(self.mod.PREFERRED_GLYPHS, {'kr': '☐', 'en': '', 'hand': ''})

    def test_고른_한글_폰트가_하드_글리프를_다_그린다(self):
        """`⊕→·※` — 없으면 □ 로 나가고 줄바꿈까지 어긋난다."""
        chosen = self.mod.font_path('kr')
        for ch in self.mod.REQUIRED_GLYPHS['kr']:
            with self.subTest(ch=ch):
                self.assertTrue(self.mod._covers(chosen, ch), f'{chosen} 에 {ch} 가 없다')

    def test_맑은_고딕은_동그라미더하기가_없어_밀린다(self):
        """2026-09-19 사고의 장본인. `_covers` 가 이걸 못 잡으면 규칙이 무의미하다."""
        malgun = 'C:/Windows/Fonts/malgun.ttf'
        if not os.path.exists(malgun):
            self.skipTest('이 머신에 맑은 고딕이 없다')
        self.assertTrue(self.mod._covers(malgun, '가'), '한글은 되는 폰트여야 대조가 된다')
        self.assertFalse(self.mod._covers(malgun, '⊕'))
        self.assertNotEqual(self.mod.font_path('kr'), malgun)

    def test_체크칸까지_그리는_후보가_있으면_그쪽을_고른다(self):
        """본고딕은 하드는 다 되지만 ☐ 가 없다 — 함초롬돋움이 앞선다."""
        handotum = 'C:/Windows/Fonts/HANDotum.ttf'
        if not os.path.exists(handotum):
            self.skipTest('이 머신에 함초롬돋움이 없다')
        self.assertTrue(self.mod._covers(handotum, self.mod.PREFERRED_GLYPHS['kr']))
        self.assertEqual(self.mod.font_path('kr'), handotum)

    def test_소프트_글리프만_없는_후보는_버리지_않고_경고만_한다(self):
        noto = 'C:/Windows/Fonts/NotoSansKR-VF.ttf'
        if not os.path.exists(noto):
            self.skipTest('이 머신에 본고딕이 없다')
        self.assertTrue(self.mod._covers(noto, self.mod.REQUIRED_GLYPHS['kr']))
        self.assertFalse(self.mod._covers(noto, '☐'), '소프트가 빠진 후보여야 대조가 된다')
        err = io.StringIO()
        with self.candidates('kr', [noto]), contextlib.redirect_stderr(err):
            self.assertEqual(self.mod.font_path('kr'), noto)
            self.mod.font_path('kr')          # 두 번 불러도 경고는 한 번
        self.assertEqual(err.getvalue().count('☐'), 1, err.getvalue())
        self.assertIn(noto, err.getvalue())

    def test_하드_글리프가_다_빠지면_그때만_던진다(self):
        malgun = 'C:/Windows/Fonts/malgun.ttf'
        if not os.path.exists(malgun):
            self.skipTest('이 머신에 맑은 고딕이 없다')
        with self.candidates('kr', [malgun]):
            with self.assertRaises(FileNotFoundError) as cm:
                self.mod.font_path('kr')
        self.assertIn(malgun, str(cm.exception))

    def test_열_수_없는_후보는_글리프_누락과_따로_적힌다(self):
        """폰트가 아닌 파일이 후보 자리에 있으면 "글리프가 없다" 가 아니라 "못 열었다" 다."""
        malgun = 'C:/Windows/Fonts/malgun.ttf'
        if not os.path.exists(malgun):
            self.skipTest('이 머신에 맑은 고딕이 없다')
        with tempfile.TemporaryDirectory() as d:
            junk = os.path.join(d, 'junk.ttf')
            with open(junk, 'wb') as f:
                f.write(b'not a font at all')
            with self.candidates('kr', [junk, malgun]):
                with self.assertRaises(FileNotFoundError) as cm:
                    self.mod.font_path('kr')
        msg = str(cm.exception)
        unreadable, glyph = msg.split('글리프')[0], msg.split('글리프')[1]
        self.assertIn(junk, unreadable)
        self.assertNotIn(junk, glyph)
        self.assertIn(malgun, glyph)


if __name__ == '__main__':
    unittest.main()
