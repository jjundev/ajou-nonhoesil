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
from scripts.lab.spec_parser import parse_spec

ROOT = Path(__file__).resolve().parents[1]
PRE = ROOT / ".claude/skills/write-pre-report/SKILL.md"
RESULT = ROOT / ".claude/skills/write-result-report/SKILL.md"
REVIEW = ROOT / ".claude/skills/review-lab-report/SKILL.md"
DRAFT = ROOT / ".claude/skills/draft-lab-spec/SKILL.md"
SYNC = ROOT / ".claude/skills/sync-report-to-notion/SKILL.md"
VERIFY = ROOT / ".claude/skills/verify-draft-lab-spec/SKILL.md"
VERIFY_RESULT = ROOT / ".claude/skills/verify-write-result-report/SKILL.md"
HAND = ROOT / ".claude/skills/review-hand-diagram/SKILL.md"
INIT = ROOT / ".claude/skills/init-lab-experiment/SKILL.md"
FIGURE = ROOT / ".claude/skills/draw-expected-figure/SKILL.md"
FIGURE_TEMPLATE = ROOT / ".claude/skills/draw-expected-figure/template.html"
FIGURE_PY = ROOT / "scripts/lab/figure.py"
FIGURE_EXPORT_PY = ROOT / "scripts/lab/figure_export.py"
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
    "검증": (VERIFY, ("절대 규칙", "실행 절차")),
    "결보검증": (VERIFY_RESULT, ("절대 규칙", "실행 절차")),
    "그림": (FIGURE, ("절대 규칙", "실행 절차")),
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

# 다른 문서를 가리키는 상호참조. `③ §절대 규칙 9` 처럼 스킬 번호가 앞에 붙는다.
# 이 참조는 **자기 문서에서 풀면 안 된다** — ⑤ 에는 `## 절대 규칙` 이 없어서
# `§절대 절 없음` 으로 잡혔고, ④ 의 `③ §절대 규칙 5` 는 하필 ④ 자신의 규칙 5 가
# 있어서 엉뚱한 문서를 보고 조용히 통과했다. 앞의 번호가 가리키는 문서에서 푼다.
CROSS_DOC = re.compile(r"([①-⑦])\s*§(절대 규칙|실행 절차)\s*([\d·~]+)")
MARKERS = {"③": "예보", "④": "결과", "⑤": "리뷰"}

# 핀아웃 근거가 실제로 사는 곳. 경로를 문서에만 두면 폴더가 옮겨졌을 때
# 문서가 조용히 거짓말을 한다 — `Breadboard.jpg` 가 정확히 그렇게 깨졌다.
DATASHEET_DIR = "from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃"

# ③·④ 가 함께 따르는 서식 규칙의 본문. 두 스킬 문서의 해당 번호에는 굵은 첫
# 문장과 포인터만 남는다 — 같은 규칙을 두 벌 두었더니 한쪽만 고쳐져 벌어졌다
# (2026-09-29 측정: 열 쌍 중 넷이 유사도 0.55~0.79).
SHARED = ROOT / ".claude/보고서서식.md"
# 공용 절 이름 → (③ 번호, ④ 번호). 번호는 바꾸지 않는다 — 저장소 전체 인용이 442곳이다.
SHARED_RULES = {
    "강의노트 호칭": (6, 7),
    "AI 티": (7, 8),
    "다른 파일 언급": (8, 9),
    "목차 블록": (10, 11),
    "헤딩": (11, 12),
    "여백 블록": (12, 13),
    "표 캡션": (13, 14),
    "관찰 문장": (14, 15),
    "표 예고": (15, 16),
    "붙여쓰기": (21, 18),
}
SHARED_POINTER = "`.claude/보고서서식.md` §"


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


def _flat(text):
    """줄바꿈·들여쓰기를 공백 하나로 누른다. 문단을 다시 접어도 문장 검사가 같다."""
    return re.sub(r"\s+", " ", text)


def rule_blocks(section_body):
    """번호 항목마다 본문을 돌려준다(`5b.` 는 5 에 붙는다). 다음 번호 줄 앞까지다."""
    out, cur = {}, None
    for line in section_body.splitlines():
        m = re.match(r"^(\d+)[a-z]?\. ", line)
        if m:
            cur = int(m.group(1))
            out.setdefault(cur, [])
        if cur is not None:
            out[cur].append(line)
    return {n: "\n".join(v) for n, v in out.items()}


def shared_pointer_targets(text):
    """`SHARED_POINTER` 바로 뒤의 글 40자씩을 돌려준다.

    절 이름에 공백이 있어(`여백 블록`) 정규식으로 이름을 자르지 않는다 — 받은 쪽이
    알려진 이름으로 시작하는지 본다.
    """
    flat = _flat(text)
    out, i = [], flat.find(SHARED_POINTER)
    while i != -1:
        j = i + len(SHARED_POINTER)
        out.append(flat[j:j + 40])
        i = flat.find(SHARED_POINTER, j)
    return out


def cross_reference_errors(text, titles=("절대 규칙", "실행 절차")):
    """`§절대 규칙 N`·`§실행 절차 N`·`N단계` 가 실재하는 항목을 가리키는지 본다.

    `titles` 는 그 문서에서 번호 매긴 항목이 사는 절 이름이다. 문서마다 다르므로
    함수 안에 박지 않는다 — ⑤ 에는 `## 절대 규칙` 이 없어서, 박아 두면 거기
    `§절대 규칙 N` 참조가 생기는 순간 전부 "없음"으로 잡힌다.
    """
    # 다른 문서를 가리키는 참조는 여기서 풀지 않는다 (위 `CROSS_DOC` 참조).
    # `test_cross_document_references_resolve_in_the_target_doc` 가 본다.
    text = CROSS_DOC.sub(" ", text)
    # 공용 서식 파일의 절(`.claude/보고서서식.md` §여백 블록)도 이 문서의 절이
    # 아니다. `SharedReportStyle` 이 공용 파일 쪽에서 푼다.
    text = re.sub(r"`\.claude/보고서서식\.md`\s+§", " ", text)
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

    def test_shared_style_pointers_are_left_to_the_shared_file(self):
        # `.claude/보고서서식.md` §여백 블록 은 이 문서의 절이 아니다 — 풀이는
        # `SharedReportStyle` 이 한다. 포인터 없이 쓴 `§여백` 은 여전히 죽은 참조다.
        doc = ("## 절대 규칙\n\n1. **하나.** 본문은 `.claude/보고서서식.md`\n"
               "   §여백 블록. 그리고 §여백 을 본다\n"
               "\n## 실행 절차\n\n0. **영.** 본문\n")
        self.assertEqual(cross_reference_errors(doc), ["§여백 절 없음"])


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

    def test_cross_document_references_resolve_in_the_target_doc(self):
        """`③ §절대 규칙 9` 가 ③ 에 실재하는가.

        자기 문서에서 푸는 검사로는 이것을 볼 수 없다 — ⑤ 는 `## 절대 규칙`
        이 없어 죽은 참조로 잡히고(거짓 경보), ④ 는 자기 규칙 번호와 우연히
        겹쳐 통과한다(무음). 둘 다 실제로 있었던 상태다.
        """
        checked = 0
        for name, text in self.docs.items():
            for marker, title, token in CROSS_DOC.findall(text):
                target = MARKERS.get(marker)
                if target is None:
                    continue      # DOCS 밖의 스킬은 대조할 원본이 없다
                checked += 1
                with self.subTest(f"{name} → {target} §{title} {token}"):
                    items = numbered_items(sections(self.docs[target])[title])
                    self.assertEqual(
                        sorted(_expand(token) - items), [],
                        f"{name} 이 가리키는 {target} §{title} 항목이 없다")
        # 커밋된 문서에 실재하는 최소 개수다(④ 가 ③ 을 두 번 가리킨다).
        # 살아 있는 트리에는 더 있지만, 여기 박는 숫자는 커밋된 것만 센다.
        self.assertGreaterEqual(checked, 2, "상호참조를 하나도 못 찾으면 이 테스트는 공허하다")

    def test_code_and_schema_cross_references_resolve(self):
        """`scripts/lab/*.py` 와 `docs/schema/*.md` 안의 `③ §절대 규칙 9` 도 푼다.

        위 테스트는 스킬 문서끼리의 상호참조만 본다. 코드 docstring·메시지와 스키마
        문서의 `④ §절대 규칙 8` 같은 인용은 가리키는 규칙이 지워지거나 번호가 밀려도
        아무도 몰랐다. 도입 때(2026-09-14) 10건을 풀어 오탐 0건이었다.

        **이 그물 밖에 남는 것:** 원문자가 없는 인용(`§절대 규칙 4`)과 원문자와 § 사이에
        스킬 이름이 끼인 인용(``③ `write-pre-report` §절대 규칙 22``)은 `CROSS_DOC` 이
        잡지 않는다. draft-lab-spec 규칙은 원문자가 없어 스킬 이름으로 인용한다.
        """
        files = (sorted((ROOT / "scripts/lab").glob("*.py"))
                 + sorted((ROOT / "docs/schema").glob("*.md"))
                 + [SHARED])
        checked = 0
        for path in files:
            for marker, title, token in CROSS_DOC.findall(path.read_text(encoding="utf-8")):
                target = MARKERS.get(marker)
                if target is None:
                    continue
                checked += 1
                with self.subTest(f"{path.name} → {target} §{title} {token}"):
                    items = numbered_items(sections(self.docs[target])[title])
                    self.assertEqual(sorted(_expand(token) - items), [],
                                     f"{path.name} 이 가리키는 {target} §{title} 항목이 없다")
        self.assertGreater(checked, 0, "교차참조를 하나도 못 찾으면 이 테스트는 공허하다")

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
        # 무너져 표 레이아웃이 통째로 뒤집힌다. 두 스킬이 같은 기계를 쓰고,
        # 그 기계는 공용 서식 파일 한 곳에 산다(§표 캡션).
        self.assertIn("형제 소절(같은 대절 안의 소절)",
                      _flat(SHARED.read_text(encoding="utf-8")))

    def test_heading_levels_are_capped_at_two(self):
        # `###` 를 허용하면 여백 규칙이 정의되지 않은 자리가 생긴다.
        # 공용 서식 파일 §헤딩 에 산다.
        self.assertIn("`###` 이하는 쓰지 않는다",
                      _flat(SHARED.read_text(encoding="utf-8")))

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

    def test_the_fresh_review_loops_back_to_validation(self):
        # 9단계에서 수용한 지적을 고치면 5·7단계 검증이 보는 자리(셀·토큰
        # 규약 표·미확정 표)가 바뀐다. 그런데 그 두 단계의 "error 0 까지
        # 반복" 은 이미 지나갔다 — 다시 돌리라고 적어 두지 않으면 방금
        # 만든 error 를 못 본 채 10단계 보고로 직행한다.
        self.assertIn("고쳤으면 5·7단계 검증을 다시 돌린다", self.flat["명세"])

    def test_breadboard_template_path_and_home_are_pinned(self):
        # 경로가 §절대 규칙 8 의 예시에만 있고, 저장소에 사본이 둘이다.
        # 템플릿은 이제 기본이 아니라 폴백이다 — `diagram` 이 없는 주차에서만
        # 쓴다. 그래도 경로는 여기 못박아 둔다: 사본을 집으면 조용히 다른
        # 판본이 실린다.
        rows = [ln for ln in self.docs["예보"].splitlines()
                if ln.startswith("| 회로 결선도 |")]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn(".claude/assets/Breadboard.jpg", rows[0])
        # 그림의 근원이 netlist 의 `diagram` 이라는 것과, 그림이 회로 소절
        # 안에 산다는 것 둘 다 재료 표에 있어야 한다. 앞의 것이 없으면
        # 파일명을 짐작해 쓰고, 뒤의 것이 없으면 다시 절 끝에 몰아 둔다.
        self.assertIn("diagram", rows[0])
        self.assertIn("회로 소절마다 제목 바로 아래", rows[0])

    def test_the_diagram_lives_inside_its_circuit_subsection(self):
        # 그림이 절 맨 뒤 `## 브레드보드 작도` 소절에 한 장 몰려 있었다.
        # 결선도 PNG 는 이미 회로마다 있는데 예보 본문에는 한 장도 안 실려
        # 있었고, 학생은 표를 보면서 그림을 대조할 수 없었다.
        rules = numbered_items(sections(self.docs["예보"])["절대 규칙"])
        self.assertIn(20, rules)
        flat = self.flat["예보"]
        self.assertIn("결선도 그림은 그 회로의 소절 안에, 표 바로 위에 둔다", flat)
        # 폴백이 규칙에 없으면 결선도 PNG 가 없는 주차(실험01 말고 전부)에서
        # 예보가 멈추거나 깨진 링크를 낸다.
        self.assertIn("빈 브레드보드 캔버스로 폴백한다", flat)
        # 정본도 실제로 그 차례여야 한다 — 규칙만 고치고 정본이 옛 모양이면
        # 다음 재생성이 정본을 본보기로 삼아 되돌아간다.
        # 보고서는 대절이 `# `, 소절이 `## ` 다 — `sections()` 는 스킬 문서용
        # 이라 여기 쓰면 대절을 못 찾는다.
        canon = CANON.read_text(encoding="utf-8")
        body = re.split(r"^# 회로 결선도\n", canon, flags=re.M)[1]
        body = re.split(r"^# ", body, flags=re.M)[0]
        image = re.compile(r"^!\[[^\]]*\]\((\S+)\)\s*$")
        for chunk in body.split("\n## ")[1:]:
            head, *lines = chunk.splitlines()
            if head.startswith(("공통 결선 규칙", "실험 전 확인할 사항")):
                continue
            hits = [i for i, ln in enumerate(lines) if image.match(ln)]
            self.assertEqual(len(hits), 1, f"{head}: 그림이 {len(hits)}장이다")
            table = next((i for i, ln in enumerate(lines)
                          if ln.lstrip().startswith("|")), len(lines))
            self.assertLess(hits[0], table, f"{head}: 그림이 표 아래에 있다")
            target = image.match(lines[hits[0]]).group(1)
            self.assertTrue((CANON.parent / target).exists(),
                            f"{head}: {target} 이 없다")

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
        # 5개다(공통 규칙 + 배선 3 + 실험 전 확인할 사항).
        # 문자열 존재만 보면 같은 실수가 다시 지나간다.
        # 숫자를 손으로 박지 않는다. 2026-2 배포본이 실험1 을 항목 셋에서
        # 다섯으로 늘렸을 때 정본과 규칙 17 은 5·8 로 따라갔는데 이 테스트만
        # 3·6 에 남아 깨졌다 — 규칙 17 이 말하는 그 파생을 여기서도 한다.
        spec = parse_spec(ROOT / config.experiment_dir(1) / "체크리스트/명세.md")
        n_proc = len(spec.items)
        # 고정 소절 둘: 공통 결선 규칙 + 실험 전 확인할 사항. 브레드보드
        # 작도는 소절이 아니라 회로 소절 안의 그림이 됐다(§절대 규칙 20).
        n_wire = n_proc + 2
        counts = subsection_counts(CANON.read_text(encoding="utf-8"))
        self.assertEqual(counts["실험 과정 및 예상 결과"], n_proc)
        self.assertEqual(counts["회로 결선도"], n_wire)
        # 규칙의 예시 문장을 정본에서 센 숫자로 조립해 대조한다. 줄바꿈에
        # 기대지 않는다 — 문단을 다시 감싸도 규칙이 같으면 통과해야 한다.
        self.assertIn(f"`items` {n_proc}개면 과정 {n_proc}소절, 결선 {n_wire}소절이다",
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

    def test_body_style_check_is_called_by_writer_and_reviewer(self):
        # warn 검사라도 ④ 가 안 부르면 md 를 낸 세션 안에서 못 고치고, ⑤ 가
        # 안 부르면 같은 보고서를 두 기준으로 잰다.
        for name in ("결과", "리뷰"):
            with self.subTest(name):
                self.assertIn("check_body_style(", self.docs[name])
                # ⑤ 가 ④ 보다 좁게 재면 안 된다 — 2026-09-12 격리 1회차에서 ⑤ 에
                # `check_notion_markdown` 이 빠져 있던 것을 에이전트가 지적했다.
                self.assertIn("check_notion_markdown(", self.docs[name])

    def test_photo_diagram_check_is_called_by_writer_and_reviewer(self):
        # 2026-09-18 실험01 결보 조교 피드백으로 실험 사진 절에 예보 결선도를
        # 싣게 됐다. ④ 가 안 부르면 쓴 세션 안에서 못 고치고, ⑤ 가 안 부르면
        # 같은 보고서를 두 기준으로 잰다.
        for name in ("결과", "리뷰"):
            with self.subTest(name):
                self.assertIn("check_result_photo_diagrams(", self.docs[name])

    def test_section_material_table_example_matches_the_diagram_first_rule(self):
        # §사진 배치가 "결선도를 먼저" 싣는다고 바꾼 뒤에도 §섹션별 재료 표의
        # 승인본 실험01 예시 문장이 옛 순서("사진을 한 장에 모았다"로 시작)를
        # 그대로 인용해 규칙과 모순됐다. 표 행 자체가 새 규칙을 따라야 한다.
        for line in self.docs["결과"].splitlines():
            if "| 실험 사진 |" in line:
                self.assertIn("결선도를 먼저", line)
                break
        else:
            self.fail("`| 실험 사진 |` 행을 찾지 못했다")

    def test_table_header_check_is_called_by_writer_and_reviewer(self):
        # 2026-09 실험01 예보가 명세 T1~T4 의 `A B C L1 L2` 를 `A B C Y` 로 내고
        # ⑤ 를 통과해 조교 감점을 받았다. ③ 이 안 부르면 쓴 세션 안에서 못 고치고,
        # ⑤ 가 안 부르면 행 수만 보고 다시 통과시킨다.
        for name in ("예보", "리뷰"):
            with self.subTest(name):
                self.assertIn("check_report_tables(", self.docs[name])

    def test_rule_22_example_uses_the_spec_column_names(self):
        # 이 문서는 예시를 따라 쓰기 쉬워서 예시가 규칙을 이긴다. 옛 규칙 13 의
        # 인용 `Y = A·B·C` 가 실험01 예보의 `Y` 열 이름을 굳혔다.
        self.assertIn("(`L1 = A·B`, `L2 = A·B·C`)", self.docs["예보"])
        self.assertNotIn("Y = A·B·C", self.docs["예보"])

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

    def test_photo_naming_is_the_contact_sheet_rule(self):
        # 2026-09-19: 옛 관례 `T<n> row<m>.jpg` 가 세 문서에 남아 시트 엔진
        # 규칙(`<항목> <입력비트>.jpg`)과 어긋났다.
        paths = {
            "결과": RESULT,
            "체크": ROOT / ".claude/skills/prep-lab-checklist/SKILL.md",
            "시트": ROOT / ".claude/skills/export-photo-sheet/SKILL.md",
            # 결과보고서 템플릿의 사진 CSS 주석도 옛 예시를 들고 있었다.
            "결과 템플릿": ROOT / ".claude/skills/write-result-report/template.html",
        }
        for name, path in paths.items():
            text = path.read_text(encoding="utf-8")
            with self.subTest(name):
                self.assertNotIn("row<m>", text)
                self.assertNotIn("T1 row", text)
        self.assertIn("<항목> <입력비트>.jpg", self.docs["결과"])
        self.assertIn("<항목> <표ID> <설명>.jpg", self.docs["결과"])

    def test_photo_only_flow_is_an_official_path(self):
        # 실험03 은 확인 칸을 손으로 채우지 않고 행 사진만 찍었다.
        result = self.flat["결과"]
        self.assertIn("필기 PDF 가 없고 행 사진만 있으면 사진에서 전사한다", result)
        self.assertIn("입력 조합은 **파일명에서만** 읽는다", result)
        self.assertIn("채워진 칸이 0개이고 행 사진도 스텝표·파형 사진도 없으면", result)
        self.assertIn("행 사진(`<항목> <입력비트>.jpg`)도 없으면", result)
        self.assertIn("사진이 찍힌 행에 아직 빈 확인 칸이 있으면 아래 사진 전사로 간다",
                      result)
        self.assertNotIn("행 사진이 있으면 아래 사진 전사로 간다", result)

    def test_photo_transcription_never_overwrites_hand_filled_cells(self):
        # 최종 리뷰: 사진이 있다는 이유만으로 손으로 채운 칸을 사진 판독으로
        # 덮어쓸 수 있었다. 2단계 제목도 "비어 있으면 멈춘다" 라 사진만 있는
        # 경우와 어긋났다.
        result = self.flat["결과"]
        self.assertIn("기록.md 상태 판정 — 확인 칸도 실험 사진(행 사진·스텝표·파형 사진)도 "
                      "없으면 여기서 멈춘다.",
                      result)
        self.assertNotIn("기록.md 상태 판정 — 비어 있으면 여기서 멈춘다.", result)
        self.assertIn("사진 전사는 빈 칸만 대상이다. 이미 채워진 칸은 덮어쓰지 않고, "
                      "사진 판독이 다르면 두 값을 나란히 제시해 사용자가 정한다.", result)
        self.assertIn("사진이 한 장도 없는 표는 진행 여부를 사용자에게 묻고, 진행하지 "
                      "않았으면 그 표 아래에 `- 실험을 진행하지 않았음.` 을 적는다.",
                      result)

    def test_misnamed_photos_are_not_reported_as_no_experiment(self):
        # 실험02 는 `실험02 1-1 …` 처럼 접두어를 붙여 찍었다. 규칙 밖 이름을
        # "실험을 안 했다" 로 보고하면 사용자를 헛걸음시킨다.
        result = self.flat["결과"]
        self.assertIn("규칙 밖 이름의 이미지 파일이 있으면", result)
        self.assertIn("이름을 바꿀지 묻는다", result)

    def test_side_photos_only_week_is_not_reported_as_no_experiment(self):
        # 실험02 는 진리표 없이 capture 표뿐이라 확인 칸도 행 사진도 없다.
        # 스텝표·파형 사진만 있어도 "실험을 안 했다" 로 멈추면 안 된다.
        result = self.flat["결과"]
        self.assertIn("채워진 칸이 0개이고 행 사진은 없는데 스텝표·파형 사진이 있으면",
                      result)
        self.assertIn("print('스텝표·파형 사진:'", result)
        self.assertIn("추측으로 채우지 않는다", result)
        self.assertIn("확인 칸도 실험 사진(행 사진·스텝표·파형 사진)도 없으면", result)

    def test_free_memo_file_goes_through_the_record_first(self):
        # 실험03 은 `실험중있었던일.md` 에 자유 형식으로 적었다.
        result = self.flat["결과"]
        self.assertIn("자유 메모 파일이 있으면 그것이 재료다", result)
        self.assertIn("**`기록.md` 종료 메모를 먼저 채우고**", result)
        self.assertIn("4문항이 전부 공란이고 자유 메모 파일도 없으면", result)

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

    def test_particle_spacing_rule_lives_in_both_report_skills(self):
        # 2026-09-12 실험01 결보 v5 되읽기: 사용자가 본문 전체에서 `L1 이`→`L1이`,
        # `330 Ω`→`330Ω` 로 고쳤다. 표기 규약이라 ③④ 둘 다 규칙으로 갖는다.
        for name in REPORT_DOCS:
            with self.subTest(name):
                self.assertIn("조사와 숫자 뒤 단위는 붙여 쓴다", self.flat[name])

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

    def test_the_verifier_answer_keys_agree_in_all_three_places(self):
        # 답안지 목록의 정본은 §답안지 목록(산문)인데, §실행 절차 1단계의
        # `KEYS = [...]` 가 이를 그대로 옮겨야 한다(§실행 절차 1단계 지시
        # 문구). 코드(scripts/lab/isolate.py)는 받은 목록을 지우기만 하므로
        # 여기서는 KEYS 와 산문 불릿 두 곳을 직접 대조한다.
        text = self.docs["검증"]
        proc = sections(text)["실행 절차"]
        start = proc.index("KEYS = [") + len("KEYS = [")
        end = proc.index("]", start)
        keys = {m.rstrip("/") for m in re.findall(r"'([^']+)'", proc[start:end])}

        sec = sections(text)["답안지 목록"]
        before, marker, after = sec.partition("남기는 것:")
        self.assertNotEqual(marker, "", "\"남기는 것:\" 문장이 없다 — 앵커가 바뀌었다")
        # 불릿 단위로 나눈다 — "스킬 여덟" 불릿은 `draft-lab-spec` 과
        # `write-pre-report` 둘 다 예시 인용이지 답안지 경로가 아니다.
        # 불릿 전체를 통짜로 빼야 그 안의 backtick 이 전부 빠진다.
        bullets = [b for b in re.split(r"(?m)^- ", before)[1:]]
        prose = set()
        excluded = set()
        for b in bullets:
            toks = {m.rstrip("/") for m in re.findall(r"`([^`]+)`", b)}
            if "<실험NN>" in b or "스킬 여덟" in b:
                excluded |= toks
            else:
                prose |= toks
        prose_all = prose | excluded

        # `draft-lab-spec` 을 뺀 스킬 여덟은 §답안지 목록이 "스킬 여덟" 이라는
        # 구절로만 가리키고 이름을 나열하지 않는다 — KEYS 쪽 개수·이름으로
        # 따로 잰다.
        other_skills = {k for k in keys if k.startswith(".claude/skills/")
                        and "/verify-" not in k} - {".claude/skills/breadboard-diagram"}
        self.assertEqual(len(other_skills), 8, other_skills)
        self.assertNotIn(".claude/skills/draft-lab-spec", other_skills)

        # 보고서 불릿(`<실험NN>` 자리표시자)과 "스킬 여덟" 불릿의 backtick 은
        # KEYS 에 문자 그대로는 없다 — 위 두 이유로 뺀다. 나머지는 KEYS 에
        # 전부 있어야 한다.
        self.assertEqual(prose - keys, set(), prose - keys)

        # 반대 방향: 스킬 여덟을 뺀 KEYS 는 전부 산문 불릿에 실려 있어야 한다.
        self.assertEqual((keys - other_skills) - prose_all, set(),
                         (keys - other_skills) - prose_all)

        # "남기는 것:" 은 답안지가 아니다 — KEYS 항목이 거기 섞여 있으면
        # 지우면 안 되는 자리를 지우거나 그 반대다.
        for k in keys:
            with self.subTest(k):
                self.assertNotIn(k, after)

    def test_the_verifier_lists_itself_as_an_answer_key(self):
        # 스킬 문서 자체가 합격 조건을 담는다. 격리 트리에서 빼지 않으면
        # 에이전트가 저장소를 뒤지다 자기 채점표를 읽는다 — 2026-08-31 에
        # docs/verify/ 로 실제로 일어난 일이다.
        text = self.docs["검증"]
        sec = sections(text)["답안지 목록"]
        self.assertIn("`.claude/skills/verify-draft-lab-spec/`", sec)
        self.assertIn("`docs/verify/`", sec)
        self.assertIn("`tests/`", sec)
        self.assertIn("`scripts/lab/regen_compare.py`", sec)
        self.assertIn("`scripts/lab/isolate.py`", sec)
        self.assertIn("`docs/corpus-audit/`", sec)

    def test_the_verifier_prompt_gives_no_reasons_and_forbids_git_history(self):
        # 금지 사유는 첫 줄부터 "채점되는 시험" 임을 알려준다(런북 2026-09-01
        # 누출 (3)). 이력은 답안지 이름을 흘린다.
        sec = sections(self.docs["검증"])["에이전트 프롬프트"]
        self.assertNotIn("합격", sec)
        self.assertNotIn("채점", sec)
        self.assertIn("`git log`", sec)
        self.assertIn("한 번에 통과했으면 그렇다고 명시", sec)

    def test_the_verifier_does_not_fix_anything(self):
        sec = sections(self.docs["검증"])["비-목표"]
        self.assertIn("`draft-lab-spec` 을 고치지 않는다", sec)
        self.assertIn("커밋하지 않는다", sec)

    def test_the_result_verifier_answer_keys_agree_with_its_prose(self):
        # `verify-write-result-report` 판. "스킬 여덟" 예외는 없고, `{exp}` 로
        # 실험 폴더를 끼우는 f-string 키는 `<실험NN>` 불릿이 맡는다.
        text = self.docs["결보검증"]
        proc = sections(text)["실행 절차"]
        start = proc.index("KEYS = [") + len("KEYS = [")
        end = proc.index("]", start)
        keys = {m.rstrip("/") for m in re.findall(r"'([^']+)'", proc[start:end])}
        literal_keys = {k for k in keys if "{exp}" not in k}

        sec = sections(text)["답안지 목록"]
        before, marker, after = sec.partition("남기는 것:")
        self.assertNotEqual(marker, "")
        prose, placeholder = set(), set()
        for b in re.split(r"(?m)^- ", before)[1:]:
            toks = {m.rstrip("/") for m in re.findall(r"`([^`]+)`", b)}
            (placeholder if "<실험NN>" in b else prose).update(toks)
        self.assertEqual(prose - literal_keys, set(), prose - literal_keys)
        self.assertEqual(literal_keys - prose, set(), literal_keys - prose)
        for k in literal_keys:
            with self.subTest(k):
                self.assertNotIn(k, after)

    def test_the_result_verifier_lists_itself_and_its_tools_as_answer_keys(self):
        sec = sections(self.docs["결보검증"])["답안지 목록"]
        for key in ("`.claude/skills/verify-write-result-report/`", "`docs/verify/`",
                    "`docs/plans/`", "`docs/notion-feedback/`", "`tests/`",
                    "`scripts/lab/report_compare.py`", "`scripts/lab/isolate.py`"):
            with self.subTest(key):
                self.assertIn(key, sec)

    def test_the_result_verifier_prompt_and_non_goals_match_the_sibling(self):
        sec = sections(self.docs["결보검증"])["에이전트 프롬프트"]
        self.assertNotIn("합격", sec)
        self.assertNotIn("채점", sec)
        self.assertIn("`git log`", sec)
        self.assertIn("한 번에 통과했으면 그렇다고 명시", sec)
        self.assertIn("`review-lab-report`", sec)
        non = sections(self.docs["결보검증"])["비-목표"]
        self.assertIn("`write-result-report` 를 고치지 않는다", non)
        self.assertIn("커밋하지 않는다", non)

    def test_both_verifiers_keep_each_other_out_of_the_tree(self):
        # 두 검증 스킬은 서로의 프롬프트·답안지 목록을 싣는다 — 한쪽 격리 트리에
        # 다른 쪽이 남으면 에이전트가 거기서 시험 형식을 읽는다.
        self.assertIn("'.claude/skills/verify-write-result-report'", self.docs["검증"])
        self.assertIn("'.claude/skills/verify-draft-lab-spec'", self.docs["결보검증"])


class FigureSkill(unittest.TestCase):
    """`draw-expected-figure` 전용 불변식. 상호참조·번호 연속은 `DOCS` 편입으로 본다."""

    def setUp(self):
        self.text = FIGURE.read_text(encoding="utf-8")
        self.proc = sections(self.text)["실행 절차"]

    def test_판정은_capture_tables_로만_한다(self):
        self.assertIn("figure.capture_tables(", self.proc)
        self.assertIn("figure.gate_message(", self.proc)

    def test_숫자_검사가_추출보다_먼저다(self):
        check = self.proc.index("figure_export <실험번호> --check-only")
        export = self.proc.index("figure_export <실험번호>\n")
        self.assertLess(check, export)

    def test_올린_보고서는_고치지_않는다(self):
        self.assertIn("figure.is_uploaded(", self.proc)
        self.assertIn("figure.insert_placeholder(", self.proc)
        self.assertIn("figure.set_spec_figure(", self.proc)

    def test_통제군_값을_예시로_쓰지_않는다(self):
        # 실험02 가 격리 검증의 통제군이다. 문서·템플릿·모듈에 그 값이 있으면
        # 재생성이 규칙이 아니라 예시를 따라 합격한다. `figure`·`figure_export`
        # 의 docstring 도 같은 그물에 든다 — 실제로 `figure_export` 의 숫자
        # 검사 설명 docstring이 `1.4` 를 예시로 써서 누출됐었다.
        texts = {
            "SKILL.md": self.text,
            "template.html": FIGURE_TEMPLATE.read_text(encoding="utf-8"),
            "figure.py": FIGURE_PY.read_text(encoding="utf-8"),
            "figure_export.py": FIGURE_EXPORT_PY.read_text(encoding="utf-8"),
        }
        tokens = ("74HC04", "74HC14", "2.38", "1.35", "3.15", "0.98", "인버터", "슈미트",
                  "2.1", "2.4", "1.4", "0.9", "1.7", "2.0")
        for token in tokens:
            # 소수 토큰은 부분 문자열로 보면 `0.74em`·`12.5px`·`1.65` 같은
            # 무관한 값 안에서 오탐이 난다 — 숫자 경계로 자른다. 칩 이름·용어
            # 토큰은 부분 문자열로 그대로 본다.
            pattern = (re.compile(r"(?<![\d.])" + re.escape(token) + r"(?!\d)")
                       if token[0].isdigit() else None)
            for name, text in texts.items():
                with self.subTest(token=token, file=name):
                    if pattern is not None:
                        self.assertIsNone(pattern.search(text), f"{name} 에 {token} 이 있다")
                    else:
                        self.assertNotIn(token, text)

    def test_승인본_모양을_묘사하지_않는다(self):
        # 값만 막으면 부족하다. 옛 규칙 5 의 "파형과 특성 곡선을 짝지어" 는 통제군
        # 승인본의 패널 구성을 그대로 적은 예시라, 재생성이 짝으로 그려도 규칙이
        # 막았는지 예시를 베꼈는지 가를 수 없었다. 규칙은 일반형으로만 쓴다.
        texts = {
            "SKILL.md": self.text,
            "template.html": FIGURE_TEMPLATE.read_text(encoding="utf-8"),
        }
        for token in ("X-Y", "시간축", "고리", "에지", "짝", "히스테리시스", "S자", "Typ"):
            for name, text in texts.items():
                with self.subTest(token=token, file=name):
                    self.assertNotIn(token, text)

    def _rule(self, n):
        body = sections(self.text)["절대 규칙"]
        m = re.search(rf"^{n}\. (.*?)(?=^\d+\. |\Z)", body, re.M | re.S)
        self.assertIsNotNone(m, f"절대 규칙 {n} 이 없다")
        return m.group(1)

    def test_패널_구성은_이론_쪽과_비교_묶음까지_본다(self):
        # 1회차: 이론 쪽 그림을 한 항목에만 적용하고, 비교하라고 묶인 다른 항목은
        # 다른 구성으로 그렸다. "그 항목의 그림" 이 어디까지인지 문서가 말해야 한다.
        # 2회차: 한 쪽에 나란히 놓인 그림 중 명세 축과 맞는 하나만 골랐다.
        rule = self._rule(5)
        for token in ("items[].pages", "이론 쪽", "비교", "나란히", "하나만 골라"):
            with self.subTest(token):
                self.assertIn(token, rule)

    def test_모양과_위치를_근거에_묶는다(self):
        # 1회차: 전이 위치를 "범위 중앙 부근에 임의로" 두고 라벨을 달지 않았고,
        # 본문이 말한 모양을 다른 곡선으로 바꿨다. 규칙 3·4 는 둘 다 막지 않았다.
        # 2회차: 위치를 사이에 두는 경계의 대표값을 위치로 보지 않고, 본문의
        # "정확한 값은 없다" 를 근거로 모식으로 뒀다. 사용자는 대표값이 맞다고 했다.
        rule = self._rule(11)
        for token in ("대표값", "모식", "§절대 규칙 3", "§실행 절차 3", "경계", "§절대 규칙 4"):
            with self.subTest(token):
                self.assertIn(token, rule)
        step3 = re.search(r"^3\. (.*?)(?=^4\. )", self.proc, re.M | re.S).group(1)
        self.assertIn("모양·위치", step3)
        self.assertIn("모식", step3)

    def test_근거_표에_모양_위치_칸이_있다(self):
        template = FIGURE_TEMPLATE.read_text(encoding="utf-8")
        head = re.search(r"<table class=\"evidence\">.*?<thead>(.*?)</thead>", template, re.S).group(1)
        self.assertEqual(re.findall(r"<th>(.*?)</th>", head), ["그림", "요소", "근거", "모양·위치"])

    def test_실험NN_치환이_주석을_건드리지_않는다(self):
        # 3회차: 4단계 "`실험NN` 을 바꾼다" 를 글자대로 하면 맨 위 주석 문장까지
        # 바뀌어 말이 안 됐다. 자리표시는 제목 세 곳에만 두고 절차가 그 셋을 부른다.
        template = FIGURE_TEMPLATE.read_text(encoding="utf-8")
        comment = re.search(r"<!--.*?-->", template, re.S).group(0)
        self.assertNotIn("실험NN", comment)
        self.assertEqual(template.count("실험NN"), 3)
        step4 = re.search(r"^4\. (.*?)(?=^5\. )", self.proc, re.M | re.S).group(1)
        for token in ("<title>", "eyebrow", "h1"):
            with self.subTest(token):
                self.assertIn(token, step4)

    def test_강의노트_렌더_자리가_정해져_있다(self):
        # 2·3회차: `<스크래치>` 가 정의되지 않아 격리 에이전트가 둘 곳을 매번 지어냈다.
        self.assertNotIn("<스크래치>", self.text)
        step2 = re.search(r"^2\. (.*?)(?=^3\. )", self.proc, re.M | re.S).group(1)
        self.assertIn("tmp/manual", step2)

    def test_캡션을_옮겨_적지_않고_html_에서_읽는다(self):
        # 3회차: 10단계 `CAPTIONS` 를 4단계 HTML 에서 손으로 옮겨 적어 둘이 어긋날 수 있었다.
        step10 = re.search(r"^10\. (.*?)(?=^11\. )", self.proc, re.M | re.S).group(1)
        self.assertIn("figure_export.read_captions(", step10)
        self.assertNotIn("CAPTIONS", step10)

    def test_템플릿이_캡처_계약을_지킨다(self):
        template = FIGURE_TEMPLATE.read_text(encoding="utf-8")
        for token in ("data-fig-heights", 'get("fig")', 'class="tick"', "var FIGURES = ["):
            with self.subTest(token):
                self.assertIn(token, template)

    def test_예비보고서_스킬이_그림_스킬을_안내한다(self):
        proc = sections(PRE.read_text(encoding="utf-8"))["실행 절차"]
        self.assertIn("draw-expected-figure", proc)


class HandDiagramSkill(unittest.TestCase):
    def test_문서가_있다(self):
        self.assertTrue(HAND.exists())

    def test_출력_경로가_박혀_있다(self):
        text = HAND.read_text(encoding="utf-8")
        self.assertIn("output/손그림검토/round", text)

    def test_폴더_가드가_거절보다_앞에_온다(self):
        """실험 폴더가 없으면 만들지 않고 init-lab-experiment 로 보낸다."""
        text = HAND.read_text(encoding="utf-8")
        self.assertIn("init-lab-experiment", text)
        self.assertLess(text.index("experiment_dir"),
                        text.index("init-lab-experiment"))

    def test_규칙_열다섯개가_검사_목록_표에_있다(self):
        text = HAND.read_text(encoding="utf-8")
        for n in range(1, 16):
            self.assertIn(f"| H{n} |", text)

    def test_전사가_신호_이름을_적는다고_돼_있다(self):
        """H15 는 전사의 labels 로만 판정한다. 적으라는 말이 없으면 늘 비어서 잡힌다."""
        text = HAND.read_text(encoding="utf-8")
        self.assertIn('"labels"', text)
        self.assertIn("보드 밖", text)

    def test_전사가_pin_1_열을_적는다고_돼_있다(self):
        """뒤집어 그린 칩은 pin1_col 없이는 전사가 못 담는다."""
        text = HAND.read_text(encoding="utf-8")
        self.assertIn("pin1_col", text)

    def test_전사를_사람이_한다고_적혀_있다(self):
        text = HAND.read_text(encoding="utf-8")
        self.assertIn("전사", text)
        self.assertIn("uncertain", text)


class InitSkill(unittest.TestCase):
    """폴더 골격은 `config.EXPERIMENT_SUBDIRS` 한 곳에만 있다."""

    def setUp(self):
        self.text = INIT.read_text(encoding="utf-8")

    def test_폴더_목록을_config에서_읽는다(self):
        self.assertIn("config.EXPERIMENT_SUBDIRS", self.text)

    def test_폴더_목록을_문서에_베끼지_않는다(self):
        # 중괄호 확장 목록이나 개수를 적으면 config 를 고칠 때 문서가 따로
        # 거짓이 된다. 일정표가 정확히 이렇게 열한 곳에서 한꺼번에 틀렸다.
        self.assertNotRegex(self.text, r"\{[^}\n]*체크리스트[^}\n]*\}")
        self.assertNotRegex(self.text, r"\d+개 하위 폴더")

    def test_선택_폴더와_하위_산출물_폴더를_만들지_않는다고_적혀_있다(self):
        sec = sections(self.text)["비-목표"]
        for folder in ("`강의노트/`", "`퀴즈/`", "`STT/`",
                       "`결선도/손그림/`", "`실험사진/시트/`", "`output/손그림검토/`"):
            with self.subTest(folder=folder):
                self.assertIn(folder, sec)


class SharedReportStyle(unittest.TestCase):
    """③·④ 의 공용 서식 규칙(`.claude/보고서서식.md`)."""

    def setUp(self):
        self.shared = SHARED.read_text(encoding="utf-8")
        self.rules = {
            key: rule_blocks(sections(DOCS[key][0].read_text(encoding="utf-8"))["절대 규칙"])
            for key in REPORT_DOCS
        }

    def test_shared_sections_are_exactly_the_listed_rules(self):
        self.assertEqual(set(sections(self.shared)), set(SHARED_RULES))

    def test_every_listed_rule_is_a_stub_pointing_to_its_section(self):
        # 그루터기에 포인터가 없으면 ⑤·⑦ 처럼 번호로 따라온 쪽이 본문을 못 찾는다.
        for name, numbers in SHARED_RULES.items():
            for key, n in zip(REPORT_DOCS, numbers):
                with self.subTest(f"{key} §절대 규칙 {n} → §{name}"):
                    self.assertIn(n, self.rules[key])
                    self.assertIn(SHARED_POINTER + name, _flat(self.rules[key][n]))

    def test_every_pointer_resolves(self):
        files = [SHARED, PRE, RESULT, REVIEW, SYNC] + sorted((ROOT / "scripts/lab").glob("*.py"))
        checked = 0
        for path in files:
            for rest in shared_pointer_targets(path.read_text(encoding="utf-8")):
                checked += 1
                with self.subTest(f"{path.name}: §{rest}"):
                    self.assertTrue(any(rest.startswith(n) for n in SHARED_RULES), rest)
        # 그루터기만 해도 열 쌍이다. 못 찾으면 이 테스트는 공허하다.
        self.assertGreaterEqual(checked, 2 * len(SHARED_RULES))

    def test_internal_references_use_names(self):
        # 같은 규칙의 번호가 ③ 과 ④ 에서 다르다(③ 12 = ④ 13). 원문자 없는 번호
        # 인용은 어느 문서의 번호인지 말하지 않는다. 원문자 인용(`③ §절대 규칙 6`)은
        # `test_code_and_schema_cross_references_resolve` 가 푼다.
        bad = re.findall(r"(?<![①-⑦] )§(?:절대 규칙|실행 절차) \d|\d+단계|\d+번대로|Task \d+",
                         self.shared)
        self.assertEqual(bad, [])
        for m in re.finditer("§", self.shared):
            rest = self.shared[m.end():m.end() + 40]
            if rest[:1].isdigit() or rest.startswith(("절대 규칙", "실행 절차")):
                continue   # `§5.2` 는 §헤딩 이 "쓰지 말라" 고 드는 예시다
            with self.subTest(rest):
                self.assertTrue(any(rest.startswith(n) for n in SHARED_RULES), rest)

    def test_the_moved_bodies_are_not_duplicated_back(self):
        # 공용화의 목적이 한 벌이다. 본문이 스킬 문서로 돌아오면 다시 두 벌이 된다.
        for key in REPORT_DOCS:
            flat = _flat(DOCS[key][0].read_text(encoding="utf-8"))
            for phrase in ("형제 소절(같은 대절 안의 소절)", "`###` 이하는 쓰지 않는다"):
                with self.subTest(f"{key}: {phrase}"):
                    self.assertNotIn(phrase, flat)


if __name__ == "__main__":
    unittest.main()

