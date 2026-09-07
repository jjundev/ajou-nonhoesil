"""`docs/schema/lab-spec-v2.md` 의 `### 검사 강도` 절과 `validate.py` 를 맞댄다.

이 세션의 최종 리뷰(I2)가 발견한 사실: "정본은 코드다" 문단이
`validate_spec` 의 구성 함수로 넷(`check_metadata`·`check_row_count`·
`check_boolean`·`check_orphan_tables`)만 대고 있었는데 실제로는 여섯이었다
— `check_table_integrity`(셀 수 불일치·escape 된 파이프·`<br>`·탭)와
`check_diagnostic_claims`(이 브랜치가 새로 넣은 info 검사)가 빠져 있었다.
**드리프트를 막으려고 쓴 문단이 그 문단 자신 안에서 이미 드리프트해
있었다** — 그 문단을 최초로 쓴 커밋이 두 함수를 놓쳤다. 사람이 손으로
맞대는 것만으로는 이 종류의 누락이 재발하는 것을 못 막는다는 뜻이라,
여기서 양방향을 코드로 잠근다.

- `validate_spec` 이 실제로 부르는 `check_*` 가 전부 이 절 본문에
  등장하는가 (문서가 코드를 못 따라간 경우)
- 이 절 본문이 언급하는 `check_*` 이름이 전부 `validate.py` 에 실재하는가
  (문서가 존재하지 않는 함수를 가리키는 경우 — 리팩터로 이름이 바뀌었는데
  문서만 옛 이름을 쥐고 있는 경우가 여기 해당한다)

절 경계는 `### ` 레벨이다. `scripts/lab/config.py` 의 `_section_body` 는
`# ` 레벨만, `tests/test_skill_docs.py` 의 `sections()` 는 `## ` 레벨만
잘라내므로 둘 다 이 절에는 못 쓴다 — 아래 헬퍼가 `#`~`###` 아무 레벨의
다음 헤딩에서 멈춘다.
"""

import inspect
import re
import unittest
from pathlib import Path

from scripts.lab import validate

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DOC = ROOT / "docs/schema/lab-spec-v2.md"
SECTION_HEADING = "### 검사 강도"


def _section_body(text: str, heading: str) -> str:
    """`heading` 줄 다음부터, 다음에 나오는 `#`~`###` 헤딩 직전까지를 자른다."""
    lines = text.split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            start = i + 1
            break
    if start is None:
        raise AssertionError(f"{heading!r} 절을 문서에서 못 찾았다")
    end = len(lines)
    for j in range(start, len(lines)):
        if re.match(r"^#{1,3} ", lines[j]):
            end = j
            break
    return "\n".join(lines[start:end])


class SchemaDocValidateSync(unittest.TestCase):
    def test_validate_spec가_부르는_check가_전부_문서에_있다(self):
        src = inspect.getsource(validate.validate_spec)
        called = sorted(set(re.findall(r"check_\w+", src)))
        self.assertTrue(called, "validate_spec 소스에서 check_ 함수를 못 찾았다")

        body = _section_body(SCHEMA_DOC.read_text(encoding="utf-8"),
                              SECTION_HEADING)
        missing = [name for name in called if name not in body]
        self.assertEqual(
            missing, [],
            f"'{SECTION_HEADING}' 절 본문이 이 함수를 언급하지 않는다: "
            f"{missing} — validate_spec 은 실제로 이 함수들을 부른다: {called}")

    def test_문서가_언급한_check가_전부_validate_py에_실재한다(self):
        body = _section_body(SCHEMA_DOC.read_text(encoding="utf-8"),
                              SECTION_HEADING)
        mentioned = sorted(set(re.findall(r"check_\w+", body)))
        self.assertTrue(mentioned,
                         f"'{SECTION_HEADING}' 절에서 check_ 이름을 못 찾았다")
        missing = [name for name in mentioned if not hasattr(validate, name)]
        self.assertEqual(
            missing, [],
            f"'{SECTION_HEADING}' 절이 언급하는데 validate.py 에 없다: {missing}")
