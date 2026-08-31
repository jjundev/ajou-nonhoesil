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

        # 새로 끼운 표 자체는 정확히 한 번 보고된다. 그냥 "재생성에만
        # 있다" 는 아니다 — 원본에도 T2 라는 ID(D Latch with Enable,
        # source 로 재생성 T3 과 짝지어진 다른 표)가 있기 때문이다. 하지만
        # 새로 끼운 표의 source(manual:p5)는 원본 어디에도 없으므로(원본은
        # p7~p11 뿐이다) 그냥 "짝을 못 지었다" 도 아니다 — 정말 원본에는
        # 없는 표라는 사실 자체는 여전히 알려야 한다. 그래서 세 갈래 중
        # 2번("~에만 있는 표다, 상대에는 같은 ID로 다른 표가 있다")으로
        # 보고된다.
        table_report = [
            d for d in diffs
            if d.startswith("표 T2:") and "재생성에만 있는 표다" in d
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
        # 이건 파싱을 위해 꼭 필요한 것은 아니다(`parse_spec` 은 *없는
        # 표를 가리키는 항목* 만 막지, 아무 항목도 안 가리키는 고아 표는
        # 그냥 통과시킨다 — `scripts/lab/spec_parser.py` 의 `가 없는 표`
        # 예외 참고). 그래도 재생성물이 표를 정당하게 하나 더 실을 때는
        # 보통 그 표를 가리키는 항목도 함께 생기므로, 붙여야 시나리오가
        # 현실적이다.
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
        # 재생성 Tx 가 둘 다 짝을 잃는다. 밀림으로 ID 만 어긋난 표들은
        # 어느 쪽으로도(3갈래 중 무엇으로도) "이 표가 상대에 없다" 는
        # 취지의 줄로 보고되면 안 된다 — 전부 source 로 정상 짝지어지기
        # 때문이다. 유일한 예외는 `_shifted` 가 새로 끼워 넣는 T2 다 —
        # 그 표의 source(`manual:p99`)는 원본 어디에도 없는 **정말 새
        # 표**라서(A 의 2번 갈래로 떨어진다: "재생성에만 있는 표다"),
        # 이 표만 빼고 나머지 T1·T3~T10 전부를 통틀어 검사한다. 옛
        # 필터(`d.startswith("표 T2:")`)처럼 검사 범위 자체를 T2 하나로
        # 좁히면 T4·T5 가 잘못 짝을 잃어도 못 잡으므로 쓰지 않는다.
        target = self._shifted(self.WEEK2, 2, 9)
        diffs = compare_specs(self.WEEK2, target)
        # `_table_diffs` 가 짝을 못 지은 표에 내는 줄은 항상
        # "표 {id}: ..." 형태다(필드 차이 줄은 "표 {id} {field}: ..." 로
        # ID 뒤에 콜론이 바로 오지 않는다) — 그 형태만 골라낸다.
        unmatched = [d for d in diffs if re.match(r"^표 T\d+(?:→T\d+)?: ", d)]
        others = [d for d in unmatched if not d.startswith("표 T2:")]
        self.assertEqual(
            others, [],
            f"밀림으로 ID 만 어긋난 표가 상대에 없다는 취지로 잘못 보고됐다: {others}")
        self.assertEqual(len(unmatched), 1, unmatched)
        self.assertIn("재생성에만 있는 표다", unmatched[0])

    def _table_removed(self, source, tid):
        """`source` 명세에서 표 `tid` 블록을 통째로 지우고 뒤 ID 를 하나씩
        당긴 사본. `_shifted` 와 정반대 상황 — 표가 하나 더 끼어드는 게
        아니라 **정말로 사라지는** 것을 재현한다.
        """
        n = int(tid[1:])
        lines = source.read_text(encoding="utf-8").split("\n")
        start = next(i for i, l in enumerate(lines) if l.startswith(f"## {tid} "))
        end = next(
            (i for i in range(start + 1, len(lines)) if lines[i].startswith("## T")),
            len(lines),
        )
        del lines[start:end]

        def bump(m):
            k = int(m.group(1))
            return f"T{k - 1}" if k > n else m.group(0)

        out = []
        for line in lines:
            if line.lstrip().startswith("tables:") or line.startswith("## T"):
                line = re.sub(r"T(\d+)", bump, line)
            out.append(line)
        target = Path(self.tmp.name) / "명세.md"
        target.write_text("\n".join(out), encoding="utf-8")
        return target

    def test_표가_통째로_지워지면_짝을_못_지은_것이_아니라_원본에만_있다고_말한다(self):
        # Important 1 회귀. 실험06 에서 T2(D Latch with Enable, source
        # manual:p8) 블록을 통째로 지우고 뒤 ID(T3~T5)를 하나씩 당기면,
        # 밀린 표들(원본 T3→사본 T2 등)은 source 로 정상 짝지어져서
        # 사본에도 우연히 "T2" 라는 ID 가 있다. ID 만 보면 이건 A 의
        # 3번 갈래("짝을 못 지었다")처럼 보이기 쉽지만, 원본 T2 의 내용
        # (D Latch with Enable, source manual:p8)은 사본 어디에도 없으므로
        # source 기준으로는 2번 갈래("원본에만 있는 표다")가 맞다. 이걸
        # 3번 갈래로 찍으면 진짜 삭제가 정렬 잡음처럼 읽힌다.
        target = self._table_removed(WEEK6, "T2")
        diffs = compare_specs(WEEK6, target)
        hit = [d for d in diffs if d.startswith("표 T2:")]
        self.assertEqual(len(hit), 1, diffs)
        self.assertIn("원본에만 있는 표다", hit[0])
        self.assertNotIn("짝을 못 지었다", hit[0])

    def test_derived_경로에서_밀림_속_진짜_오류가_묻히지_않는다(self):
        # Important 3. 기존 묵음 검증(브리프 Step 6·7)은 전부 실험06 위에서
        # 도는데, 실험06 의 표 다섯은 전부 `manual:pN` 이라 derived 키
        # 경로를 한 번도 지나지 않는다. 이 테스트는 실험01(9개 중 5개가
        # derived)을 `_shifted(2, 9)` 로 밀고, 밀려서 T4 가 되는 표
        # (원래 T3, source `derived (Y = (A·B·C)')`, 3-input NAND)의
        # 마지막 행 Y 값을 0→1 로 바꿔 진짜 오류를 심는다. source 는
        # 안 건드렸으니 T3↔T4 짝짓기는 그대로 유지돼야 하고, 오정렬
        # 소음이 사라졌다고 해서 이 셀 오류까지 함께 묻히면 안 된다.
        target = self._shifted(self.WEEK2, 2, 9)
        text = target.read_text(encoding="utf-8")
        old, new = "| 1 | 1 | 1 | 0 |", "| 1 | 1 | 1 | 1 |"
        self.assertEqual(
            text.count(old), 2,
            f"픽스처가 바뀌었다 — {old!r} 가 두 번 나와야 한다(NAND·NOR 표 각각 한 번)")
        target.write_text(text.replace(old, new, 1), encoding="utf-8")

        diffs = compare_specs(self.WEEK2, target)
        hit = [d for d in diffs if d.startswith("표 T3→T4") and "Y" in d]
        self.assertEqual(len(hit), 1, diffs)
        self.assertIn("'0'", hit[0])
        self.assertIn("'1'", hit[0])


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
