"""스킬 문서의 불변식.

`write-pre-report`·`write-result-report`·`review-lab-report` 는 코드가 아니라
산문 규칙 문서라 컴파일도 실행도 되지 않는다. 그래서 같은 모순이 두 번 되살아났다 — 각주를
없앤 뒤에도 다른 규칙이 그 각주를 가리켰고, 삭제된 단계가 유일한 근거이던
규칙이 함께 사라졌다. 둘 다 격리 에이전트에게 스킬을 실행시켜서야 드러났다.

여기 있는 테스트는 그 실행을 대신하지 못한다. 문서가 좋은 보고서를 만드는지는
검사하지 않는다 — 검사하는 것은 이미 한 번 고친 결함이 되돌아오지 않는지뿐이다.
새 모순을 고칠 때마다 여기에 한 건씩 늘린다.
"""

import re
import unittest
from pathlib import Path

from scripts.lab import config, validate

ROOT = Path(__file__).resolve().parents[1]
PRE = ROOT / ".claude/skills/write-pre-report/SKILL.md"
RESULT = ROOT / ".claude/skills/write-result-report/SKILL.md"
REVIEW = ROOT / ".claude/skills/review-lab-report/SKILL.md"
DRAFT = ROOT / ".claude/skills/draft-lab-spec/SKILL.md"
SYNC = ROOT / ".claude/skills/sync-report-to-notion/SKILL.md"
CANON = ROOT / config.experiment_dir(1) / "output/실험01_예비보고서.md"

# 검사 대상 문서와, 그 문서에서 번호 매긴 항목이 사는 절 이름.
#
# 나머지 다섯 스킬은 **일부러 뺐다.** 관례가 달라 통짜로 넣으면 오탐이 난다 —
# `explain-lab-preview` 는 `## 0.`~`## 8.` 로 자기 절을 번호 매기고 `§0`~`§8` 로
# 참조하며(21건), `sync-report-to-notion` 은 단계가 `## 실행 절차` 가 아니라
# `## push`·`## pull` 안에 산다(7건). 거짓 경보를 내는 검사는 없느니만 못하다.
# `DOCS` 편입과 `check_report_sections` 호출 여부는 별개다 — 상호참조를 보는
# 목록(`DOCS`)과 그 호출부를 보는 목록(`REPORT_SECTION_DOCS`)이 갈려 있다.
# `draft-lab-spec` 처럼 보고서를 만들지 않는 문서를 `DOCS` 에 넣어도
# `REPORT_SECTION_DOCS` 에 넣지 않으면 item_count 검사는 그 문서를 보지 않는다.
DOCS = {
    "예보": (PRE, ("절대 규칙", "실행 절차")),
    "결과": (RESULT, ("절대 규칙", "실행 절차")),
    "리뷰": (REVIEW, ("실행 절차",)),
    "명세": (DRAFT, ("절대 규칙", "실행 절차")),
}

# 보고서를 **쓰는** 두 스킬. 작성 규칙(여백·표 제목·이론 범위 등)은 여기에만 있다.
# ⑤ 는 보고서를 **검사**하는 스킬이라 그 규칙들을 갖지 않는다.
REPORT_DOCS = ("예보", "결과")

# `check_report_sections` 를 실제로 부르는 스킬. **`DOCS` 전체가 아니다** —
# `draft-lab-spec` 은 명세를 만들고 보고서를 만들지 않으므로 그 호출을
# 갖지 않는다. 이 분리 없이 `DOCS` 에 넣으면
# `test_every_skill_passes_item_count_to_the_section_check` 가 곧바로 깨진다.
# `DOCS` 는 상호참조를 보는 목록이고, 이쪽은 호출부를 보는 목록이다.
REPORT_SECTION_DOCS = ("예보", "결과", "리뷰")

# 핀아웃 근거가 실제로 사는 곳. 경로를 문서에만 두면 폴더가 옮겨졌을 때
# 문서가 조용히 거짓말을 한다 — `Breadboard.jpg` 가 정확히 그렇게 깨졌다.
DATASHEET_DIR = "from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃"


def sections(text):
    """`## 제목` 으로 문서를 갈라 {제목: 본문} 으로 돌려준다."""
    out = {}
    for part in re.split(r"^## ", text, flags=re.M)[1:]:
        title, _, body = part.partition("\n")
        out[title.strip()] = body
    return out


def numbered_items(section_body):
    """줄 맨 앞에서 시작하는 항목 번호를 모은다 (`1.` 도 `5b.` 도 받는다)."""
    return {int(n) for n in re.findall(r"^(\d+)[a-z]?\. ", section_body, re.M)}


def subsection_counts(text):
    """`# 대절` 마다 그 아래 `## 소절` 이 몇 개인지 센다."""
    counts = {}
    major = None
    for line in text.splitlines():
        if line.startswith("## "):
            if major is not None:
                counts[major] += 1
        elif line.startswith("# "):
            major = line[2:].strip()
            counts[major] = 0
    return counts


def call_arguments(text, func_name):
    r"""`func(...)` 호출의 괄호 안을 균형을 맞춰 뽑는다.

    정규식 `\([^)]*\)` 은 중첩 괄호(`len(spec.items)`)에서 한 칸 일찍 끊긴다.
    지금은 인자 순서 덕분에 우연히 통과하지만, `item_count` 앞에 다른 중첩
    호출이 오도록 순서가 바뀌면 있는 인자를 없다고 보고한다.
    """
    out = []
    needle = func_name + "("
    i = text.find(needle)
    while i != -1:
        j, depth = i + len(needle), 1
        while j < len(text) and depth:
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
            j += 1
        out.append(text[i + len(needle):j - 1])
        i = text.find(needle, j)
    return out


def _expand(token):
    """`11·13`, `10~15`, `7` 을 번호 집합으로 편다."""
    out = set()
    for part in token.split("·"):
        if "~" in part:
            lo, hi = part.split("~", 1)
            out.update(range(int(lo), int(hi) + 1))
        elif part.isdigit():
            out.add(int(part))
    return out


def cross_reference_errors(text, titles=("절대 규칙", "실행 절차")):
    """`§절대 규칙 N`·`§실행 절차 N`·`N단계` 가 실재하는 항목을 가리키는지 본다.

    `titles` 는 그 문서에서 번호 매긴 항목이 사는 절 이름이다. 문서마다 다르므로
    함수 안에 박지 않는다 — ⑤ 에는 `## 절대 규칙` 이 없어서, 박아 두면 거기
    `§절대 규칙 N` 참조가 생기는 순간 전부 "없음"으로 잡힌다.
    """
    sec = sections(text)
    rules = numbered_items(sec["절대 규칙"]) if "절대 규칙" in titles else None
    steps = numbered_items(sec["실행 절차"]) if "실행 절차" in titles else None
    errors = []
    if rules is not None:
        for token in re.findall(r"§절대 규칙 ([\d·~]+)", text):
            for n in sorted(_expand(token) - rules):
                errors.append(f"§절대 규칙 {n} 없음")
    if steps is not None:
        for token in re.findall(r"§?실행 절차 ([\d·~]+)", text):
            for n in sorted(_expand(token) - steps):
                errors.append(f"실행 절차 {n} 없음")
        for token in re.findall(r"([\d·~]+)단계", text):
            for n in sorted(_expand(token) - steps):
                errors.append(f"{n}단계 없음")

    # 이름 있는 절(`§섹션별 재료` 등) 참조도 검사한다. `§` 다음 토큰이 이
    # 문서의 절 제목 중 하나와 시작이 일치하면 통과.
    # `titles` 로 만든다 — 하드코딩하면 ⑤ 처럼 `## 절대 규칙` 이 없는 문서에서
    # `§절대 규칙 N` 이 이름 검사를 통과한다. 숫자 검사는 위에서 이미
    # 건너뛰므로, 여기까지 통과하면 진짜 죽은 참조가 무음이 된다.
    known = set(sec) | set(titles)
    for ref in re.findall(r"§([^\s,.·()`]+)", text):
        if ref[0].isdigit():
            continue          # `§3` 형태는 별도 테스트가 잡는다
        if not any(k.startswith(ref) or ref.startswith(k.split()[0]) for k in known):
            errors.append(f"§{ref} 절 없음")
    return errors


class CallArgumentScanner(unittest.TestCase):
    """`call_arguments` 가 중첩 괄호에서 일찍 끊기지 않는지 본다."""

    def test_nested_parentheses_do_not_truncate_the_argument_list(self):
        # 정규식 `\([^)]*\)` 은 여기서 `item_count` 앞에서 끊겨 거짓 실패를 낸다.
        src = "f(str(p), fmt.pre, item_count=len(spec.items))"
        self.assertEqual(call_arguments(src, "f"),
                         ["str(p), fmt.pre, item_count=len(spec.items)"])

    def test_finds_every_call_site(self):
        src = "f(a)\n설명 문장\nf(b, c)\n"
        self.assertEqual(call_arguments(src, "f"), ["a", "b, c"])


class SubsectionCounter(unittest.TestCase):
    """`subsection_counts` 가 문자열이 아니라 헤딩 구조를 세는지 본다."""

    def test_counts_subsections_per_major_section(self):
        doc = ("# 가\n## 가1\n본문\n## 가2\n# 나\n## 나1\n## 나2\n## 나3\n")
        self.assertEqual(subsection_counts(doc), {"가": 2, "나": 3})

    def test_a_major_section_with_no_subsections_counts_zero(self):
        doc = ("# 가\n본문만 있다\n# 나\n## 나1\n")
        self.assertEqual(subsection_counts(doc), {"가": 0, "나": 1})


class CrossReferenceChecker(unittest.TestCase):
    """검사기 자체가 죽은 참조를 잡는지부터 확인한다."""

    def test_flags_a_rule_reference_with_no_such_rule(self):
        doc = ("## 절대 규칙\n\n1. **하나.** 본문\n"
               "2. **둘.** §절대 규칙 9 를 본다\n"
               "\n## 실행 절차\n\n1. **첫.** 본문\n")
        self.assertEqual(cross_reference_errors(doc), ["§절대 규칙 9 없음"])

    def test_flags_a_step_reference_with_no_such_step(self):
        doc = ("## 절대 규칙\n\n1. **하나.** 7단계 를 본다\n"
               "\n## 실행 절차\n\n1. **첫.** 본문\n")
        self.assertEqual(cross_reference_errors(doc), ["7단계 없음"])

    def test_expands_ranges_and_lists(self):
        doc = ("## 절대 규칙\n\n1. **하나.** 본문\n2. **둘.** 본문\n3. **셋.** 본문\n"
               "4. **넷.** §절대 규칙 1~3 과 §절대 규칙 2·9 를 본다\n"
               "\n## 실행 절차\n\n0. **영.** 본문\n")
        self.assertEqual(cross_reference_errors(doc), ["§절대 규칙 9 없음"])

    def test_expands_lists_in_step_references_too(self):
        # `5·6단계` 같은 묶음 인용에서 앞 번호가 조용히 빠지면 안 된다 —
        # write-result-report 가 실제로 쓰는 형태다.
        doc = ("## 절대 규칙\n\n1. **하나.** 3·9단계 와 §실행 절차 2·8 을 본다\n"
               "\n## 실행 절차\n\n2. **둘.** 본문\n3. **셋.** 본문\n")
        self.assertEqual(cross_reference_errors(doc),
                         ["실행 절차 8 없음", "9단계 없음"])

    def test_a_clean_document_has_no_errors(self):
        doc = ("## 절대 규칙\n\n1. **하나.** §절대 규칙 2 와 0단계 를 본다\n"
               "2. **둘.** 본문\n"
               "\n## 실행 절차\n\n0. **영.** §실행 절차 0 본문\n")
        self.assertEqual(cross_reference_errors(doc), [])


class SkillDocInvariants(unittest.TestCase):
    def setUp(self):
        self.docs = {k: p.read_text(encoding="utf-8") for k, (p, _) in DOCS.items()}
        # 산문 규칙을 문장으로 찾을 때 쓴다. 문단을 다시 감싸도 규칙이 같으면
        # 통과해야 하므로, 줄바꿈·들여쓰기를 공백 하나로 눌러 둔 사본이다.
        self.flat = {k: re.sub(r"\s+", " ", v) for k, v in self.docs.items()}

    def test_no_dangling_cross_references(self):
        for name, text in self.docs.items():
            with self.subTest(name):
                self.assertEqual(cross_reference_errors(text, DOCS[name][1]), [])

    def test_no_bare_section_number_references(self):
        # 상호참조 표기는 `§절대 규칙 N`·`§실행 절차 N`·`N단계` 뿐이다.
        # `§3` 은 어느 번호 체계인지 말하지 않아 규칙 3 으로도 절차 3 으로도
        # 읽힌다. (`§5.2`·`§3.2` 는 §절대 규칙 11 이 "쓰지 말라"고 인용하는
        # 형태이므로 제외한다 — 숫자 뒤에 점이 온다.)
        for name, text in self.docs.items():
            with self.subTest(name):
                self.assertEqual(re.findall(r"§\d+(?!\.\d)", text), [])

    def test_no_unchecked_rule_reference_notation(self):
        # `§규칙 N` 은 상호참조 검사기가 보지 않는 표기다 — 실제로 이 표기로
        # 쓰인 죽은 참조가 한 번 있었다(§실행 절차 7).
        for name, text in self.docs.items():
            with self.subTest(name):
                self.assertEqual(re.findall(r"§규칙 \d", text), [])

    def test_rule_and_step_numbering_is_contiguous(self):
        # 참조되지 않는 규칙이 지워져도 상호참조 검사기는 보지 못한다 —
        # 가리켜지는 규칙만 보기 때문이다. 번호가 비면 여기서 걸린다.
        for name, text in self.docs.items():
            sec = sections(text)
            for title in DOCS[name][1]:
                first = 0 if title == "실행 절차" else 1
                with self.subTest(f"{name}/{title}"):
                    got = numbered_items(sec[title])
                    self.assertEqual(got, set(range(first, max(got) + 1)))

    def test_sibling_subsection_scope_is_defined(self):
        # 형제를 문서 전체로 읽으면 소절 제목이 표 제목을 겸하는 예외가
        # 무너져 표 레이아웃이 통째로 뒤집힌다. 두 스킬이 같은 기계를 쓴다.
        # ⑤ 는 보고서를 검사하는 스킬이라 작성 규칙을 갖지 않는다.
        for name in REPORT_DOCS:
            with self.subTest(name):
                self.assertIn("형제 소절(같은 대절 안의 소절)", self.flat[name])

    def test_heading_levels_are_capped_at_two(self):
        # `###` 를 허용하면 여백 규칙이 정의되지 않은 자리가 생긴다.
        # ⑤ 는 보고서를 검사하는 스킬이라 작성 규칙을 갖지 않는다.
        for name in REPORT_DOCS:
            with self.subTest(name):
                self.assertIn("`###` 이하는 쓰지 않는다", self.flat[name])

    def test_the_fresh_review_step_withholds_the_manual(self):
        # 저작한 에이전트는 오염돼 있다 — 교안을 20번 읽고 나면 자기가 쓴
        # 명세를 읽을 때 '쓴 것' 이 아니라 '의도한 것' 을 본다. 그래서 맥락
        # 없는 에이전트에게 문서만 건넨다. 교안까지 주면 두 번째 재생성이
        # 되어 비용이 배가 되고 fresh eyes 의 값어치가 사라진다.
        #
        # 대신 교안 전사 오류는 원리적으로 못 잡는다. 그 한계가 문서에
        # 적혀 있어야 "fresh 검토를 통과했으니 맞다" 는 거짓 안심을
        # 안 만든다 — 10단계가 경고하는 바로 그 실패다.
        steps = numbered_items(sections(self.docs["명세"])["실행 절차"])
        self.assertIn(9, steps)
        self.assertIn(10, steps)
        flat = self.flat["명세"]
        self.assertIn("교안 경로는 주지 않는다", flat)
        self.assertIn("교안 전사 오류는 못 잡는다", flat)

    def test_the_folder_guard_precedes_the_refusal(self):
        # config 가 준 경로에 폴더가 없다고 곧바로 거절하면, 폴더가 다른
        # 자리에 멀쩡히 있는데 config 만 안 따라온 경우를 "폴더 없음" 으로
        # 오진한다. 2026-09 에 실험 폴더가 루트에서 `보고서/` 아래로
        # 옮겨졌을 때 실제로 이렇게 틀렸다 — 명세도 결선도도 다 있는데
        # "폴더를 먼저 만드세요" 로 끝날 뻔했다.
        #
        # 가드가 거절 **앞**에 있어야 한다. 뒤에 있으면 이미 거절한 뒤다.
        flat = self.flat["명세"]
        guard = flat.find("거절하기 전에 경로 규약이 낡지 않았는지 본다")
        refuse = flat.find("없으면 거절하고 `init-lab-experiment` 를 안내한다")
        self.assertNotEqual(guard, -1, "경로 가드 문장이 없다")
        self.assertNotEqual(refuse, -1, "거절 문장 앵커가 바뀌었다")
        self.assertLess(guard, refuse)
        # 찾은 경로로 우회하면 나머지 여덟 스킬이 같은 실패를 되풀이한다.
        self.assertIn("우회하지 않는다", flat)

    def test_pinout_evidence_locations_are_pinned(self):
        # 교안에 핀아웃 쪽이 없다고 곧바로 "표준 배치 가정" 으로 적으면
        # 근거 등급이 떨어진다. 실측: 실험01 을 격리 재생성했을 때 초안은
        # 다섯 칩 중 하나만 확인했는데, 승인본은 저장소 데이터시트와 **다른
        # 주차 교안 회로도**로 넷을 확인했다. 저장소에 근거가 있는데 못 찾은
        # 것이다.
        flat = self.flat["명세"]
        self.assertIn(DATASHEET_DIR, flat)
        self.assertIn("다른 주차 교안", flat)
        # 경로가 실재해야 한다 — 문서만 고치고 폴더가 사라지면 무의미하다.
        self.assertTrue((ROOT / DATASHEET_DIR).is_dir(), DATASHEET_DIR)

    def test_breadboard_template_path_and_home_are_pinned(self):
        # 경로가 §절대 규칙 8 의 예시에만 있고, 저장소에 사본이 둘이다.
        rows = [ln for ln in self.docs["예보"].splitlines()
                if ln.startswith("| 회로 결선도 |")]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn(".claude/assets/Breadboard.jpg", rows[0])
        self.assertIn("## 브레드보드 작도", rows[0])

    def test_subsection_count_is_derived_from_the_spec(self):
        # 규칙만으로 재생성하면 소절이 늘어난다 (8,345자 → 11,130자 실측).
        self.assertIn("소절 수는 명세에서 파생한다", self.flat["예보"])
        rules = numbered_items(sections(self.docs["예보"])["절대 규칙"])
        self.assertIn(17, rules)

    def test_report_paragraphs_are_not_hard_wrapped(self):
        # 검사기(`check_report_wrapping`)만 알고 스킬 문서는 모르던 규칙이다.
        # 격리 재생성에서 118곳이 접힌 채 나왔다 — 저장소의 다른 마크다운이
        # 전부 76열로 접혀 있어 에이전트가 그 관례를 따랐고, 문서에 말릴
        # 근거가 없었다. 검사가 뒤에서 잡았지만 예방은 못 했다.
        rules = numbered_items(sections(self.docs["예보"])["절대 규칙"])
        self.assertIn(18, rules)
        self.assertIn("보고서 문단을 줄로 쪼개지 않는다 — 한 문단이 한 줄이다",
                      self.flat["예보"])
        # 무엇을 접지 '않는' 대상인지까지 적혀야 표까지 이어 붙이지 않는다.
        self.assertIn("표 행·헤딩·`<empty-block/>` 같은 블록", self.flat["예보"])

    def test_wide_tables_are_split_for_the_a4_export(self):
        # 노션 PDF 내보내기가 넓은 표를 경고 없이 자른다. 실험05 v1 이 14열
        # 표에서 Y7~Y9 를, 13열 표에서 GS·EO 를 잃은 채 나갔다 — 하필 본문이
        # "GS 와 EO 가 함께 갈라 준다"고 설명하는 그 두 열이었다.
        rules = numbered_items(sections(self.docs["예보"])["절대 규칙"])
        self.assertIn(19, rules)
        # 한계값이 규칙과 코드 두 곳에 산다. 문서 쪽을 코드 상수로 조립해
        # 대조한다 — 글자로 박아 두면 한쪽만 바뀌어도 초록으로 지나간다.
        self.assertIn(f"표는 {validate.NOTION_A4_MAX_COLUMNS}열까지다",
                      self.flat["예보"])
        # 명세를 고치는 쪽으로 새면 정본이 렌더 사정에 끌려간다.
        self.assertIn("명세를 고치지 말고 보고서에서 나눈다", self.flat["예보"])

    def test_worked_subsection_example_matches_the_approved_report(self):
        # 규칙 17 의 예시 숫자를 살아 있는 정본에서 실제로 세어 대조한다.
        # 노션 baseline 이 아니라 정본을 읽는다 — baseline 은 판본이 바뀌면
        # 낡고, 게다가 사용자가 옛 노션 페이지를 지울 때 함께 지우기 쉽다.
        # 계획이 이 숫자를 한 번 틀렸다 — 결선 소절을 4개라고 썼는데 정본은
        # 6개다(공통 규칙 + 배선 3 + 실험 전 확인할 사항 + 브레드보드 작도).
        # 문자열 존재만 보면 같은 실수가 다시 지나간다.
        counts = subsection_counts(CANON.read_text(encoding="utf-8"))
        self.assertEqual(counts["실험 과정 및 예상 결과"], 3)
        self.assertEqual(counts["회로 결선도"], 6)
        # 규칙의 예시 문장을 정본에서 센 숫자로 조립해 대조한다. 줄바꿈에
        # 기대지 않는다 — 문단을 다시 감싸도 규칙이 같으면 통과해야 한다.
        n_proc, n_wire = counts["실험 과정 및 예상 결과"], counts["회로 결선도"]
        self.assertIn(f"`items` {n_proc}개면 과정 {n_proc}소절, 결선 {n_wire}소절이다.",
                      self.flat["예보"])

    def test_ai_usage_log_gate_is_written_against_the_parsed_value(self):
        # config.load_course_info() 는 YAML `~` 를 None 으로 돌려준다.
        # "`~` 가 아니면" 을 글자대로 구현하면 항상 참이 되어 로그를 남긴다.
        # ⑤ 는 보고서를 검사하는 스킬이라 작성 규칙을 갖지 않는다.
        for name in REPORT_DOCS:
            with self.subTest(name):
                self.assertNotIn("`ai_usage_log` 가 `~` 가 아니면", self.docs[name])
                self.assertIn(
                    "`ai_usage_log` 가 비어 있지 않으면(`None` 이 아니면)",
                    self.flat[name])

    def test_every_skill_passes_item_count_to_the_section_check(self):
        # item_count 없이 부르면 per-item 반복 횟수 검사가 통째로 생략된다.
        # ⑤ 도 같은 인자를 넘겨야 한다 — 안 그러면 같은 보고서를 두 기준으로 잰다.
        for name in REPORT_SECTION_DOCS:
            with self.subTest(name):
                calls = call_arguments(self.docs[name], "check_report_sections")
                self.assertTrue(calls, "호출부가 없다")
                for call in calls:
                    self.assertIn("item_count", call)

    def test_rule_16_covers_additions_as_well_as_omissions(self):
        # 강의노트 준비물에 없는 브레드보드·점퍼선·저항 없이는 결선 절이
        # 성립하지 않는다. 규칙 16 이 빼는 쪽만 말해서 판단이 갈렸다.
        self.assertIn("회로가 성립하는 데 필요한데 강의노트 준비물에 없는 소모품",
                      self.flat["예보"])
        # 규칙 5 와의 관계를 명시한 문장도 지워지면 안 된다.
        self.assertIn("§절대 규칙 5 를 푸는 것이 아니다", self.flat["예보"])

    def test_theory_scope_is_bounded_by_what_the_circuit_uses(self):
        # 명세에 표가 없어도 회로가 쓰면 다루고(NOT), 회로가 안 쓰면
        # 강의노트에 있어도 넣지 않는다(부울 대수 기본 정리).
        pre = self.docs["예보"]
        self.assertIn("이론 절은 그 주 회로가 실제로 쓰는 것만 다룬다",
                      self.flat["예보"])
        # 규칙의 예시가 하필 그 주 회로의 핵심 기법을 "빼라" 목록에 넣은 적이
        # 있다 — 실험1 의 2입력→3입력 캐스케이드가 곧 결합법칙인데, 예시가
        # `결합 법칙` 을 일반 이론으로 들어 이론 소절 하나를 통째로 지웠다.
        self.assertIn("회로의 기법인 항등식을 일반 이론으로 오해해 빼면",
                      self.flat["예보"])
        rows = [ln for ln in pre.splitlines() if ln.startswith("| 실험 이론 |")]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("범위는 §절대 규칙 16", rows[0])

    def test_untried_table_scan_is_anchored_to_the_body_not_the_raw_text(self):
        # MdTable.line 은 split_frontmatter 뒤의 body 기준이다. `기록.md` 의
        # 프론트매터가 7줄이라, 원문을 훑으면 미진행 표와 미확인 표가 뒤바뀐다.
        result = self.flat["결과"]
        self.assertIn("다음 헤딩까지의 **`body`**", result)
        self.assertNotIn("다음 헤딩까지의 원문에", result)
        # `line` 은 구분선의 1-based 줄 번호다 (scripts/lab/md.py:26·214).
        # 한 라운드에서 이것을 "첫 데이터 행" 으로 잘못 바꿔 쓴 적이 있다.
        self.assertIn("표 구분선 줄 번호", result)
        self.assertNotIn("첫 데이터 행 줄 번호", result)

    def test_all_blank_table_without_a_marker_has_its_own_row(self):
        # 마커 없이 전부 공란인 표는 "표 전체 미진행" 규칙에 걸리지 않는다.
        # 모의 실행에서 정보량 0 인 표가 그대로 실렸다.
        self.assertIn("표 전체 공란 + 마커 없음", self.docs["결과"])

    def test_table_bullet_example_does_not_teach_internal_ids(self):
        # 이 문서는 예시를 따라 쓰기 쉬워서 예시가 규칙을 이긴다.
        # §절대 규칙 9 가 이름을 대어 금지한 표 ID 를 규칙 14 예시가 가르쳤다.
        self.assertNotIn("- **T1 결과**", self.docs["결과"])
        self.assertNotIn("![T1 row5", self.docs["결과"])

    def test_end_memo_transcription_handles_internal_ids(self):
        # 학생 메모에 표 ID 가 있으면 "지어내지 않는다"와 규칙 9 가 부딪힌다.
        self.assertIn("메모 원문의 표 ID·파일명은", self.flat["결과"])

    def test_missing_pre_report_notice_goes_to_the_user_not_the_body(self):
        # 규칙 8·9 와 절차 10 이 이미 본문 안내문을 금지한다.
        self.assertIn("본문이 아니라 §실행 절차 14 의 결과 안내에서", self.flat["결과"])

    def test_unfillable_section_is_removed_heading_and_all(self):
        # check_report_sections 는 절 이름만 대조한다 — 헤딩만 남은 빈 섹션은
        # error 로 잡히지 않고 그대로 제출된다.
        self.assertIn("헤딩까지 함께 뺀다", self.flat["결과"])

    def test_no_leaked_plan_task_numbers(self):
        # 구현 계획의 작업 번호는 문서를 읽는 사람이 닿을 수 없는 좌표다.
        for name, text in self.docs.items():
            with self.subTest(name):
                self.assertEqual(re.findall(r"Task \d+", text), [])

    def test_rule_5b_cites_a_result_report_sample(self):
        # 결과보고서 서식 규칙의 근거로 예비보고서 3편을 들고 있었다.
        result = self.flat["결과"]
        self.assertNotIn("160310", result)
        self.assertIn("160314", result)

    def test_the_review_skill_is_covered_by_the_net(self):
        # ⑤ 의 결함 3건(item_count 미전달·낡은 HTML 근거·죽은 §4)은 사람이
        # 실험01 을 재생성해서 찾았다. 그물이 봤다면 자동으로 걸렸을 종류다.
        self.assertIn("리뷰", DOCS)
        # 키만 보면 `DOCS["리뷰"] = (REVIEW, ())` 로 바꿔도 통과하면서 ⑤ 의
        # 상호참조 검사가 통째로 무음이 된다. 선언한 절이 있는지까지 본다.
        self.assertTrue(DOCS["리뷰"][1], DOCS["리뷰"])

    def test_the_spec_producer_is_covered_by_the_net(self):
        # ⑨ 는 저장소에서 명세를 **만드는** 유일한 스킬이다. 소비자 여덟이
        # 전부 그 산출물에 기대므로, 죽은 상호참조가 여기 생기면 그 아래가
        # 전부 흔들린다.
        self.assertIn("명세", DOCS)
        self.assertTrue(DOCS["명세"][1], DOCS["명세"])
        # 보고서를 만들지 않으므로 `check_report_sections` 를 부르지 않는다.
        # 이 분리 없이 `DOCS` 에 넣으면 아래 item_count 테스트가 깨진다.
        self.assertNotIn("명세", REPORT_SECTION_DOCS)

    def test_the_upload_step_passes_the_versioned_title(self):
        # 사용자는 노션 사이드바에서 PDF 를 내보내 제출한다. 제목이 전부 같으면
        # 옛 판본을 골라도 아무 데서도 오류가 나지 않는다 — 이 하네스에서
        # 조용히 틀린 것을 제출할 수 있는 유일한 경로였다. ⑦ 은 `DOCS` 에
        # 없으므로(단계가 `## push`·`## pull` 안에 산다) 여기서 따로 본다.
        calls = call_arguments(SYNC.read_text(encoding="utf-8"), "push_markdown")
        self.assertTrue(calls, "⑦ 에 push_markdown 호출부가 없다")
        self.assertTrue(any("title=page_title" in c for c in calls), calls)

    def test_the_pull_procedure_calls_the_empty_image_check(self):
        # `check_pulled_images` 를 부르는 곳은 저장소에 ⑦ 의 pull 절차 하나뿐이다.
        # 그 단계를 지우면 함수가 죽은 코드가 되는데 단위 테스트 7개는 그대로
        # 통과한다 — 이 브랜치의 성과가 조용히 되돌려지는 유일한 경로다.
        # push 에 걸면 매번 거짓 경보이므로(올린 직후엔 그림이 비어 있는 것이
        # 정상이다) pull 절 **안**에 있는지까지 본다.
        text = SYNC.read_text(encoding="utf-8")
        where = text.find("check_pulled_images(")
        self.assertNotEqual(where, -1, "⑦ 에 빈 그림 검사가 없다")
        pull = text.index("\n## pull")
        submit = text.index("\n## 제출")
        self.assertTrue(pull < where < submit,
                        f"빈 그림 검사가 pull 절 밖에 있다 (pull={pull}, 검사={where}, 제출={submit})")


if __name__ == "__main__":
    unittest.main()
