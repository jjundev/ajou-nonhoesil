# Logic Lab Review Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 실험 프리뷰를 기초 설명과 전수 기출 풀이를 제공하는 실험별 HTML·MD 학습팩 스킬로 대체한다.

**Architecture:** 스킬이 자료 판독·교수 설계·풀이를 담당하고, 작은 Python 모듈이 자료 목록·manifest·조립·MD 변환·검사·안전한 저장을 담당한다. 기존 config·부울식 평가기를 재사용한다. 생명과학 변환기의 유용한 부분을 독립적으로 이식하되 날짜·객관식 중심 가정은 제거한다.

**Tech Stack:** 기존 Python 환경과 표준 라이브러리, 저장소 pytest/pytest-xdist, PDF 판독용 기존 PyMuPDF·Pillow, 정적 HTML/CSS/JavaScript, 로컬 MathML/SVG. 신규 런타임 패키지나 프런트엔드 빌드 시스템은 도입하지 않는다.

**Spec:** [논리회로실험 학습팩 설계](../specs/2026-09-29-logic-lab-review-pack-design.md). 실행자는 이 문서와 설계를 모두 읽는다. #10·#11은 사용자 응답 규칙에 의해 기본값 확정이며, 구현 실행 방식은 아직 미선택이다.

## Global Constraints

- 설명 수준은 기초부터 충분히 설명하는 완전판이며, 맨 앞에 짧은 복습 요약을 둔다.
- 판독 가능한 고유 기출 전체를 수록하고, 예상문제는 기출이 다루지 못한 개념만 보충한다.
- 실험 설명과 기출 풀이를 각각 HTML·MD로 생성한다.
- 현재 교안과 과거 판본을 구분하고, 실험 수행 범위와 시험 범위를 별도로 관리한다.
- 원문·보고서·측정 기록·결선도는 읽기만 하며, 기존 프리뷰 산출물은 보존한다.
- HTML은 로컬 자원만으로 동작하며, 위젯에는 MD용 정적 표·그림·설명을 제공한다.
- HTML과 MD는 같은 저작 내용에서 생성하며, MD의 풀이·수식·그림·출처를 누락하지 않는다.
- 독립 검토를 수행하지 않았으면 블라인드 검증 완료라고 표시하지 않는다.
- Windows와 macOS 경로를 지원하고, 실험 번호는 실험01~실험10 형식으로 출력한다.
- 실패한 초안으로 기존 검증된 팩을 교체하지 않는다.

## Review Focus

1. NFD 한글·공백·괄호가 들어간 경로: 실제 파일을 찾고 링크가 유지되어야 한다. Task 1 경로 fixture, Task 4 링크 테스트.
2. 같은 문제의 다른 정답지 또는 회로 조건 변경: 출처만 합치거나 별도 문항으로 보존하고 충돌을 숨기지 않아야 한다. Task 2 충돌 fixture.
3. 초기 상태가 없는 순서회로 및 active-low 신호: 임의로 0을 채워 검증 완료로 만들지 않아야 한다. Task 5 내용 검토 사례.
4. HTML에서는 접힌 풀이·수식·위젯이 MD에서 사라지는 경우: 모든 교육 내용을 정적 형태로 보존해야 한다. Task 4 round-trip fixture.
5. 재생성 중 실패 또는 원문 변경: 기존 팩과 사용자 추가 파일을 보존하고 검증 상태를 갱신해야 한다. Task 6 rollback 테스트.

---

## 실행 전 맥락과 파일 지도

현재 `scripts/lab/config.py:41,62,146,272,303,318`은 폴더명·보고서 경로·교안 후보·주차·다음 일정·수행 범위를 제공한다. `next_experiments()`는 `(date, list[int])` 또는 None이다. `scripts/lab/boolexpr.py`의 `eval_boolean(text, env)`와 `variables(text)`는 명시적인 `·`, `+`, `⊕`, 후위 `'`를 처리하며 숫자 상수 구문은 지원하지 않는다. 새 스킬이 이를 범용 회로 시뮬레이터로 확장하지 않는다.

실행 시작 때 git 상태를 기록하고 필요하면 using-git-worktrees로 격리한다. 계획 작성 시 작업 트리는 깨끗했다. 실제 작업 시 상태를 다시 확인한다. baseline은 `python -m pytest -n0 tests/test_lab_config.py tests/test_lab_validate.py tests/test_skill_docs.py -q`로 기록한다. 기존 Windows 환경 실패가 있으면 새 변경으로 인한 실패와 구분한다. 아래 python은 실행 환경에서 확인한 Python 실행 파일을 뜻한다.

| 경로 | 책임 |
|---|---|
| `.claude/skills/logic-lab-review-pack/SKILL.md` | 사용자 요청 해석·단계 실행·완료 보고 |
| 같은 폴더 `references/{sources,authoring,verification,format}.md` | 자료 분류·교육·검토·저작 계약 |
| 같은 폴더 `assets/{page.html,style.css,widgets.js}` | 정적 UI와 선택적 위젯 |
| `scripts/lab/review_pack/__init__.py` | 패키지 표식 |
| 같은 패키지 `sources.py` | 대상·자료 탐색, 해시 |
| 같은 패키지 `manifest.py` | JSON 계약과 참조 검증 |
| 같은 패키지 `render.py` | HTML 조립·출처 목록 |
| 같은 패키지 `html2md.py` | 독립적인 HTML→MD 변환 |
| 같은 패키지 `checks.py` | 산출물 연결·내용 보존·부울식 검산 |
| 같은 패키지 `publish.py` | 검증 후 교체·백업·rollback |
| 같은 패키지 `__main__.py` | CLI 진입점 |
| `tests/test_review_pack_{sources,manifest,render,md,checks,publish}.py` | 기능 단위 행동 테스트 |
| `tests/fixtures/review_pack/` | 최소 팩·타이밍·계산 검토 사례 |
| `.claude/skills/explain-lab-preview/SKILL.md` | 기존 명령 호환 안내 |
| `.claude/skills/{init-lab-experiment,write-pre-report,review-lab-report,verify-draft-lab-spec}/SKILL.md` | 구 프리뷰 설명·경로 참조 정리 |
| `tests/test_lab_validate.py`, `tests/test_skill_docs.py` | 구 템플릿 설명의 의미를 보존하며 갱신 |
| `복습노트/실험04/` | 실제 첫 사용 결과 |

새 public API의 실패는 ValueError(잘못된 입력·계약) 또는 OSError(파일 I/O)로 표현한다. 자동 검사의 finding은 `list[str]`이다. 빈 목록은 그 검사의 통과이며 내용 정확성이나 사용자 학습 완료를 뜻하지 않는다.

## Task 1: 보고서 초기화 없이 실험과 자료 찾기

**Files:** Create `scripts/lab/review_pack/__init__.py`, `sources.py`; Test `tests/test_review_pack_sources.py`.

**Interfaces:** `resolve_experiments(*, numbers: list[int] | None = None, week: int | None = None, today: date | None = None) -> list[int]`; `inventory(root: Path, experiment: int) -> dict`; `file_sha256(path: Path) -> str`.
inventory 반환: `experiment`, `manual`(source record 또는 None), `sources`(source record 목록), `scope_tokens`(기존 함수 값). source record: `id`, `path`(root 상대 POSIX), `sha256`, `kind`(manual/quiz/theory/report/record/datasheet/stt/notice), `edition`(current/archive/unknown). ID는 최초 정규화 상대 경로의 SHA256 앞 16자리, 파일 내용 해시는 별도. 기존 manifest에 같은 자료 경로가 있으면 그 ID를 유지한다.

- [ ] **1. 행동 테스트를 작성한다.**

```python
from datetime import date
from pathlib import Path
import unicodedata
from scripts.lab.review_pack.sources import inventory, resolve_experiments

def test_same_day_returns_both():
    assert resolve_experiments(today=date(2026, 9, 18)) == [2, 3]

def test_archive_without_report_folder(tmp_path):
    p = tmp_path / 'from_the_past/정리/강의노트/실험4.pdf'
    p.parent.mkdir(parents=True)
    p.write_bytes(b'fixture')
    got = inventory(tmp_path, 4)
    assert got['manual']['edition'] == 'archive'
    assert not (tmp_path / '보고서').exists()

def test_unicode_quiz_path(tmp_path):
    folder = tmp_path / 'from_the_past/정리/퀴즈/실험4'
    folder.mkdir(parents=True)
    p = folder / unicodedata.normalize('NFD', '기출 (1).pdf')
    p.write_bytes(b'fixture')
    rows = inventory(tmp_path, 4)['sources']
    assert any((tmp_path / row['path']).is_file() for row in rows)
```

- [ ] **2. `python -m pytest -n0 tests/test_review_pack_sources.py -q`를 실행한다.** 새 모듈이 없어서 collection 실패가 나오는 것을 확인한다.
- [ ] **3. 대상 결정과 파일 목록화를 구현한다.**

```python
def resolve_experiments(*, numbers=None, week=None, today=None):
    if numbers is not None and week is not None:
        raise ValueError('실험 번호와 주차를 동시에 지정할 수 없습니다')
    if numbers is not None:
        result = sorted(set(numbers))
    elif week is not None:
        result = config.experiments_in_week(week)
    else:
        upcoming = config.next_experiments(today)
        result = upcoming[1] if upcoming else []
    for number in result:
        config.experiment_folder_name(number)
    return result
```

sources.py에서 config를 import한다. bool 번호는 set으로 변환하기 전에 config.experiment_folder_name으로 검증한다. inventory는 config.manual_candidates(experiment, root=root) 후보 중 실제 파일을 선택한다. 후보가 상대 경로면 root에 결합한다. 퀴즈는 해당 실험 폴더를 재귀 순회하되 실행 파일은 읽지 않는다. 이론·데이터시트·공지 목록은 경로만 제공하고 관련 페이지 선별은 스킬이 한다. 보고서·명세·기록·netlist·STT는 config.experiment_dir로 찾되 없으면 빈 목록이다. 정규화는 비교에만 사용하고 반환 path는 실제 디스크 철자를 보존한다. PDF 내용 판독은 이 모듈에서 하지 않는다.

```python
def file_sha256(path):
    import hashlib
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
```

- [ ] **4. 같은 테스트를 다시 실행하고 현재 교안 우선·잘못된 번호·학기 종료 사례도 추가 실행한다.** 현재 교안과 archive를 함께 만들면 current가 선택되어야 한다. `numbers=[True]`와 `[11]`은 예외, `today=date(2027,1,1)`은 빈 목록이다.
- [ ] **5. 커밋한다.** `git add scripts/lab/review_pack tests/test_review_pack_sources.py` 후 `git commit -m "feat: discover review pack sources"`.

## Task 2: 출처·문항·개념의 보존 계약

**Files:** Create `scripts/lab/review_pack/manifest.py`, `tests/test_review_pack_manifest.py`, `tests/fixtures/review_pack/manifest.json`, `.claude/skills/logic-lab-review-pack/references/format.md`.

**Interfaces:** `validate_manifest(data: dict) -> list[str]`; `load_manifest(path: Path) -> dict`(invalid는 ValueError); `output_names(experiment: int) -> dict[str,str]`(note_html,review_html,note_md,review_md). Task 1 source record를 소비한다.

- [ ] **1. 최소 유효 fixture와 오류 테스트를 작성한다.** 다음 JSON을 fixture에 저장한다.

```json
{"schema_version":1,"experiment":4,"title":"MUX","edition_status":"current","sources":[{"id":"s1","path":"강의노트/실험4.pdf","sha256":"0000000000000000000000000000000000000000000000000000000000000000","kind":"manual","edition":"current"}],"topics":[{"id":"t-mux","title":"선택 신호","requires":[],"sources":[{"source_id":"s1","pdf_page":1,"printed_page":null}],"fragment":"sections/t-mux.html"}],"problems":[{"id":"q-mux-001","kind":"practice","status":"included","reason":"선택선 적용 연습","topics":["t-mux"],"sources":[],"duplicate_of":null,"scope":"current","given_answer":null,"derived_answer":"I0","answer_status":"verified","fragment":"problems/q-mux-001.html"}],"checks":{"source_visual":"not_run","content":"not_run","independent":"not_run","browser":"not_run"}}
```

```python
import copy, json
from pathlib import Path
from scripts.lab.review_pack.manifest import validate_manifest

def test_past_question_needs_location():
    m = json.loads(Path('tests/fixtures/review_pack/manifest.json').read_text(encoding='utf-8'))
    m['problems'][0]['kind'] = 'past'
    assert any('source' in error for error in validate_manifest(m))

def test_conflicting_answer_is_not_silently_verified():
    m = json.loads(Path('tests/fixtures/review_pack/manifest.json').read_text(encoding='utf-8'))
    m['problems'][0].update(given_answer='I1', answer_status='disputed')
    assert validate_manifest(m) == []
    assert m['problems'][0]['given_answer'] != m['problems'][0]['derived_answer']
```

- [ ] **2. `python -m pytest -n0 tests/test_review_pack_manifest.py -q`를 실행하고 새 모듈 import 실패를 확인한다.**
- [ ] **3. manifest 검사와 파일명 함수를 구현한다.**

```python
def output_names(experiment):
    base = config.experiment_folder_name(experiment)
    return {'note_html': f'{base}_실험설명.html',
            'review_html': f'{base}_기출풀이.html',
            'note_md': f'{base}_실험설명.md',
            'review_md': f'{base}_기출풀이.md'}

def load_manifest(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    errors = validate_manifest(data)
    if errors:
        raise ValueError('\n'.join(errors))
    return data
```

검사: schema_version=1, 실험1~10, ID 전역 유일, topics.requires 참조 존재·cycle 금지, 문항 topics 참조 존재, 포함 문항 fragment 존재 선언, fragment 상대 경로·`..` 금지. kind는 past/unknown/predicted/practice, status는 included/duplicate/held/other_experiment, scope는 current/supplement/unknown, answer_status는 verified/disputed/unresolved. duplicate는 유효 대상 ID와 이유 필수이고 자기참조·cycle 금지. 기출·예상·미확인 문항은 source_id와 양의 pdf_page(이미지 원문은 null 허용)가 필요하다. practice만 출처 없이 허용한다. printed_page는 문자열 또는 null이다. 비포함 문항에는 이유가 필수다. disputed/unresolved 문항은 읽을 수 있으나 확정 정답 배지를 금지한다. checks 값은 pass/fail/not_run/self_review이며 independent=self_review는 독립 검토 통과가 아니다. 정답의 문자열 차이만으로 논리적 오류라고 단정하지 않는다.

- [ ] **4. 사용자 지정 위치에 format.md를 작성한다.** `.claude/skills/logic-lab-review-pack/`를 사용하며 `.gitignore`는 변경하지 않는다.

format.md에 위 필드·enum·경로 규약과 안정 ID 규칙을 기록한다. 재생성 시 기존 source·problem ID를 먼저 읽어 재사용하며, 문항 순서로 ID를 만들지 않는다. 조건 변경 문항은 새 ID를 발급한다.
- [ ] **5. 테스트를 실행하고 추가 fixture로 dangling topic, 중복 ID, duplicate cycle, 보류 이유 없음, 잘못된 페이지를 검사한다.** 또한 조건이 다른 두 문항을 별도 ID로 유지한 manifest가 통과하는지 확인한다.
- [ ] **6. 커밋한다.** `git add .claude/skills/logic-lab-review-pack/references/format.md scripts/lab/review_pack/manifest.py tests/test_review_pack_manifest.py tests/fixtures/review_pack/manifest.json` 후 `git commit -m "feat: define review pack content contract"`.

## Task 3: 읽을 수 있는 두 HTML과 출처 목록

**Files:** Create `render.py`, skill `assets/page.html`, `assets/style.css`, `assets/widgets.js`, `tests/test_review_pack_render.py`, fixture `sections/t-mux.html`, `problems/q-mux-001.html`.

**Interfaces:** `assemble(manifest: dict, run: Path, out: Path, assets: Path) -> dict[str,Path]`. Task 2 manifest를 소비하고 note_html/review_html/manifest/audit 경로를 반환한다. out은 임시 stage이며 기존 최종 폴더를 받지 않는다.

- [ ] **1. 교육 내용이 실제로 보존되는 fixture와 테스트를 작성한다.**

```html
<!-- sections/t-mux.html -->
<p>여러 입력 중 하나를 출력으로 보냅니다.</p>
<p data-content-id="mux-example">선택선이 0이면 I0가 출력됩니다.</p>
<a href="{{REVIEW_HREF}}#q-mux-001">적용 문제</a>
```

```html
<!-- problems/q-mux-001.html -->
<p>선택선이 0일 때 어느 입력이 출력됩니까?</p>
<a href="{{NOTE_HREF}}#t-mux">필요한 개념</a>
<details><summary>힌트</summary><p>선택선과 입력 번호를 연결하세요.</p></details>
<details><summary>풀이</summary><p data-content-id="mux-answer">I0입니다.</p></details>
```

```python
def test_assemble_keeps_solution_and_links(tmp_path):
    import json
    from pathlib import Path
    from scripts.lab.review_pack.render import assemble
    root = Path('tests/fixtures/review_pack')
    m = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    paths = assemble(m, root, tmp_path / 'stage', Path('.claude/skills/logic-lab-review-pack/assets'))
    review = paths['review_html'].read_text(encoding='utf-8')
    assert 'I0입니다.' in review
    assert '실험04_실험설명.html#t-mux' in review
    assert '예상' not in review or '연습' in review
    assert paths['audit'].is_file()
```

- [ ] **2. `python -m pytest -n0 tests/test_review_pack_render.py -q`로 실패를 확인한다.**
- [ ] **3. 조립기를 구현한다.** 제목·경로·manifest 텍스트는 html.escape로 escape한다. 저작 fragment만 HTML로 취급하며 script 삽입은 금지하고 공통 widgets.js만 허용한다. 각 topic/problem을 `<article id="...">`로 감싼다. note는 요약·개념·실험 설명, review는 포함 문항과 보류 목록을 표시한다. 문제가 0개면 자료 없음 문구를 출력한다. 출처 목록은 모든 문항의 분류·이유·위치·답안 상태를 포함한다.

```python
def read_fragment(run, relative, names):
    candidate = (run / relative).resolve()
    if not candidate.is_relative_to(run.resolve()):
        raise ValueError('fragment 경로가 작업 폴더를 벗어납니다')
    text = candidate.read_text(encoding='utf-8')
    return text.replace('{{NOTE_HREF}}', names['note_html']).replace('{{REVIEW_HREF}}', names['review_html'])
```

manifest와 figures/를 stage로 복사한다. figures의 symlink 외부 참조는 거절한다. template 치환 후 `{{`가 남으면 실패한다. `.claude/skills/logic-lab-review-pack/assets`를 out/assets에 복사한다.
- [ ] **4. 공통 화면을 작성한다.** 템플릿의 정확한 placeholder는 TITLE, NAV, CONTENT, STATUS 네 개다.

```html
<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{TITLE}}</title><link rel="stylesheet" href="assets/style.css">
<script defer src="assets/widgets.js"></script></head>
<body><header><h1>{{TITLE}}</h1><p>{{STATUS}}</p></header>
<nav aria-label="목차">{{NAV}}</nav><main>{{CONTENT}}</main></body></html>
```

```css
body { max-width: 76rem; margin: auto; padding: 1.25rem; color: #222; background: #faf9f6; font: 1rem/1.8 system-ui,sans-serif; }
main { max-width: 52rem; margin: auto; }
img,svg { max-width: 100%; height: auto; }
.table-wrap { overflow-x: auto; }
summary,button { cursor: pointer; }
summary:focus-visible,button:focus-visible,a:focus-visible { outline: 3px solid #2667a0; }
@media print { nav,.controls { display:none; } body { background:white; padding:0; } }
```

widgets.js는 beforeprint에서 details의 open 상태를 저장하고 모두 연 뒤 afterprint에서 복원한다. 선택적 MUX 위젯은 `data-widget="mux2"` 아래 select[name=S], checkbox[name=I0/I1], output을 사용한다. change마다 S가 가리키는 checkbox의 checked를 0/1로 출력한다. 데이터 없는 widget은 만들지 않는다. `.static-equivalent` 표는 항상 문서에 남긴다.
- [ ] **5. 테스트를 실행하고 375px/1280px 브라우저에서 실제 목차·힌트·풀이·인쇄를 확인한다.** 출처 파일 접근은 상대 URL을 percent-encode하고 PDF 페이지는 `#page=N`으로 연결한다. 링크 계산은 stage 위치가 아니라 최종 `복습노트/실험NN` 기준이다.
- [ ] **6. 커밋한다.** Task 3에 나열된 파일만 stage하고 `git commit -m "feat: render experiment learning pages"`.

## Task 4: 풀이·수식·그림이 보존되는 MD 변환

**Files:** Create `scripts/lab/review_pack/html2md.py`, `tests/test_review_pack_md.py`; Extend fixture fragments와 format.md.

**Interfaces:** `convert_pack(note_path: Path, review_path: Path) -> tuple[list[Path],int]`; `check_md(html_path: Path, md_path: Path) -> list[str]`. 반환값은 MD 경로 두 개와 export한 SVG 수다. Task 3 HTML을 소비한다.

- [ ] **1. 숨긴 풀이·수식·그림·링크 보존 테스트를 작성한다.**

```python
def test_hidden_solution_and_math_survive(tmp_path):
    from scripts.lab.review_pack.html2md import convert_pack, check_md
    note = tmp_path / '실험04_실험설명.html'
    review = tmp_path / '실험04_기출풀이.html'
    note.write_text('<body><main><article id="t"><math data-tex="V=IR"><mi>V</mi><mo>=</mo><mi>I</mi><mi>R</mi></math><a href="실험04_기출풀이.html#q">문제</a></article></main></body>', encoding='utf-8')
    review.write_text('<body><main><article id="q"><details><summary>풀이</summary><p>저항과 전류를 곱합니다.</p></details></article></main></body>', encoding='utf-8')
    outputs, count = convert_pack(note, review)
    assert '저항과 전류를 곱합니다.' in outputs[1].read_text(encoding='utf-8')
    assert '$V=IR$' in outputs[0].read_text(encoding='utf-8')
    assert '실험04_기출풀이.md#q' in outputs[0].read_text(encoding='utf-8')
    assert check_md(note, outputs[0]) == []
```

- [ ] **2. 새 테스트가 실패하는지 확인한다.** `python -m pytest -n0 tests/test_review_pack_md.py -q`.
- [ ] **3. 생명과학 변환기를 이식한다.** 참고 원본은 인접 생명과학 프로젝트 `.agents/skills/bio-review-pack/scripts/html2md.py`다. 현재 파일의 해시와 이식 출처를 모듈 docstring에 기록한다. 외부 프로젝트 import는 하지 않는다. 기존 Builder/Node·표·SVG·앵커 변환을 활용하되 NAME_RE를 `^(실험\d{2})_(실험설명|기출풀이)\.html$`로 바꾸고 두 파일의 실험 번호 일치를 검사한다. figures 폴더는 `figures/`이며 기존 SVG를 일괄 삭제하는 코드를 제거한다. 자동 생성 SVG는 `md-` 접두사를 붙이고 현재 run에서 만든 것만 관리한다.

```python
# inline(node, ctx)의 MathML 분기
if node.tag == 'math':
    tex = node.attrs.get('data-tex')
    if not tex:
        raise ValueError('MathML에는 MD 변환용 data-tex가 필요합니다')
    marker = '$$' if node.attrs.get('display') == 'block' else '$'
    return marker + tex + marker
```

HTML 수학 표기는 로컬 네이티브 MathML + data-tex를 사용한다. 원래 보이는 MathML과 data-tex의 의미 일치는 시각 검토 대상으로 기록한다. 기존 `.ov` 부울식은 후위 prime으로 변환하고 괄호 범위를 보존한다. authoring에서 긴 수식은 data-tex MathML로 통일한다. MD의 details는 펼친 제목·본문으로 변환해 순수 읽기 자료로 만든다. widget controls는 제거하고 static-equivalent는 보존한다. SVG는 독립 파일로 export하고 대체 설명도 남긴다.
- [ ] **4. 보존 검사와 경로 테스트를 확장한다.** main 내 제목·문단·표 셀·풀이 텍스트를 정규화한 목록, math 토큰, article ID, img 및 SVG 수를 MD와 대조한다. Markdown escape로 인한 문자 차이는 unescape 후 비교한다. source UI·controls는 비교에서 제외한다. NFD와 공백·괄호 이미지 경로, nested complement, 표 안 `|`, 중복 SVG ID를 넣어 그림 누락·잘못된 수식 범위가 검출되는지 테스트한다. 검사 오류에는 article ID를 포함한다.
- [ ] **5. 테스트를 다시 실행하고 두 MD를 실제로 열어 표·수식·풀이 가독성을 확인한다.**
- [ ] **6. 커밋한다.** Task 4 파일만 stage한 후 `git commit -m "feat: preserve learning content in markdown"`.

## Task 5: 내용 검산과 자료 판독 지침

**Files:** Create `checks.py`, `tests/test_review_pack_checks.py`, fixture `review-cases.md`, skill `references/sources.md`, `references/authoring.md`, `references/verification.md`.

**Interfaces:** `boolean_equivalent(left: str, right: str) -> bool`; `check_pack(folder: Path) -> list[str]`. check_pack는 manifest→HTML ID/링크/asset→MD 대응을 검사한다. source 해시 재검사는 Task 6에서 root를 받아 수행한다.

- [ ] **1. 동치식과 표현 오류 테스트를 작성한다.**

```python
import pytest
from scripts.lab.review_pack.checks import boolean_equivalent

def test_demorgan_equivalence():
    assert boolean_equivalent("(A·B)'", "A'+B'")
    assert not boolean_equivalent('A+B', 'A·B')

def test_unknown_notation_is_not_accepted():
    with pytest.raises(ValueError):
        boolean_equivalent('!A', "A'")
```

- [ ] **2. `python -m pytest -n0 tests/test_review_pack_checks.py -q`로 실패를 확인한다.**
- [ ] **3. 기존 평가기를 연결하고 pack 검사를 구현한다.**

```python
from itertools import product
from scripts.lab.boolexpr import eval_boolean, variables

def boolean_equivalent(left, right):
    names = sorted(set(variables(left)) | set(variables(right)))
    if len(names) > 8:
        raise ValueError('자동 전수 검산은 입력 8개까지 지원합니다')
    return all(eval_boolean(left, dict(zip(names,bits))) ==
               eval_boolean(right, dict(zip(names,bits)))
               for bits in product((0,1), repeat=len(names)))
```

check_pack는 load_manifest를 호출하고 포함 ID/필요한 개념 링크/힌트·풀이/MathML data-tex/보류 이유/그림·CSS·JS 파일/중복 ID/남은 placeholder/MD 보존을 검사한다. 자동 판독이 불가능한 문항은 unresolved로 보고하지 자동 검산 통과로 올리지 않는다. remote href 출처는 허용하되 remote src·stylesheet·script·CSS url/import는 금지한다. missing image와 duplicate ID를 의도적으로 넣은 Task 3 stage로 실패 테스트를 작성한다.
- [ ] **4. 세 reference를 작성한다.** sources.md에는 spec의 주장별 자료 선택·판본·전수 분류 규칙, authoring.md에는 완성 예제→부분 연습→기출과 모든 문제 유형, verification.md에는 최대 2회 수정·독립/자기검토 구분을 명시한다. 기출 판독은 PDF 렌더를 보고 하고 page+source ID를 기록한다. 독립 검토에는 문제와 설명만 주며 제공·도출 답안과 작성자의 결론을 주지 않는다. 가용하고 승인된 실행 방식에서만 별도 agent를 사용한다.
- [ ] **5. 다음 실제 내용 검토 fixture를 작성·수행한다.**

```markdown
## C1 — 초기 상태가 없는 D FF
상승 엣지 D FF, 초기 Q 미지정. 첫 상승 전 출력은 미정이며 첫 상승 D=1 이후 Q=1.
검토 요구: 첫 상승 전 Q=0이라고 확정한 풀이를 오류로 잡는다.
## C2 — active-low enable
회로 원문에서 enable에 오버바가 있는 2:1 MUX. enable=1인 상태의 출력은 부품 자료로 판정한다.
검토 요구: 일반 MUX 식만으로 출력이 선택 입력이라고 확정하지 않는다.
## C3 — 전력 계산
문제에서 P=C V^2 f, C=10 pF, V=5 V, f=1 MHz로 주어졌다. 결과는 250 µW.
검토 요구: pF·MHz 단위 변환과 해당 식이 문제에서 주어진 조건임을 남긴다.
```

이 사례는 물리 회로의 보편 규칙 검사가 아니라 학습팩 작성·검토 행동 시험이다. 결과를 실행 중 `tmp/review-pack-validation/`에 기록하고 최종 verification 문서에 요약한다. 자동 검사 통과만으로 C1~C3를 통과 처리하지 않는다.
- [ ] **6. 테스트 통과 후 커밋한다.** `git commit -m "feat: verify review pack evidence and content"` 전에 Task 5 파일만 stage한다.

## Task 6: 실패해도 기존 팩을 유지하는 CLI

**Files:** Create `publish.py`, `__main__.py`, `tests/test_review_pack_publish.py`.

**Interfaces:** `publish(stage: Path, destination: Path, root: Path) -> Path | None`(백업 경로 반환); `main(argv: list[str] | None = None) -> int`.
CLI: `sources --root PATH --experiment N`, `build --root PATH --run PATH --stage PATH`, `check --folder PATH`, `publish --root PATH --stage PATH --experiment N`. build는 manifest의 실험 번호로 render·convert·check를 순서대로 호출한다. check는 findings 있으면 exit 1, publish 실패도 exit 1이다.

- [ ] **1. 실패 보존 테스트를 작성한다.**

```python
def test_failed_pack_cannot_replace_existing(tmp_path):
    import pytest
    from scripts.lab.review_pack.publish import publish
    old = tmp_path / '복습노트/실험04'
    old.mkdir(parents=True)
    (old / '사용자메모.md').write_text('보존', encoding='utf-8')
    stage = tmp_path / 'stage'
    stage.mkdir()
    with pytest.raises(ValueError):
        publish(stage, old, tmp_path)
    assert (old / '사용자메모.md').read_text(encoding='utf-8') == '보존'
```

- [ ] **2. 테스트 실패를 확인한다.** `python -m pytest -n0 tests/test_review_pack_publish.py -q`.
- [ ] **3. publish gate와 복구 경로를 구현한다.**

```python
errors = check_pack(stage)
if errors:
    raise ValueError('\n'.join(errors))
data = load_manifest(stage / 'manifest.json')
for source in data['sources']:
    if file_sha256(root / source['path']) != source['sha256']:
        raise ValueError('원문 변경: ' + source['path'])
if data['checks']['browser'] != 'pass' or data['checks']['content'] not in ('pass','self_review'):
    raise ValueError('브라우저·내용 검토 기록이 필요합니다')
```

destination은 root/복습노트/실험NN과 resolve 결과가 일치해야 하며 source/stage/destination 중첩과 symlink 탈출을 거절한다. 같은 부모의 새 임시 폴더에 stage를 복사하고, 기존 폴더의 생성 목록 밖 파일은 새 폴더에도 보존한다. 최초 기존 팩에 생성 목록이 없으면 모든 파일을 보존하고 새 생성 파일만 명시적으로 덮는다. 생성 목록은 manifest의 `generated_files: list[str]`로 build 끝에 기록한다. 사용자 파일과 새 생성 파일이 충돌하면 중단한다.

기존 destination을 고유 timestamp+random 백업 경로로 rename한 후 새 임시 폴더를 destination으로 rename한다. 두 번째 rename이 실패하면 백업을 원위치로 복구한다. 백업은 자동 삭제하지 않는다. Windows에서는 같은 볼륨·닫힌 핸들을 전제로 하고 실패는 경로와 복구 결과를 보고한다. 다른 볼륨 stage는 복사를 거치므로 허용한다.
- [ ] **4. rollback·해시·사용자 메모 테스트를 추가한다.** `unittest.mock.patch('scripts.lab.review_pack.publish.os.replace', ...)`로 두 번째 rename만 OSError를 발생시키고 기존 내용 복구를 검증한다. Task 3~4 fixture로 유효 stage를 만들고 source 파일 실제 해시와 content/browser 상태를 채운다. 이후 source bytes를 바꾸면 publish가 거절되고 기존 팩이 그대로인지 확인한다. 정상 교체 시 사용자메모.md 및 백업이 모두 있는지 확인한다.
- [ ] **5. CLI를 연결하고 도움말·fixture build를 실행한다.**

```powershell
python -m scripts.lab.review_pack --help
python -m scripts.lab.review_pack build --root . --run tests/fixtures/review_pack --stage tmp/review-pack-fixture
python -m scripts.lab.review_pack check --folder tmp/review-pack-fixture
```

fixture build는 형식 검사까지만 수행한다. 가짜 source hash 때문에 fixture를 실제 publish하지 않는다. build는 검토 상태를 임의로 pass로 바꾸지 않는다. stage가 이미 있으면 다른 빈 경로를 요청하고 내용을 지우지 않는다.
- [ ] **6. 테스트 통과 후 커밋한다.** Task 6 파일만 stage하고 `git commit -m "feat: publish review packs with rollback"`.

## Task 7: 새 스킬 진입점과 구 프리뷰 대체

**Files:** Create `.claude/skills/logic-lab-review-pack/SKILL.md`; Modify `.claude/skills/explain-lab-preview/SKILL.md`, `.claude/skills/init-lab-experiment/SKILL.md:154`, `.claude/skills/write-pre-report/SKILL.md:494`, `.claude/skills/review-lab-report/SKILL.md:250`, `.claude/skills/verify-draft-lab-spec/SKILL.md:93`, `tests/test_lab_validate.py:1012`, `tests/test_skill_docs.py:39`.

**Interfaces:** 사용자 입력 → Task 1 대상 결정 → sources/manifest 저작 → CLI build → 내용·브라우저 검토 → publish. 기존 명령은 인자를 새 스킬에 전달한다. PDF 명시 요청은 HTML 인쇄 안내로 처리하며 PDF가 생성됐다고 주장하지 않는다.

- [ ] **1. 스킬 진입 지침을 작성한다.** 다음 frontmatter와 절 순서를 사용한다.

```yaml
---
name: logic-lab-review-pack
description: 논리회로실험 1~10의 기초부터 실험 원리를 설명하고 기출을 풀이하는 HTML·MD 학습팩을 만든다. 실험 설명, 예습, 복습팩, 기출 풀이를 요청할 때 사용한다. 보고서 작성과 측정 체크리스트는 기존 전용 스킬을 사용한다.
---
```

절은 대상 결정, 자료 확인, 문항 감사, 설명·풀이 저작, build, 검증·수정, publish·보고 순서로 쓴다. 각 절에서 필요한 reference만 읽게 한다. 새 팩 생성은 중간 질문 없이 진행하되 원문이 없어 확정 못 하는 사실은 미확인 처리한다. 최종 보고에 HTML·MD 링크, 판본, 포함·중복·보류 수, 답안 충돌, 수행한 검토 종류, 미해결, 백업 경로를 표시한다. 모델명·서브에이전트 사용·lite 모드·고정 카드 수를 강제하지 않는다.
- [ ] **2. 호환 안내를 작성하고 과거 규칙을 중복 유지하지 않는다.**

```markdown
---
name: explain-lab-preview
description: 기존 explain-lab-preview 명령을 logic-lab-review-pack으로 연결한다. 새 실험 설명·예습 요청에는 logic-lab-review-pack을 사용한다.
---
이 스킬은 logic-lab-review-pack으로 대체되었다.
저장소 루트의 `.claude/skills/logic-lab-review-pack/SKILL.md`를 읽고 기존 실험·주차 인자를 전달한다.
기존 프리뷰 파일은 보존한다. `저장`은 새 기본 HTML·MD 출력으로 해석한다.
`pdf` 요청에는 이번 버전은 HTML·MD와 브라우저 인쇄를 제공한다고 안내한다.
```

- [ ] **3. 관련 문서와 테스트의 오래된 설명을 갱신한다.** 구 template.html은 보존한다. `test_real_preview_template_is_clean`은 `test_legacy_preview_template_is_clean`으로 이름과 설명만 바꿔 기존 산출물 호환 검사를 유지한다. 새 템플릿 검증은 Task 3~5 테스트가 담당한다. init의 STT 읽기 설명을 새 스킬로, 보고서 스킬의 현재 프리뷰 PDF 생성 주장을 과거 출력 호환 설명으로 바꾼다. verify 문서의 목록에는 새 정본 경로도 포함한다. skill_docs의 구 프리뷰 절번호 설명은 호환 안내로 대체됐음을 반영한다. 일반 보고서 검사의 DOCS에 새 학습팩을 넣지 않는다.
- [ ] **4. 실제 발견과 회귀 검사를 수행한다.**

```powershell
git check-ignore .claude/skills/logic-lab-review-pack/SKILL.md
python -m pytest -n0 tests/test_lab_config.py tests/test_lab_validate.py tests/test_skill_docs.py tests/test_review_pack_sources.py tests/test_review_pack_manifest.py tests/test_review_pack_render.py tests/test_review_pack_md.py tests/test_review_pack_checks.py tests/test_review_pack_publish.py -q
```

check-ignore는 출력 없음(exit 1)이 정상이다. 적용 중인 skill-creator의 quick_validate.py로 새 스킬을 검사한다. `.claude/skills` 자동 발견 여부는 환경별로 확인한다. 이 경로를 자동 발견하지 않는 환경에서는 경로 지정 호출로 검증하며, 사용자 지정 위치를 다른 위치로 옮기거나 복제하지 않는다. 발견 확인 없이 자동 호출 확인 완료라고 쓰지 않는다.
- [ ] **5. 커밋한다.** 수정한 문서·테스트만 stage하고 `git commit -m "feat: replace lab preview with review pack skill"`.

## Task 8: 실험4 실제 생성과 최종 수용 검토

**Files:** Create `복습노트/실험04/실험04_실험설명.html`, `.md`, `실험04_기출풀이.html`, `.md`, `manifest.json`, `출처와_문항목록.md`, `검증결과.md`, 필요한 `figures/`, `assets/`; Create `docs/verify/logic-lab-review-pack.md`.

**Interfaces:** 완성된 새 스킬을 실제 사용자 요청 `실험4 설명과 기출 풀이를 완전판으로 만들어줘`로 실행한다. 이 작업은 앞선 CLI·manifest·references를 소비하며 추가 생성 프레임워크를 만들지 않는다.

- [ ] **1. 실험4 자료 목록을 확인한다.** `python -m scripts.lab.review_pack sources --root . --experiment 4`. 현재 교안과 실제 퀴즈 폴더에 있는 2016-1, 정답, 채점본, 종합 기출, 해설, 예상 v2~v4를 모두 감사 대상으로 잡는다. 파일명이 기출인 것과 원문으로 확인한 기출을 구분한다.
- [ ] **2. 현재 교안의 그림·기호와 각 퀴즈 문항을 판독한다.** 작은 페이지 묶음으로 렌더하고 원문 위치·중복·조건 차이를 기록한다. 문항 수를 미리 고정하지 않는다. 보고서 내용이 있으면 개념 누락 확인에만 사용한다.
- [ ] **3. 토픽과 풀이를 저작한다.** 입력·출력·선택선, 비트 조합, MUX/DEMUX 관계를 필요한 기초로 설명하고 실제 IC 조건은 판독 자료를 따른다. 모든 포함 문항에 필요한 개념이 있는지 매핑한다. 새 연습은 기출의 개념 공백을 메우는 경우만 추가한다.
- [ ] **4. stage를 build하고 내용 검토를 수행한다.** Task 5 C1~C3 검토도 수행하고 결과를 기록한다. 승인된 실행 방식에 독립 리뷰가 포함되면 별도 리뷰어에게 답안을 제외한 자료를 전달한다. 그렇지 않으면 self_review로 기록한다. 사용자 답안을 받았다고 가정하지 않는다.
- [ ] **5. 브라우저 검증을 수행한다.** 375px·1280px에서 목차, 개념↔문항 링크, 수식, 그림, 힌트·풀이, 위젯 입력, 인쇄에서 펼쳐진 풀이를 확인한다. 외부 네트워크를 사용하지 않는지 확인하고 screenshot/발견 사항을 `검증결과.md`에 기록한다. source_visual/content/browser 상태를 실제 결과로 업데이트하고 build 산출물을 다시 검사한다.
- [ ] **6. publish 후 최종 폴더에서 재검사한다.** 이동 후 원문 PDF 상대 링크·그림 링크를 확인한다. 백업 경로와 미해결 문항을 `docs/verify/logic-lab-review-pack.md`에 기록한다. 문항 감사 목록 수와 실제 수록 수의 합계를 대조한다.
- [ ] **7. 관련 회귀 테스트를 한 번 실행하고 변경 diff를 검토한다.** Task 7의 명시된 테스트 목록을 사용한다. 새 실패가 있으면 원인을 해결하고 관련 검사만 다시 수행한다. 보고서·기록·결선도·생명과학 프로젝트에 변경이 없는지 git diff로 확인한다.
- [ ] **8. 최종 산출물을 커밋한다.** 검증된 `복습노트/실험04`와 `docs/verify/logic-lab-review-pack.md`만 stage하고 `git commit -m "docs: add experiment 4 learning pack"`. 완료 보고는 네 학습 파일 링크와 검증 범위·미해결을 포함한다.

## 계획 자체 검토

- 설계 범위 대응: 요청·대상 Task 1/7, 교육·자료 Task 5/8, 문항 계약 Task 2, 화면 Task 3, MD Task 4, 저장 Task 6, 구 스킬 대체 Task 7, 실제 수용 Task 8.
- Review Focus 대응: 경로 1/4, 중복·답안 충돌 2, 타이밍·극성 5, 정적 변환 4, 교체 실패·원문 변경 6.
- public API와 반환 키는 위 Interfaces가 정본이다. reference와 CLI가 다른 함수명이나 키를 만들지 않는다.
- 계획 작성은 구현·테스트 실행을 뜻하지 않는다. 문서의 명령과 코드는 실행자가 수행할 단계다.
- 실행 권장: Native. 자료→manifest→HTML→MD 계약이 연속적으로 연결돼 동일 구현자가 맥락을 유지하기 좋다. 끝에 독립적인 전체 변경·교육 내용 리뷰를 수행한다. 사용자가 Subagent-driven을 선택하면 각 task별 구현·리뷰를 나누되 동일한 interface를 사용한다.

## 구현 중 사용자 확정 (2026-09-29)

Native 실행. 학습 화면은 생명과학 note-template.html/review-template.html 원본을 그대로 사용한다. 새 page.html/style.css 디자인은 폐기한다. 렌더 시 placeholder와 외부 자원 URL만 로컬 번들로 교체한다. 원본 템플릿 파일의 SHA256을 기록한다.
