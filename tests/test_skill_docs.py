"""스킬 문서의 불변식.

`write-pre-report`·`write-result-report` 는 코드가 아니라 산문 규칙 문서라
컴파일도 실행도 되지 않는다. 그래서 같은 모순이 두 번 되살아났다 — 각주를
없앤 뒤에도 다른 규칙이 그 각주를 가리켰고, 삭제된 단계가 유일한 근거이던
규칙이 함께 사라졌다. 둘 다 격리 에이전트에게 스킬을 실행시켜서야 드러났다.

여기 있는 테스트는 그 실행을 대신하지 못한다. 문서가 좋은 보고서를 만드는지는
검사하지 않는다 — 검사하는 것은 이미 한 번 고친 결함이 되돌아오지 않는지뿐이다.
새 모순을 고칠 때마다 여기에 한 건씩 늘린다.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRE = ROOT / ".claude/skills/write-pre-report/SKILL.md"
RESULT = ROOT / ".claude/skills/write-result-report/SKILL.md"
BASELINE_V6 = ROOT / "실험01/output/실험01_예비보고서_notion_baseline_v6.md"


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


def cross_reference_errors(text):
    """`§절대 규칙 N`·`§실행 절차 N`·`N단계` 가 실재하는 항목을 가리키는지 본다."""
    sec = sections(text)
    rules = numbered_items(sec.get("절대 규칙", ""))
    steps = numbered_items(sec.get("실행 절차", ""))
    errors = []
    for token in re.findall(r"§절대 규칙 ([\d·~]+)", text):
        for n in sorted(_expand(token) - rules):
            errors.append(f"§절대 규칙 {n} 없음")
    for token in re.findall(r"§?실행 절차 ([\d·~]+)", text):
        for n in sorted(_expand(token) - steps):
            errors.append(f"실행 절차 {n} 없음")
    for token in re.findall(r"([\d·~]+)단계", text):
        for n in sorted(_expand(token) - steps):
            errors.append(f"{n}단계 없음")
    return errors


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
        self.docs = {"예보": PRE.read_text(encoding="utf-8"),
                     "결과": RESULT.read_text(encoding="utf-8")}

    def test_no_dangling_cross_references(self):
        for name, text in self.docs.items():
            with self.subTest(name):
                self.assertEqual(cross_reference_errors(text), [])

    def test_no_bare_section_number_references(self):
        # 상호참조 표기는 `§절대 규칙 N`·`§실행 절차 N`·`N단계` 뿐이다.
        # `§3` 은 어느 번호 체계인지 말하지 않아 규칙 3 으로도 절차 3 으로도
        # 읽힌다. (`§5.2`·`§3.2` 는 §절대 규칙 11 이 "쓰지 말라"고 인용하는
        # 형태이므로 제외한다 — 숫자 뒤에 점이 온다.)
        for name, text in self.docs.items():
            with self.subTest(name):
                self.assertEqual(re.findall(r"§\d+(?!\.\d)", text), [])

    def test_sibling_subsection_scope_is_defined(self):
        # 형제를 문서 전체로 읽으면 소절 제목이 표 제목을 겸하는 예외가
        # 무너져 표 레이아웃이 통째로 뒤집힌다. 두 스킬이 같은 기계를 쓴다.
        for name, text in self.docs.items():
            with self.subTest(name):
                self.assertIn("형제 소절(같은 대절 안의 소절)", text)

    def test_heading_levels_are_capped_at_two(self):
        # `###` 를 허용하면 여백 규칙이 정의되지 않은 자리가 생긴다.
        for name, text in self.docs.items():
            with self.subTest(name):
                self.assertIn("`###` 이하는 쓰지 않는다", text)

    def test_breadboard_template_path_and_home_are_pinned(self):
        # 경로가 §절대 규칙 8 의 예시에만 있고, 저장소에 사본이 둘이다.
        rows = [ln for ln in self.docs["예보"].splitlines()
                if ln.startswith("| 회로 결선도 |")]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn(".claude/assets/Breadboard.jpg", rows[0])
        self.assertIn("## 브레드보드 작도", rows[0])

    def test_subsection_count_is_derived_from_the_spec(self):
        # 규칙만으로 재생성하면 소절이 늘어난다 (8,345자 → 11,130자 실측).
        self.assertIn("소절 수는 명세에서 파생한다", self.docs["예보"])
        rules = numbered_items(sections(self.docs["예보"])["절대 규칙"])
        self.assertIn(17, rules)

    def test_worked_subsection_example_matches_the_approved_report(self):
        # 규칙 17 의 예시 숫자를 사용자가 승인한 정본에서 실제로 세어 대조한다.
        # 계획이 이 숫자를 한 번 틀렸다 — 결선 소절을 4개라고 썼는데 정본은
        # 6개다(공통 규칙 + 배선 3 + 실험 전 확인할 사항 + 브레드보드 작도).
        # 문자열 존재만 보면 같은 실수가 다시 지나간다.
        counts = subsection_counts(BASELINE_V6.read_text(encoding="utf-8"))
        self.assertEqual(counts["실험 과정 및 예상 결과"], 3)
        self.assertEqual(counts["회로 결선도"], 6)
        # 규칙의 예시 문장을 정본에서 센 숫자로 조립해 대조한다. 줄바꿈에
        # 기대지 않는다 — 문단을 다시 감싸도 규칙이 같으면 통과해야 한다.
        n_proc, n_wire = counts["실험 과정 및 예상 결과"], counts["회로 결선도"]
        self.assertIn(f"`items` {n_proc}개면 과정 {n_proc}소절, 결선 {n_wire}소절이다.",
                      re.sub(r"\s+", " ", self.docs["예보"]))


if __name__ == "__main__":
    unittest.main()
