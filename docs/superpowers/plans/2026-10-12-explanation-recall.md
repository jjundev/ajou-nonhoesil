# 문제설명 "이 문제를 보면 떠올려요" 영역 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 논회실 문제설명(`실험NN_문제설명.html/.md`)의 모든 문항에 "이 문제를 보면 떠올려요" 영역(`data-explanation="recall"`)을 필수로 넣고, 이미 발행한 실험01~06(86문항)에도 소급한다.

**Architecture:** 영역 계약은 `explanation_content.validate_fragment` 한 곳에서 강제한다. 렌더러·MD 변환·발행 검사는 조각을 그대로 이어 붙이고 다시 렌더해 대조하므로 손대지 않는다. 기존 팩은 저작 조각을 고친 뒤 `explain-stage` → 검토 → `publish`로 교체한다. 문제지·해설지·PDF는 바뀌지 않는다.

**Tech Stack:** Python 3.14 표준 라이브러리, pytest(+xdist), Playwright(브라우저 검사), 기존 note-template.

**Spec:** 설계는 2026-10-12 대화에서 확정했고 파일로 따로 저장하지 않았다. 아래 "설계 요약"과 Global Constraints가 그 사본이다.

## 설계 요약

- 영역 위치: 문제 읽기 바로 다음, understand 앞. 조각의 **첫** `data-explanation` 영역이다.
- 마크업(고정):
  ```html
  <div class="layer eli5" data-explanation="recall"><span class="layer-title">이 문제를 보면 떠올려요</span><p class="lead cue">구절</p><p>문제의 “…”를 보면 …를 떠올려요. …이기 때문이에요.</p></div>
  ```
  굵기는 기존 `.layer.eli5 .lead`(note-template.html:84)가 준다. 템플릿은 고치지 않는다.
- `div.sum`의 첫 `<p>`: `<p><strong>떠올릴 것:</strong> 구절</p>`
- 문항당 구절 1개. 버전으로 가르지 않고 항상 필수다(6개 팩을 같은 라운드에 소급).
- 결정: Hint 띠 라벨 교체 안 함, 문항당 1개, 제목 "이 문제를 보면 떠올려요".

## Global Constraints

- 구절(`p.cue`): 자식 태그 없음, 앞뒤 공백 제거 후 1~60자(원문 문자 수, `$…$` 소스 포함), `$$` 금지, 명사형 한 구절.
- recall 영역: `p.cue` 정확히 1개 + cue 외 비어 있지 않은 `<p>` 1개 이상. 설명 문장은 ‘~해요’체로 "문제 속 단서 → 떠올릴 것 → 이유"를 담는다.
- 영역 제목 문구: `이 문제를 보면 떠올려요` (그대로).
- sum 첫 줄 접두어: `떠올릴 것:` (그대로).
- 구절은 그 문항 풀이의 실제 첫 판단과 맞아야 한다. 원문에 없는 조건을 끌어오지 않는다. disputed·unresolved 문항에서는 다툼이 있는 답을 사실처럼 단정하지 않는다.
- 문제지·해설지(`기출문제`, `기출풀이`) HTML·PDF 바이트 불변. PDF 재생성 금지.
- independent=pass는 리뷰어가 실제로 검토한 범위에만 쓴다. 01~05는 not_run 유지, 06은 recall 리뷰 후 pass 유지.
- 작업은 git worktree `../논회실-recall`(브랜치 `feat/explanation-recall`)에서. `.venv`는 원본 저장소의 것을 심볼릭 링크한다. push 금지(요청 시에만).
- 테스트 명령 기본형: `.venv/bin/python -m pytest -q <파일>`. xdist가 없으면 `-o addopts=""`를 붙인다.

## Review Focus

1. **문제 읽기 → recall 사이 간격.** 이제 문제 읽기 바로 뒤 레이어가 recall이므로, 기존 understand 간격 규칙(≥48px)이 recall에도 성립해야 한다 → Task 5의 브라우저 테스트가 `[data-explanation="recall"]`에 `assert_explanation_section_gap`을 건다.
2. **구절 속 프라임·엔티티(`Q′`, `&lt;`).** 길이는 디코드된 텍스트로 센다 → Task 1 `test_recall_cue_length_counts_decoded_text`.
3. **구절 속 inline 식(`$\overline{S}$`)이 KaTeX 오류 없이 굵게 렌더.** → Task 5 브라우저 테스트의 기존 `.katex-error` 0 검사를 6개 팩 전부로 넓힌다.
4. **MD에 구절과 `떠올릴 것:`이 남는가.** → Task 1 `test_recall_exported_to_md`.
5. **375px에서 긴 구절의 가로 넘침.** → Task 5 브라우저 테스트의 기존 `scrollWidth<=innerWidth` 검사를 실험06까지 넓힌다.

---

### Task 0: 작업 트리와 테스트 환경

**Files:** 없음(환경만)

- [ ] **Step 1: worktree 생성**

```bash
git worktree add ../논회실-recall -b feat/explanation-recall main
ln -s "$PWD/.venv" ../논회실-recall/.venv
```
이후 모든 명령은 `../논회실-recall`에서 실행한다.

- [ ] **Step 2: 테스트 의존성 확인**

Run: `.venv/bin/python -c "import pytest, xdist, playwright"`
실패하면 `.venv/bin/pip install -r requirements-dev.txt playwright`를 실행한다. Chromium은 `~/Library/Caches/ms-playwright/chromium-1243`에 있다.
Expected: 오류 없이 종료.

- [ ] **Step 3: 기준선**

Run: `.venv/bin/python -m pytest -q tests/test_review_pack_explanation_content.py tests/test_review_pack_explanation_render.py tests/test_review_pack_explanation_stage.py`
Expected: 모두 PASS(현재 content 21 passed).

---

### Task 1: recall 계약·검사·문서

**Files:**
- Modify: `scripts/lab/review_pack/explanation_content.py:8,28-52`
- Modify: `tests/test_review_pack_explanation_content.py:8-14,64-68`
- Modify: `tests/fixtures/review_pack/explanations/q-mux-001.html`
- Modify: `tests/test_review_pack_explanation_render.py`
- Modify: `.claude/skills/logic-lab-review-pack/SKILL.md`("문제풀이 입문 설명" 절), `.claude/skills/logic-lab-review-pack/references/authoring.md:42-53`, `.claude/skills/logic-lab-review-pack/references/verification.md:38-50`

**Interfaces:**
- Produces:
  - `SECTIONS = ('recall','understand','start','solve','verify','pitfall','retry')`
  - `RECALL_CUE_MAX = 60`
  - `recall_cue(fragment: str) -> str` — 조각의 `p.cue` 텍스트(strip). 없으면 `ValueError`. Task 4 리뷰 목록과 테스트가 쓴다.
  - `validate_fragment(fragment, ident, state)`의 새 오류 메시지(모두 `ident+': '` 접두):
    `recall must be first` / `recall requires one cue` / `cue must be 1-60 plain characters` / `recall requires a reason paragraph` / `summary must start with 떠올릴 것`

- [ ] **Step 1: 테스트 픽스처 갱신**

`FRAGMENT`(content 테스트)와 `q-mux-001.html` 맨 앞에 넣는다:
```html
<div class="layer eli5" data-explanation="recall"><span class="layer-title">이 문제를 보면 떠올려요</span><p class="lead cue">선택선 값 = 고를 입력 번호</p><p>문제에 선택선 S가 보이면 S의 값이 곧 출력으로 나갈 입력 번호라는 걸 떠올려요.</p></div>
```
sum을 `<div class="sum" hidden><p><strong>떠올릴 것:</strong> 선택선 값 = 고를 입력 번호</p><p>S를 읽고 입력을 골라요.</p></div>`로 바꾼다.

- [ ] **Step 2: 실패 테스트 작성** (`tests/test_review_pack_explanation_content.py`)

```python
CUE='<p class="lead cue">선택선 값 = 고를 입력 번호</p>'

def write(root,m,body):(root/m['problems'][0]['explanation_fragment']).write_text(body)

# 기존 파라미터에 'recall' 추가
@pytest.mark.parametrize('key',['recall','understand','start','solve','verify','pitfall','retry','sum'])
def test_required_learning_sections(tmp_path,key): ...  # 본문은 그대로

def test_recall_must_be_first(tmp_path):
    m,root,data=setup(tmp_path)
    recall,rest=FRAGMENT.split('\n',1)
    write(root,m,rest.replace('<div class="sum"',recall+'\n<div class="sum"'))
    with pytest.raises(ValueError,match='recall must be first'):load_explanations(m,data,root)

@pytest.mark.parametrize('cue',['', 'x'*61, '$$A$$', '<strong>A</strong>'])
def test_bad_cue_rejected(tmp_path,cue):
    m,root,data=setup(tmp_path)
    write(root,m,FRAGMENT.replace('선택선 값 = 고를 입력 번호</p><p>문제에',cue+'</p><p>문제에'))
    with pytest.raises(ValueError):load_explanations(m,data,root)

def test_two_cues_rejected(tmp_path):
    m,root,data=setup(tmp_path); write(root,m,FRAGMENT.replace(CUE,CUE+CUE,1))
    with pytest.raises(ValueError,match='one cue'):load_explanations(m,data,root)

def test_recall_needs_reason(tmp_path):
    m,root,data=setup(tmp_path)
    write(root,m,FRAGMENT.replace('<p>문제에 선택선 S가 보이면 S의 값이 곧 출력으로 나갈 입력 번호라는 걸 떠올려요.</p>',''))
    with pytest.raises(ValueError,match='reason paragraph'):load_explanations(m,data,root)

def test_summary_must_lead_with_cue(tmp_path):
    m,root,data=setup(tmp_path); write(root,m,FRAGMENT.replace('<p><strong>떠올릴 것:</strong> 선택선 값 = 고를 입력 번호</p>',''))
    with pytest.raises(ValueError,match='떠올릴 것'):load_explanations(m,data,root)

def test_recall_cue_length_counts_decoded_text(tmp_path):
    m,root,data=setup(tmp_path); cue='Q&prime;'+'x'*58   # 디코드 후 60자
    write(root,m,FRAGMENT.replace('선택선 값 = 고를 입력 번호',cue))
    load_explanations(m,data,root)
    assert recall_cue(FRAGMENT)=='선택선 값 = 고를 입력 번호'
```
렌더 테스트(`tests/test_review_pack_explanation_render.py`)에 추가:
```python
def test_recall_exported_to_md(tmp_path):
    # 기존 setup·write_explanations 호출 방식 그대로
    html=paths['explanation_html'].read_text(); md=paths['explanation_md'].read_text()
    assert html.index('data-explanation="recall"')<html.index('data-explanation="understand"')
    assert '이 문제를 보면 떠올려요' in md and '선택선 값 = 고를 입력 번호' in md and '떠올릴 것:' in md
```

- [ ] **Step 3: 실패 확인**

Run: `.venv/bin/python -m pytest -q tests/test_review_pack_explanation_content.py tests/test_review_pack_explanation_render.py`
Expected: 새 테스트들 FAIL(`recall_cue` import 오류 또는 ValueError 미발생).

- [ ] **Step 4: 구현** (`scripts/lab/review_pack/explanation_content.py`)

`SECTIONS` 앞에 `'recall'` 추가, `RECALL_CUE_MAX = 60`, `recall_cue()` 추가. `validate_fragment`의 기존 영역 루프 뒤에서 위 Interfaces의 다섯 검사를 한다. 첫 영역은 `nodes`(문서 순서)에서 `data-explanation`을 가진 첫 노드로 판정한다. cue의 "자식 태그 없음"은 `all(isinstance(c,str) for c in cue.children)`로 판정한다. sum 검사는 sum의 첫 `p` 자식의 `text().strip()`이 `떠올릴 것:`으로 시작하고 cue를 포함하는지 본다.

- [ ] **Step 5: 통과 확인**

Run: `.venv/bin/python -m pytest -q tests/test_review_pack_explanation_content.py tests/test_review_pack_explanation_render.py tests/test_review_pack_explanation_stage.py`
Expected: 전부 PASS.

- [ ] **Step 6: 스킬 문서**

- `authoring.md` "문제설명 저작" 목록 맨 앞에 추가: `recall(eli5): 문제 속 단서를 보면 떠올릴 것. p.lead.cue 구절 1개(태그 없는 60자 이내 명사형, inline $…$만, $$ 금지)와 단서→떠올릴 것→이유 문단. 조각의 첫 영역이다.` 이어서 `직계 div.sum[hidden]` 문장에 "첫 줄은 `<p><strong>떠올릴 것:</strong> 구절</p>`"을 덧붙인다.
- `SKILL.md` "문제풀이 입문 설명" 둘째 문단 끝에 한 줄: `각 문항은 문제 읽기 직후 ‘이 문제를 보면 떠올려요’(recall) 구절로 시작한다(authoring.md).`
- `verification.md` "문제설명 검증"에 한 문단: 구절이 풀이의 실제 첫 판단과 맞는지, 원문 밖 조건을 끌어오지 않는지, disputed·unresolved에서 답을 단정하지 않는지 확인하고, 브라우저 간격 검사는 문제 읽기→recall 경계에도 적용한다.

- [ ] **Step 7: 커밋**

```bash
git add scripts/lab/review_pack/explanation_content.py tests/test_review_pack_explanation_content.py tests/test_review_pack_explanation_render.py tests/fixtures/review_pack/explanations/q-mux-001.html .claude/skills/logic-lab-review-pack
git commit -m "feat(review-pack): 문제설명 각 문항에 '이 문제를 보면 떠올려요' 영역을 필수로 둔다"
```
(커밋 메시지 끝에 attribution 줄을 붙인다.)

---

### Task 2: 실험06 생성기에 recall

**Files:**
- Modify: `docs/learning-pack-source/실험06/explanations.py:13-27` 및 `E[...]` 14개 호출

**Interfaces:**
- Consumes: Task 1의 마크업·sum 규칙, `validate_fragment`
- Produces: `build(pid, cue, why, understand, start, solve, answer, check, pitfall, retry, judge)` — `cue`는 평문 구절, `why`는 `p(...)`로 감싼 HTML. RUN `tmp/review-pack/실험06-recall-<id>/problem-explanations/*.html` 14개(Task 5의 author-root).

- [ ] **Step 1: `build`에 `cue`, `why` 인자 추가**

recall div를 반환 문자열 맨 앞에, sum의 첫 `<p>`로 `<p><strong>떠올릴 것:</strong> {cue}</p>`를 넣는다(설계 요약의 마크업 그대로).

- [ ] **Step 2: 14문항 구절·이유 저작**

각 `E[...]` 호출에 `cue`와 `why`를 넣는다. 근거는 같은 파일의 solve·pitfall과 `PR.PROBLEM_TOPICS[pid]`가 가리키는 실험설명 토픽이다. 예시(그대로 써도 된다):
| pid | cue |
|---|---|
| q-sr-nand-00 | NAND 래치는 0이 활성, S=R=0은 금지 입력 |
| q-diff | 레벨 트리거(동안) 대 엣지 트리거(순간) |
| q-tff | J=K=1이면 토글, J=K=0이면 유지 |
| q-74hc76 | 비동기 CLR·PR은 클럭과 무관하고 Low 활성 |
| q-p-76-trace | 하강 엣지 직전의 J·K만 본다 |

- [ ] **Step 3: RUN 생성과 검증**

Run:
```bash
.venv/bin/python docs/learning-pack-source/실험06/build_run.py tmp/review-pack/실험06-recall-r20261012
.venv/bin/python -c "import sys,pathlib;from scripts.lab.review_pack.explanation_content import validate_fragment,recall_cue;[print(f.stem,'|',recall_cue(t:=f.read_text())) or validate_fragment(t,f.stem,'verified') for f in sorted(pathlib.Path(sys.argv[1]).glob('*.html'))]" tmp/review-pack/실험06-recall-r20261012/problem-explanations
```
Expected: 14줄 `id | 구절` 출력, 예외 없음.

- [ ] **Step 4: 커밋**

```bash
git add docs/learning-pack-source/실험06/explanations.py
git commit -m "feat(실험06): 문제설명 14문항에 떠올릴 구절을 단다"
```

---

### Task 3: 실험01~05 조각에 recall

**Files:**
- Modify: `docs/learning-pack-source/실험0{1..5}/problem-explanations/*.html` (12+14+15+12+19 = 72개)

**Interfaces:**
- Consumes: Task 1의 마크업·sum 규칙, Task 2 Step 3의 검증 명령
- Produces: Task 5의 author-root 5개(각 `docs/learning-pack-source/실험NN/problem-explanations`)

실험마다 아래 Step 1~3을 반복한다(실험별로 독립이라 병렬 가능).

- [ ] **Step 1: 저작**

각 조각 맨 앞에 recall div를, `div.sum` 첫 `<p>`로 `떠올릴 것:` 줄을 넣는다. 근거는 그 조각의 start·solve·pitfall, `복습노트/실험NN/실험NN_기출문제.html` 원문, 같은 폴더 `검증결과.md`의 첫 줄 열이다. disputed·unresolved 문항(Task 5 표 참조)은 다툼이 없는 판단을 구절로 고른다. 기존 영역 본문은 바꾸지 않는다.

- [ ] **Step 2: 검증**

Run: Task 2 Step 3의 두 번째 명령을 `docs/learning-pack-source/실험NN/problem-explanations`에 실행.
Expected: 문항 수만큼 `id | 구절`, 예외 없음.

- [ ] **Step 3: 커밋**

```bash
git add docs/learning-pack-source/실험NN/problem-explanations
git commit -m "feat(실험NN): 문제설명 조각에 떠올릴 구절을 단다"
```

---

### Task 4: recall 독립 리뷰

**Files:**
- Modify: `docs/learning-pack-source/실험0{1..5}/problem-explanations/검증결과.md`, `docs/learning-pack-source/실험06/검증결과.md`

**Interfaces:**
- Consumes: Task 2·3의 86개 조각, `recall_cue`
- Produces: 각 검증결과.md 끝의 `## 떠올릴 구절 검토 (2026-10-12)` 표 — `| 문항 ID | 구절 | 판정 | 메모 |`. Task 5의 `explanation_checks` 기록 근거.

- [ ] **Step 1: 리뷰어 실행**

저작에 관여하지 않은 서브에이전트에게 실험별로 조각, 문제지 원문, Global Constraints의 구절 규칙을 준다. 판정은 `ok` / `fix` 둘 중 하나다.

- [ ] **Step 2: fix 반영**

`fix` 판정 조각을 고치고 Task 2 Step 3 검증 명령을 다시 실행한다. 수정은 최대 2회. 남으면 메모에 미해결로 적는다.

- [ ] **Step 3: 커밋**

```bash
git add docs/learning-pack-source
git commit -m "docs(review-pack): 떠올릴 구절 독립 검토 결과를 적는다"
```

---

### Task 5: 6개 팩 재발행과 발행본 테스트

**Files:**
- Modify: `tests/test_review_pack_explanation_published.py`
- Modify: `tests/test_review_pack_explanation_browser.py:80-100`
- Modify(생성물): `복습노트/실험0{1..6}/실험NN_문제설명.html/.md`, `복습노트/실험NN/자료/problem-explanations/*`, `복습노트/실험NN/자료/manifest.json`

**Interfaces:**
- Consumes: Task 2 RUN, Task 3 author-root, Task 4 검토표
- Produces: 발행된 6개 팩

- [ ] **Step 1: 발행본 실패 테스트**

`test_review_pack_explanation_published.py`:
- `test_experiment_coverage`의 키 튜플에 `'recall'`을 추가한다.
- 새 테스트:
```python
@pytest.mark.parametrize('number',range(1,7))
def test_published_recall(number):
    folder=ROOT/'복습노트'/f'실험{number:02d}'
    tree=Parser();tree.feed((folder/f'실험{number:02d}_문제설명.html').read_text())
    for article in [n for n in tree.root.walk() if n.tag=='article' and 'topic' in n.attrs.get('class','').split()]:
        regions=[n.attrs['data-explanation'] for n in article.walk() if n.attrs.get('data-explanation')]
        assert regions[0]=='recall'
        assert '이 문제를 보면 떠올려요' in text(article)
```
`test_review_pack_explanation_browser.py`: 발행본 순회 테스트의 `range(1,6)`을 `range(1,7)`로 넓히고, 각 문항에 `assert_explanation_section_gap(page, '#'+ident+' [data-explanation="recall"]')`를 추가한다.

Run: `.venv/bin/python -m pytest -q tests/test_review_pack_explanation_published.py`
Expected: `test_published_recall` 6개 FAIL.

- [ ] **Step 2: stage 생성(팩마다)**

```bash
.venv/bin/python -m scripts.lab.review_pack explain-stage --folder 복습노트/실험NN --author-root <author-root> --stage tmp/review-pack/실험NN-recall-stage-r20261012
```
author-root: 01~05는 `docs/learning-pack-source/실험NN/problem-explanations`, 06은 `tmp/review-pack/실험06-recall-r20261012/problem-explanations`(`docs/learning-pack-source/실험06/검증결과.md`를 그 폴더에 먼저 복사).
Expected: 오류 없이 stage 경로 출력(내부에서 `check_pack` 통과).

- [ ] **Step 3: 문제지·해설지 불변 확인**

Run: `cmp 복습노트/실험NN/실험NN_기출문제.html <stage>/실험NN_기출문제.html && cmp 복습노트/실험NN/실험NN_기출풀이.html <stage>/실험NN_기출풀이.html`
Expected: 출력 없음(동일).

- [ ] **Step 4: 브라우저 확인**

stage의 `실험NN_문제설명.html`을 375px/1280px × light/dark로 연다. 확인 항목:
- 모든 문항에서 recall이 문제 읽기 다음에 보이고, 구절이 굵게 나온다.
- 간격이 48px 이상이다.
- `.katex-error`가 0개다.
- 가로 넘침이 없다.
- 우측 요약 첫 줄이 `떠올릴 것:`이다.

- [ ] **Step 5: 검토 기록**

stage의 `자료/manifest.json` `explanation_checks`를 실제 결과로 쓴다.
- 01~05: `source_visual=pass, content=self_review, independent=not_run, browser=pass`
- 06: `independent=pass`. 단, Task 4 표가 06 전부 `ok`일 때만 쓴다.

- [ ] **Step 6: 발행**

```bash
.venv/bin/python -m scripts.lab.review_pack publish --root . --stage <stage> --experiment N
.venv/bin/python -m scripts.lab.review_pack check --folder 복습노트/실험NN
```
Expected: publish가 백업 경로를 보고하고, check는 오류 0이다.

- [ ] **Step 7: 발행본 테스트 통과**

Run: `.venv/bin/python -m pytest -q tests/test_review_pack_explanation_published.py tests/test_review_pack_explanation_browser.py tests/test_review_pack_layout.py`
Expected: 전부 PASS.

- [ ] **Step 8: 커밋**

```bash
git add 복습노트 tests/test_review_pack_explanation_published.py tests/test_review_pack_explanation_browser.py
git commit -m "feat(복습노트): 실험01~06 문제설명에 떠올릴 구절을 반영해 다시 발행한다"
```
`git status`로 PDF가 변경 목록에 없는지 확인한다.

- [ ] **Step 9: 전체 스위트와 병합**

Run: `.venv/bin/python -m pytest -q tests/`
Expected: 기존 알려진 실패 외 PASS. 이후 사용자 확인을 받아 main에 병합한다. push는 하지 않는다.
