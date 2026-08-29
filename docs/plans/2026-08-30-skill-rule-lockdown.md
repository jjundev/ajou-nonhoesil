# 보고서 스킬 규칙 확정 + 회귀 그물 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 2차 재생성이 남긴 미정의 8건(A~H)을 스킬 문서에 못박고, 같은 결함이 되살아나지 못하도록 스킬 문서 불변식 테스트를 만든 뒤, 한 번도 실행된 적 없는 결과보고서 스킬을 합성 기록으로 한 번 돌려 본다.

**Architecture:** 새 파일 `tests/test_skill_docs.py` 하나가 그물이다. 그 안의 `cross_reference_errors()` 는 스킬 문서의 `§절대 규칙 N`·`§실행 절차 N`·`N단계` 가 실재하는 항목을 가리키는지 기계로 검사한다 — 이 저장소에서 **두 번 되살아난** 죽은 참조가 정확히 그 종류다. 나머지 테스트는 이번에 고치는 8건이 되돌아오지 않는지를 문자열 존재/부재로 못박는다. 스킬 문서를 고치는 태스크마다 그 태스크의 테스트가 먼저 실패하고, 문서를 고치면 통과한다. `scripts/lab/` 파이썬 코드는 **한 줄도 고치지 않는다.**

**Tech Stack:** Python 3.14.6 표준 라이브러리 `unittest` + `re` + `pathlib`. 마크다운 스킬 문서 2종.

## Global Constraints

- **`pytest` 가 없다.** `unittest` 만 쓴다. 전체 실행은 `zsh -c 'PYTHONPATH=. python3 -m unittest discover -s tests -t .'`.
- **`requests` 가 없다.** 이 계획은 네트워크를 쓰지 않는다.
- **Bash 는 비대화형 zsh 라 `~/.zshrc` 를 읽지 않는다.** 환경변수가 필요한 명령은 `zsh -c '...'` 로 감싼다. 이 계획에서는 `NOTION_TOKEN` 이 필요 없다.
- **`scripts/lab/*.py` 를 고치지 않는다.** `validate.check_report_sections` 는 이미 `item_count` 를 받는다 — 빠진 것은 호출 쪽 문서다.
- **`실험01/output/실험01_예비보고서.md` 를 고치지 않는다.** 사용자가 노션에서 승인한 v6 정본이다.
- **스킬 문서는 한국어**이고 76열 내외에서 줄바꿈한다. 기존 문서의 목소리(단정형 규칙문 + `**굵게**` 로 규칙 머리 강조)를 그대로 따른다.
- 태스크당 커밋 1개. 커밋 메시지는 한국어, `test:` 또는 `docs:` 접두.
- 테스트 개수는 현재 **322개, `OK`** 다. 어느 태스크에서도 기존 테스트를 깨지 않는다.

---

## File Structure

| 파일 | 책임 | 상태 |
|---|---|---|
| `tests/test_skill_docs.py` | 스킬 문서 불변식. 상호참조 검사기 + 이번에 고친 8건의 회귀 방지 | **신규** |
| `.claude/skills/write-pre-report/SKILL.md` | 예비보고서 작성 규칙. 8건 중 7건이 여기 | 수정 |
| `.claude/skills/write-result-report/SKILL.md` | 결과보고서 작성 규칙. E 1건만 | 수정 |

테스트 파일은 하나로 둔다 — 검사 대상이 문서 2개뿐이고, 상호참조 검사기를 두 문서가 공유하므로 나누면 헬퍼가 흩어진다.

### 사전 조건 (Task 1 의 Step 0 에서 처리)

현재 작업 트리에는 2차 재생성 결과가 남아 있다. `실험01_예비보고서.md` 가 재생성본(18,378 B)으로 덮여 있고 노션 베이스라인 6개와 `notion_v3.md` 가 삭제된 상태다. 정본 v6 은 `HEAD` 에 온전하다.

---

## Task 1: 상호참조 검사기 + A(`§3` 죽은 참조)

**Files:**
- Create: `tests/test_skill_docs.py`
- Modify: `.claude/skills/write-pre-report/SKILL.md:209-211`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: `tests/test_skill_docs.py` 의 모듈 수준 이름 — 이후 모든 태스크가 여기에 테스트를 덧붙인다.
  - `ROOT: Path` — 저장소 루트
  - `PRE: Path`, `RESULT: Path` — 두 SKILL.md 경로
  - `sections(text: str) -> dict[str, str]` — `## 제목` 으로 갈라 `{제목: 본문}`
  - `numbered_items(section_body: str) -> set[int]` — `1.`·`5b.` 항목 번호
  - `cross_reference_errors(text: str) -> list[str]` — 죽은 참조 메시지 목록
  - `class SkillDocInvariants(unittest.TestCase)` — `self.docs` 가 `{"예보": str, "결과": str}`

- [ ] **Step 0: 작업 트리를 정본으로 되돌린다**

재생성본을 스크래치패드로 옮긴 뒤 `HEAD` 로 복원한다. 커밋하지 않는다.

```bash
cp 실험01/output/실험01_예비보고서.md /tmp/regen2-실험01-예비보고서.md
git checkout -- 실험01/output/
git status --short
```

Expected: `?? 실험01/output/eli5_실험01.html` 한 줄만 남는다. (이 파일은 추적 대상이 아니고 이 계획과 무관하다 — **건드리지 않는다.**)

```bash
wc -c 실험01/output/실험01_예비보고서.md
```

Expected: `12882` (v6 정본).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_skill_docs.py` 를 새로 만든다.

```python
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
        # 산문 규칙을 문장으로 찾을 때 쓴다. 문단을 다시 감싸도 규칙이 같으면
        # 통과해야 하므로, 줄바꿈·들여쓰기를 공백 하나로 눌러 둔 사본이다.
        self.flat = {k: re.sub(r"\s+", " ", v) for k, v in self.docs.items()}

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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest tests.test_skill_docs -v 2>&1 | tail -20'
```

Expected: `test_no_bare_section_number_references` 가 `FAIL` — subTest `예보` 에서 `['§3'] != []`.
나머지 6개(`CrossReferenceChecker` 5개 + `test_no_dangling_cross_references`)는 `ok`.

**`test_no_dangling_cross_references` 는 지금 통과한다.** 이 테스트는 결함을 찾는 도구가 아니라 이미 두 번 고친 결함이 되살아나는 것을 막는 그물이다 — 그래서 검사기 자체를 `CrossReferenceChecker` 4개로 따로 검증했다. 통과를 보고 "테스트가 무의미하다"고 판단하지 말 것.

- [ ] **Step 3: `§3` 을 고친다**

`.claude/skills/write-pre-report/SKILL.md` 의 §실행 절차 1 에서 아래 세 줄을 찾는다:

```
   손으로 짐작하지 않는다(§절대 규칙 6). `<실험NN>/결선도/netlist.md`
   가 없으면 §3 의 `check_netlist` 가 "결선도 netlist 파일이 없다" error 를 내는데,
   그 자리까지 미루지 않고 여기서 먼저 정직하게 보고하고 멈춘다 — **회로 결선도
```

아래로 교체한다 (줄바꿈 위치가 바뀐다 — 길이를 맞추기 위해서다):

```
   손으로 짐작하지 않는다(§절대 규칙 6). `<실험NN>/결선도/netlist.md` 가 없으면
   §실행 절차 3 의 `check_netlist` 가 "결선도 netlist 파일이 없다" error 를 내는데,
   그 자리까지 미루지 않고 여기서 먼저 정직하게 보고하고 멈춘다 — **회로 결선도
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest tests.test_skill_docs -v 2>&1 | tail -12'
```

Expected: `Ran 7 tests`, `OK`.

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest discover -s tests -t . 2>&1 | grep -E "^(OK|FAILED|Ran )"'
```

Expected: `Ran 329 tests`, `OK`. (322 + 7)

- [ ] **Step 5: 커밋**

```bash
git add tests/test_skill_docs.py .claude/skills/write-pre-report/SKILL.md
git commit -m "test: 스킬 문서 상호참조 불변식 + 죽은 참조 §3 정정"
```

---

## Task 2: C(형제 소절 범위) · D(헤딩 단계 상한)

**Files:**
- Modify: `tests/test_skill_docs.py` (`SkillDocInvariants` 에 테스트 2개 추가)
- Modify: `.claude/skills/write-pre-report/SKILL.md` — §절대 규칙 13
- Modify: `.claude/skills/write-result-report/SKILL.md` — §절대 규칙 14, §절대 규칙 12

**Interfaces:**
- Consumes: Task 1 의 `SkillDocInvariants.setUp` 이 채우는 `self.docs` (예보, 결과 모두)
- Produces: 없음 (테스트만 늘어난다)

**배경 — 왜 이 두 건인가.** 격리 에이전트가 실험01 을 재생성했을 때 둘 다 **판단을 강요당한** 자리다. 규칙 13 의 "형제 소절"이 같은 대절 안인지 문서 전체인지 말하지 않아, 반대로 읽으면 표 10개의 레이아웃이 통째로 뒤집힌다. 규칙 11 은 `#`·`##` 만 정의해서 소절 아래 한 단계가 더 필요할 때 `###` 를 써도 되는지가 비어 있다. **결과보고서 쪽이 오히려 더 중요하다** — `항목반복형` 프리셋이 여기서 쓰이고 항목마다 표가 반복되기 때문이다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_skill_docs.py` 의 `SkillDocInvariants` 클래스 안, `test_no_bare_section_number_references` 다음에 붙인다.

```python
    def test_sibling_subsection_scope_is_defined(self):
        # 형제를 문서 전체로 읽으면 소절 제목이 표 제목을 겸하는 예외가
        # 무너져 표 레이아웃이 통째로 뒤집힌다. 두 스킬이 같은 기계를 쓴다.
        for name, text in self.docs.items():
            with self.subTest(name):
                self.assertIn("형제 소절(같은 대절 안의 소절)", self.flat[name])

    def test_heading_levels_are_capped_at_two(self):
        # `###` 를 허용하면 여백 규칙이 정의되지 않은 자리가 생긴다.
        for name, text in self.docs.items():
            with self.subTest(name):
                self.assertIn("`###` 이하는 쓰지 않는다", self.flat[name])
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest tests.test_skill_docs -v 2>&1 | tail -20'
```

Expected: 새 테스트 2개가 `FAIL` (각각 subTest `예보`·`결과` 양쪽), 기존 7개는 `ok`.

- [ ] **Step 3: 예보 규칙 13 을 고친다**

`.claude/skills/write-pre-report/SKILL.md` §절대 규칙 13 에서 아래 다섯 줄을 찾는다:

```
    씌운다 — 형제 소절(같은 대절 안의 소절)의 같은 성격 표가 제목을 달고
    있는데 이것만 맨몸이면 어긋나 보인다. **형제는 같은 대절 안까지다** —
    다른 대절의 표와는 맞추지 않는다. 대절이 다르면 표의 성격도 다르고
    (준비물·핀 배치·결선 표는 각자 예외를 갖는다), 문서 전체를 형제로 보면
    그 예외가 전부 무너진다.
```

아래로 교체한다:

```
    씌운다 — 형제 소절(같은 대절 안의 소절)의 같은 성격 표가 제목을 달고
    있는데 이것만 맨몸이면 어긋나 보인다. **형제는 같은 대절 안까지다** —
    다른 대절의 표와는 맞추지 않는다. 예를 들어 `# 실험 부품` 의 준비물·핀
    배치 표는 서로 형제라 같이 맞추지만, `# 회로 결선도` 의 결선 표는 대절이
    달라 그것들과 맞출 필요가 없다. 문서 전체를 형제로 보면 이 규칙이 든
    예외가 전부 무너진다.
```

- [ ] **Step 4: 결과 규칙 14 를 고친다**

`.claude/skills/write-result-report/SKILL.md` 의 규칙 14 에서 아래 두 줄을 찾는다:

```
    끼면 표가 하나여도 불릿 제목을 씌운다** — 형제 소절의 같은 성격 표가
    제목을 달고 있는데 이것만 맨몸이면 어긋나 보인다.
```

아래로 교체한다:

```
    끼면 표가 하나여도 불릿 제목을 씌운다** — 형제 소절(같은 대절 안의 소절)의
    같은 성격 표가 제목을 달고 있는데 이것만 맨몸이면 어긋나 보인다.
    **형제는 같은 대절 안까지다** — 다른 대절의 표와는 맞추지 않는다. 대절이
    다르면 표의 성격도 다르고, 문서 전체를 형제로 보면 이 규칙이 바로 위에서
    든 예외(소절 제목이 곧 표 제목을 겸하는 경우)가 무너진다.
```

- [ ] **Step 5: 결과 규칙 12 를 고친다**

같은 파일의 규칙 12 (97행) 다음에 빈 줄 하나와 아래 문단을 삽입한다 (기존 "번호가 빠지면…" 문단 앞):

```
    **헤딩은 이 두 단계뿐이다 — `###` 이하는 쓰지 않는다.** 소절 아래 한
    단계가 더 필요해 보이면 헤딩을 늘리지 말고 §절대 규칙 14 의 굵은 불릿
    제목으로 흡수한다. `#`·`##` 두 단계면 노션 목차 블록이 충분히 읽히고,
    단계를 늘리면 §절대 규칙 13 의 여백 규칙이 정의되지 않은 자리가 생긴다.
```

- [ ] **Step 6: 테스트를 돌려 통과를 확인한다**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest discover -s tests -t . 2>&1 | grep -E "^(OK|FAILED|Ran )"'
```

Expected: `Ran 331 tests`, `OK`.

- [ ] **Step 7: 커밋**

```bash
git add tests/test_skill_docs.py .claude/skills/write-pre-report/SKILL.md .claude/skills/write-result-report/SKILL.md
git commit -m "docs: 형제 소절 범위·헤딩 상한을 결과보고서 스킬에도 적용하고 예시를 정정"
```

---

## Task 3: B(브레드보드 템플릿) · 소절 수 파생 규칙 (신설 §절대 규칙 17)

**Files:**
- Modify: `tests/test_skill_docs.py` (테스트 5개 추가 — `SubsectionCounter` 2 + `SkillDocInvariants` 3, 그리고 `BASELINE_V6` 상수와 `subsection_counts` 헬퍼)
- Modify: `.claude/skills/write-pre-report/SKILL.md` — §섹션별 재료 `회로 결선도` 행, §절대 규칙 끝에 17 신설

**Interfaces:**
- Consumes: Task 1 의 `SkillDocInvariants.setUp`, `cross_reference_errors`
- Produces: 예보 스킬의 절대 규칙이 16개 → **17개**가 된다. Task 5 가 §절대 규칙 16 을 고칠 때 번호가 밀리지 않게 17 은 **16 뒤에** 붙인다.

**배경 — 왜 이 두 건인가.** 브레드보드 템플릿은 §절대 규칙 3 과 §섹션별 재료가 둘 다 "산출물에 포함된다"고 말하는데 **경로를 말하는 곳이 없다.** 실제 경로는 §절대 규칙 8 의 예시 한 줄에만 나오고, 그 규칙의 주제는 정반대("경로를 산문에 쓰지 마라")다. 게다가 저장소에 사본이 둘이다 (`.claude/assets/Breadboard.jpg`, `from_the_past/정리/강의노트/Breadboard.jpg`).

소절 수 규칙은 실측에서 나왔다 — 같은 실험을 규칙만 보고 재생성했더니 8,345자가 11,130자가 됐고, 회로 결선 소절이 4개에서 6개로 늘었다(항목 단위가 아니라 회로 단위로 쪼갰다). 사용자가 승인한 v6 은 `items` 3개 → 과정 3소절, 결선 6소절이다(공통 결선 규칙 + 배선 3 + 실험 전 확인할 사항 + 브레드보드 작도).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

모듈 수준에 상수와 헬퍼를 더한다. 상수는 `RESULT = …` 다음에, 헬퍼는
`numbered_items` 다음에 놓는다.

```python
BASELINE_V6 = ROOT / "실험01/output/실험01_예비보고서_notion_baseline_v6.md"
```

```python
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
```

첫 테스트 클래스 앞에 헬퍼 자신의 단위 테스트를 둔다 — 정본 파일의 모양에
기대지 않고 "문자열이 아니라 구조를 센다"를 보장하기 위해서다.

```python
class SubsectionCounter(unittest.TestCase):
    """`subsection_counts` 가 문자열이 아니라 헤딩 구조를 세는지 본다."""

    def test_counts_subsections_per_major_section(self):
        doc = ("# 가\n## 가1\n본문\n## 가2\n# 나\n## 나1\n## 나2\n## 나3\n")
        self.assertEqual(subsection_counts(doc), {"가": 2, "나": 3})

    def test_a_major_section_with_no_subsections_counts_zero(self):
        doc = ("# 가\n본문만 있다\n# 나\n## 나1\n")
        self.assertEqual(subsection_counts(doc), {"가": 0, "나": 1})
```

`SkillDocInvariants` 클래스 안에 셋을 붙인다.

```python
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
                      self.flat["예보"])
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest tests.test_skill_docs -v 2>&1 | tail -20'
```

Expected: 새 테스트 5개 중 `SkillDocInvariants` 의 3개가 `FAIL` (`SubsectionCounter` 의 2개는 헬퍼만 쓰므로 바로 통과한다). `test_breadboard_template_path_and_home_are_pinned` 는 `.claude/assets/Breadboard.jpg not found in '| 회로 결선도 | ...'`, 나머지 둘은 문자열 부재.

- [ ] **Step 3: §섹션별 재료 의 `회로 결선도` 행을 고친다**

`.claude/skills/write-pre-report/SKILL.md` 에서 아래 한 줄(표의 한 행)을 찾는다:

```
| 회로 결선도 | `<실험NN>/결선도/netlist.md` 표 + 브레드보드. **본문에는 `netlist.md` 를 인용하지 않는다** — 결선 근거는 학생이 강의노트 회로도를 직접 읽고 파악한 것처럼 쓴다(§절대 규칙 8) |
```

아래 한 줄로 교체한다:

```
| 회로 결선도 | `<실험NN>/결선도/netlist.md` 표 + 브레드보드 템플릿 `.claude/assets/Breadboard.jpg`. **템플릿은 이 절의 마지막 소절 `## 브레드보드 작도` 에 이미지 한 줄로 넣는다** — 형태는 §절대 규칙 8 의 예시 그대로이고, 그림 자체는 사용자가 노션에서 끼워 넣는다. `from_the_past/정리/강의노트/Breadboard.jpg` 는 같은 그림의 사본이니 쓰지 않는다. **`## 실험 전 확인할 사항` 소절의 재료도 `netlist.md` 다** — 그 주 회로에 적혀 있는 주의 사항(실물 대조가 필요한 핀 배치, 다른 주차와 달라지는 처리 규칙, 강의노트가 지정하지 않아 판단한 자리)을 학생이 실험 전에 짚어 볼 목록으로 옮긴다. **본문에는 `netlist.md` 를 인용하지 않는다** — 결선 근거는 학생이 강의노트 회로도를 직접 읽고 파악한 것처럼 쓴다(§절대 규칙 8) |
```

- [ ] **Step 4: §절대 규칙 17 을 신설한다**

같은 파일에서 §절대 규칙 16 의 마지막 줄을 찾는다:

```
    인버터가 한 칩에 6개라 두 단 모두 한 칩으로 잡힌다.
```

그 줄 **다음에** 빈 줄 하나와 아래를 삽입한다 (`## 실행 절차` 헤딩 앞):

```
17. **소절 수는 명세에서 파생한다 — 늘리지 않는다.** 실험 과정 절의 소절은
    명세 `items` 하나당 정확히 하나다. 회로 결선 절은 거기에 **고정 소절
    셋**이 붙는다 — 맨 앞의 공통 결선 규칙, 그리고 맨 뒤의 실험 전 확인할
    사항과 브레드보드 작도(§섹션별 재료가 셋의 재료를 든다). `items` 3개면
    과정 3소절, 결선 6소절이다. 다만 그 주 결선도 자료에 적어 둘 주의
    사항이 하나도 없으면 실험 전 확인할 사항 소절을 만들지 않는다 — 없는
    것을 지어내지 않는다(§절대 규칙 5). 그 경우 결선 5소절이다. 다섯 주차를
    확인한 결과 지금까지는 모두 적을 것이 있었다.

    **항목 안에서 회로 단위로 더 쪼개지 않는다** — 3입력 AND 와 OR 는 명세
    에서 한 항목이므로 배선 소절도 하나다. 이론 절의 범위는 §절대 규칙 16 이
    정하므로 따로 세지 않는다.

    **길어지면 소절을 쪼개는 게 아니라 지운다.** 규칙만 보고 같은 보고서를
    다시 쓰게 했더니 8,345자가 11,130자가 됐다. 늘어난 원인은 둘이었다 —
    배선 소절을 항목(3개)이 아니라 회로(5개) 단위로 쪼갠 것, 그리고
    §절대 규칙 14·15 가 이미 금지한 종류의 문장이었다.
```

- [ ] **Step 5: 테스트를 돌려 통과를 확인한다**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest discover -s tests -t . 2>&1 | grep -E "^(OK|FAILED|Ran )"'
```

Expected: `Ran 336 tests`, `OK`. (`test_no_dangling_cross_references` 도 계속 통과해야 한다 — 규칙 17 이 참조하는 14·15·16 은 전부 실재한다.)

- [ ] **Step 6: 커밋**

```bash
git add tests/test_skill_docs.py .claude/skills/write-pre-report/SKILL.md
git commit -m "docs: 브레드보드 템플릿 경로·자리 확정, 소절 수 파생 규칙 신설"
```

---

## Task 4: E(`~` 판정) · F(`item_count` 미전달)

**Files:**
- Modify: `tests/test_skill_docs.py` (테스트 2개 추가)
- Modify: `.claude/skills/write-pre-report/SKILL.md` — §실행 절차 9, §실행 절차 10
- Modify: `.claude/skills/write-result-report/SKILL.md` — §실행 절차 13

**Interfaces:**
- Consumes: Task 1 의 `SkillDocInvariants.setUp` (`self.docs` 가 두 문서를 모두 담는다)
- Produces: 없음

**배경 — 이 둘만 "규칙과 코드가 어긋난" 실제 결함이다.**

E: `config.load_course_info()` 는 YAML `~` 를 파이썬 `None` 으로 돌려준다. 문서가 "`ai_usage_log` 가 `~` 가 아니면 로그를 남긴다"고 쓰여 있어, 글자대로 `!= '~'` 로 구현하면 **항상 참**이 되어 아직 확정되지 않은 경로에 로그를 남긴다. 두 스킬에 똑같이 있다.

F: `validate.check_report_sections` 는 `item_count is None` 이면 per-item 반복 횟수 검사를 통째로 건너뛴다. 예보 §실행 절차 2 는 `repeat: per-item` 섹션을 항목마다 반복하라고 시키는데, §실행 절차 9 의 호출이 `item_count` 를 넘기지 않아 **그 반복을 검사할 수 없다.** 결과보고서 쪽은 이미 넘기고 있다(`write-result-report/SKILL.md:429-430`) — 예보만 빠져 대칭이 깨졌다. `check_report_sections` 자체는 고치지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`SkillDocInvariants` 클래스 안에 붙인다.

```python
    def test_ai_usage_log_gate_is_written_against_the_parsed_value(self):
        # config.load_course_info() 는 YAML `~` 를 None 으로 돌려준다.
        # "`~` 가 아니면" 을 글자대로 구현하면 항상 참이 되어 로그를 남긴다.
        for name, text in self.docs.items():
            with self.subTest(name):
                self.assertNotIn("`ai_usage_log` 가 `~` 가 아니면", text)
                self.assertIn(
                    "`ai_usage_log` 가 비어 있지 않으면(`None` 이 아니면)",
                    self.flat[name])

    def test_both_skills_pass_item_count_to_the_section_check(self):
        # item_count 없이 부르면 per-item 반복 횟수 검사가 통째로 생략된다.
        for name, text in self.docs.items():
            with self.subTest(name):
                calls = call_arguments(text, "check_report_sections")
                self.assertTrue(calls, "호출부가 없다")
                for call in calls:
                    self.assertIn("item_count", call)
```

Task 4 의 호출부 검사는 정규식이 아니라 균형 괄호 스캐너를 쓴다 —
`check_report_sections\([^)]*\)` 은 중첩 괄호 `len(spec.items)` 에서 한 칸 일찍
끊겨서, 인자 순서가 바뀌면 있는 인자를 없다고 보고한다. 모듈 수준에 헬퍼를 두고
그 자신의 단위 테스트를 붙인다.

```python
def call_arguments(text, func_name):
    """`func(...)` 호출의 괄호 안을 균형을 맞춰 뽑는다.

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
```

```python
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
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest tests.test_skill_docs -v 2>&1 | tail -25'
```

Expected: 새 테스트 2개가 `FAIL`. `test_ai_usage_log_...` 는 subTest `예보`·`결과` 양쪽에서, `test_both_skills_pass_item_count_...` 는 subTest `예보` 에서만.

- [ ] **Step 3: 예보 §실행 절차 9 의 명령을 고친다**

`.claude/skills/write-pre-report/SKILL.md` 에서 아래 코드 블록을 찾는다:

````
    ```bash
    python3 -c "
    from pathlib import Path
    from scripts.lab import config, validate
    root = config.find_project_root(Path('.'))
    fmt = config.load_report_format(root)
    for f in validate.check_report_sections('<실험NN>/output/<실험NN>_예비보고서.md', fmt.pre):
        print(f)
    "
    ```
````

아래로 교체한다:

````
    ```bash
    python3 -c "
    from pathlib import Path
    from scripts.lab import config, validate
    from scripts.lab.spec_parser import parse_spec
    root = config.find_project_root(Path('.'))
    fmt = config.load_report_format(root)
    spec = parse_spec('<실험NN>/체크리스트/명세.md')
    for f in validate.check_report_sections('<실험NN>/output/<실험NN>_예비보고서.md',
                                             fmt.pre, item_count=len(spec.items)):
        print(f)
    "
    ```
````

이어서 그 아래 문단의 첫 줄을 찾는다:

```
    출력이 없으면 모든 섹션이 존재하는 것이다. 출력을 파일로 남기지 않는다
```

아래 두 줄로 교체한다 (문단 앞에 한 문장을 더한다):

```
    `item_count=len(spec.items)` 를 항상 넘긴다 — §실행 절차 2 가 시킨
    `repeat: per-item` 반복이 항목 수만큼 정확히 나왔는지는 이 인자 없이는
    검사되지 않는다. 출력이 없으면 모든 섹션이 존재하는 것이다. 출력을
    파일로 남기지 않는다
```

- [ ] **Step 4: 예보 §실행 절차 10 을 고친다**

같은 파일에서 아래 두 줄을 찾는다:

```
10. `과목정보.md` 의 `ai_usage_log` 가 `~` 가 아니면 그 경로에 로그 한 줄을
    남긴다. `~` 면 아무것도 하지 않는다.
```

아래로 교체한다:

```
10. `과목정보.md` 의 `ai_usage_log` 가 비어 있지 않으면(`None` 이 아니면) 그
    경로에 로그 한 줄을 남긴다. 비어 있으면 아무것도 하지 않는다.
    `config.load_course_info()` 는 YAML `~` 를 파이썬 `None` 으로 돌려주므로
    `!= '~'` 로 비교하면 항상 참이 되어 로그를 남긴다 — §실행 절차 7 이
    `missing_identity()` 로 감싼 것과 같은 관례다.
```

- [ ] **Step 5: 결과 §실행 절차 13 을 고친다**

`.claude/skills/write-result-report/SKILL.md` 에서 아래 두 줄을 찾는다:

```
13. `과목정보.md` 의 `ai_usage_log` 가 `~` 가 아니면 그 경로에 로그 한 줄을
    남긴다. `~` 면 아무것도 하지 않는다.
```

아래로 교체한다 (예보와 달리 단계 번호를 인용하지 않는다 — 이 문서의 신원 확인 단계 번호가 다르다):

```
13. `과목정보.md` 의 `ai_usage_log` 가 비어 있지 않으면(`None` 이 아니면) 그
    경로에 로그 한 줄을 남긴다. 비어 있으면 아무것도 하지 않는다.
    `config.load_course_info()` 는 YAML `~` 를 파이썬 `None` 으로 돌려주므로
    `!= '~'` 로 비교하면 항상 참이 되어 로그를 남긴다.
```

- [ ] **Step 6: 테스트를 돌려 통과를 확인한다**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest discover -s tests -t . 2>&1 | grep -E "^(OK|FAILED|Ran )"'
```

Expected: `Ran 340 tests`, `OK`.

명령 자체가 실제로 도는지도 한 번 확인한다 (v6 정본 대상, 산출물을 만들지 않는다):

```bash
zsh -c 'PYTHONPATH=. python3 -c "
from pathlib import Path
from scripts.lab import config, validate
from scripts.lab.spec_parser import parse_spec
root = config.find_project_root(Path(\".\"))
fmt = config.load_report_format(root)
spec = parse_spec(\"실험01/체크리스트/명세.md\")
out = validate.check_report_sections(\"실험01/output/실험01_예비보고서.md\", fmt.pre, item_count=len(spec.items))
print(\"\n\".join(str(f) for f in out) or \"문제 없음\")
"'
```

Expected: `문제 없음`. (교집합 프리셋에는 `repeat: per-item` 이 없으므로 인자를 넘겨도 결과가 달라지지 않는다 — 문서와 코드가 어긋난 것을 고치는 게 목적이다.)

- [ ] **Step 7: 커밋**

```bash
git add tests/test_skill_docs.py .claude/skills/write-pre-report/SKILL.md .claude/skills/write-result-report/SKILL.md
git commit -m "docs: ai_usage_log 판정을 파싱된 값 기준으로, 예보 검증에 item_count 전달"
```

---

## Task 5: G(준비물에 없는 소모품) · H(이론 절 범위)

**Files:**
- Modify: `tests/test_skill_docs.py` (테스트 2개 추가)
- Modify: `.claude/skills/write-pre-report/SKILL.md` — §절대 규칙 16, §섹션별 재료 `실험 이론` 행

**Interfaces:**
- Consumes: Task 1 의 `SkillDocInvariants.setUp`
- Produces: 없음. §절대 규칙 16 에 문단 2개가 붙지만 **번호는 그대로 16 이다** — Task 3 이 신설한 17 의 번호가 밀리면 안 된다.

**배경 — 규칙 16 이 한쪽만 말한다.** 지금 규칙 16 은 "준비물에 있지만 회로에 안 쓰는 소자는 이론에서 다루지 말고, 표에서는 지우지도 말라"고 한다. **더하는 쪽은 침묵이다.** 실제로 실험1 강의노트 준비물에는 브레드보드·점퍼선·330Ω 저항이 없는데(330Ω 은 회로도 옆 주의 박스에만 나온다) 이것들 없이는 결선 절이 성립하지 않는다. 재생성 에이전트는 표에 넣었지만 "규칙 16 의 이유가 추가에도 걸린다고 읽을 수 있어 판단이 갈릴 자리"라고 보고했다.

같은 침묵이 이론 절에도 있다. 실험1 의 NOT 진리표는 명세에 대응 표가 없는데 복합회로가 74HC04 를 실제로 쓴다. 규칙 16 은 "회로에 안 쓰는 소자"만 막으므로 NOT 은 걸리지 않지만, 이론 절이 `role: reference` 표를 넘어서도 되는지는 어디에도 없다. 반대로 재생성본은 회로가 쓰지 않는 "부울 대수의 기본 정리" 소절을 새로 만들었다 — 이 규칙이 그것을 자른다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`SkillDocInvariants` 클래스 안에 붙인다.

```python
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
        rows = [ln for ln in pre.splitlines() if ln.startswith("| 실험 이론 |")]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("범위는 §절대 규칙 16", rows[0])
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest tests.test_skill_docs -v 2>&1 | tail -25'
```

Expected: 새 테스트 2개가 `FAIL` (문자열 부재).

- [ ] **Step 3: 규칙 16 에 두 문단을 더한다**

`.claude/skills/write-pre-report/SKILL.md` §절대 규칙 16 의 마지막 줄을 찾는다:

```
    인버터가 한 칩에 6개라 두 단 모두 한 칩으로 잡힌다.
```

**Task 3 이 그 아래에 §절대 규칙 17 을 붙여 두었다.** 위 줄과 `17.` 사이에 빈 줄을 두고 아래 두 문단을 삽입한다 (17 보다 **앞**이다):

```
    **반대로, 회로가 성립하는 데 필요한데 강의노트 준비물에 없는 소모품은
    표에 더한다** — 브레드보드·점퍼선·전류 제한 저항처럼 강의노트가 당연하게
    보고 적지 않은 것들이다. 비고에는 기능만 적고 "강의노트에 없다" 같은 메타
    서술은 쓰지 않는다(§절대 규칙 7). 이 규칙이 막는 것은 **회로에 쓰지도
    않는 소자를 설명하는 것**이지, 회로가 실제로 쓰는 것을 표에서 빠뜨리는
    것이 아니다. 이것은 §절대 규칙 5 를 푸는 것이 아니다 — 브레드보드·점퍼선은
    회로를 꽂으려면 물리적으로 있어야 하고, 전류 제한 저항은 회로도가 이미
    요구한다. 표에 적는 것은 그 사실뿐이지 지어낸 근거가 아니다.

    이론 절의 범위도 같은 기준이다. **이론 절은 그 주 회로가 실제로 쓰는
    것만 다룬다** — 명세에 대응하는 `role: reference` 표가 없어도 회로가 쓰는
    소자면 다루고(실험1 의 NOT 게이트: 복합회로가 74HC04 를 쓰는데 명세에는
    표가 없다), 회로가 쓰지 않는 일반 이론은 강의노트에 있어도 넣지 않는다
    (부울 대수의 교환·결합·분배 법칙 등).
```

- [ ] **Step 4: §섹션별 재료 의 `실험 이론` 행을 고친다**

같은 파일에서 아래 한 줄(표의 한 행)을 찾는다:

```
| 실험 이론 | 그 주 강의노트(`실험N.pdf`) 이론 슬라이드 + `논회 강의노트/Ch*.pdf`(이름이 겹치는 별도의 이론 교재 — §절대 규칙 6) + `docs/study/` + 명세의 **`role: reference` 표**(실험1 T6~T9 = 2입력 이론표, `encoding: H/L`). **`H/L` 을 `0/1` 로 바꾸지 말 것.** 본문에는 이 자료들의 이름을 밝히지 않고 내용만 녹여 쓴다(§절대 규칙 8) |
```

아래 한 줄로 교체한다 (마지막에 한 문장이 붙는다):

```
| 실험 이론 | 그 주 강의노트(`실험N.pdf`) 이론 슬라이드 + `논회 강의노트/Ch*.pdf`(이름이 겹치는 별도의 이론 교재 — §절대 규칙 6) + `docs/study/` + 명세의 **`role: reference` 표**(실험1 T6~T9 = 2입력 이론표, `encoding: H/L`). **`H/L` 을 `0/1` 로 바꾸지 말 것.** 본문에는 이 자료들의 이름을 밝히지 않고 내용만 녹여 쓴다(§절대 규칙 8). **범위는 §절대 규칙 16 이 정한다** — 자료에 있다고 다 쓰는 것이 아니라 그 주 회로가 실제로 쓰는 것만 |
```

- [ ] **Step 5: 테스트를 돌려 통과를 확인한다**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest discover -s tests -t . 2>&1 | grep -E "^(OK|FAILED|Ran )"'
```

Expected: `Ran 342 tests`, `OK`.

규칙 번호가 밀리지 않았는지 눈으로 확인한다:

```bash
grep -nE "^1[4-7]\. \*\*" .claude/skills/write-pre-report/SKILL.md
```

Expected: 14·15·16·17 네 줄이 이 순서로 나오고, 17 은 "소절 수는 명세에서 파생한다" 다.

- [ ] **Step 6: 커밋**

```bash
git add tests/test_skill_docs.py .claude/skills/write-pre-report/SKILL.md
git commit -m "docs: 준비물에 없는 소모품 추가 허용, 이론 절 범위를 회로 기준으로 확정"
```

---

## Task 6: 결과보고서 스킬 dry run (합성 기록)

**Files:**
- Create: `.superpowers/sdd/result-dryrun-report.md` (git 추적 안 됨 — `.superpowers/sdd/.gitignore` 가 전부 무시한다)
- Temporarily modify: `실험01/체크리스트/기록.md` (실행 후 `git checkout` 으로 되돌린다)
- Temporarily create: `실험01/output/실험01_결과보고서.md` (실행 후 삭제한다)
- Conditionally modify: `tests/test_skill_docs.py`, `.claude/skills/write-result-report/SKILL.md` (모순이 나왔을 때만)

**Interfaces:**
- Consumes: Task 4 가 고친 `write-result-report/SKILL.md` §실행 절차 13
- Produces: 발견된 모순 목록. 고칠 것이 있으면 Task 1~5 와 같은 형태(불변식 테스트 + 문서 수정)로 같은 커밋에 담는다.

**왜 하는가.** `write-result-report/SKILL.md` 는 **한 번도 실행된 적이 없다.** `실험01/체크리스트/기록.md` 는 템플릿만 있고 `filled_by: ~` 이며 확인 칸이 전부 비어 있다. 이 세션에서 배운 것은 하나다 — **모순은 읽어서가 아니라 실행해서만 나온다.** 예보 스킬은 두 번의 격리 재생성으로 모순 11건이 나왔고, 그중 어느 것도 문서를 눈으로 읽어서는 나오지 않았다. 실제 실험 후로 미루면 제출 전날 밤에 처음 만난다.

**이 태스크는 TDD 사이클이 아니다.** 실행이 곧 검사다. 산출물은 버리고 발견만 남긴다.

- [ ] **Step 1: 합성 기록을 만든다**

`실험01/체크리스트/기록.md` 의 확인 칸을 채운다. 파일 머리의 규칙이 이렇다 — `✓` 일치 / 값 = 불일치 시 실제 관찰값 / 공란 = 미확인 / 표를 통째로 안 했으면 표 아래에 `- 실험을 진행하지 않았음.`

**네 갈래를 전부 태운다:**

- `T1`(3입력 AND) — 8행 전부 `✓`. 정상 경로.
- `T2`(3입력 OR) — 7행 `✓`, `A=0 B=1 C=0` 행의 확인 칸에 `0` (예상 `1` 과 불일치). 고찰 분기.
- `T3`(3입력 NAND) — 4행 `✓`, 나머지 4행 공란. 부분 미확인 분기.
- `T5`(복합 논리회로) — 확인 칸 전부 공란 + 표 아래에 `- 실험을 진행하지 않았음.` 한 줄. 미진행 분기.
- `T4`(3입력 NOR)는 손대지 않는다 — 확인 칸을 전부 공란으로 둔다. (기록.md 에는 `T1`~`T5` 다섯 개만 있다. `T6`~`T9` 는 명세의 `role: reference` 이론표라 기록 대상이 아니다.)

frontmatter 의 `filled_by: ~` 를 `filled_by: hand` 로 바꾼다.

`- 메모:` 줄 중 두 곳에 짧은 관찰을 적는다 (`T2` 아래: `- 메모: 해당 행에서 LED 가 켜지지 않았다. 재확인 필요.`).

- [ ] **Step 2: 결과보고서 스킬을 격리 에이전트로 실행시킨다**

`write-result-report` 를 **fresh 에이전트**로 실행한다(모델 opus, effort high). 브리프에 명시할 것:

- 대상은 `실험01` (2주차).
- **노션에 올리지 않는다** — `sync-report-to-notion` 을 부르지 않는다.
- v6 예비보고서나 이 계획, git 이력을 참조하지 않는다. 스킬 문서와 저장소 자료만 본다.
- 보고서 파일은 스킬이 지시하는 경로에 정상적으로 쓴다.
- **막히거나 판단해야 했던 자리를 전부 기록한다** — 문서가 침묵한 곳, 참조가 어긋난 곳, 지시대로 하면 결과가 틀어지는 곳. 심각도가 아니라 문서 순서로 나열한다.
- 보고서는 `.superpowers/sdd/result-dryrun-report.md` 에 쓰고, 최종 응답으로는 상태·발견 건수·차단 건수만 돌려준다.

- [ ] **Step 3: 산출물을 기계로 확인한다**

에이전트가 끝나면 생성된 보고서에 대해 아래를 돌린다.

```bash
zsh -c 'PYTHONPATH=. python3 -c "
from pathlib import Path
from scripts.lab import config, validate
from scripts.lab.spec_parser import parse_spec
root = config.find_project_root(Path(\".\"))
fmt = config.load_report_format(root)
spec = parse_spec(\"실험01/체크리스트/명세.md\")
p = \"실험01/output/실험01_결과보고서.md\"
out = (validate.check_report_sections(p, fmt.result, item_count=len(spec.items))
       + validate.check_notion_markdown(p))
print(\"\n\".join(str(f) for f in out) or \"문제 없음\")
"'
```

Expected: `✗` 0건. `!`·`ℹ` 는 각각 이유를 적는다.

레이아웃 규칙이 실제로 먹었는지도 센다:

```bash
p=실험01/output/실험01_결과보고서.md
echo "목차   $(grep -c 'table_of_contents' $p)"
echo "여백   $(grep -c 'empty-block' $p)"
echo "쪽번호 $(grep -cE 'p\.[0-9]|p[0-9]+' $p)"
echo "출처블록 $(grep -c '^> 출처:' $p)"
echo "각주   $(grep -cE '\[\^[0-9]+\]' $p)"
echo "ov스팬 $(grep -c 'class=\"ov\"' $p)"
echo "탭표   $(grep -cP '^\t\|' $p)"
```

Expected: 목차 1, 여백 ≥ 헤딩 수, 쪽번호 0, 출처블록 0, 각주 0, ov스팬 0, 탭표 > 0.

- [ ] **Step 4: 산출물을 되돌린다**

```bash
rm -f 실험01/output/실험01_결과보고서.md
git checkout -- 실험01/체크리스트/기록.md
git status --short
```

Expected: `?? 실험01/output/eli5_실험01.html` 한 줄만. (`.superpowers/sdd/` 는 무시된다.)

- [ ] **Step 5: 발견을 분류한다**

`.superpowers/sdd/result-dryrun-report.md` 의 각 발견을 셋으로 나눈다:

- **체계적 결함** (지시와 코드가 어긋남, 죽은 참조, 따를 수 없는 지시) → 지금 고친다.
- **미정의** (문서가 침묵해 에이전트가 판단) → 지금 고친다. 판단이 갈리면 다음 실험에서 다르게 나온다.
- **일회성** (이번 합성 데이터에만 해당) → 고치지 않고 보고서에만 남긴다.

앞의 두 갈래는 각각 아래 순서로 고친다:

1. `tests/test_skill_docs.py` 의 `SkillDocInvariants` 안에 그 결함을 잡는 테스트를 하나 쓴다. 사라지면 안 되는 문장이면 `assertIn`, 되살아나면 안 되는 문장이면 `assertNotIn`, 표의 한 행이면 `startswith("| 이름 |")` 로 그 행만 뽑아 검사한다. 주석에 **왜** 그 문장이 필요한지 한 줄 적는다 — 문자열만 남으면 다음 사람이 지운다.
2. `zsh -c 'PYTHONPATH=. python3 -m unittest tests.test_skill_docs -v 2>&1 | tail -20'` 으로 그 테스트가 실패하는 것을 확인한다.
3. `.claude/skills/write-result-report/SKILL.md` 를 고친다. 규칙 번호를 밀지 않는다 — 새 규칙은 마지막 번호 뒤에 붙인다(현재 절대 규칙 1~17, 실행 절차 0~14).
4. 같은 명령을 다시 돌려 통과를 확인한다.

발견이 0건이면 Step 6 을 건너뛴다 — 커밋할 것이 없다.

- [ ] **Step 6: 고친 것이 있으면 커밋한다**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest discover -s tests -t . 2>&1 | grep -E "^(OK|FAILED|Ran )"'
```

Expected: `OK`, 테스트 수는 342 + 새로 추가한 만큼.

```bash
git add tests/test_skill_docs.py .claude/skills/write-result-report/SKILL.md
git commit -m "docs: 결과보고서 스킬 모의 실행에서 나온 모순 정리"
```

---

## 이 계획 다음 (별도 계획)

Task 6 까지 끝나면 **최종 전체 리뷰 → `main` 머지**다. 리뷰어에게 `.superpowers/sdd/progress.md` 의 미해결 Minor 목록을 함께 넘긴다.

그 뒤는 하네스 *개발*이 아니라 *사용*이라 별도 계획으로 뗀다:

1. **실험02 검문소** — 유일한 계측 주차(오실로스코프·DMM, VTC·히스테리시스·Rn/Rp 계산). 진리표를 전제로 쓰인 규칙이 처음 깨질 자리다. 생성 → 노션 업로드 → 사용자가 직접 수정 → diff 를 규칙으로 환원. `docs/강의노트_이론_실험_매핑_정리.md` 의 확인된 오류 (2)(`t_pd = Δt/2` 는 틀렸고 `Δt/4` 가 맞다)를 그대로 베끼는지 특히 본다.
2. **실험05** — 항목 4개로 §절대 규칙 17(소절 수 파생)의 첫 시험대이고, 매핑 문서 오류 (1)(준비물에 `74HC138`·7-segment 오기재)이 §절대 규칙 16 과 정면으로 만난다.
3. **실험06·10** — 앞의 둘을 통과했으면 연속으로.

**대기 중이지만 막힘은 아니다:** `과목정보.md` 의 `team`·`student_ids`·`student_names` 는 1주차 조 편성 후, `ai_usage_log` 는 강의계획서 §13 관련 조교 안내 후. 확정 전까지 표지는 만들지 않고 예보는 md 까지만 낸다.

**사용자 몫:** 노션에서 v4·v5 와 프로브 페이지 2개를 지운다. 하네스에는 삭제 기능을 넣지 않는다 — 업로드는 append-only 설계다(`scripts/lab/notion.py` 에 덮어쓰기 함수가 없다).

---

## 이 계획이 하지 않는 것

- **`scripts/lab/*.py` 를 고치지 않는다.** `check_report_sections` 는 이미 `item_count` 를 받고, `load_course_info` 는 이미 `None` 을 돌려준다. 어긋난 것은 문서뿐이다.
- **재생성 대조를 따로 돌리지 않는다.** 실험02·05·06·10 생성이 곧 격리 실행이고, 남은 4개가 공짜 테스트 4번이다.
- **분량을 문자 수로 막지 않는다.** 주차마다 정당한 편차가 커서 상한은 거짓 경보를 낸다. §절대 규칙 17 은 소절 **수**를 명세에서 파생시킬 뿐이다.
- **결과보고서에는 소절 수 규칙을 넣지 않는다.** 결과보고서의 섹션 반복은 이미 프리셋의 `repeat: per-item` + `item_count` 로 명세에서 파생된다. 필요한지는 Task 6 의 dry run 이 알려 준다 — 그때 넣는다.
- **9건 중 I 는 고치지 않는다.** §절대 규칙 5 의 예시("`74HC08`·`74HC32` 핀아웃 데이터시트는 저장소에 없다")는 실측 결과 사실이고, `netlist.md` 가 확보한 확신도를 본문에 못 쓰는 것은 §절대 규칙 9 의 의도된 결과다. 결과는 안전한 쪽으로 보수적이다.
