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

from scripts.lab import config
from scripts.lab.specdiff import compare_specs, uncovered_tables

ROOT = Path(__file__).resolve().parents[1]
# 씨앗은 픽스처다. 살아 있는 실험을 쓰면, 그 주차를 다시 저작할 때마다
# 여기 박아 둔 `0->1`·`manual:p9` 같은 값이 함께 사라져 검사기 회귀망이
# 통째로 빨개진다 — 검사기는 안 바뀌었는데도. `EDGE` 는 표 T1~T5·머리말
# 규약표를 가진 씨앗, `CAPTURE` 는 capture/stepped 표를 가진 씨앗이다.
EDGE = ROOT / "tests/fixtures/spec_edge.md"
CAPTURE = ROOT / "tests/fixtures/spec_capture.md"


class CompareSpecs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _mutated(self, old, new, source=EDGE):
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
        self.assertEqual(compare_specs(EDGE, EDGE), [])

    def test_라이징_엣지가_리터럴_1_로_돌아가면_그_자리를_짚는다(self):
        # 이 파일이 존재하는 이유가 이 한 줄이다. 재생성물의 이 셀이 `1` 이면
        # 텍스트 추출의 지뢰를 밟은 것이고, 그것을 사람 눈에 맡기지 않는다.
        target = self._mutated("| 0 | 0->1 | 0 |", "| 0 | 1 | 0 |")
        diffs = compare_specs(EDGE, target)
        self.assertEqual(len(diffs), 1, diffs)
        self.assertIn("0->1", diffs[0])
        self.assertIn("'1'", diffs[0])

    def test_encoding_이_바뀌면_잡는다(self):
        target = self._mutated("- encoding: 0/1", "- encoding: H/L")
        diffs = compare_specs(EDGE, target)
        self.assertTrue(any("encoding" in d for d in diffs), diffs)

    def test_같은_글자_열의_셀_차이는_자리로_부른다(self):
        """실험3 반감산기 `A B D B` — 입력 B 와 출력 B 중 어느 쪽이 갈렸는지 말한다."""
        shared = ROOT / "tests/fixtures/spec_shared_letter.md"
        target = self._mutated("| 0 | 1 | 1 | 1 |", "| 0 | 1 | 1 | 0 |", source=shared)
        diffs = compare_specs(shared, target)
        self.assertEqual(len(diffs), 1, diffs)
        self.assertIn("표 T5 행2 B(4열): 원본 '1' / 재생성 '0'", diffs[0])

    def test_pages_가_바뀌면_잡는다(self):
        shared = ROOT / "tests/fixtures/spec_shared_letter.md"
        target = self._mutated("pages: [6]", "pages: [7]", source=shared)
        diffs = compare_specs(shared, target)
        self.assertEqual(len(diffs), 1, diffs)
        self.assertIn("pages", diffs[0])

    def test_source_가_바뀌면_잡는다(self):
        target = self._mutated("- source: manual:p9", "- source: manual:p99")
        diffs = compare_specs(EDGE, target)
        self.assertTrue(any("source" in d for d in diffs), diffs)

    def test_source_manual이_바뀌면_잡는다(self):
        # 최종 전체-브랜치 리뷰 C1. `source_manual` 은 스키마 필수 필드이고
        # `write-pre-report`·`write-result-report` 두 스킬이 "손으로
        # 짐작하지 않는다 — 명세의 `source_manual` 이 가리킨다" 로 실제로
        # 소비한다. 컨트롤러 재현: 실험06 명세의 `source_manual` 을
        # 실험6.pdf -> 실험5.pdf 로 바꿔도 옛 코드는 차이 0건이었다.
        target = self._mutated(
            "source_manual: from_the_past/정리/강의노트/실험6.pdf",
            "source_manual: from_the_past/정리/강의노트/실험5.pdf",
        )
        diffs = compare_specs(EDGE, target)
        self.assertTrue(any("source_manual" in d for d in diffs), diffs)

    def test_전원_레일이_빠지면_잡는다(self):
        target = self._mutated('power: {VCC: "+5V", GND: "GND"}',
                               'power: {VCC: "+5V"}')
        diffs = compare_specs(EDGE, target)
        self.assertTrue(any("전원" in d for d in diffs), diffs)

    def test_표_제목이_바뀌면_잡는다(self):
        """표 제목은 산문이 아니다 — `render.py`·`record.py` 가 소비해
        인쇄용 체크리스트와 `기록.md` 헤딩에 그대로 찍힌다. 2026-08-31·
        09-01 두 회차에서 재생성이 다섯 표를 전부 `특성표` -> `진리표` 로
        바꿨는데 대조가 0건을 냈다."""
        target = self._mutated("## T1 · R-S Latch with Enable 특성표",
                               "## T1 · R-S Latch with Enable 진리표")
        diffs = compare_specs(EDGE, target)
        self.assertTrue(any("표 T1" in d and "title" in d for d in diffs),
                        diffs)

    def test_항목_제목이_바뀌면_잡는다(self):
        """`E6.P1` 이 잃은 `(Gate 이용)` 은 게이트 구성과 IC 구성을
        가르는 표시다. 뜻이 있는 차이인데 대조 밖이었다."""
        target = self._mutated("title: R-S Latch with Enable (Gate 이용)",
                               "title: R-S Latch with Enable")
        diffs = compare_specs(EDGE, target)
        self.assertTrue(any("항목" in d and "title" in d for d in diffs),
                        diffs)

    def test_명세_제목이_바뀌면_잡는다(self):
        """프론트매터 `title` 도 계약 필수 필드다(스키마 `:22`) —
        `source_manual` 을 대조에 넣은 것과 같은 이유다."""
        target = self._mutated("title: Latch & Flip-Flop",
                               "title: 래치와 플립플롭")
        diffs = compare_specs(EDGE, target)
        self.assertTrue(any("프론트매터 title" in d for d in diffs), diffs)

    def test_ics_순서만_바뀌면_차이로_보지_않는다(self):
        # ics 는 그 항목이 쓰는 IC 패키지 이름의 집합이지 순서가 아니다.
        # device·tables 도 같은 이유로 순서 무시다(스키마상 참조 목록).
        target = self._mutated('ics: ["74HC00", "74HC04"]',
                               'ics: ["74HC04", "74HC00"]')
        self.assertEqual(compare_specs(EDGE, target), [])

    def test_capture_표의_expected가_바뀌어도_compare_specs는_묵음이다(self):
        # capture 표는 셀이 없고 기술적 주장이 전부 expected 산문에 있다.
        # expected 는 산문이라 대조 대상이 아니므로, 사실을 뒤집어도
        # compare_specs 는 잡지 못한다 — 이것은 결함이 아니라 알려진 구멍
        # 이고, uncovered_tables 가 그 구멍을 알린다(아래 UncoveredTables).
        #
        # `expected` 는 `SpecTable` 로 실제로 파싱된다 — 파서가 아예 담지
        # 않는 본문 서술(예: 어떤 필드로도 안 들어가는 안내문)을 만지면,
        # `_ITEM_FIELDS`·`_TABLE_FIELDS` 에 `expected` 가 실수로 들어가도
        # 이 테스트는 원래부터 통과해 아무것도 지키지 못한다. 그래서
        # 반드시 "파싱되지만 일부러 뺀" 자리(`expected`)를 만져야 한다 —
        # `title` 은 2026-09-01 부터 더 이상 그 자리가 아니다(대조에
        # 들어왔다). 이 파일에 있던
        # `test_파싱은_되지만_제외된_필드는_차이로_보지_않는다` 가 그
        # 취지를 `title` 로 지키다가 이 테스트와 중복이 되어, 이 테스트로
        # 취지를 옮기고 그쪽은 지웠다.
        target = self._mutated(
            "계단 상승한 뒤 리셋되는 톱니 형태",
            "계단 하강한 뒤 리셋되는 역톱니 형태",
            source=CAPTURE,
        )
        self.assertEqual(compare_specs(CAPTURE, target), [])

    def test_다른_주차끼리는_양쪽_방향을_다_보고한다(self):
        # 실험06 은 표 T1~T5·항목 다섯, 실험10 은 표 T1~T2·항목 둘이다.
        forward = compare_specs(EDGE, CAPTURE)
        self.assertTrue(any("원본에만 있다" in d for d in forward), forward)
        backward = compare_specs(CAPTURE, EDGE)
        self.assertTrue(any("재생성에만 있다" in d for d in backward), backward)

    def test_표_삽입으로_ID가_밀리면_셀_차이_대신_ID_불일치를_먼저_알린다(self):
        # 실측(실험06 재생성 2건): 교안 p5 이론표를 T2 로 끼워 넣으면 그
        # 뒤 T2~T5 가 전부 T3~T6 로 밀린다. ID 로만 짝지으면 원본 T3
        # (교안 p9)과 재생성 T3(실은 밀린 옛 T2, 교안 p8)이 서로 다른
        # 표인데 짝지어져, 셀 내용이 완전히 같은데도 차이가 쏟아진다
        # (실측 19건). 이 테스트는 그 상황을 실험06 명세를 직접 변형해
        # 재현한다 — 손으로 만든 픽스처가 아니다.
        text = EDGE.read_text(encoding="utf-8")
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

        diffs = compare_specs(EDGE, target)

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
        # 없는 표라는 사실(observed: source 가 원본에 없다) 자체는 여전히
        # 알려야 한다. 그래서 네 갈래 중 2번("source 가 상대에 없다")으로
        # 보고된다.
        #
        # Minor 1 회귀(라운드 1 에서 못 고친 것): 검사 범위를 T2 하나로
        # 좁히면 나머지 표(T1·T3~T6)가 잘못 한쪽에만 있다고 찍혀도 못
        # 잡는다. `_table_diffs` 가 짝을 못 지은 표에 내는 줄은 항상
        # "표 {id}: ..." 형태다(필드 차이 줄은 "표 {id} {field}: ..." 로
        # ID 뒤에 콜론이 바로 오지 않는다) — 그 형태의 줄 **전부**를 먼저
        # 걷어낸 뒤, T2 를 뺀 나머지에 그런 줄이 하나도 없는지 검사한다.
        one_sided = [d for d in diffs if re.match(r"^표 T\d+(?:→T\d+)?: ", d)]
        others = [d for d in one_sided if not d.startswith("표 T2:")]
        self.assertEqual(
            others, [],
            f"밀림으로 ID 만 어긋난 표가 상대에 없다는 취지로 잘못 보고됐다: {others}")
        table_report = [d for d in one_sided if d.startswith("표 T2:")]
        self.assertEqual(len(table_report), 1, diffs)
        self.assertIn("원본 어디에도 없다", table_report[0])

    WEEK2 = ROOT / config.experiment_dir(1) / "체크리스트/명세.md"
    DERIVED = ROOT / "tests/fixtures/spec_derived.md"

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
        # 5/6, 실험01 은 5/10. `derived` 를 짝짓기 키에서 빼면 그 명세들에서
        # 오정렬이 그대로 남는다. 실측: 고치기 전 19건(셀 차이 8건), 진짜
        # 내용 오류는 0건이었다.
        target = self._shifted(self.WEEK2, 2, 10)
        diffs = compare_specs(self.WEEK2, target)
        cells = [d for d in diffs if "행" in d]
        self.assertEqual(cells, [], f"셀을 하나도 안 건드렸는데 차이가 났다: {cells}")

        # Critical 1 회귀 — 짝마다 한 줄이 아니라 요약 한 줄이어야 한다.
        # 이 시나리오는 T2~T10 아홉 개가 전부 ID 가 어긋난 채 짝지어지는데
        # (원본 T2→사본 T3, ..., 원본 T10→사본 T11), 짝마다 냈으면 9줄이
        # 늘었을 자리다. 실측(컨트롤러): 짝마다 내면 실험01 정당한 밀림에서
        # 9줄이 늘고, 요약이면 1줄이다.
        shift_lines = [d for d in diffs if d.startswith("[표 ID 가 어긋난 채 짝지어졌다]")]
        self.assertEqual(len(shift_lines), 1, diffs)
        # I1 회귀(재리뷰 2). 이 시나리오는 표가 하나 늘어(ID 집합이
        # 다르다) 밀림으로 설명은 되지만, 같은 실행 안에서 "밀림"과
        # "표 내용이 다른 ID 로 옮겨간 것"은 코드가 구별할 수 없는 같은
        # 관측 결과를 낳는다(리뷰어 재현: 실험06 에서 정당한 밀림 8건과
        # 밀림+내용이동 8건이 건수가 같았다). 그래서 이 문구는 원인을
        # 단정하지 않고 두 가능성을 함께 말해야 한다 — 강한 경고 쪽
        # ("표 내용이 서로 다른 ID 로 옮겨갔을 수 있다는 뜻이다")처럼
        # 하나로 단정하면 안 된다.
        self.assertIn("표 추가·삭제로 ID 가 밀린 것일 수도", shift_lines[0])
        self.assertIn("표 내용이 서로 다른 ID 로 옮겨간 것일 수도 있다", shift_lines[0])
        self.assertIn("코드가 구별할 수 없다", shift_lines[0])

    def test_짝을_못_지은_표는_한쪽에만_있다고_말하지_않는다(self):
        # source 짝짓기가 원본 Tx 를 재생성 Ty(x≠y) 와 묶으면, 원본 Ty 와
        # 재생성 Tx 가 둘 다 짝을 잃는다. 밀림으로 ID 만 어긋난 표들은
        # 어느 쪽으로도(3갈래 중 무엇으로도) "이 표가 상대에 없다" 는
        # 취지의 줄로 보고되면 안 된다 — 전부 source 로 정상 짝지어지기
        # 때문이다. 유일한 예외는 `_shifted` 가 새로 끼워 넣는 T2 다 —
        # 그 표의 source(`manual:p99`)는 원본 어디에도 없는 **정말 새
        # 표**라서(2번 갈래로 떨어진다: source 가 상대에 없다는 관측
        # 사실을 말한다), 이 표만 빼고 나머지 T1·T3~T11 전부를 통틀어
        # 검사한다. 옛 필터(`d.startswith("표 T2:")`)처럼 검사 범위
        # 자체를 T2 하나로 좁히면 T4·T5 가 잘못 짝을 잃어도 못 잡으므로
        # 쓰지 않는다.
        target = self._shifted(self.WEEK2, 2, 10)
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
        self.assertIn("원본 어디에도 없다", unmatched[0])

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
        # Important 1 회귀(라운드 2 재작성). 실험06 에서 T2(D Latch with
        # Enable, source manual:p8) 블록을 통째로 지우고 뒤 ID(T3~T5)를
        # 하나씩 당기면, 밀린 표들(원본 T3→사본 T2 등)은 source 로 정상
        # 짝지어져서 사본에도 우연히 "T2" 라는 ID 가 있다. ID 만 보면
        # 이건 4번 갈래("짝을 못 지었다")처럼 보이기 쉽지만, 원본 T2 의
        # 내용(D Latch with Enable, source manual:p8)은 사본 어디에도
        # 없으므로 source 기준으로는 2번 갈래가 맞다. 이걸 4번 갈래로
        # 찍으면 진짜 삭제가 정렬 잡음처럼 읽힌다.
        #
        # 재리뷰 Important 1: 2번 갈래는 더 이상 "원본에만 있는 표다"로
        # 단정하지 않는다 — 삭제와 source 오기재를 구별할 수 없기
        # 때문이다. 대신 관측 사실(source 가 상대 어디에도 없다)만 말하고
        # 원인 후보 둘을 함께 적는다.
        target = self._table_removed(EDGE, "T2")
        diffs = compare_specs(EDGE, target)
        hit = [d for d in diffs if d.startswith("표 T2:")]
        self.assertEqual(len(hit), 1, diffs)
        self.assertIn("manual:p8", hit[0])
        self.assertIn("재생성 어디에도 없다", hit[0])
        self.assertIn("표가 빠졌거나 source 가 잘못 옮겨졌을 수 있다", hit[0])
        self.assertIn("재생성에도 같은 ID 가 있다", hit[0])
        self.assertNotIn("짝을 못 지었다", hit[0])

    def test_derived_경로에서_밀림_속_진짜_오류가_묻히지_않는다(self):
        # Important 3. 기존 묵음 검증(브리프 Step 6·7)은 전부 실험06 위에서
        # 도는데, 실험06 의 표 다섯은 전부 `manual:pN` 이라 derived 키
        # 경로를 한 번도 지나지 않는다. 이 테스트는 실험01(10개 중 5개가
        # derived)을 `_shifted(2, 10)` 로 밀고, 밀려서 T4 가 되는 표
        # (원래 T3, source `derived (L1 = A·B ; L2 = (A·B·C)')`, 3-input
        # NAND)의 마지막 행 L2 값을 0→1 로 바꿔 진짜 오류를 심는다. source 는
        # 안 건드렸으니 T3↔T4 짝짓기는 그대로 유지돼야 하고, 오정렬
        # 소음이 사라졌다고 해서 이 셀 오류까지 함께 묻히면 안 된다.
        target = self._shifted(self.WEEK2, 2, 10)
        text = target.read_text(encoding="utf-8")
        old, new = "| 1 | 1 | 1 | 1  | 0  |", "| 1 | 1 | 1 | 1  | 1  |"
        self.assertEqual(
            text.count(old), 2,
            f"픽스처가 바뀌었다 — {old!r} 가 두 번 나와야 한다(NAND·NOR 표 각각 한 번)")
        target.write_text(text.replace(old, new, 1), encoding="utf-8")

        diffs = compare_specs(self.WEEK2, target)
        hit = [d for d in diffs if d.startswith("표 T3→T4") and "L2" in d]
        self.assertEqual(len(hit), 1, diffs)
        self.assertIn("'0'", hit[0])
        self.assertIn("'1'", hit[0])

    def _table_ids_swapped(self, source, id1, id2):
        """`source` 명세에서 `## {id1} ·`/`## {id2} ·` 헤딩 **줄만** 맞바꾼
        사본. 몸통(필드·셀)과 항목은 손대지 않는다.

        헤딩 줄만 바뀌고 그 아래 내용은 원래 자리에 그대로 남으므로,
        결과는 "표 몸통이 다른 ID 로 옮겨간" 것과 정확히 같은 모양이다
        — 예를 들어 원래 `## T1 · 반가산기 진리표` 였던 자리는 헤딩만
        `## T2 · 전가산기 진리표` 로 바뀌고 그 아래 필드·셀(반가산기
        내용)은 그대로다.
        """
        lines = source.read_text(encoding="utf-8").split("\n")
        idx1 = next(i for i, l in enumerate(lines) if l.startswith(f"## {id1} "))
        idx2 = next(i for i, l in enumerate(lines) if l.startswith(f"## {id2} "))
        lines[idx1], lines[idx2] = lines[idx2], lines[idx1]
        target = Path(self.tmp.name) / "명세.md"
        target.write_text("\n".join(lines), encoding="utf-8")
        return target

    def test_표_헤딩만_맞바뀌면_ID_어긋난_짝을_경고한다(self):
        # Critical 1. `_pair_tables` 는 source 로 짝짓는다. 헤딩(ID+제목)
        # 만 맞바꾸고 몸통(필드·셀)은 그대로 두면, 원본 T1 의 source·셀이
        # 사본에서는 ID T2 아래에 있다 — 표 내용이 다른 ID 로 옮겨간 것과
        # 구별할 수 없는 모양이다. 43b91c6 은 필드·셀이 완전히 같은 이
        # 짝에 대해 아무 줄도 내지 않아 차이 0건(거짓 합격)이었다(컨트롤러
        # 실측). 실험03 은 표 4개가 전부 `derived` 라 C1(derived 도
        # 짝짓기 키로 허용)이 만든 사각지대 그 자체를 지난다.
        target = self._table_ids_swapped(self.DERIVED, "T1", "T2")
        diffs = compare_specs(self.DERIVED, target)
        # `title` 이 2026-09-01 에 대조 대상이 된 뒤로는 3건이 맞다 — 헤딩을
        # 맞바꾸면 제목도 몸통과 함께 옮겨가므로, ID 불일치 알림 1건에 더해
        # 양쪽 짝 각각의 title 차이 2건이 정당하게 따라붙는다. 이 테스트는
        # 원래 "제목이 대조 밖이라 조용하다"를 전제로 1건을 기대했었다 —
        # 그 전제 자체가 이번 태스크가 닫는 사각지대였다.
        self.assertEqual(
            len(diffs), 3,
            f"차이가 3건이 아니다 — ID 불일치 알림 1건과 헤딩을 따라 옮겨간 "
            f"title 차이 2건(양쪽 짝)을 기대했다: {diffs}")
        # 실험03 은 표를 넣거나 뺀 적이 없다 — ID 집합이 같은데 짝이
        # 어긋났으므로 강한 경고(표 내용이 다른 ID 로 옮겨갔을 수 있다)
        # 여야 한다. `_table_id_mismatch_notice`(표 추가·삭제 알림)와는
        # 다른 문구다.
        self.assertIn("표 내용이 서로 다른 ID 로 옮겨갔을 수 있다", diffs[0])
        self.assertIn("T1→T2", diffs[0])
        self.assertIn("T2→T1", diffs[0])
        self.assertTrue(any("표 T1→T2 title" in d for d in diffs), diffs)
        self.assertTrue(any("표 T2→T1 title" in d for d in diffs), diffs)
        # 짝지은 필드·셀 중 title 을 뺀 나머지(행·헤더 등 진짜 몸통)는
        # 여전히 조용하다 — 손댄 것은 헤딩(ID+제목)뿐이다.
        self.assertFalse(any("행" in d for d in diffs), diffs)
        self.assertFalse(any("헤더" in d for d in diffs), diffs)

    def test_source_없는_새_표는_source_없음이라고_말한다(self):
        # Minor 2. `SpecTable.source` 는 `Optional[str]` 이라, 재생성이
        # 표를 새로 끼우며 `- source:` 줄을 빠뜨리면 그 표는 source 로
        # 판별할 수 없다. 그냥 "짝을 못 지었다"로만 찍으면 정말 새로
        # 추가된 표가 정렬 잡음처럼 읽힌다 — source 가 없어 판별 불가
        # 라는 사실 자체를 알려야 한다.
        target = self._shifted(self.WEEK2, 2, 10)
        text = target.read_text(encoding="utf-8")
        old = "- source: manual:p99\n"
        self.assertIn(old, text, "픽스처가 바뀌었다 — source 줄이 없다")
        target.write_text(text.replace(old, "", 1), encoding="utf-8")

        diffs = compare_specs(self.WEEK2, target)
        hit = [d for d in diffs if d.startswith("표 T2:")]
        self.assertEqual(len(hit), 1, diffs)
        self.assertIn("source 가 없어 판별할 수 없다", hit[0])
        self.assertIn("원본에도 같은 ID 가 있다", hit[0])

    def test_한쪽만_있음_갈래가_서로_다른_시나리오에서_섞이지_않는다(self):
        # I3 회귀(재리뷰 2). 옛 테스트("Minor 3 회귀")는 여덟 문구를
        # 하드코딩한 리터럴 리스트로 두고 자기들끼리 부분 문자열 검사를
        # 했다 — `_table_diffs` 를 한 번도 부르지 않았다. 리뷰어가 두 번
        # 증명했다: 갈래 2 문구를 라운드 1 것으로 되돌려도 그 테스트는
        # OK 였고, 갈래 4 를 갈래 3 의 부분 문자열로 바꿔도 OK 였다.
        # 게다가 그 테스트가 고정하려던 성질의 전제 자체가 틀렸다 —
        # "원본에만 있다" 는 "원본에만 있는 표다" 의 부분 문자열이
        # 아니다(`있다` vs `있는`). 라운드 0 이 공허 통과한 진짜 원인은
        # 소비자 필터의 접두 어긋남이지 부분 문자열 관계가 아니었다.
        #
        # 그래서 리터럴 비교 대신 `compare_specs` 를 실제로 두 번 불러
        # 서로 다른 갈래(3: source 가 없어 판별 불가 / 4: source·ID 가
        # 둘 다 상대에 있는데 짝짓기만 실패)를 발화시키고, 각 출력 줄이
        # 자기 갈래로만 식별되는지 — 다른 갈래의 판별 문구가 섞여
        # 들어오지 않는지 — 검사한다.
        def bump(text, first, last):
            def repl(m):
                n = int(m.group(1))
                return f"T{n + 1}" if first <= n <= last else m.group(0)
            out = []
            for line in text.split("\n"):
                if line.lstrip().startswith("tables:") or line.startswith("## T"):
                    line = re.sub(r"T(\d+)", repl, line)
                out.append(line)
            return "\n".join(out)

        marker = "## T3 · D Latch with Enable 특성표"

        # 시나리오 1 — 갈래 3(source 없음): 정당한 밀림(T2~T5 → T3~T6)에
        # 새로 끼운 표가 source 를 아예 안 적었다.
        text1 = bump(EDGE.read_text(encoding="utf-8"), 2, 5)
        self.assertIn(marker, text1, "픽스처가 바뀌었다 — 삽입 지점을 못 찾았다")
        inserted1 = ("## T2 · source 없이 끼운 표\n\n"
                     "- kind: truth-table\n- encoding: 0/1\n- role: reference\n\n"
                     "| A | Y |\n|---|---|\n| 0 | 0 |\n\n")
        target1 = Path(self.tmp.name) / "명세1.md"
        target1.write_text(text1.replace(marker, inserted1 + marker, 1),
                           encoding="utf-8")
        diffs1 = compare_specs(EDGE, target1)

        # 시나리오 2 — 갈래 4(짝짓기만 실패): 같은 밀림에, 새로 끼운
        # 표의 source 를 원본 T3(D F/F, source manual:p9)과 중복시킨다.
        # source 유일성이 깨지면 원본 T3 은 1차 루프에서 짝을 못 찾고,
        # 밀렸으므로 ID 로도 못 찾는다(사본의 "T3" 자리는 이미 다른
        # 짝(원본 T2 ↔ 사본 T3, source p8)이 차지했다) — source 도 ID 도
        # 상대에 있지만 그저 짝짓기에 실패한, 갈래 4 의 정의 그대로다.
        text2 = bump(EDGE.read_text(encoding="utf-8"), 2, 5)
        self.assertIn(marker, text2, "픽스처가 바뀌었다 — 삽입 지점을 못 찾았다")
        inserted2 = ("## T2 · 끼운 중복 source 표\n\n"
                     "- kind: truth-table\n- encoding: 0/1\n"
                     "- source: manual:p9\n- role: reference\n\n"
                     "| A | Y |\n|---|---|\n| 0 | 0 |\n\n")
        target2 = Path(self.tmp.name) / "명세2.md"
        target2.write_text(text2.replace(marker, inserted2 + marker, 1),
                           encoding="utf-8")
        diffs2 = compare_specs(EDGE, target2)

        one_sided_pat = re.compile(r"^표 T\d+(?:→T\d+)?: (.+)$")
        # 갈래 3 의 정체성: "source 가 없어 판별할 수 없다" 라는 사실이
        # 반드시 있어야 한다. 갈래 4 의 정체성: 그 사실 없이 "짝을 못
        # 지었다 (…에도 같은 ID 가 있다)" 로 끝나야 한다 — 괄호 안에
        # "source 가 없어 판별할 수 없다;" 가 끼어들면(리뷰어가 증명한
        # 바로 그 변형) 더 이상 이 갈래로 식별되지 않는다.
        markers = {
            "no_source": re.compile(r"^짝을 못 지었다 \(source 가 없어 판별할 수 없다;"),
            "unmatched_only": re.compile(r"^짝을 못 지었다 \((원본|재생성)에도 같은 ID 가 있다\)$"),
        }

        def classify(msg):
            return sorted(name for name, pat in markers.items() if pat.search(msg))

        def one_sided_messages(diffs):
            out = []
            for d in diffs:
                m = one_sided_pat.match(d)
                if m:
                    out.append(m.group(1))
            return out

        msgs1 = one_sided_messages(diffs1)
        msgs2 = one_sided_messages(diffs2)

        self.assertEqual(len(msgs1), 1, diffs1)
        self.assertEqual(
            classify(msgs1[0]), ["no_source"],
            f"갈래 3 문구가 다른 갈래와 섞였거나 정체성을 잃었다: {msgs1[0]!r}")

        self.assertEqual(len(msgs2), 3, diffs2)
        for msg in msgs2:
            self.assertEqual(
                classify(msg), ["unmatched_only"],
                f"갈래 4 문구가 다른 갈래와 섞였거나 정체성을 잃었다: {msg!r}")


class UncoveredTablesTest(unittest.TestCase):
    """`uncovered_tables` 가 `compare_specs` 의 사각지대를 실제로 짚는지 본다.

    두 사각지대를 각각 확인한다.

    1. capture 표는 `header=[]`·`rows=[]` 라 `compare_specs` 의 셀 대조가
       언제나 같다고 나온다(위 `test_capture_표의_expected가_바뀌어도_
       compare_specs는_묵음이다` 참조).
    2. 최종 전체-브랜치 리뷰 I1. 첫 `## T` 헤딩 **앞**의 본문에 있는
       마크다운 표는 `spec_parser.parse_spec` 이 아예 스캔하지 않아
       `LabSpec.tables` 에 실리지 않는다 — `compare_specs` 는 그런 표가
       있는지조차 모른다.

    둘 다 사람이 알아채도록 이름/위치와 이유를 목록으로 내는 함수가
    실제로 그 표를 짚는지, 그리고 없을 때는 짚지 않는지 확인한다.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_실험10_명세에서_capture_표_T1을_짚는다(self):
        found = uncovered_tables(CAPTURE)
        self.assertEqual(len(found), 1, found)
        self.assertIn("T1", found[0])

    def test_실험06_명세는_capture_표가_없어_그_이유로는_안_짚는다(self):
        # 실험06 은 truth-table 뿐이라 capture 표로는 안 짚혀야 한다.
        # (머리말 표는 따로 짚는다 — 아래
        # test_실험06_머리말의_토큰_규약표를_짚는다.)
        found = uncovered_tables(EDGE)
        self.assertFalse(any("셀이 없어 대조가 성립하지 않는다" in f
                             for f in found), found)

    def test_실험06_머리말의_토큰_규약표를_짚는다(self):
        # I1 회귀. 실험06 명세는 첫 `## T1` 헤딩보다 앞, 프론트매터
        # 바로 다음에 "셀 값 표기 규약" 표(`0->1` 을 라이징 엣지로
        # 정의하는 유일한 자리)가 있다 — 컨트롤러 실측으로 실험06 은
        # 이런 머리말 표가 1개다. capture 표가 없으므로 이 한 줄만 나와야
        # 한다.
        found = uncovered_tables(EDGE)
        self.assertEqual(len(found), 1, found)
        self.assertIn("머리말", found[0])
        self.assertIn("1개", found[0])

    WEEK2 = ROOT / config.experiment_dir(1) / "체크리스트/명세.md"

    def test_머리말에_표가_없는_명세는_그_이유로는_안_짚는다(self):
        # I1 회귀. 실험10 은 첫 `## T` 헤딩 앞에 마크다운 표가 0개다 —
        # uncovered_tables 가 머리말 표 사유로 잘못 짚으면 안 된다.
        # (실험10 은 capture 표(T1) 사유로 여전히 짚히므로, 여기서는
        # "머리말" 문구가 섞여 들지 않는지만 본다.) 실험01 은 2026-09-07
        # 이후 머리말에 토큰 규약표가 하나 있어 **그 사유로 정확히 한 번**
        # 짚혀야 한다 — 양성 대조군이다.
        found_week2 = uncovered_tables(self.WEEK2)
        self.assertEqual(len(found_week2), 1, found_week2)
        self.assertIn("머리말", found_week2[0])

        found_week12 = uncovered_tables(CAPTURE)
        self.assertFalse(any("머리말" in f for f in found_week12), found_week12)

    def test_expected가_바뀌어도_여전히_그_표를_짚는다(self):
        # compare_specs 는 이 변형을 못 잡는다(별도 테스트로 확인됨) —
        # 여기서는 uncovered_tables 가 그 자리를 계속 알린다는 것,
        # 즉 "묵음" 이 아니라 "알려진 구멍" 임을 고정한다.
        text = CAPTURE.read_text(encoding="utf-8")
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
