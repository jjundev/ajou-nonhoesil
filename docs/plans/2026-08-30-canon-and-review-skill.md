# 실험01 정본 교체 · 노션 제목 버전 · 검사 스킬 수리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 규칙으로 재생성한 실험01 예비보고서를 정본으로 확정하고, 노션 페이지 제목에 버전을 붙여 잘못된 판본을 제출할 경로를 막고, 검사 스킬 ⑤ 의 확인된 결함 3건을 고친 뒤 회귀 그물을 ⑤ 까지 넓힌다.

**Architecture:** 세 갈래가 서로 독립적이다. (1) 실험01 산출물 교체는 커밋 하나. (2) 노션 제목 버전은 `notion.py` 에 `next_version()` 을 추가하고 ⑦ 이 업로드 **전에** 버전을 계산해 제목에 붙이는 것 — 지금은 `append_record` 가 업로드 **뒤에** 세므로 순서를 뒤집을 수 없어 헬퍼가 필요하다. (3) ⑤ 수리와 그물 확장은 기존 `tests/test_skill_docs.py` 를 문서별 설정 표로 바꿔 ⑤ 를 편입한다. **그물을 나머지 5개 스킬로 넓히지 않는다** — 관례가 달라 오탐이 난다(근거는 Global Constraints 아래).

**Tech Stack:** Python 3.14.6 표준 라이브러리 `unittest`·`urllib.request`·`json`. 마크다운 스킬 문서.

## Global Constraints

- **`pytest` 가 없다.** `unittest` 만 쓴다. 전체 실행은 `zsh -c 'PYTHONPATH=. python3 -m unittest discover -s tests -t .'`.
- **`requests` 가 없다.** `urllib.request` 를 쓴다. 이 계획은 Task 5 를 뺀 어느 태스크에서도 네트워크를 쓰지 않는다.
- **노션 페이지를 덮어쓰는 함수를 만들지 않는다.** 업로드는 append-only 설계다 — 사용자가 노션에서 고쳤지만 아직 되읽히지 않은 구간이 구조적으로 존재한다.
- **토큰은 `NOTION_TOKEN` 환경변수에서만 읽는다.** `.claude/` 는 git 추적 대상이라 거기 두면 저장소에 비밀이 들어간다.
- **비대화형 셸은 `~/.zshrc` 를 읽지 않는다.** 토큰이 필요한 명령은 `zsh -c '...'` 로 감싼다.
- **스킬 문서는 한국어**이고 **76열을 넘기지 않는다**(한글은 2열로 센다). 마크다운 표 행만 예외로 한 줄로 길게 간다.
- **규칙·단계 번호를 밀지 않는다.** 새 항목이 필요하면 마지막 번호 뒤에 붙인다.
- 태스크당 커밋 1개. 커밋 메시지는 한국어, `feat:`·`fix:`·`docs:`·`test:` 접두.
- 직전 테스트는 **352개, `OK`** 다. 어느 태스크에서도 기존 테스트를 깨지 않는다.

### 그물을 8개 스킬 전부로 넓히지 않는 이유 (실측)

기존 검사기를 8개 스킬에 그대로 돌린 결과다. **거짓 경보를 내는 검사는 없느니만 못하다.**

| 스킬 | 결과 | 왜 |
|---|---|---|
| `explain-lab-preview` | 오탐 21건 | `## 0.`~`## 8.` 로 자기 절을 번호 매기고 `§0`~`§8` 로 참조한다. 정상인데 "맨 숫자 §" 규칙에 걸린다 |
| `sync-report-to-notion` | 오탐 7건 | 단계가 `## 실행 절차` 가 아니라 `## push`·`## pull` 절 안에 산다 |
| `review-lab-report` | **진짜 결함** | `## 실행 절차` 를 쓴다 — 표에 한 줄 추가로 편입된다 |
| 나머지 4개 | 참조 없음 | 편입해도 얻는 게 없다 |

---

## File Structure

| 파일 | 책임 | 상태 |
|---|---|---|
| `scripts/lab/notion.py` | 노션 API. `next_version()` 신설, `append_record` 가 그것을 쓰도록, `push_markdown` docstring 정정 | 수정 |
| `tests/test_lab_notion.py` | 위 함수들의 단위 테스트 | 수정 |
| `.claude/skills/sync-report-to-notion/SKILL.md` | ⑦. 업로드 전에 버전을 계산해 제목에 붙인다 | 수정 |
| `.claude/skills/review-lab-report/SKILL.md` | ⑤. 결함 3건 | 수정 |
| `tests/test_skill_docs.py` | 스킬 문서 불변식. 문서별 설정 표로 바꾸고 ⑤ 편입 | 수정 |
| `실험01/output/실험01_예비보고서.md` | 실험01 정본 | 커밋만 |

---

## Task 1: 실험01 정본 교체

**Files:**
- Commit: `실험01/output/실험01_예비보고서.md` (이미 작업 트리에 있다 — 내용을 새로 만들지 않는다)

**Interfaces:**
- Consumes: 없음
- Produces: `HEAD` 의 `실험01/output/실험01_예비보고서.md` 가 13,893 바이트 판본이 된다. Task 5 가 이 파일을 노션에 올린다.

**배경.** 지금 `HEAD` 에 있는 예비보고서는 규칙보다 **먼저** 만들어졌다. 사용자가 노션에서 세 번 고친 것이고, 규칙은 그 뒤에 정비됐다. 고친 규칙만 주고 격리 에이전트에게 다시 쓰게 한 결과가 지금 작업 트리에 있고, 대조 결과 옛 판본이 §절대 규칙 16 을 어긴다는 것이 드러났다 — 준비물 표에 브레드보드·점퍼선·330Ω 저항 행이 없다. 회로를 꽂으려면 반드시 필요한 것들이다. 개념 단위로 대조한 결과 새 판본이 잃은 내용은 **0건**이다.

옛 판본은 `HEAD~`·노션 v6 페이지·스크래치패드 세 곳에 남는다.

- [ ] **Step 1: 바뀐 것이 그 파일 하나뿐인지 확인한다**

```bash
git status --short
```

Expected: `M "실험01/output/실험01_예비보고서.md"` 한 줄만. 다른 줄이 있으면 **멈추고 보고한다** — 이 태스크는 그 파일만 커밋한다.

- [ ] **Step 2: 새 판본이 규칙을 만족하는지 확인한다**

```bash
p=실험01/output/실험01_예비보고서.md
wc -c "$p"
grep -c '^## ' "$p"
grep -c '| 브레드보드' "$p"
grep -c '| 점퍼선' "$p"
grep -cE '^#{3,} ' "$p"
```

Expected: 순서대로 `13893`, `16`, `1`, `1`, `0`.
(`0` 은 §절대 규칙 11 이 금지한 `###` 이하 헤딩이 없다는 뜻이다.)

- [ ] **Step 3: 소절 수가 명세에서 파생되는지 확인한다**

```bash
p=실험01/output/실험01_예비보고서.md
awk '/^# 실험 과정/{f=1;next}/^# /{f=0}f&&/^## /{n++}END{print "과정", n+0}' "$p"
awk '/^# 회로 결선도/{f=1;next}/^# /{f=0}f&&/^## /{n++}END{print "결선", n+0}' "$p"
```

Expected: `과정 3`, `결선 6`. (명세 `items` 3개 + 고정 소절 3개 — §절대 규칙 17.)

- [ ] **Step 4: 검증기를 돌린다**

```bash
zsh -c 'PYTHONPATH=. python3 -c "
from pathlib import Path
from scripts.lab import config, validate
from scripts.lab.spec_parser import parse_spec
root = config.find_project_root(Path(\".\"))
fmt = config.load_report_format(root)
spec = parse_spec(\"실험01/체크리스트/명세.md\")
p = \"실험01/output/실험01_예비보고서.md\"
out = (validate.check_report_sections(p, fmt.pre, item_count=len(spec.items))
       + validate.check_notion_markdown(p))
print(\"\n\".join(str(f) for f in out) or \"문제 없음\")
"'
```

Expected: `ℹ` 한 줄만 — 노션에서 직접 넣어야 할 브레드보드 그림 안내다. `✗` 나 `!` 가 나오면 **멈추고 보고한다.**

- [ ] **Step 5: 커밋**

```bash
git add 실험01/output/실험01_예비보고서.md
git commit -m "docs: 실험01 예비보고서를 고친 규칙으로 재생성한 판본으로 교체"
```

---

## Task 2: 노션 페이지 제목에 버전을 붙인다

**Files:**
- Modify: `scripts/lab/notion.py` — `next_version()` 신설, `append_record` 수정, `push_markdown` docstring 정정
- Modify: `tests/test_lab_notion.py` — `next_version` 테스트 추가
- Modify: `.claude/skills/sync-report-to-notion/SKILL.md` — push 4단계

**Interfaces:**
- Consumes: 기존 `load_records(output_dir) -> list`, `append_record(output_dir, kind, page_id, url, source, when) -> dict`
- Produces: `next_version(output_dir, kind) -> int` — 다음 업로드가 받을 버전 번호. Task 5 의 업로드가 이것을 쓴다.

**배경 — 왜 필요한가.** 지금 노션에 실험01 예비보고서 페이지가 여섯 개 있고 **제목이 전부 같다.** 사용자는 노션 사이드바에서 PDF 를 내보내 제출하는데, 거기엔 `notion.json` 이 보이지 않는다. v5 를 골라 제출해도 어디서도 오류가 나지 않는다 — 이 하네스에서 **조용히 틀린 것을 제출할 수 있는 유일한 경로**다.

**왜 헬퍼가 필요한가.** `append_record` 는 버전을 이렇게 센다:

```python
"version": sum(1 for r in records if r.get("kind") == kind) + 1,
```

그런데 이 함수는 업로드가 **끝난 뒤에** 불린다. 제목에 버전을 넣으려면 업로드 **전에** 같은 수를 알아야 한다. 두 곳에서 같은 식을 따로 쓰면 어긋나므로 헬퍼로 뽑아 둘 다 그것을 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_lab_notion.py` 의 `class TestRecords` 안, `def test_version_은_같은_kind_안에서만_증가한다` **다음에** 아래 세 개를 붙인다. 그 클래스의 `setUp` 은 `self.out = Path(tempfile.mkdtemp())` 를 만든다 — 임시 디렉터리 변수 이름은 `self.out` 이다.

```python
    def test_다음_버전은_이력이_없으면_1이다(self):
        self.assertEqual(notion.next_version(self.out, "예비보고서"), 1)

    def test_다음_버전은_같은_kind_만_센다(self):
        notion.append_record(self.out, "예비보고서", "p1", "u1", "s.md", "t")
        notion.append_record(self.out, "결과보고서", "p2", "u2", "s.md", "t")
        notion.append_record(self.out, "예비보고서", "p3", "u3", "s.md", "t")
        self.assertEqual(notion.next_version(self.out, "예비보고서"), 3)
        self.assertEqual(notion.next_version(self.out, "결과보고서"), 2)

    def test_다음_버전은_append_record_가_붙일_번호와_같다(self):
        # 제목은 업로드 전에, 기록은 업로드 후에 만들어진다. 둘이 어긋나면
        # 페이지 제목의 버전과 notion.json 의 버전이 달라진다.
        notion.append_record(self.out, "예비보고서", "p1", "u1", "s.md", "t")
        expected = notion.next_version(self.out, "예비보고서")
        rec = notion.append_record(self.out, "예비보고서", "p2", "u2", "s.md", "t")
        self.assertEqual(rec["version"], expected)
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest tests.test_lab_notion -v 2>&1 | tail -12'
```

Expected: 새 테스트 3개가 `ERROR` — `AttributeError: module 'scripts.lab.notion' has no attribute 'next_version'`. 기존 테스트는 전부 `ok`.

- [ ] **Step 3: `next_version` 을 만들고 `append_record` 가 그것을 쓰게 한다**

`scripts/lab/notion.py` 에서 `def append_record` 정의 **바로 앞**에 아래를 넣는다 (빈 줄 두 개로 띄운다):

```python
def next_version(output_dir, kind) -> int:
    """다음 업로드가 받을 버전 번호. `append_record` 가 붙일 번호와 같다.

    페이지 제목은 업로드 **전에** 만들어야 하는데 `append_record` 는 업로드
    **뒤에** 불린다. 두 곳에서 같은 식을 따로 쓰면 제목의 버전과 `notion.json`
    의 버전이 어긋나므로, 세는 자리를 여기 하나로 둔다.
    """
    return sum(1 for r in load_records(output_dir) if r.get("kind") == kind) + 1
```

이어서 `append_record` 안의 아래 두 줄을 찾아

```python
    records = load_records(output_dir)
    record = {
        "kind": kind,
        "version": sum(1 for r in records if r.get("kind") == kind) + 1,
```

아래로 바꾼다:

```python
    version = next_version(output_dir, kind)
    records = load_records(output_dir)
    record = {
        "kind": kind,
        "version": version,
```

- [ ] **Step 4: `push_markdown` 의 docstring 을 고친다**

같은 파일에서 `push_markdown` docstring 의 마지막 문단을 찾는다:

```
    제목에 버전 번호는 넣지 않는다 — 몇 번째 업로드인지는 `notion.json` 이 안다.
```

아래로 교체한다:

```
    **제목 끝에 버전을 붙여 넘긴다** (`… 예비보고서 v7`). 사용자는 노션
    사이드바에서 PDF 를 내보내 제출하는데 거기엔 `notion.json` 이 보이지
    않는다. 제목이 전부 같으면 옛 판본을 골라도 아무 데서도 오류가 나지
    않는다. 번호는 `next_version()` 으로 업로드 **전에** 구한다.
```

- [ ] **Step 5: 테스트를 돌려 통과를 확인한다**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest discover -s tests -t . 2>&1 | grep -E "^(OK|FAILED|Ran )"'
```

Expected: `Ran 355 tests`, `OK`. (352 + 3)

- [ ] **Step 6: ⑦ 의 업로드 단계가 버전 붙은 제목을 쓰게 한다**

`.claude/skills/sync-report-to-notion/SKILL.md` 의 push 4단계 코드에서 아래 네 줄을 찾는다:

```
   title = config.document_title(spec.experiment, spec.title, KIND)
```
```
   if body.startswith(f'# {title}\n'):
       body = body[len(f'# {title}\n'):].lstrip('\n')
```
```
   page = notion.push_markdown(body, info['notion_parent_page_id'], token, title=title)
```

각각 아래로 바꾼다. **본문 제목을 떼는 비교는 버전 없는 `title` 로 그대로 둔다** — 본문 첫 헤딩에는 버전이 없기 때문이다:

```
   title = config.document_title(spec.experiment, spec.title, KIND)
   page_title = f"{title} v{notion.next_version(OUT, KIND)}"
```
```
   if body.startswith(f'# {title}\n'):
       body = body[len(f'# {title}\n'):].lstrip('\n')
```
```
   page = notion.push_markdown(body, info['notion_parent_page_id'], token, title=page_title)
```

그리고 그 단계의 출력 줄을 찾아

```
   print('제목', title)
```

아래로 바꾼다:

```
   print('제목', page_title)
```

이어서 그 단계 아래 산문에 한 문단을 더한다 (위치는 `4b.` 단계 **앞**):

```
   **제목 끝의 `v<N>` 은 업로드 전에 `next_version` 으로 구한다.** 사용자는
   노션 사이드바에서 PDF 를 내보내므로 거기서 판본을 구분할 수 있어야 한다.
   본문 첫 헤딩을 떼는 비교에는 버전 없는 `title` 을 그대로 쓴다 — 본문에는
   버전이 없다. 이미 올라간 v1~v6 의 제목은 소급하지 않는다.
```

- [ ] **Step 7: 스킬 문서의 폭과 상호참조를 확인한다**

```bash
python3 -c "
import unicodedata
def w(s): return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in s)
p='.claude/skills/sync-report-to-notion/SKILL.md'
bad=[(i,w(l)) for i,l in enumerate(open(p,encoding='utf-8').read().splitlines(),1)
     if w(l)>78 and not l.startswith('|') and i>5]
print('78열 초과:', bad[:8] or '없음')
"
```

이 파일에는 **이 태스크 이전부터 85~90열인 줄이 약 30개 있다**(push 4b 단계). 새로 넣은 줄이 그 목록에 들어가지 않았는지만 본다 — 위 Step 6 의 교체 텍스트는 76열 안이다.

- [ ] **Step 8: 커밋**

```bash
git add scripts/lab/notion.py tests/test_lab_notion.py .claude/skills/sync-report-to-notion/SKILL.md
git commit -m "feat: 노션 페이지 제목에 버전을 붙인다 — 사이드바에서 옛 판본을 골라도 오류가 없었다"
```

---

## Task 3: 검사 스킬 ⑤ 의 결함 3건

**Files:**
- Modify: `.claude/skills/review-lab-report/SKILL.md` — 3단계 코드, 3b 단계 산문, 5단계 템플릿

**Interfaces:**
- Consumes: 없음
- Produces: ⑤ 가 `check_report_sections` 에 `item_count` 를 넘기게 된다. Task 4 의 테스트가 이것을 검사한다.

**배경.** ⑤ 는 실험02 검증에 바로 쓰이는 스킬인데, 세 곳이 어긋나 있다. 셋 다 컨트롤러가 실측 확인했다.

**(1) `item_count` 미전달 — 이 브랜치가 만든 비대칭이다.** 앞선 계획이 예보·결보의 `check_report_sections` 호출에 `item_count` 를 넣었지만 ⑤ 는 그대로다. 그래서 예보 §실행 절차 9 는 "⑤ 로 검증"이라 하면서 "`item_count` 를 항상 넘긴다"고 하는데, 정작 ⑤ 는 안 넘긴다. `check_report_sections` 는 `item_count is None` 이면 `repeat: per-item` 반복 횟수 검사를 통째로 건너뛴다.

**(2) 3b 단계의 근거가 통째로 낡았다.** "③·④ 는 자기 절차 안에서 이 둘을 부르지만 (8b·11b 단계)" 라고 하는데 — ③ `write-pre-report` 의 단계는 0~11 로 `8b` 가 없고, ④ `write-result-report` 는 0~14(`1b` 포함)로 `11b` 가 없다. **없어진 이유가 있다**: 이 브랜치가 보고서를 `md → html → pdf` 에서 `md → 노션` 으로 바꾸면서 두 스킬의 HTML 단계를 지웠다. 지금 HTML 을 내는 것은 ② `prep-lab-checklist` 뿐이고(4단계), **② 는 `check_rendered_html`·`check_embedded_images` 를 부르지 않는다**(저장소 전체 grep 결과 이 두 함수를 부르는 스킬은 ⑤ 하나다). 즉 3b 는 여전히 필요하고 대상만 체크리스트로 좁혀졌다.

**(3) `§4` 는 이 문서에 없는 표기다.** ⑤ 의 `## ` 절은 `인자`·`실행 절차`·`비-목표` 셋뿐이고 표가 없다. 실제 대상은 **§실행 절차 4**("코드가 못 보는 것을 사람이 본다", 105행)다. 예보 스킬에서 고쳤던 `§3` 과 같은 종류다.

- [ ] **Step 1: 3단계의 검증 코드에 `item_count` 를 넘긴다**

`.claude/skills/review-lab-report/SKILL.md` 의 3단계에서 아래 코드 블록을 찾는다:

````
   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config, validate
   root = config.find_project_root(Path('.'))
   fmt = config.load_report_format(root)
   sections = fmt.pre if '<pre|result>' == 'pre' else fmt.result
   for f in validate.check_report_sections('<보고서 경로>', sections):
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
   sections = fmt.pre if '<pre|result>' == 'pre' else fmt.result
   for f in validate.check_report_sections('<보고서 경로>', sections,
                                            item_count=len(spec.items)):
       print(f)
   "
   ```
````

이어서 그 블록 다음 산문에 한 문단을 더한다:

```
   `item_count=len(spec.items)` 를 항상 넘긴다 — `repeat: per-item` 섹션이
   항목 수만큼 정확히 반복됐는지는 이 인자 없이는 검사되지 않는다. ③·④ 가
   자기 절차 안에서 같은 인자를 넘기므로, 여기서 빠지면 같은 보고서를 두
   기준으로 재는 셈이 된다.
```

- [ ] **Step 2: 3b 단계의 낡은 근거를 고친다**

같은 파일 3b 단계에서 아래 문장을 찾는다:

```
    검사 없이 제출된 적이 있다. ③·④ 는 자기 절차 안에서 이 둘을 부르지만
    (8b·11b 단계), **"☑ 제출 가능" 을 최종으로 쓰는 건 이 스킬이다** — 여기서
    다시 부르지 않으면, ③·④ 밖에서(예: 렌더러를 고친 뒤 수동으로 다시 낸
    HTML) 생긴 같은 결함을 ⑤ 혼자로는 못 잡는다. 대상은 그 주차의 **모든**
    HTML 이다 — 보고서는 `<실험NN>/output/`, 체크리스트는 `<실험NN>/체크리스트/`
    에 있으므로 **두 곳을 다 본다.**
```

아래로 교체한다:

```
    검사 없이 제출된 적이 있다. **이 두 함수를 부르는 스킬은 이제 ⑤ 뿐이다** —
    ③·④ 는 보고서를 노션에 올리는 방식으로 바뀌면서 HTML 을 아예 만들지 않고,
    HTML 을 내는 ② 는 이 검사를 자기 절차에 갖고 있지 않다. 그래서 여기서
    부르지 않으면 아무도 안 부른다. 대상은 그 주차의 HTML **전부**이지만
    실무상 체크리스트뿐이다 — `<실험NN>/체크리스트/` 를 본다. `output/` 에
    HTML 이 남아 있으면 옛 파이프라인의 잔재이므로 함께 검사하고 보고한다.
```

- [ ] **Step 3: `§4` 를 실재하는 표기로 고친다**

같은 파일 5단계의 라운드 문서 템플릿에서 아래 줄을 찾는다:

```
   - (§4 표의 항목 중 해당하는 것)
```

아래로 바꾼다:

```
   - (§실행 절차 4 의 항목 중 해당하는 것)
```

- [ ] **Step 4: 죽은 참조가 없는지 기계로 확인한다**

```bash
zsh -c 'PYTHONPATH=. python3 -c "
import re
from pathlib import Path
from tests.test_skill_docs import sections, numbered_items
t = Path(\".claude/skills/review-lab-report/SKILL.md\").read_text(encoding=\"utf-8\")
steps = numbered_items(sections(t)[\"실행 절차\"])
print(\"실행 절차 번호:\", sorted(steps))
refs = {int(n) for n in re.findall(r\"§?실행 절차 (\d+)\", t)} | {int(n) for n in re.findall(r\"(\d+)단계\", t)}
print(\"참조:\", sorted(refs), \"| 없는 것:\", sorted(refs - steps) or \"없음\")
print(\"맨 숫자 §:\", re.findall(r\"§\d+(?!\.\d)\", t) or \"없음\")
print(\"8b·11b:\", re.findall(r\"\b(?:8b|11b)\b\", t) or \"없음\")
"'
```

Expected: `없는 것: 없음`, `맨 숫자 §: 없음`, `8b·11b: 없음`.
(`실행 절차 번호` 는 `[0, 1, 2, 3, 4, 5, 6]` 이다 — `3b` 는 3 으로 센다.)

- [ ] **Step 5: 줄 폭을 확인한다**

```bash
python3 -c "
import unicodedata
def w(s): return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in s)
p='.claude/skills/review-lab-report/SKILL.md'
bad=[(i,w(l)) for i,l in enumerate(open(p,encoding='utf-8').read().splitlines(),1)
     if w(l)>78 and not l.startswith('|') and i>5]
print('78열 초과:', bad[:8] or '없음')
"
```

Expected: `없음`. 초과가 나오면 그 줄을 다시 감싼다.

- [ ] **Step 6: 전체 테스트를 돌린다**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest discover -s tests -t . 2>&1 | grep -E "^(OK|FAILED|Ran )"'
```

Expected: `Ran 355 tests`, `OK`. (이 태스크는 테스트를 늘리지 않는다 — Task 4 가 붙인다.)

- [ ] **Step 7: 커밋**

```bash
git add .claude/skills/review-lab-report/SKILL.md
git commit -m "fix: ⑤ 가 item_count 를 안 넘겼고, HTML 검사 근거와 §4 참조가 낡았다"
```

---

## Task 4: 회귀 그물을 문서별 설정 표로 바꾸고 ⑤ 를 편입한다

**Files:**
- Modify: `tests/test_skill_docs.py`

**Interfaces:**
- Consumes: Task 3 이 고친 `.claude/skills/review-lab-report/SKILL.md`
- Produces: 모듈 수준 `REVIEW: Path` 와 `DOCS: dict`. 앞으로 문서를 편입할 때는 `DOCS` 에 한 줄만 더한다.

**배경.** 지금 `tests/test_skill_docs.py` 는 예보·결보 **둘만** 본다. ⑤ 의 결함 3건은 실험01 재생성이 사람 손으로 찾은 것이고, 그물이 봤다면 자동으로 걸렸을 종류다. 그런데 나머지 5개 스킬로 통짜 확장하면 오탐이 28건 난다(Global Constraints 아래 표). 그래서 **어느 문서의 번호가 어느 절에 사는지**를 표로 선언하고 검사기가 그 표를 읽게 한다.

`cross_reference_errors` 는 지금 절 이름 `"절대 규칙"`·`"실행 절차"` 를 함수 안에 박아 두고 있다. ⑤ 에는 `## 절대 규칙` 이 없으므로 그대로 두면 `rules` 가 빈 집합이 되고, ⑤ 에 `§절대 규칙 N` 참조가 하나라도 생기는 순간 전부 "없음"으로 잡힌다. 지금은 그런 참조가 없어 우연히 통과하지만 함정이다.

- [ ] **Step 1: 설정 표와 커버리지 테스트를 쓴다**

`tests/test_skill_docs.py` 의 모듈 수준에서 `RESULT = ROOT / ...` 줄을 찾아, 그
**다음에** 아래를 넣는다:

```python
REVIEW = ROOT / ".claude/skills/review-lab-report/SKILL.md"

# 검사 대상 문서와, 그 문서에서 번호 매긴 항목이 사는 절 이름.
#
# 나머지 다섯 스킬은 **일부러 뺐다.** 관례가 달라 통짜로 넣으면 오탐이 난다 —
# `explain-lab-preview` 는 `## 0.`~`## 8.` 로 자기 절을 번호 매기고 `§0`~`§8` 로
# 참조하며(21건), `sync-report-to-notion` 은 단계가 `## 실행 절차` 가 아니라
# `## push`·`## pull` 안에 산다(7건). 거짓 경보를 내는 검사는 없느니만 못하다.
# 편입하려면 그 문서의 절 이름을 여기 한 줄로 선언하면 된다.
DOCS = {
    "예보": (PRE, ("절대 규칙", "실행 절차")),
    "결과": (RESULT, ("절대 규칙", "실행 절차")),
    "리뷰": (REVIEW, ("실행 절차",)),
}

# 보고서를 **쓰는** 두 스킬. 작성 규칙(여백·표 제목·이론 범위 등)은 여기에만 있다.
# ⑤ 는 보고서를 **검사**하는 스킬이라 그 규칙들을 갖지 않는다.
REPORT_DOCS = ("예보", "결과")
```

이어서 `SkillDocInvariants` 클래스 안, 기존 테스트들 **다음에** 하나만 붙인다.
죽은 참조와 번호 연속성은 이미 기존 테스트 둘이 검사하므로 새로 만들지 않는다 —
Step 5 에서 그 둘이 `DOCS` 를 읽게 고친다.

```python
    def test_the_review_skill_is_covered_by_the_net(self):
        # ⑤ 의 결함 3건(item_count 미전달·낡은 HTML 근거·죽은 §4)은 사람이
        # 실험01 을 재생성해서 찾았다. 그물이 봤다면 자동으로 걸렸을 종류다.
        self.assertIn("리뷰", DOCS)
        self.assertIn("리뷰", self.docs)
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest tests.test_skill_docs -v 2>&1 | tail -12'
```

Expected: `test_the_review_skill_is_covered_by_the_net` **하나만** `FAIL` —
`AssertionError: '리뷰' not found in {'예보': ..., '결과': ...}`. `setUp` 이 아직
두 문서만 담기 때문이다. 다른 실패가 나오면 **멈추고 실제 출력을 보고한다.**

- [ ] **Step 3: `cross_reference_errors` 가 절 이름을 인자로 받게 한다**

같은 파일에서 함수 머리와 첫 세 줄을 찾는다:

```python
def cross_reference_errors(text):
    """`§절대 규칙 N`·`§실행 절차 N`·`N단계` 가 실재하는 항목을 가리키는지 본다."""
    sec = sections(text)
    rules = numbered_items(sec.get("절대 규칙", ""))
    steps = numbered_items(sec.get("실행 절차", ""))
```

아래로 교체한다:

```python
def cross_reference_errors(text, titles=("절대 규칙", "실행 절차")):
    """`§절대 규칙 N`·`§실행 절차 N`·`N단계` 가 실재하는 항목을 가리키는지 본다.

    `titles` 는 그 문서에서 번호 매긴 항목이 사는 절 이름이다. 문서마다 다르므로
    함수 안에 박지 않는다 — ⑤ 에는 `## 절대 규칙` 이 없어서, 박아 두면 거기
    `§절대 규칙 N` 참조가 생기는 순간 전부 "없음"으로 잡힌다.
    """
    sec = sections(text)
    rules = numbered_items(sec["절대 규칙"]) if "절대 규칙" in titles else None
    steps = numbered_items(sec["실행 절차"]) if "실행 절차" in titles else None
```

이어서 같은 함수의 세 루프를 찾아

```python
    for token in re.findall(r"§절대 규칙 ([\d·~]+)", text):
        for n in sorted(_expand(token) - rules):
            errors.append(f"§절대 규칙 {n} 없음")
    for token in re.findall(r"§?실행 절차 ([\d·~]+)", text):
        for n in sorted(_expand(token) - steps):
            errors.append(f"실행 절차 {n} 없음")
    for token in re.findall(r"([\d·~]+)단계", text):
        for n in sorted(_expand(token) - steps):
            errors.append(f"{n}단계 없음")
```

아래로 교체한다. **선언하지 않은 절의 참조는 검사하지 않는다** — 그 문서가 그
번호 체계를 안 쓴다는 뜻이므로, 검사하면 오탐이 된다:

```python
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
```

- [ ] **Step 4: `setUp` 이 세 문서를 다 담게 한다**

같은 파일 `SkillDocInvariants.setUp` 에서 아래를 찾는다:

```python
        self.docs = {"예보": PRE.read_text(encoding="utf-8"),
                     "결과": RESULT.read_text(encoding="utf-8")}
```

아래로 교체한다:

```python
        self.docs = {k: p.read_text(encoding="utf-8") for k, (p, _) in DOCS.items()}
```

그 다음 줄의 `self.flat = ...` 은 **그대로 둔다** — `self.docs` 를 훑으므로
자동으로 세 문서를 담는다.

여기서 테스트를 한 번 돌려 **무엇이 깨지는지 눈으로 본다:**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest tests.test_skill_docs 2>&1 | grep -E "^(FAIL|ERROR):" | sort'
```

Expected: 아래 넷이 나온다. 다른 것이 섞이면 **멈추고 보고한다.**

```
ERROR: test_rule_and_step_numbering_is_contiguous ...   ← KeyError: '절대 규칙'
FAIL: test_ai_usage_log_gate_is_written_against_the_parsed_value ...
FAIL: test_heading_levels_are_capped_at_two ...
FAIL: test_sibling_subsection_scope_is_defined ...
```

- [ ] **Step 5: 깨진 넷과 참조 검사 하나를 고친다**

**(5-1) `test_no_dangling_cross_references`** — 새 인자를 넘긴다. 아래를

```python
                self.assertEqual(cross_reference_errors(text), [])
```

아래로 바꾼다:

```python
                self.assertEqual(cross_reference_errors(text, DOCS[name][1]), [])
```

**(5-2) `test_rule_and_step_numbering_is_contiguous`** — 하드코딩한 절 이름을
`DOCS` 에서 읽는다. 메서드 본문을

```python
        for name, text in self.docs.items():
            sec = sections(text)
            for title, first in (("절대 규칙", 1), ("실행 절차", 0)):
                with self.subTest(f"{name}/{title}"):
                    got = numbered_items(sec[title])
                    self.assertEqual(got, set(range(first, max(got) + 1)))
```

아래로 바꾼다:

```python
        for name, text in self.docs.items():
            sec = sections(text)
            for title in DOCS[name][1]:
                first = 0 if title == "실행 절차" else 1
                with self.subTest(f"{name}/{title}"):
                    got = numbered_items(sec[title])
                    self.assertEqual(got, set(range(first, max(got) + 1)))
```

**(5-3) 보고서 작성 규칙 셋을 두 문서로 좁힌다.** 아래 세 메서드의 순회 첫 줄

```python
        for name, text in self.docs.items():
```

을 각각 아래로 바꾸고, 그 위에 이유 주석을 한 줄 붙인다:

```python
        # ⑤ 는 보고서를 검사하는 스킬이라 작성 규칙을 갖지 않는다.
        for name in REPORT_DOCS:
```

대상 셋과, 각 메서드 안에서 `text` 를 쓰던 자리를 바꾸는 법:

| 메서드 | 본문에서 고칠 것 |
|---|---|
| `test_sibling_subsection_scope_is_defined` | 이미 `self.flat[name]` 을 쓴다 — 순회 줄만 바꾼다 |
| `test_heading_levels_are_capped_at_two` | 이미 `self.flat[name]` 을 쓴다 — 순회 줄만 바꾼다 |
| `test_ai_usage_log_gate_is_written_against_the_parsed_value` | 본문의 `text` 두 곳을 `self.docs[name]` 과 `self.flat[name]` 로 바꾼다 (`assertNotIn` 은 원문, `assertIn` 은 flat) |

**(5-4) `test_both_skills_pass_item_count_to_the_section_check` 는 건드리지 않는다.**
Task 3 이 ⑤ 에도 `item_count` 를 넣었으므로 세 문서 다 통과해야 한다. 이름만
`test_every_skill_passes_item_count_to_the_section_check` 로 바꾸고 주석에 한
줄 더한다: `# ⑤ 도 같은 인자를 넘겨야 한다 — 안 그러면 같은 보고서를 두 기준으로 잰다.`
**이 테스트가 실패하면 Task 3 이 덜 된 것이니 멈추고 보고한다.**

- [ ] **Step 6: 테스트를 돌려 통과를 확인한다**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest discover -s tests -t . 2>&1 | grep -E "^(OK|FAILED|Ran )"'
```

Expected: `Ran 356 tests`, `OK`. (355 + 1)

그물이 실제로 ⑤ 를 보는지 확인한다 — ⑤ 의 단계 참조를 일부러 깨뜨려 RED 를 본 뒤
되돌린다:

```bash
sed -i '' 's/§실행 절차 4 의 항목/§실행 절차 99 의 항목/' .claude/skills/review-lab-report/SKILL.md
zsh -c 'PYTHONPATH=. python3 -m unittest tests.test_skill_docs 2>&1 | grep -E "^(OK|FAILED|Ran )"'
sed -i '' 's/§실행 절차 99 의 항목/§실행 절차 4 의 항목/' .claude/skills/review-lab-report/SKILL.md
git diff --stat .claude/skills/review-lab-report/SKILL.md
```

Expected: 가운데 명령이 `FAILED`, 마지막 `git diff --stat` 이 **출력 없음**(되돌아왔다).
되돌아오지 않으면 멈추고 보고한다.

- [ ] **Step 7: 커밋**

```bash
git add tests/test_skill_docs.py
git commit -m "test: 회귀 그물을 문서별 설정 표로 바꾸고 검사 스킬 ⑤ 를 편입"
```

---

## Task 5: 노션 v7 업로드 후 머지

**Files:**
- Modify: `실험01/output/notion.json` (업로드가 자동으로 덧붙인다)
- Create: `실험01/output/실험01_예비보고서_notion_baseline_v7.md` (업로드가 자동으로 만든다)

**Interfaces:**
- Consumes: Task 1 의 정본, Task 2 의 `next_version()` 과 버전 붙은 제목
- Produces: 없음 (마지막 태스크)

**배경.** 이 하네스의 목적은 사용자가 노션에서 실물을 고치고 그 차이를 규칙으로 되돌리는 것이다. 올리지 않으면 루프가 안 닫힌다. **네트워크를 쓰는 유일한 태스크다.**

- [ ] **Step 1: 토큰이 보이는지 확인한다**

```bash
zsh -c 'python3 -c "
import os
t = os.environ.get(\"NOTION_TOKEN\", \"\")
print(\"토큰\", \"있음\" if t.startswith(\"ntn_\") else \"없음 또는 형식 이상\")
"'
```

Expected: `토큰 있음`. `없음` 이면 **멈추고 사용자에게 알린다** — `~/.zshenv` 에 `export NOTION_TOKEN='ntn_...'` 이 필요하다(`~/.zshrc` 가 아니다. 비대화형 셸이 안 읽는다).

- [ ] **Step 2: ⑦ 를 실행해 올린다**

`.claude/skills/sync-report-to-notion/SKILL.md` 의 **push** 절을 읽고 그대로 따른다. 대상은 `실험01`, kind 는 `예비보고서`.

**직접 API 를 부르지 말고 스킬의 절차를 쓴다** — 업로드 전 검사·이력 기록·baseline 뜨기가 그 절차 안에 있고, 이번 실행이 Task 2 가 바꾼 제목 경로의 첫 검증이기도 하다.

- [ ] **Step 3: 제목에 버전이 붙었는지 확인한다**

```bash
python3 -c "
import json
d=json.load(open('실험01/output/notion.json'))
u=d['uploads'][-1]
print('version', u['version'])
print('url', u['url'])
"
```

Expected: `version 7`, 그리고 URL. 그다음 노션에서 그 페이지를 열어 **사이드바 제목이 `실험1 Basic Gates 예비보고서 v7`** 인지 눈으로 확인한다. 제목에 `v7` 이 없으면 Task 2 의 Step 6 이 덜 된 것이니 멈추고 보고한다.

- [ ] **Step 4: 왕복 손실을 확인한다**

⑦ 의 push 5단계(왕복 손실 확인)를 그대로 돌린다. Expected: 손실 보고 없음. `✗` 가 나오면 올린 것과 되읽은 것이 다르다는 뜻이므로 **멈추고 그대로 보고한다.**

- [ ] **Step 5: 커밋**

```bash
git add 실험01/output/notion.json 실험01/output/실험01_예비보고서_notion_baseline_v7.md
git commit -m "chore: 실험01 예비보고서 v7 노션 업로드 기록"
```

- [ ] **Step 6: 전체 테스트와 작업 트리를 확인한다**

```bash
zsh -c 'PYTHONPATH=. python3 -m unittest discover -s tests -t . 2>&1 | grep -E "^(OK|FAILED|Ran )"'
git status --short
```

Expected: `Ran 356 tests` / `OK`, 그리고 `git status` 는 **출력 없음**.

- [ ] **Step 7: main 에 머지한다**

```bash
git checkout main
git merge --no-ff feat/notion-report-loop -m "merge: 노션 보고서 루프 + 스킬 규칙 확정"
zsh -c 'PYTHONPATH=. python3 -m unittest discover -s tests -t . 2>&1 | grep -E "^(OK|FAILED|Ran )"'
```

Expected: 충돌 없이 머지되고 `Ran 356 tests` / `OK`.
**충돌이 나면 멈추고 보고한다** — 이 브랜치는 main 보다 60커밋 이상 앞서 있고 main 은 그동안 움직이지 않은 것으로 보이지만, 확인 없이 해결하지 않는다.

**푸시하지 않는다.** 원격 반영은 사용자가 따로 정한다.

---

## 이 계획 다음 (별도 계획)

**실험02 검문소.** 유일한 계측 주차(오실로스코프·DMM, VTC·히스테리시스·Rn/Rp 계산)라, 진리표를 전제로 쓰인 규칙이 처음 깨질 자리다. 격리 생성 → 노션 업로드 → 사용자가 노션에서 수정 → diff 를 규칙으로 환원 → **실험01 재생성으로 회귀 확인** → 05 → 06·10.

실험02 에서 특별히 볼 것: `docs/강의노트_이론_실험_매핑_정리.md` 의 확인된 오류 — 전파지연 식이 `t_pd = Δt/2` 로 적혀 있는데 실제 체인은 4단이라 **`Δt/4` 가 맞다.** `explain-lab-preview` 에는 경고를 붙였지만 예보 쪽은 실제 실행으로만 확인된다.

**결과보고서 스킬의 계측 주차 대응**은 실험02 예보를 본 뒤 판단한다. 모의 실행은 진리표만 태웠고, 실험02 는 파형·계산값이라 결보가 한 번도 안 겪은 모양이다.

## 대기 중 (막힘 아님)

`.claude/과목정보.md` 의 `team`·`student_ids`·`student_names` 는 1주차 조 편성 후, `ai_usage_log` 는 강의계획서 §13 관련 조교 안내 후. 확정 전까지 표지는 만들지 않고 예보는 md 까지만 낸다.

## 사용자 몫

노션에서 **v4**(`3cbb06d263bc81b28e67ef6da12a73c3`)와 **v5**(`3cbb06d263bc817f8333c9ae027eb57a`)를 지운다. 테스트본이다. **v6 은 Task 5 의 v7 을 확인한 뒤에** 지운다 — 그때까지는 되돌릴 길로 남긴다.

## 이 계획이 하지 않는 것

- **그물을 나머지 5개 스킬로 넓히지 않는다.** 오탐 28건이 실측으로 확인됐다.
- **이미 올라간 v1~v6 의 노션 제목을 소급하지 않는다.** 덮어쓰기 함수가 없고, 만들지 않는 것이 이 모듈의 설계다.
- **원격에 푸시하지 않는다.**
- **`scripts/lab/validate.py` 를 고치지 않는다.** `check_report_sections` 는 이미 `item_count` 를 받는다 — 빠진 것은 ⑤ 의 호출 쪽이다.
