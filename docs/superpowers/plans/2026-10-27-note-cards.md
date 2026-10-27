# 실험설명 표·수식 카드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 문제설명에만 있던 표 카드(`table-card`)·수식 카드(`equation-card`)를 실험설명 생성기에 넣고, 이미 발행한 실험설명 7개(실험01~07)에 제자리 업그레이드로 소급 적용한다.

**Architecture:** 생성기는 `render.assemble`의 note 토픽 조각에 문제설명과 같은 `separate_tables(separate_equations(...))`를 건다. 소급은 재빌드 대신 `navigation_upgrade.py`와 같은 골격(전체 사전 점검 → 백업 → 원자적 쓰기 → 실패 시 되돌림)의 새 모듈 `card_upgrade.py`가 발행본 HTML의 본문 래핑·카드 CSS 삽입·스와이프 제외 선택자 교체를 한다.

**Tech Stack:** Python 3.11+(현재 3.14), html.parser, pytest. 브라우저 확인은 Claude Browser 창.

**Spec:** 이 문서의 §승인 설계. 2026-10-27 채팅의 grill-yourself 설계(확인 필요 #1·#9는 추천값으로 기본 확정)를 옮겼다.

## 승인 설계

- 적용 범위는 표 카드·수식 카드뿐이다. 열 배치 계약(`table-layout.json`, 그룹 머리글·열 폭·경계 여백)은 이번에 하지 않는다(#1 기본 확정).
- 생성기: `scripts/lab/review_pack/render.py`의 note 토픽 조각에만 적용한다. 순서는 `explanation_render.py:59`와 같다(식 먼저, 표 다음). legacy 기출풀이(review) 조각에는 적용하지 않는다.
- 템플릿(`note-template.html`)은 카드 CSS(111–121행)와 스와이프 제외 선택자(785행)를 이미 갖고 있으므로 고치지 않는다.
- 소급: 발행본 `복습노트/실험NN/실험NN_실험설명.html`만 제자리에서 고친다. 재빌드는 하지 않는다(실험01~03 원고 폴더엔 manifest가 없고, 재빌드는 워크북·문제설명까지 다시 만든다). `.pack/assets/note-template.html`은 이미 카드 CSS가 있어 건드리지 않는다. MD는 텍스트가 같으므로 재생성하지 않고 `check_pack`(내부 `check_md`)으로 대조만 한다.
- 래핑 범위는 `<section id="learning">`부터 `</main>` 직전까지 전부다(요약 `.sum`, `details`, `figure` 안 포함 — 문제설명과 동일).
- 카드 CSS가 없는 파일(실험01~05)에는 템플릿의 카드 규칙 블록을 `.katex-display` 줄 바로 뒤에 넣는다. 스와이프 제외 선택자는 템플릿 값으로 바꾼다.
- 기본은 점검(dry-run). `--apply`에는 `--backup-dir` 필수. 하나라도 점검에 실패하면 아무것도 쓰지 않는다. 두 번째 실행은 변경 0건이다.
- 적용 순서: 점검 보고를 본 뒤 7개를 한 번에 적용한다(#9 기본 확정).
- 이번에 하지 않는 것: 열 배치, 다운로드 폴더의 기존 standalone 재내보내기, review-pack `format.md`의 MathML 문구 정리.

## Global Constraints

- 래퍼 마크업은 기존 함수가 내는 그대로: `<div class="table-card" role="group" aria-label="표">`, `<div class="equation-card" role="group" aria-label="수식">`. 새 래퍼 함수를 만들지 않고 `table_cards.separate_tables`·`equation_cards.separate_equations`를 재사용한다.
- 카드 CSS 블록의 정본은 `.claude/skills/logic-lab-review-pack/assets/note-template.html`이다. 업그레이드 코드에 CSS 문자열을 복사해 두지 않고 실행 시 템플릿에서 잘라 온다.
- CSS 삽입 앵커(정확히 1회): `    .katex-display { overflow-x: auto; overflow-y: hidden; padding: var(--s1) 0; }\n`
- 옛 스와이프 선택자: `.closest('.widget, .katex-display, .table-wrap, svg, input, details')` → 새 값: `.closest('.widget, .equation-card, .table-card, .katex-display, .table-wrap, svg, input, details')`
- 발행본 원고·문제설명·문제지·해설지·MD·`.pack/assets`의 바이트는 바뀌지 않아야 한다(실험설명 HTML만 변경).
- 문서·주석은 저장소 관례대로 한국어, 코드 스타일은 `navigation_upgrade.py`를 따른다.

## Review Focus

1. 이미 일부만 카드가 있는 파일(실험06·07: CSS·선택자는 최신, 본문은 미적용) — CSS를 두 번 넣지 않고 본문만 감싸야 한다. → Task 2 `test_css_already_present_wraps_body_only`.
2. 이미 감싼 표/식이 있는 본문 — 다시 감싸지 않아야 한다(이중 카드 금지). → Task 2 `test_upgrade_is_idempotent`.
3. 위젯·`details`·요약 안의 표 — 감싸되 글자 내용은 그대로라 MD 대조가 통과해야 한다. → Task 2 `test_apply_keeps_md_and_other_pages`(실제 팩 복사본에 `check_pack`).
4. 앵커가 없거나 두 번 나오는 낯선 HTML — 배치 전체가 쓰기 전에 멈춰야 한다. → Task 2 `test_unknown_page_aborts_batch_before_writes`.
5. 문장 속 인라인 식(`$x$`가 섞인 설명 문단)·식+문장 문단 — 수식 카드로 감싸면 안 된다. → Task 1 `test_note_cards_skip_prose_with_inline_math`.

---

### Task 1: 생성기에 카드 래핑 추가

**Files:**
- Modify: `scripts/lab/review_pack/render.py` (토픽 루프, `fragment=read_fragment(run,t['fragment'],names)` 바로 뒤)
- Modify: `.claude/skills/logic-lab-review-pack/references/format.md` ("표는 .table-wrap으로 감싼다." 줄)
- Test: `tests/test_review_pack_render.py`

**Interfaces:**
- Consumes: `equation_cards.separate_equations(source: str) -> str`, `table_cards.separate_tables(source: str) -> str` (기존)
- Produces: 없음(동작 변경만)

- [ ] **Step 1: 실패 테스트 작성** — `RUN`을 `tmp_path/'run'`으로 복사한 뒤 `sections/t-mux.html`에 표·식·인라인 식 문단을 덧붙이는 헬퍼 `run_with_cards(tmp_path) -> Path`를 두고:

```python
def test_note_wraps_tables_and_equations(tmp_path):
    paths=assemble(fixture(),run_with_cards(tmp_path),tmp_path/'stage',ASSETS)
    note=paths['note_html'].read_text(encoding='utf-8')
    assert '<div class="table-wrap"><div class="table-card" role="group" aria-label="표"><table>' in note
    assert '<div class="equation-card" role="group" aria-label="수식"><p>$$Y=\\overline{S}I_0+SI_1$$</p></div>' in note
    assert 'aria-label="표"' not in paths['review_html'].read_text(encoding='utf-8')

def test_note_cards_skip_prose_with_inline_math(tmp_path):
    paths=assemble(fixture(),run_with_cards(tmp_path),tmp_path/'stage',ASSETS)
    note=paths['note_html'].read_text(encoding='utf-8')
    assert '<p>선택선 $S$가 0이면 $Y=I_0$예요.</p>' in note
    assert note.count('aria-label="수식"')==1
```

review 쪽 단언이 의미를 갖도록 헬퍼는 `problems/q-mux-001.html`에도 같은 `table-wrap` 표를 덧붙인다(legacy review는 감싸지 않아야 함). 덧붙일 조각: `<div class="table-wrap"><table><thead><tr><th>S</th><th>Y</th></tr></thead><tbody><tr><td>0</td><td>I0</td></tr></tbody></table></div><p>$$Y=\overline{S}I_0+SI_1$$</p><p>선택선 $S$가 0이면 $Y=I_0$예요.</p>`

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_review_pack_render.py -k "cards" -v` / Expected: 두 테스트 FAIL(`table-card` 없음).
- [ ] **Step 3: 구현** — `render.py`에서 note 토픽 조각에 `separate_tables(separate_equations(fragment))` 적용. `forbidden_note_metadata` 검사는 래핑 전 원본에 대해 그대로 둔다. review 루프는 손대지 않는다.
- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_review_pack_render.py tests/test_review_pack_md.py tests/test_review_pack_checks.py -v` / Expected: 전부 PASS.
- [ ] **Step 5: 형식 문서** — `format.md`의 "표는 .table-wrap으로 감싼다." 뒤에 한 문장 추가: "실험설명의 표와 식만 있는 문단은 렌더러가 table-card·equation-card로 감싸므로 해석·주의 문장은 표·식 밖 문단에 쓴다."
- [ ] **Step 6: Commit**

```bash
git add scripts/lab/review_pack/render.py tests/test_review_pack_render.py .claude/skills/logic-lab-review-pack/references/format.md
git commit -m "feat: wrap note tables and equations in cards"
```

### Task 2: 발행본 카드 업그레이드 모듈

**Files:**
- Create: `scripts/lab/review_pack/card_upgrade.py`
- Modify: `.claude/skills/logic-lab-review-pack/SKILL.md:133` (rerender 안내 문단 끝)
- Test: `tests/test_review_pack_card_upgrade.py`

**Interfaces:**
- Consumes: `separate_equations`, `separate_tables`; `navigation_upgrade._atomic_write(path, data: bytes)`(가져다 쓴다, 복사 금지); `manifest.load_manifest`, `output_names`, `DATA`; `checks.check_pack(folder) -> list[str]`
- Produces:
  - `upgrade_card_html(text: str) -> str` — 순수 함수. 본문 래핑 + 필요 시 CSS 삽입 + 선택자 교체. 낯선 구조면 `ValueError`.
  - `upgrade_packs(folders: list[Path], *, apply: bool = False, backup_root: Path | None = None) -> list[Path]` — 바뀔(바뀐) 실험설명 경로 목록. 의미는 `navigation_upgrade.upgrade_packs`와 같다(사전 점검 전부 → 백업 → 쓰기 → 실패 시 되돌림). 적용 후 각 폴더 `check_pack` 오류가 있으면 되돌리고 `ValueError`.
  - CLI `python -m scripts.lab.review_pack.card_upgrade (--all | --folder DIR) [--apply --backup-dir DIR]`, 출력 마지막 줄 `N packs inspected; M files would change|updated`.

`upgrade_card_html` 규칙:
- `<section id="learning">`과 그 뒤 `</main>`이 각각 정확히 1회가 아니면 `ValueError('Unsupported note body')`.
- 본문 구간 `[section 시작, </main>)`에 `separate_tables(separate_equations(구간))`을 적용해 되붙인다.
- 템플릿에서 카드 블록 = `    .equation-card { margin`로 시작하는 줄부터 `    .table-card > table { margin: 0; }\n`까지(템플릿에 각각 1회여야 함).
- 대상에 `    .table-card { margin`이 없으면: 앵커가 정확히 1회가 아니면 `ValueError('Missing card CSS anchor')`, 맞으면 앵커 뒤에 카드 블록 삽입. 이미 있으면 CSS는 그대로.
- 새 선택자가 있으면 그대로, 옛 선택자가 정확히 1회면 교체, 둘 다 아니면 `ValueError('Unsupported swipe guard')`.

- [ ] **Step 1: 실패 테스트 작성** — 옛 형식 최소 HTML 헬퍼 `old_html()`(앵커 줄·옛 선택자·`<main><section id="learning">` 안에 `table-wrap` 표 1개와 `<p>$$A=B$$</p>` 1개)과 `pack_copy(tmp_path, name='실험05')`(실제 `복습노트/실험05` 복사)를 두고:

```python
def test_wraps_body_and_adds_css():
    out=upgrade_card_html(old_html())
    assert out.count('aria-label="표"')==1 and out.count('aria-label="수식"')==1
    assert out.count('    .table-card { margin')==1
    assert ".closest('.widget, .equation-card, .table-card, .katex-display, .table-wrap, svg, input, details')" in out

def test_upgrade_is_idempotent():
    once=upgrade_card_html(old_html())
    assert upgrade_card_html(once)==once

def test_css_already_present_wraps_body_only():
    once=upgrade_card_html(old_html())
    unwrapped=once.replace('<div class="table-card" role="group" aria-label="표">','',1)  # 카드 하나 벗김
    unwrapped=unwrapped.replace('</table></div></div>','</table></div>',1)
    again=upgrade_card_html(unwrapped)
    assert again.count('    .table-card { margin')==1 and again.count('aria-label="표"')==1

def test_missing_anchor_raises():
    with pytest.raises(ValueError):
        upgrade_card_html(old_html().replace('padding: var(--s1) 0; }','}'))

def test_dry_run_writes_nothing(tmp_path): ...            # 바이트 전부 동일, 반환 목록에 실험설명 1개
def test_unknown_page_aborts_batch_before_writes(tmp_path): ...  # 실험05+실험04 복사, 실험04 실험설명을 '<html>unknown</html>'로; apply 시 ValueError, 실험05 불변, 백업 폴더 없음
def test_apply_keeps_md_and_other_pages(tmp_path): ...     # 실험05 복사본 apply: 실험설명만 바뀜(다른 모든 파일 바이트 동일), 백업에 원본, check_pack==[], 재실행 시 []
def test_backup_inside_pack_rejected(tmp_path): ...        # backup_root=폴더/'bk' → ValueError, 무변경
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_review_pack_card_upgrade.py -v` / Expected: ImportError로 전부 FAIL.
- [ ] **Step 3: 구현** — 위 Interfaces·규칙대로 `card_upgrade.py` 작성. 폴더 목록·중복 검사·백업·되돌림은 `navigation_upgrade.upgrade_packs`와 같은 순서. 대상은 `output_names(...)['note_html']` 하나뿐이고 템플릿 사본 동기화는 하지 않는다. `--all`은 `ROOT/'복습노트'`의 `실험[0-9][0-9]` 폴더만.
- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_review_pack_card_upgrade.py tests/test_review_pack_navigation_upgrade.py -v` / Expected: 전부 PASS.
- [ ] **Step 5: 스킬 문서** — SKILL.md 133행 문단 끝에 추가: "카드 서식(표·수식) 도입 전에 발행한 실험설명은 `python -m scripts.lab.review_pack.card_upgrade --all`로 점검하고 `--apply --backup-dir <팩 밖 새 폴더>`로 제자리 업그레이드한다. 다시 실행하면 변경이 0건이어야 한다."
- [ ] **Step 6: Commit**

```bash
git add scripts/lab/review_pack/card_upgrade.py tests/test_review_pack_card_upgrade.py .claude/skills/logic-lab-review-pack/SKILL.md
git commit -m "feat: add in-place card upgrade for published notes"
```

### Task 3: 발행본 7개 소급 적용과 확인

**Files:**
- Modify(도구가 씀): `복습노트/실험01~07/실험NN_실험설명.html`

- [ ] **Step 1: 기준선** — Run(PowerShell): `foreach ($n in 1..7) { python -m scripts.lab.review_pack check --folder ("복습노트/실험{0:D2}" -f $n) }` / Expected: 7줄 모두 `OK (mechanical checks only)`. 실패하면 멈추고 보고(이 작업 탓이 아님).
- [ ] **Step 2: 점검** — Run: `python -m scripts.lab.review_pack.card_upgrade --all` / Expected: 실험설명 7개 경로와 `7 packs inspected; 7 files would change`.
- [ ] **Step 3: 적용** — Run: `python -m scripts.lab.review_pack.card_upgrade --all --apply --backup-dir "$env:TEMP\card-upgrade-20261027"` / Expected: `7 files updated`.
- [ ] **Step 4: 수량·멱등 확인** — 각 실험설명의 `aria-label="표"`/`aria-label="수식"` 수가 표 11/7/9/8/12/9/3, 식 2/2/0/5/6/4/0(실험01~07)인지 세고, `--all`을 다시 돌려 `0 files would change`. 수가 다르면 차이 나는 항목을 보고한다(설계 당시 수치와의 차이는 원인만 확인하면 됨).
- [ ] **Step 5: 회귀** — Run: `python -m pytest tests/test_review_pack_template_scrollbar.py tests/test_review_pack_navigation_upgrade.py tests/test_review_pack_explanation_published.py -v`와 Step 1 명령 재실행 / Expected: 전부 PASS·OK. `git status`에 실험설명 HTML 7개만 바뀌어 있어야 한다.
- [ ] **Step 6: 브라우저** — 실험05(CSS 새로 삽입)·실험06(CSS 기존) 실험설명을 Claude Browser로 열어 375px·1280px, 라이트·다크에서: 표가 카드 안에 있고 넘치는 표는 카드 안에서만 가로 스크롤, 수식 카드 표시, 카드 위 좌우 스와이프가 토픽을 넘기지 않음, 우측 요약 패널의 표, 콘솔 오류 0.
- [ ] **Step 7: Commit**

```bash
git add 복습노트/실험0*/실험0*_실험설명.html
git commit -m "chore: apply table and equation cards to published notes"
```
