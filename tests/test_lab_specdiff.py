"""`compare_specs` 가 재생성물의 어긋남을 실제로 짚는지 본다.

격리 재생성은 이 저장소에서 스킬 결함을 찾는 유일한 방법인데, 판정을 사람
눈에 맡기면 매번 기준이 흔들린다. 실제로 한 번은 판정 스크립트가 `C` 열을
가진 표를 전부 훑는 바람에, 레벨 인에이블이라 `1` 이 맞는 표 셋을 FAIL 로
찍었다 — 스크립트가 틀린 것이지 재생성이 틀린 게 아니었다.

여기 있는 테스트는 살아 있는 실험06 명세를 한 군데씩 변형해, 검사기가 그
자리를 짚는지 확인한다. 합성 픽스처를 따로 만들지 않는다.
"""

import tempfile
import unittest
from pathlib import Path

from scripts.lab.specdiff import compare_specs

ROOT = Path(__file__).resolve().parents[1]
WEEK6 = ROOT / "실험06/체크리스트/명세.md"
WEEK12 = ROOT / "실험10/체크리스트/명세.md"


class CompareSpecs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _mutated(self, old, new):
        """실험06 명세에서 `old` 를 한 번만 `new` 로 바꾼 사본 경로."""
        text = WEEK6.read_text(encoding="utf-8")
        self.assertIn(old, text, f"픽스처가 바뀌었다 — {old!r} 가 없다")
        target = Path(self.tmp.name) / "명세.md"
        target.write_text(text.replace(old, new, 1), encoding="utf-8")
        return target

    def test_같은_문서끼리는_차이가_없다(self):
        self.assertEqual(compare_specs(WEEK6, WEEK6), [])

    def test_라이징_엣지가_리터럴_1_로_돌아가면_그_자리를_짚는다(self):
        # 이 파일이 존재하는 이유가 이 한 줄이다. 재생성물의 이 셀이 `1` 이면
        # 텍스트 추출의 지뢰를 밟은 것이고, 그것을 사람 눈에 맡기지 않는다.
        target = self._mutated("| 0 | 0->1 | 0 |", "| 0 | 1 | 0 |")
        diffs = compare_specs(WEEK6, target)
        self.assertEqual(len(diffs), 1, diffs)
        self.assertIn("0->1", diffs[0])
        self.assertIn("'1'", diffs[0])

    def test_encoding_이_바뀌면_잡는다(self):
        target = self._mutated("- encoding: 0/1", "- encoding: H/L")
        diffs = compare_specs(WEEK6, target)
        self.assertTrue(any("encoding" in d for d in diffs), diffs)

    def test_source_가_바뀌면_잡는다(self):
        target = self._mutated("- source: manual:p9", "- source: manual:p99")
        diffs = compare_specs(WEEK6, target)
        self.assertTrue(any("source" in d for d in diffs), diffs)

    def test_전원_레일이_빠지면_잡는다(self):
        target = self._mutated('power: {VCC: "+5V", GND: "GND"}',
                               'power: {VCC: "+5V"}')
        diffs = compare_specs(WEEK6, target)
        self.assertTrue(any("전원" in d for d in diffs), diffs)

    def test_산문이_달라도_차이로_보지_않는다(self):
        # 재생성물이 같은 사실을 다른 문장으로 쓰는 것은 결함이 아니다.
        target = self._mutated("교안 p7. `74HC00` 쿼드 NAND",
                               "교안 p7 의 회로다. `74HC00` 쿼드 NAND")
        self.assertEqual(compare_specs(WEEK6, target), [])

    def test_다른_주차끼리는_양쪽_방향을_다_보고한다(self):
        # 실험06 은 표 T1~T5·항목 다섯, 실험10 은 표 T1~T2·항목 둘이다.
        forward = compare_specs(WEEK6, WEEK12)
        self.assertTrue(any("원본에만 있다" in d for d in forward), forward)
        backward = compare_specs(WEEK12, WEEK6)
        self.assertTrue(any("재생성에만 있다" in d for d in backward), backward)
