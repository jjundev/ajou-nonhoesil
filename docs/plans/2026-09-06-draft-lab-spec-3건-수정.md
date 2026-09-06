# draft-lab-spec 수정 3건 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `draft-lab-spec` 이 ① 낡은 경로 규약을 "폴더 없음" 으로 오진하지 않게 하고, ② 핀아웃 근거를 어디서 찾는지 알려 주며, ③ 저작 맥락이 없는 fresh 에이전트에게 검토받는 단계를 갖게 한다.

**Architecture:** 셋 다 `.claude/skills/draft-lab-spec/SKILL.md` 한 파일의 산문 수정이다. 코드는 건드리지 않는다. 각 수정은 `tests/test_skill_docs.py` 의 `SkillDocInvariants` 에 회귀 테스트 하나씩을 갖는다 — 이 저장소의 규약은 "규칙은 코드에 있고 테스트가 붙어 있다" 이고, 산문 규칙도 같은 그물로 고정한다. ③ 은 실행 절차에 단계를 하나 끼우므로 기존 9단계(보고)가 10단계가 되고, 문서 안의 `9단계` 참조 한 곳을 같이 고쳐야 한다.

**Tech Stack:** Markdown(스킬 문서) · Python 3.14 + `unittest`(pytest 러너로 실행) · `tests/test_skill_docs.py`

## Global Constraints

- **코드를 바꾸지 않는다.** 이번 변경 대상은 `SKILL.md` 와 `tests/test_skill_docs.py` 둘뿐이다. `scripts/lab/` 아래는 손대지 않는다.
- **`draft-lab-spec` 은 `DOCS` 안에 있다** (`tests/test_skill_docs.py:41`, 키는 `"명세"`, 검사 절은 `("절대 규칙", "실행 절차")`). 따라서 아래 넷이 항상 걸린다.
  - `test_rule_and_step_numbering_is_contiguous` — `실행 절차` 는 **0부터** 연속이어야 한다 (`first = 0`).
  - `test_no_dangling_cross_references` — `N단계` · `§실행 절차 N` · `§절대 규칙 N` 이 실재해야 한다.
  - `test_no_bare_section_number_references` — `§3` 처럼 `§` 뒤에 바로 숫자가 오면 안 된다.
  - `test_no_unchecked_rule_reference_notation` — `§규칙 N` 표기 금지.
- **`numbered_items` 는 줄 맨 앞만 본다** (`^(\d+)[a-z]?\. `). 새 단계는 반드시 **0열에서** `9. **...` 로 시작한다.
- `test_heading_levels_are_capped_at_two` 와 `test_sibling_subsection_scope_is_defined` 는 `REPORT_DOCS = ("예보", "결과")` 에만 걸린다 — **이 문서에는 안 걸린다.** 실제로 7단계가 이미 `###` 를 쓴다.
- **테스트 실행은 venv 로 한다.** Homebrew 파이썬은 PEP 668 로 시스템 설치를 막는다. `requirements-dev.txt` 가 의존성 정본이다.
- 확정된 설계 결정: fresh 에이전트에게 **교안을 주지 않는다**. fresh 검토를 `review-lab-report` 에는 **넣지 않는다**.

---

## File Structure

| 파일 | 책임 | 이번 변경 |
|---|---|---|
| `.claude/skills/draft-lab-spec/SKILL.md` | 명세·결선도 저작 절차 (377줄) | 세 곳 수정 + 단계 재번호. 약 +31줄 |
| `tests/test_skill_docs.py` | 스킬 문서 산문에 씌운 회귀 그물 (약 340줄) | `SkillDocInvariants` 에 테스트 3개 + 모듈 상수 1개 추가 |

새로 만드는 파일은 없다.

**편집 앵커 (현재 줄 번호, 작업 순서대로 바뀌므로 문자열로 찾는다):**

| 앵커 문자열 | 현재 위치 | 쓰는 작업 |
|---|---|---|
| `앞에서부터 실재하는 첫 후보를 연다.` | `SKILL.md:174` | Task 2 (①) |
| `   없으면 거절하고 \`init-lab-experiment\` 를 안내한다 — 폴더를 만들어` | `SKILL.md:163` | Task 2 (①) |
| `   번호·실험 절차가 교안 밖이라는 것이다.` | `SKILL.md:273` | Task 3 (②) |
| `9. **보고한다.**` | `SKILL.md:335` | Task 1 (③) |
| `나란히 스크래치패드에 적고 **어긋난 자리를 전부 표로 남긴다** — 9단계` | `SKILL.md:203` | Task 1 (③, 재번호) |

**작업 순서가 중요하다.** Task 1(③)이 단계 번호를 바꾸므로 먼저 한다. Task 2·3 은 서로 독립이라 순서 무관이지만, Task 1 뒤에 와야 앵커가 안 흔들린다.

---

## Task 1: ③ fresh 검토 단계 추가 + 보고를 10단계로 재번호

**Files:**
- Modify: `.claude/skills/draft-lab-spec/SKILL.md` (203줄 참조 1곳, 335줄에 단계 삽입)
- Test: `tests/test_skill_docs.py` (`SkillDocInvariants` 에 테스트 1개 추가)

**Interfaces:**
- Consumes: 없음 (첫 작업)
- Produces: `실행 절차` 에 **10단계**가 존재한다. Task 2·3 은 단계 번호를 새로 만들지 않으므로 이 사실만 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_skill_docs.py` 의 `class SkillDocInvariants` 안, `test_breadboard_template_path_and_home_are_pinned` **바로 앞**에 추가한다.

```python
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
```

- [ ] **Step 2: 실패를 확인한다**

```bash
.venv/bin/python -m pytest tests/test_skill_docs.py -k fresh_review -q
```

Expected: FAIL — `AssertionError: 10 not found in {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}`

- [ ] **Step 3: 기존 9단계를 10단계로 바꾼다**

`SKILL.md:335` 의 `9. **보고한다.**` 를 `10. **보고한다.**` 로 바꾼다. 본문은 그대로 둔다.

```
10. **보고한다.** 세 목록을 낸다 — 텍스트와 vision 이 어긋난 자리와 어느
```

- [ ] **Step 4: 203줄의 죽은 참조를 고친다**

`SKILL.md:203` 의 `9단계` 를 `10단계` 로 바꾼다. 이 문서 안에서 단계를 가리키는 참조 중 9를 쓰는 곳은 **여기 하나뿐이다** (`grep -n "9단계" 로 확인됨).

```
   나란히 스크래치패드에 적고 **어긋난 자리를 전부 표로 남긴다** — 10단계
   확인 목록의 재료다. 회로도 세부가 안 잡히면 같은 쪽을 900dpi 로 다시
```

- [ ] **Step 5: 새 9단계를 삽입한다**

`8. **진단 문장을 감사한다.**` 문단이 끝난 직후, `10. **보고한다.**` 바로 앞에 넣는다. **`9.` 는 0열에서 시작해야 한다** (`numbered_items` 가 줄 맨 앞만 본다).

```markdown
9. **fresh 에이전트에게 검토받는다.** 지금까지의 저작 맥락이 없는 에이전트에게
   **이번에 쓴 문서만** 건넨다. 저작한 사람은 교안을 여러 번 읽은 뒤라 자기가
   쓴 문서를 읽을 때 **쓴 것이 아니라 의도한 것**을 본다. 그 자리를 메우는
   단계다.

   **교안 경로는 주지 않는다.** 교안을 다시 읽히면 두 번째 재생성이 되어
   비용이 배가 되고, 맥락 없이 문서만으로 앞뒤가 맞는지 보는 이 단계의
   값어치가 사라진다.

   에이전트에게 아래를 준다. **파일 편집을 금지한다**(§절대 규칙 13).

   - 이번에 쓴 파일 경로만. 1단계에서 확정한 대상을 그대로 따른다 —
     `명세만` 이면 명세, `결선도만` 이면 결선도, 인자가 없으면 둘 다.
   - 과제는 다섯이다.
     1. 문서 안에서 앞뒤가 어긋나는 곳 — 산문의 서술과 표의 셀이 다른 자리
     2. 정의 없이 쓰인 셀 토큰·기호
     3. 근거 없이 단정한 문장 — `source` 도 "교안 원문이 아니다" 표시도 없는 것
     4. 미확정이라 말하면서 `# 미확정 사항` 표에 없는 것, 또는 그 반대
     5. 물리적으로 그럴듯하지 않은 값·배선

   **이 검토가 무엇을 못 잡는지 알고 쓴다 — 교안 전사 오류는 못 잡는다.**
   교안을 안 봤으므로 셀이 교안과 다른 것은 원리적으로 볼 수 없다. 그건
   3단계의 이중 판독이 맡는다. 이 한계를 잊으면 "fresh 검토를 통과했으니
   맞다" 는 거짓 안심이 생긴다.

   **지적을 그대로 먹지 않는다.** 하나씩 교안으로 가른다 — 교안이 이기고
   (§절대 규칙 1·3), 지적이 맞으면 고치고 틀리면 왜 틀렸는지를 10단계
   보고에 남긴다. **이 단계는 아무것도 막지 않는다** — 교안을 안 본
   에이전트의 의견이 저작을 막으면 안 된다. 5·7단계의 "error 0 까지 반복"
   과는 층이 다르다.

   에이전트를 쓸 수 없는 환경이면 건너뛰고 **"fresh 검토를 돌리지 못했다"
   를 10단계 보고에 적는다.** 조용히 건너뛰면 안 돌았다는 것을 아무도
   모른다.

```

- [ ] **Step 6: 10단계 보고에 네 번째 목록을 더한다**

`10. **보고한다.** 세 목록을 낸다` 를 아래로 바꾼다.

```
10. **보고한다.** 네 목록을 낸다 — 텍스트와 vision 이 어긋난 자리와 어느
    쪽을 택했는지, 남긴 진단 문장과 방향을 정한 근거, 미확정 항목 전부,
    그리고 9단계 fresh 검토가 낸 지적과 각각의 처리(수용·기각과 그 교안
    근거). 그리고 한 줄을 반드시 붙인다:
```

들여쓰기가 3칸에서 **4칸**으로 늘어난다(`10.` 이 두 자리라서다). 이 단계 본문의 나머지 줄도 전부 4칸으로 맞춘다.

- [ ] **Step 7: 테스트를 돌려 통과를 확인한다**

```bash
.venv/bin/python -m pytest tests/test_skill_docs.py -q
```

Expected: PASS. 특히 `test_rule_and_step_numbering_is_contiguous`(0~10 연속)와 `test_no_dangling_cross_references`(203줄 참조)가 통과해야 한다.

- [ ] **Step 8: 커밋**

```bash
git add .claude/skills/draft-lab-spec/SKILL.md tests/test_skill_docs.py
git commit -m "feat: 저작 맥락 없는 fresh 검토를 9단계로 넣고 보고를 10단계로 민다"
```

---

## Task 2: ① 1단계 경로 가드

**Files:**
- Modify: `.claude/skills/draft-lab-spec/SKILL.md` (1단계, 폴더 거절 문장 앞)
- Test: `tests/test_skill_docs.py`

**Interfaces:**
- Consumes: 없음. **Task 1 과 기능적 의존이 없다** — 이 작업은 1단계 산문만 건드리고 단계 번호를 만들지도 가리키지도 않는다. Task 1 뒤에 두는 이유는 오직 앵커의 줄 번호가 안 흔들리게 하려는 것이다.
- Produces: 없음 (문서 산문만)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`SkillDocInvariants` 안, Task 1 에서 추가한 테스트 바로 뒤에 넣는다.

```python
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
```

- [ ] **Step 2: 실패를 확인한다**

```bash
.venv/bin/python -m pytest tests/test_skill_docs.py -k folder_guard -q
```

Expected: FAIL — `AssertionError: 경로 가드 문장이 없다`

- [ ] **Step 3: 가드를 넣는다**

1단계에서 `없으면 거절하고 \`init-lab-experiment\` 를 안내한다 — 폴더를 만들어 주지 않는다.` 문단 **바로 앞**에 넣는다.

```markdown
   **거절하기 전에 경로 규약이 낡지 않았는지 본다.** `config` 가 준 경로에
   폴더가 없다고 곧바로 거절하면, 폴더가 **다른 자리에 멀쩡히 있는데**
   `config` 만 안 따라온 경우를 "폴더 없음" 으로 오진한다. 2026-09 에 실험
   폴더가 루트에서 `보고서/` 아래로 옮겨졌을 때 실제로 이렇게 틀렸다.

   ```bash
   find . -maxdepth 3 -type d -name "<실험NN 의 폴더 이름>" -not -path "./.git/*"
   ```

   여기서 나오면 폴더가 없는 게 아니라 **`config` 가 낡은 것이다.** 그
   사실을 보고하고 멈춘다 — 찾은 경로로 **우회하지 않는다.** `config` 를
   아홉 스킬이 공유하므로, 우회하면 나머지 여덟이 같은 실패를 되풀이한다.
   교안 후보가 둘 다 없을 때도 같은 이유로 한 번 확인한다.

```

- [ ] **Step 4: 통과를 확인한다**

```bash
.venv/bin/python -m pytest tests/test_skill_docs.py -q
```

Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/draft-lab-spec/SKILL.md tests/test_skill_docs.py
git commit -m "fix: 폴더 부재를 거절로 잇기 전에 경로 규약이 낡았는지 본다"
```

---

## Task 3: ② 6단계 핀아웃 근거 위치

**Files:**
- Modify: `.claude/skills/draft-lab-spec/SKILL.md` (6단계 끝)
- Test: `tests/test_skill_docs.py` (모듈 상수 1개 + 테스트 1개)

**Interfaces:**
- Consumes: 없음. **Task 1 과 기능적 의존이 없다** — 6단계 산문만 건드린다. Task 1 뒤에 두는 이유는 앵커의 줄 번호 안정성뿐이다.
- Produces: 모듈 상수 `DATASHEET_DIR`(`tests/test_skill_docs.py`). 이후 이 상수를 쓰는 작업은 없다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

먼저 모듈 상수를 `DOCS` 정의 **바로 뒤**에 추가한다.

```python
# 핀아웃 근거가 실제로 사는 곳. 경로를 문서에만 두면 폴더가 옮겨졌을 때
# 문서가 조용히 거짓말을 한다 — `Breadboard.jpg` 가 정확히 그렇게 깨졌다.
DATASHEET_DIR = "from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃"
```

그리고 `SkillDocInvariants` 안, Task 2 의 테스트 뒤에 넣는다.

```python
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
```

- [ ] **Step 2: 실패를 확인한다**

```bash
.venv/bin/python -m pytest tests/test_skill_docs.py -k pinout_evidence -q
```

Expected: FAIL — `AssertionError: 'from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃' not found in ...`

- [ ] **Step 3: 6단계에 안내를 넣는다**

6단계 본문 맨 끝(`번호·실험 절차가 교안 밖이라는 것이다.` 문단 뒤, `7. **결선도를 검증한다.**` 앞)에 넣는다.

```markdown
   **핀아웃 근거는 교안 밖에도 있다.** 교안에 핀아웃 쪽이 없다고 곧바로
   "표준 배치 가정" 으로 적지 않는다. 두 자리를 먼저 본다 —
   `from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃/`
   의 실물 데이터시트·핀아웃 그림, 그리고 **다른 주차 교안의 회로도**다
   (실험1 의 `74HC00` 은 실험6 교안 p7·p8 회로도가 게이트 핀을 라벨해 둔
   것으로 확인된다). 어느 칩이 확인됐고 어느 칩이 가정인지를 `# 핀아웃
   출처` 에서 등급으로 갈라 적고, **가정인 것만** 미확정 표에 올린다.

```

- [ ] **Step 4: 통과를 확인한다**

```bash
.venv/bin/python -m pytest tests/test_skill_docs.py -q
```

Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add .claude/skills/draft-lab-spec/SKILL.md tests/test_skill_docs.py
git commit -m "docs: 핀아웃 근거를 어디서 찾는지 6단계에 적는다"
```

---

## 테스트 계획

### 1. 새로 추가하는 회귀 테스트 (3개)

전부 `tests/test_skill_docs.py::SkillDocInvariants` 에 들어간다. 이 저장소의 규약은 "산문 규칙도 그물로 고정한다" 이고, 세 테스트는 각각 **이번에 실측한 결함 하나씩**을 막는다.

| 테스트 | 막는 결함 | 실측 근거 |
|---|---|---|
| `test_the_fresh_review_step_withholds_the_manual` | 단계가 사라지거나, 교안을 주도록 바뀌거나, "못 잡는 것" 경고가 지워지는 것 | 설계 결정 — 교안을 주면 두 번째 재생성 |
| `test_the_folder_guard_precedes_the_refusal` | 가드가 지워지거나 거절 **뒤로** 밀리는 것 | 2026-09 `보고서/` 이동 때 실제 오진 |
| `test_pinout_evidence_locations_are_pinned` | 경로가 지워지는 것 **그리고** 폴더가 실제로 없어지는 것 | 실험01 재생성본 M1 이 승인본보다 근거가 약했다 |

세 번째는 문서 문자열과 **디스크 상태를 함께** 본다. 문서만 검사하면 폴더가 옮겨졌을 때 문서가 조용히 거짓말을 한다 — `Breadboard.jpg` 가 정확히 그렇게 깨졌다.

### 2. 이미 있고 이번 변경에 반드시 걸리는 검사 (4개)

Task 1 의 재번호가 이 넷을 통과해야 한다. **새로 쓸 필요는 없다 — 이미 그물에 있다.**

| 검사 | 이번에 무엇을 잡나 |
|---|---|
| `test_rule_and_step_numbering_is_contiguous` | 9를 넣고 10으로 안 밀면 번호가 비거나 겹친다 |
| `test_no_dangling_cross_references` | 203줄의 `9단계` 를 안 고치면 죽은 참조가 된다 |
| `test_no_bare_section_number_references` | 새 산문이 `§9` 같은 표기를 쓰면 잡힌다 |
| `test_no_unchecked_rule_reference_notation` | 새 산문이 `§규칙 1` 로 쓰면 잡힌다 |

새 9단계 산문이 쓰는 참조는 `3단계` · `5·7단계` · `10단계` · `1단계` · `§절대 규칙 1·3` · `§절대 규칙 13` 이다. 전부 실재한다.

### 3. 실행 명령

작업마다:

```bash
.venv/bin/python -m pytest tests/test_skill_docs.py -q
```

세 작업이 끝난 뒤 전체:

```bash
.venv/bin/python -m pytest tests/ -q
```

Expected: **`550 passed` → `553 passed`**, 실패 0. `351 subtests` 는 그대로다 — 새 테스트 셋은 `subTest` 를 쓰지 않는다.

기준선 `550 / 351` 은 착수 시점(`main` @ `53e3667`)에 실측한 값이다. 계획을 처음 쓸 때 적었던 `477 / 231` 은 그사이 `main` 이 회로 단위 인쇄본 재설계를 흡수하면서 낡았다 — **실행 전에 기준선을 다시 재고 시작한다.**

venv 가 없으면 먼저:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
```

### 4. 자동 검사가 못 보는 것 — 손으로 한 번

그물은 **문자열이 있는지**만 본다. 아래 셋은 사람이 눈으로 본다.

- **새 9단계가 실제로 8단계와 10단계 사이에 있는가.** `numbered_items` 는 집합이라 순서를 안 본다. `grep -nE "^[0-9]+\. \*\*" SKILL.md` 로 줄 번호가 오름차순인지 확인한다.
- **10단계 본문의 들여쓰기가 4칸으로 맞았는가.** `10.` 이 두 자리라 3칸이면 마크다운이 어긋난다.
- **`find` 명령의 `-name` 자리에 무엇을 넣으라는 건지 읽고 알 수 있는가.** `<실험NN 의 폴더 이름>` 은 `config.experiment_folder_name()` 의 출력(`실험01`)이지 경로(`보고서/실험01`)가 아니다.

### 5. 회귀 위험과 완화

| 위험 | 완화 |
|---|---|
| 다른 스킬 문서가 draft-lab-spec 의 단계 번호를 가리킨다 | 확인함 — `sync-report-to-notion:122` 와 `write-result-report:93` 의 `9단계` 는 **자기 문서의** 9단계다. `cross_reference_errors` 가 문서별로 돌므로 영향 없다 |
| `docs/schema/lab-spec-v1.md` 가 단계를 가리킨다 | 확인함 — `grep -rn "9단계" docs/schema/` 결과 없음 |
| 문서가 408줄로 늘어 읽기 부담 | 세 수정 모두 기존 단계 **안에** 넣는다. 새 절대 규칙을 만들지 않는다 — 규칙 13개는 그대로다 |

---

## Self-Review

**Spec coverage:** grill-yourself 결정표 16건 중 이 계획이 다루는 것 — #1·#2(Task 1 배치·재번호), #3·#4·#5·#6·#7·#8·#9·#10(Task 1 본문), #11·#12·#13(Task 2), #14·#15(Task 3), #16(테스트 계획 §2). needs-you A·B 는 사용자 확인으로 닫혔고 권장값이 반영됐다. 빠진 결정 없음.

**Placeholder scan:** 모든 편집이 실제 마크다운 본문을 담고 있다. 테스트는 실행 가능한 파이썬이다. "적절히 처리한다" 류 없음.

**Type consistency:** 테스트 셋이 쓰는 헬퍼는 전부 기존 것이다 — `self.docs`/`self.flat`(`setUp`, `:218`), `sections`(`:56`), `numbered_items`(`:65`), `ROOT`(`:18` 부근). 새로 만드는 이름은 모듈 상수 `DATASHEET_DIR` 하나뿐이고 Task 3 안에서 정의·사용된다.

---

## Execution Handoff

이 계획은 아직 실행되지 않았다. 실행은 별도 턴이다.
