"""`compare_specs` 가 재생성물의 어긋남을 실제로 짚는지 본다.

격리 재생성은 이 저장소에서 스킬 결함을 찾는 유일한 방법인데, 판정을 사람
눈에 맡기면 매번 기준이 흔들린다. 실제로 한 번은 판정 스크립트가 `C` 열을
가진 표를 전부 훑는 바람에, 레벨 인에이블이라 `1` 이 맞는 표 셋을 FAIL 로
찍었다 — 스크립트가 틀린 것이지 재생성이 틀린 게 아니었다.

여기 있는 테스트는 살아 있는 실험06 명세를 한 군데씩 변형해, 검사기가 그
자리를 짚는지 확인한다. 합성 픽스처를 따로 만들지 않는다.
"""

import re
import tempfile
import unittest
from pathlib import Path

from scripts.lab.specdiff import compare_specs, uncovered_tables

ROOT = Path(__file__).resolve().parents[1]
WEEK6 = ROOT / "실험06/체크리스트/명세.md"
WEEK12 = ROOT / "실험10/체크리스트/명세.md"


class CompareSpecs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _mutated(self, old, new, source=WEEK6):
        """`source` 명세에서 `old` 를 한 번만 `new` 로 바꾼 사본 경로.

        기본은 실험06 이다. 실험10(capture 표 픽스처)을 만질 때만 `source`
        를 넘긴다.
        """
        text = source.read_text(encoding="utf-8")
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

    def test_파싱은_되지만_제외된_필드는_차이로_보지_않는다(self):
        # `title` 은 SpecItem.title 로 실제로 파싱된다 — 파서가 아예 담지
        # 않는 본문 서술(예: 어떤 필드로도 안 들어가는 안내문)을 만지면,
        # `_ITEM_FIELDS`·`_TABLE_FIELDS` 에 title 이나 expected 가 실수로
        # 들어가도 이 테스트는 원래부터 통과해 아무것도 지키지 못한다.
        # 그래서 반드시 "파싱되지만 일부러 뺀" 자리를 만져야 한다.
        target = self._mutated("title: R-S Latch with Enable (Gate 이용)",
                               "title: R-S 래치 (Enable, 게이트 구성)")
        self.assertEqual(compare_specs(WEEK6, target), [])

    def test_ics_순서만_바뀌면_차이로_보지_않는다(self):
        # ics 는 그 항목이 쓰는 IC 패키지 이름의 집합이지 순서가 아니다.
        # device·tables 도 같은 이유로 순서 무시다(스키마상 참조 목록).
        target = self._mutated('ics: ["74HC00", "74HC04"]',
                               'ics: ["74HC04", "74HC00"]')
        self.assertEqual(compare_specs(WEEK6, target), [])

    def test_capture_표의_expected가_바뀌어도_compare_specs는_묵음이다(self):
        # capture 표는 셀이 없고 기술적 주장이 전부 expected 산문에 있다.
        # expected 는 산문이라 대조 대상이 아니므로, 사실을 뒤집어도
        # compare_specs 는 잡지 못한다 — 이것은 결함이 아니라 알려진 구멍
        # 이고, uncovered_tables 가 그 구멍을 알린다(아래 UncoveredTables).
        target = self._mutated(
            "계단 상승한 뒤 리셋되는 톱니 형태",
            "계단 하강한 뒤 리셋되는 역톱니 형태",
            source=WEEK12,
        )
        self.assertEqual(compare_specs(WEEK12, target), [])

    def test_다른_주차끼리는_양쪽_방향을_다_보고한다(self):
        # 실험06 은 표 T1~T5·항목 다섯, 실험10 은 표 T1~T2·항목 둘이다.
        forward = compare_specs(WEEK6, WEEK12)
        self.assertTrue(any("원본에만 있다" in d for d in forward), forward)
        backward = compare_specs(WEEK12, WEEK6)
        self.assertTrue(any("재생성에만 있다" in d for d in backward), backward)

    def test_표_삽입으로_ID가_밀리면_셀_차이_대신_ID_불일치를_먼저_알린다(self):
        # 실측(실험06 재생성 2건): 교안 p5 이론표를 T2 로 끼워 넣으면 그
        # 뒤 T2~T5 가 전부 T3~T6 로 밀린다. ID 로만 짝지으면 원본 T3
        # (교안 p9)과 재생성 T3(실은 밀린 옛 T2, 교안 p8)이 서로 다른
        # 표인데 짝지어져, 셀 내용이 완전히 같은데도 차이가 쏟아진다
        # (실측 19건). 이 테스트는 그 상황을 실험06 명세를 직접 변형해
        # 재현한다 — 손으로 만든 픽스처가 아니다.
        text = WEEK6.read_text(encoding="utf-8")
        for old, new in (("T5", "T6"), ("T4", "T5"), ("T3", "T4"), ("T2", "T3")):
            self.assertIn(old, text, f"픽스처가 바뀌었다 — {old!r} 가 없다")
            text = text.replace(old, new)
        marker = "## T3 · D Latch with Enable 특성표"
        self.assertIn(marker, text, "표 삽입 지점을 못 찾았다 — 픽스처가 바뀌었다")
        inserted = (
            "## T2 · 래치·플립플롭 개념 정리\n\n"
            "- kind: truth-table\n"
            "- encoding: 0/1\n"
            "- source: manual:p5\n"
            "- role: reference\n\n"
            "| 구분 | 설명 |\n"
            "|---|---|\n"
            "| 래치 | 레벨 인에이블 |\n\n"
        )
        text = text.replace(marker, inserted + marker, 1)
        target = Path(self.tmp.name) / "명세.md"
        target.write_text(text, encoding="utf-8")

        diffs = compare_specs(WEEK6, target)

        # 1. 표 집합이 다르다는 사실 자체를 먼저, 눈에 띄게 알린다.
        self.assertTrue(diffs, "차이가 아예 없다 — 표가 하나 늘었는데 이상하다")
        self.assertIn("ID", diffs[0])
        self.assertIn("표", diffs[0])

        # 2. 오정렬된 짝의 셀 차이를 쏟아내지 않는다 — 내용은 실제로 같다.
        self.assertFalse(any("행" in d for d in diffs), diffs)
        self.assertFalse(any("헤더" in d for d in diffs), diffs)

        # 새로 끼운 표 자체는 정확히 한 번 보고된다. "재생성에만 있다" 가
        # 아니라 "짝을 못 지었다" 다 — 원본에도 T2 라는 ID(D Latch with
        # Enable, source 로 재생성 T3 과 짝지어진 다른 표)가 있어서,
        # "재생성에만 있다" 라고 하면 양쪽에 다 있는 ID 를 없다고 말하는
        # 셈이기 때문이다(C2).
        table_report = [
            d for d in diffs if d.startswith("표 T2:") and "짝을 못 지었다" in d
        ]
        self.assertEqual(len(table_report), 1, diffs)

    WEEK2 = ROOT / "실험01/체크리스트/명세.md"

    def _shifted(self, source, first, last):
        """`source` 명세의 표 ID 를 한 칸씩 밀고 새 `T2` 를 끼운 사본.

        재생성물이 교안 표를 하나 더 정당하게 싣는 실제 상황이다 — 실험06
        재생성 두 건이 각각 교안 p5 이론표를 `T2` 로 끼워 넣었고, 그때
        이후 ID 가 전부 밀려 서로 다른 표가 짝지어졌다.
        """
        def bump(m):
            n = int(m.group(1))
            return f"T{n + 1}" if first <= n <= last else m.group(0)

        # `tables:` 줄과 `## T<n> ·` 헤딩의 ID 만 민다. 항목이 표를 여럿
        # 가리키는 줄(`tables: [T1, T2, T6, T7]`)도 밀어야 하므로 대괄호
        # 통짜 치환이 아니라 토큰 단위로 바꾼다 — 통짜로 하면 원소가 하나인
        # 목록만 밀려서 항목이 없는 표를 가리키거나 ID 가 중복된다.
        out = []
        for line in source.read_text(encoding="utf-8").split("\n"):
            if line.lstrip().startswith("tables:") or line.startswith("## T"):
                line = re.sub(r"T(\d+)", bump, line)
            out.append(line)
        # 밀고 나면 `T2` 를 가리키는 항목이 없다 — 첫 항목에 붙인다.
        # 고아 표는 파서가 error 로 막는다.
        text = "\n".join(out).replace("tables: [", "tables: [T2, ", 1)
        text += ("\n## T2 · 끼운 참조표\n\n- kind: truth-table\n"
                 "- encoding: 0/1\n- source: manual:p99\n- role: reference\n\n"
                 "| A | Y |\n|---|---|\n| 0 | 0 |\n")
        target = Path(self.tmp.name) / "명세.md"
        target.write_text(text, encoding="utf-8")
        return target

    def test_derived_source_만_있는_명세도_밀림에서_오정렬되지_않는다(self):
        # 이 코퍼스의 절반이 `derived (...)` 다 — 실험03 은 4/4, 실험05 는
        # 5/6, 실험01 은 5/9. `derived` 를 짝짓기 키에서 빼면 그 명세들에서
        # 오정렬이 그대로 남는다. 실측: 고치기 전 19건(셀 차이 8건), 진짜
        # 내용 오류는 0건이었다.
        target = self._shifted(self.WEEK2, 2, 9)
        diffs = compare_specs(self.WEEK2, target)
        cells = [d for d in diffs if "행" in d]
        self.assertEqual(cells, [], f"셀을 하나도 안 건드렸는데 차이가 났다: {cells}")

    def test_짝을_못_지은_표는_한쪽에만_있다고_말하지_않는다(self):
        # source 짝짓기가 원본 Tx 를 재생성 Ty(x≠y) 와 묶으면, 원본 Ty 와
        # 재생성 Tx 가 둘 다 짝을 잃는다. 그것을 "한쪽에만 있다" 로 찍으면
        # 양쪽에 있는 ID 를 없다고 말하는 셈이라 읽는 사람이 오독한다.
        target = self._shifted(self.WEEK2, 2, 9)
        diffs = compare_specs(self.WEEK2, target)
        both = {"T" + str(n) for n in range(1, 10)}
        for d in diffs:
            if "원본에만 있다" in d or "재생성에만 있다" in d:
                tid = d.split()[1].rstrip(":")
                self.assertNotIn(
                    tid, both,
                    f"양쪽 문서에 다 있는 ID 를 한쪽에만 있다고 했다: {d}")


class UncoveredTablesTest(unittest.TestCase):
    """`uncovered_tables` 가 `compare_specs` 의 사각지대를 실제로 짚는지 본다.

    capture 표는 `header=[]`·`rows=[]` 라 `compare_specs` 의 셀 대조가
    언제나 같다고 나온다(위 `test_capture_표의_expected가_바뀌어도_
    compare_specs는_묵음이다` 참조). 그 사각지대를 사람이 알아채도록
    이름과 이유를 목록으로 내는 함수가 실제로 그 표를 짚는지 확인한다.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_실험10_명세에서_capture_표_T1을_짚는다(self):
        found = uncovered_tables(WEEK12)
        self.assertEqual(len(found), 1, found)
        self.assertIn("T1", found[0])

    def test_실험06_명세는_전부_truth_table이라_빈_리스트다(self):
        self.assertEqual(uncovered_tables(WEEK6), [])

    def test_expected가_바뀌어도_여전히_그_표를_짚는다(self):
        # compare_specs 는 이 변형을 못 잡는다(별도 테스트로 확인됨) —
        # 여기서는 uncovered_tables 가 그 자리를 계속 알린다는 것,
        # 즉 "묵음" 이 아니라 "알려진 구멍" 임을 고정한다.
        text = WEEK12.read_text(encoding="utf-8")
        old = "계단 상승한 뒤 리셋되는 톱니 형태"
        self.assertIn(old, text, f"픽스처가 바뀌었다 — {old!r} 가 없다")
        target = Path(self.tmp.name) / "명세.md"
        target.write_text(
            text.replace(old, "계단 하강한 뒤 리셋되는 역톱니 형태", 1),
            encoding="utf-8",
        )
        found = uncovered_tables(target)
        self.assertEqual(len(found), 1, found)
        self.assertIn("T1", found[0])
