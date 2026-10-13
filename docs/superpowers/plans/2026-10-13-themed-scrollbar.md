# 복습팩 노트 템플릿 테마 스크롤바 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `logic-lab-review-pack` 의 note·review 템플릿과 발행된 복습노트 실험01~06 에 생명과학(`96c6d63`·`aacdbd0`)과 같은 테마 스크롤바를 넣고, note 템플릿의 수식·표 카드 가로 스크롤에도 입힌다.

**Architecture:** 템플릿 CSS 에 토큰 3줄 + 규칙 블록을 앵커 문자열 뒤에 끼워 넣는다. 발행물은 다시 렌더하지 않고 같은 삽입을 텍스트로 한다 — `check_explanations` 가 `자료/assets/note-template.html` 로 문제설명을 다시 그려 바이트 비교하므로(scripts/lab/review_pack/explanation_checks.py:22-24) 팩의 템플릿 사본은 스킬 assets 를 바이트 그대로 복사한다.

**Tech Stack:** HTML/CSS, Python 3 (`.venv`), pytest.

**Spec:** 2026-10-13 세션의 grill-yourself 설계(채팅). 아래 '설계 요약' 이 그 사본이다 — 확정 #1~#9, N1=카드 2종에도 입힘, N2=브랜치에서 멈춤.

## 설계 요약

- 대상 템플릿: `.claude/skills/logic-lab-review-pack/assets/note-template.html`, `review-template.html` 둘뿐. workbook(`assets/workbook/*.html`)·보고서·표지·체크리스트·`draw-expected-figure`·`explain-lab-preview` 템플릿은 손대지 않는다.
- 문제설명 렌더러(`explanation_render.py:69`)와 `export-standalone-note` 는 note 템플릿을 읽으므로 자동 적용.
- 범위 밖: `.katex-display`(카드 안의 것 포함)·`.table-wrap` 가로 스크롤, `--scrollbar: 16px` 는 유지, `.md` 출력, `output/backups/**`, `.claude/worktrees/**`.
- 발행물: 6개 팩의 `실험NN_실험설명.html`·`실험NN_문제설명.html` 은 텍스트 삽입, `자료/assets/{note,review}-template.html`·`template-provenance.json` 은 스킬 assets 에서 바이트 복사.
- `template-provenance.json`: note 의 `local_adjustments` 해시·사유 갱신, review 항목 신설(지금 review 는 기록 `eac8…` 과 실제 `5150…` 이 어긋나 있고 항목이 없다). 이 파일을 읽는 코드는 없다.
- 실험01~05 `실험설명.html` 에는 카드 CSS(`.table-card {` 규칙)가 없다 — 카드 5줄은 건너뛰고 기존 차이는 메우지 않는다.

## Global Constraints

- 작업 트리: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실-themed-scrollbar`, 브랜치 `feat/themed-scrollbar`. 병합·push 하지 않는다.
- 파이썬은 `.venv/bin/python`, 시험은 `.venv/bin/python -m pytest`.
- 토큰 값(글자 그대로):
  - 라이트: `--scroll: #c9d0db; --scroll-hover: #9aa3b2;`
  - 다크: `--scroll: #3f414b; --scroll-hover: #5b5e6a;`
- 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. `git add` 는 경로를 하나씩 지정한다.
- 각 앵커는 파일마다 정확히 1회여야 하며(`assert`), 이미 `--scroll:` 이 있는 파일은 건너뛴다.

## 삽입 표 (Task 1·2 공용)

들여쓰기까지 글자 그대로. "앵커" 는 그 문자열 **바로 뒤**(끝 `\n` 다음)에 삽입한다는 뜻.

| 키 | 앵커 | 삽입 |
|---|---|---|
| T1 | `"\n      --warn: #b54708; --prof: #6941c6; --supp: #067647; --danger: #d92d20;\n"` | `"      --scroll: #c9d0db; --scroll-hover: #9aa3b2;\n"` |
| T2 | `"\n        --warn: #f5a15c; --prof: #b69cff; --supp: #5fd39a; --danger: #ff6b61;\n"` (8칸, 미디어쿼리 안) | `"        --scroll: #3f414b; --scroll-hover: #5b5e6a;\n"` |
| T3 | `"\n      --warn: #f5a15c; --prof: #b69cff; --supp: #5fd39a; --danger: #ff6b61;\n"` (6칸 — 앞 `\n` 이 8칸과 가른다) | `"      --scroll: #3f414b; --scroll-hover: #5b5e6a;\n"` |
| P | `"    .panel-inner { flex: 1 1 auto; min-height: 0; overflow-y: auto; overscroll-behavior: contain; padding: var(--s4) var(--s4) var(--s6); }\n"` | 아래 블록 P |
| C | `"    .table-card { margin: var(--s4) 0; padding: var(--s4); background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); max-width: 100%; overflow-x: auto; }\n"` | 아래 블록 C — **앵커가 0회면 건너뛴다**(review 템플릿, 실험01~05 실험설명) |

블록 P:
```css
    .content::-webkit-scrollbar, .panel-inner::-webkit-scrollbar { width: 8px; }
    .content::-webkit-scrollbar-track, .panel-inner::-webkit-scrollbar-track { background: transparent; }
    .content::-webkit-scrollbar-thumb, .panel-inner::-webkit-scrollbar-thumb { background: var(--scroll); border-radius: 8px; border: 2px solid var(--bg); }
    .content::-webkit-scrollbar-thumb:hover, .panel-inner::-webkit-scrollbar-thumb:hover { background: var(--scroll-hover); }
    @supports (scrollbar-color: auto) { .content, .panel-inner { scrollbar-width: thin; scrollbar-color: var(--scroll) transparent; } }
```

블록 C:
```css
    .equation-card::-webkit-scrollbar, .table-card::-webkit-scrollbar { height: 8px; }
    .equation-card::-webkit-scrollbar-track, .table-card::-webkit-scrollbar-track { background: transparent; }
    .equation-card::-webkit-scrollbar-thumb, .table-card::-webkit-scrollbar-thumb { background: var(--scroll); border-radius: 8px; border: 2px solid var(--surface); }
    .equation-card::-webkit-scrollbar-thumb:hover, .table-card::-webkit-scrollbar-thumb:hover { background: var(--scroll-hover); }
    @supports (scrollbar-color: auto) { .equation-card, .table-card { scrollbar-width: thin; scrollbar-color: var(--scroll) transparent; } }
```

삽입 스크립트는 스크래치 폴더에 둔다(저장소에 커밋하지 않는다): `insert_scrollbar(text: str) -> str` — `--scroll:` 이 있으면 그대로 반환, T1·T2·T3·P 는 `text.count(anchor) == 1` 단언 후 `replace(anchor, anchor + 삽입, 1)`, C 는 count 가 0 이면 건너뛰고 1 이면 삽입, 그 밖은 `ValueError`. 명령행으로 받은 경로들에 적용한다.

## Review Focus

1. 6칸 다크 앵커가 8칸 줄 안에서도 잡히면 미디어쿼리 블록에 토큰이 두 번, `:root[data-theme="dark"]` 에 0번 들어간다 — 블록마다 따로 단언한다. → Task 1 `test_다크_두_블록_모두_토큰`.
2. 카드 CSS 가 없는 실험01~05 실험설명에서 스크립트가 멈추거나 카드 규칙만 덩그러니 들어가면 안 된다 — 카드 규칙은 `.table-card {` 규칙이 있는 파일에만 있어야 한다. → Task 2 `test_발행물_스크롤바`.
3. 팩 템플릿 사본이 스킬 템플릿과 한 바이트라도 다르면 다음 `navigation_upgrade --all` 이 사본을 덮고 문제설명 왕복 비교가 갈린다. → Task 2 `test_팩_템플릿_사본은_스킬과_같다`.
4. 스크립트를 두 번 돌리면 토큰이 겹친다 — 정규식 개수 3 단언이 잡는다. → Task 1·2 시험의 `len(...) == 3`, Task 2 Step 5 재실행.
5. 문제설명 왕복 비교(`check_pack`)가 수정 전엔 통과했는데 수정 뒤 실패하면 발행이 막힌다. → Task 2 Step 6 기준선 대조.

---

### Task 1: 템플릿 2개에 스크롤바 + provenance

**Files:**
- Modify: `.claude/skills/logic-lab-review-pack/assets/note-template.html:20`, `:35`, `:42`, `:112`, `:249` (각 줄 뒤에 삽입)
- Modify: `.claude/skills/logic-lab-review-pack/assets/review-template.html` (T1·T2·T3·P 앵커 뒤)
- Modify: `.claude/skills/logic-lab-review-pack/assets/template-provenance.json`
- Create: `tests/test_review_pack_template_scrollbar.py`

**Interfaces:**
- Consumes: 없음
- Produces: 스크래치 `insert_scrollbar(text: str) -> str` (Task 2 가 그대로 쓴다), 시험 파일의 도우미 `check_scrollbar(text: str, cards: bool) -> None` (Task 2 의 시험이 쓴다)

- [ ] **Step 1: worktree 를 판다**

```bash
cd /Users/hyunjun_macbook_pro/Documents/Univ/논회실
git worktree add ../논회실-themed-scrollbar -b feat/themed-scrollbar
ln -s ../논회실/.venv ../논회실-themed-scrollbar/.venv
grep -qx '.venv' "$(git rev-parse --git-common-dir)/info/exclude" || echo '.venv' >> "$(git rev-parse --git-common-dir)/info/exclude"
```
이후 모든 명령은 `/Users/hyunjun_macbook_pro/Documents/Univ/논회실-themed-scrollbar` 에서.

- [ ] **Step 2: 기준선을 잰다**

Run: `.venv/bin/python -m pytest -q tests -k "review_pack or workbook" 2>&1 | tail -5`
실패 목록을 스크래치 `baseline.txt` 에 적어 둔다(Task 2 Step 6 이 대조한다).
같은 자리에서 Task 2 Step 6 의 `check_pack` 명령도 돌려 출력을 `baseline-check-pack.txt` 에 적어 둔다.

- [ ] **Step 3: 실패하는 시험을 쓴다** — `tests/test_review_pack_template_scrollbar.py`

```python
import re
from pathlib import Path
import pytest

ASSETS = Path('.claude/skills/logic-lab-review-pack/assets')
TOKEN = re.compile(r'--scroll: #[0-9a-f]{6}; --scroll-hover: #[0-9a-f]{6};')
LIGHT = '--scroll: #c9d0db; --scroll-hover: #9aa3b2;'
DARK = '--scroll: #3f414b; --scroll-hover: #5b5e6a;'

def check_scrollbar(text, cards):
    assert len(TOKEN.findall(text)) == 3
    assert text.count(LIGHT) == 1 and text.count(DARK) == 2
    assert '.content::-webkit-scrollbar-thumb, .panel-inner::-webkit-scrollbar-thumb { background: var(--scroll); border-radius: 8px; border: 2px solid var(--bg); }' in text
    assert '.content::-webkit-scrollbar-thumb:hover, .panel-inner::-webkit-scrollbar-thumb:hover { background: var(--scroll-hover); }' in text
    assert '{ .content, .panel-inner { scrollbar-width: thin; scrollbar-color: var(--scroll) transparent; } }' in text
    card = '.equation-card::-webkit-scrollbar-thumb, .table-card::-webkit-scrollbar-thumb { background: var(--scroll); border-radius: 8px; border: 2px solid var(--surface); }'
    assert (card in text) == cards
    assert ('{ .equation-card, .table-card { scrollbar-width: thin; scrollbar-color: var(--scroll) transparent; } }' in text) == cards

@pytest.mark.parametrize('name,cards', [('note-template.html', True), ('review-template.html', False)])
def test_템플릿_스크롤바(name, cards):
    check_scrollbar((ASSETS/name).read_text(encoding='utf-8'), cards)

@pytest.mark.parametrize('name', ['note-template.html', 'review-template.html'])
def test_다크_두_블록_모두_토큰(name):
    text = (ASSETS/name).read_text(encoding='utf-8')
    media = text[text.index(':root:not([data-theme="light"]) {'):]
    media = media[:media.index('}')]
    forced = text[text.index(':root[data-theme="dark"] {'):]
    forced = forced[:forced.index('}')]
    assert DARK in media and DARK in forced
```

- [ ] **Step 4: 실패를 확인한다**

Run: `.venv/bin/python -m pytest -q tests/test_review_pack_template_scrollbar.py`
Expected: 4 failed (`assert 0 == 3` 류)

- [ ] **Step 5: 스크래치에 `insert_scrollbar` 스크립트를 쓰고 두 템플릿에 적용한다**

'삽입 표' 의 규칙 그대로. 적용 뒤 `git diff --numstat` 이 note `13 0`, review `8 0`.

- [ ] **Step 6: provenance 를 갱신한다**

`shasum -a 256` 로 두 템플릿의 새 해시를 구해 `template-provenance.json` 의 `local_adjustments` 를 다음 모양으로 만든다(`source`·`sha256` 블록은 그대로):
- `note-template.html`: `sha256` = 새 해시, `reason` = `"Preserve section spacing and show equations and tables as separate scrollable cards. Themed scrollbar for panels, content and cards."`
- `review-template.html`(신설): `sha256` = 새 해시, `reason` = `"Themed scrollbar for panels and content."`

- [ ] **Step 7: 시험이 통과하고 기존 렌더 시험도 산다**

Run: `.venv/bin/python -m pytest -q tests/test_review_pack_template_scrollbar.py tests/test_review_pack_explanation_render.py tests/test_review_pack_render.py tests/test_review_pack_navigation.py`
Expected: 모두 PASS (`test_shared_note_shell_and_complete_content` 는 렌더 결과 `<style>` 이 템플릿과 같은지 본다)

- [ ] **Step 8: 커밋한다**

```bash
git add .claude/skills/logic-lab-review-pack/assets/note-template.html .claude/skills/logic-lab-review-pack/assets/review-template.html .claude/skills/logic-lab-review-pack/assets/template-provenance.json tests/test_review_pack_template_scrollbar.py
git commit -m "feat(skills): themed panel scrollbar in note templates" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: 발행된 복습노트 실험01~06 에 같은 삽입

**Files:**
- Modify: `복습노트/실험0{1..6}/실험0N_실험설명.html`, `실험0N_문제설명.html` (12개, 텍스트 삽입)
- Modify: `복습노트/실험0{1..6}/자료/assets/note-template.html`, `review-template.html`, `template-provenance.json` (18개, 스킬 assets 에서 바이트 복사)
- Test: `tests/test_review_pack_template_scrollbar.py` (시험 둘 추가)

**Interfaces:**
- Consumes: Task 1 의 `insert_scrollbar(text: str) -> str`, `check_scrollbar(text: str, cards: bool) -> None`
- Produces: 없음

- [ ] **Step 1: 실패하는 시험 둘을 추가한다**

```python
PACKS = sorted(Path('복습노트').glob('실험0[1-6]'))
CARD_RULE = '    .table-card { margin: var(--s4) 0;'

@pytest.mark.parametrize('page', [p for f in PACKS for p in (f/f'{f.name}_실험설명.html', f/f'{f.name}_문제설명.html')], ids=str)
def test_발행물_스크롤바(page):
    text = page.read_text(encoding='utf-8')
    check_scrollbar(text, cards=CARD_RULE in text)

@pytest.mark.parametrize('folder', PACKS, ids=str)
def test_팩_템플릿_사본은_스킬과_같다(folder):
    for name in ('note-template.html', 'review-template.html', 'template-provenance.json'):
        assert (folder/'자료/assets'/name).read_bytes() == (ASSETS/name).read_bytes()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `.venv/bin/python -m pytest -q tests/test_review_pack_template_scrollbar.py`
Expected: 새 시험 18개 FAIL, Task 1 의 4개 PASS

- [ ] **Step 3: 페이지 12개에 `insert_scrollbar` 를 적용한다**

- [ ] **Step 4: 사본 18개를 복사한다**

```bash
for n in 01 02 03 04 05 06; do cp .claude/skills/logic-lab-review-pack/assets/{note-template.html,review-template.html,template-provenance.json} "복습노트/실험$n/자료/assets/"; done
```

- [ ] **Step 5: diff 모양과 멱등성을 본다**

Run: `git diff --numstat -- 복습노트`
Expected: `실험0[1-5]_실험설명.html` 와 `review-template.html` 사본은 `8 0`; `실험06_실험설명.html`·문제설명 6개·`note-template.html` 사본은 `13 0`; provenance 사본 6개만 소폭 변경. 스크립트를 한 번 더 돌린 뒤 같은 명령의 출력이 바뀌지 않아야 한다.

- [ ] **Step 6: 시험과 팩 검사가 기준선보다 나빠지지 않는다**

Run: `.venv/bin/python -m pytest -q tests -k "review_pack or workbook" 2>&1 | tail -5`
Expected: 새 시험 22개 PASS, 실패 목록이 `baseline.txt` 와 같다.

Run: `.venv/bin/python -c "from pathlib import Path; from scripts.lab.review_pack.checks import check_pack; [print(f, check_pack(f)) for f in sorted(Path('복습노트').glob('실험0[1-6]'))]"`
Expected: 출력이 `baseline-check-pack.txt` 와 같다 — 특히 `explanation differs from authored content` 가 새로 생기지 않는다.

Run: `.venv/bin/python -m scripts.lab.review_pack.navigation_upgrade --all`
Expected: 바뀔 파일 없음(드라이런)

- [ ] **Step 7: 브라우저로 테마 전환을 본다**

내장 브라우저로 `복습노트/실험06/실험06_문제설명.html` 을 연다. `document.documentElement.dataset.theme` 를 `light` → `dark` 로 바꾸며 `getComputedStyle(document.querySelector('.content')).scrollbarColor` 의 첫 색이 `rgb(201, 208, 219)`(#c9d0db) → `rgb(63, 65, 75)`(#3f414b) 로 바뀌고 둘째 색이 투명인지, 같은 값이 `.table-card` 하나에서도 나오는지 확인한다(카드가 없으면 `.panel-inner` 로 대신하고 그렇게 보고한다).

- [ ] **Step 8: 커밋한다**

```bash
git add tests/test_review_pack_template_scrollbar.py
for n in 01 02 03 04 05 06; do git add "복습노트/실험$n/실험${n}_실험설명.html" "복습노트/실험$n/실험${n}_문제설명.html" "복습노트/실험$n/자료/assets/note-template.html" "복습노트/실험$n/자료/assets/review-template.html" "복습노트/실험$n/자료/assets/template-provenance.json"; done
git commit -m "docs(notes): themed scrollbar in existing note HTML" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

병합·push 하지 않고 브랜치에서 멈춘다.
