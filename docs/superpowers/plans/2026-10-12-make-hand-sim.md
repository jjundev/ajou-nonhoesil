# make-hand-sim 스킬 (손그림모사 + 부품 그리기 PDF) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 실험 하나를 받아 그 실험 `FINALS` 전부로 `실험NN_손그림모사.pdf`·`실험NN_부품그리기.pdf` 두 개를 `결선도/팀원전달용/` 에 내는 `hand_sim` CLI 와 `make-hand-sim` 스킬을 만들고, v2 판형 실험05 로 실제로 뽑는다.

**Architecture:** 엔진(`hand`·`hand_guide`, `_blank_parts`)은 그대로 쓴다. 주차 `배치.py` 의 완성본 빌더가 두 인자를 렌더러로 넘기기만 하면 된다(make-trace-guide 의 `layer` 와 같은 패턴). `scripts/lab/hand_sim.py` 는 실험 단위로 다시 짜서, 임시 폴더에서 PNG 를 뽑아 두 PDF 로 싣고 쪽 검사를 통과한 뒤에만 출력 폴더로 옮긴다.

**Tech Stack:** Python 3 (`.venv`), Pillow, pypdf, headless Chrome(`scripts.lab.html2pdf.html_to_pdf`), unittest.

**Spec:** 2026-10-12 세션의 grill-yourself 설계(채팅). 아래 '설계 요약' 이 그 사본이다 — 확정 #9 팀원전달용/ 커밋, #10 210×420mm, #11 `make-hand-sim`.

## 설계 요약

- 산출물: 실험 하나 → PDF 둘, 완성본 하나 = 각 PDF 의 한 쪽.
  - `보고서/실험NN/결선도/팀원전달용/실험NN_손그림모사.pdf` — 쪽마다 제목 + 손그림 모사 그림(흔들린 선, 칩·LED·저항·입력 이름 비움).
  - `보고서/실험NN/결선도/팀원전달용/실험NN_부품그리기.pdf` — 쪽마다 제목 + 범례 + 안내판 그림(회색 선, 그릴 부품만 색) + 부품표.
- PNG 는 임시 폴더에만 — `결선도/` 에 도장·사이드카 없는 PNG 를 두지 않는다.
- 단계 그림에 `hand` 를 주면 빌더가 거절한다.
- 빌더가 `hand_guide` 를 안 받으면 그 빌더 이름을 모두 대고 `SystemExit`. PDF 검사 실패도 `SystemExit` 한 문장, 출력 폴더엔 아무것도 안 쓴다.
- 이번 회차 밖: 부품 윤곽·손글씨 흉내(521a17a 로 거절됨), 단계·층·걷기 보드, 실험04 v2 재작도, `connect_unused_inputs`·`instrument` 손그림 대응, 병합·push.

## Global Constraints

- 작업 트리: `/Users/hyunjun_macbook_pro/Documents/Univ/논회실-hand-sim`, 브랜치 `feat/hand-diagram-sim`. 병합·push 하지 않는다.
- 파이썬은 `.venv/bin/python`. 시험은 `.venv/bin/python -m pytest`.
- 쪽 판형: `@page { size: 210mm 420mm; margin: 12mm 10mm; }` (`scripts/lab/trace_guide.py:37` 과 같다).
- 출력 폴더 이름 `팀원전달용` 은 `trace_guide.OUT_DIR` 을 가져다 쓴다.
- 파일 이름: `{config.experiment_folder_name(N)}_손그림모사.pdf`, `{…}_부품그리기.pdf`.
- 범례 문구는 지금 `hand_sim.LEGEND` 그대로(cfe7219 의 '다리' 문구 포함).
- 시드는 `hand_seed(<완성본 이름의 '결선도' → '손그림모사'>)` — 시험판과 안내판이 같은 시드.
- `hand=None` 렌더는 픽셀 불변 — 실험04·05 의 `BOARDS`·`FINALS` 전 장.
- 시험은 절대 기본 출력 폴더(`팀원전달용/`)에 쓰지 않는다 — 언제나 `--out-dir <tmp>`.
- 코드 주석·문서·커밋 메시지는 한국어. 커밋 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. 시험이나 사용자가 `--out-dir` 없이 돌리면 커밋된 PDF 를 덮는다 — 기본 경로는 `output_paths(N)` 하나에서만 정해지고, 시험은 그 함수 값만 확인하고 실제로 쓰지 않아야 한다(036f6a3 의 실험01 제출본 덮어쓰기와 같은 사고). → Task 2 `test_기본_출력은_팀원전달용`.
2. 실험05 BCD 의 부품표는 약 25행(칩 1·LED 10·저항 10·입력 4)이라 한 쪽을 넘칠 수 있다 — 넘치면 조용히 2쪽이 아니라 멈춰야 한다. → Task 2 `test_실험05_PDF_둘은_완성본마다_한_쪽`, `test_PDF_검사가_실패하면_아무것도_안_쓴다`.
3. v2 `_input_jumper` 는 배지 자리를 `tag_boxes` 에 잡았다 놓는다(`helpers.py:78-85`) — 배지를 비워도 배치가 평소와 같아야 한다. → Task 1 `test_실험05_hand_는_배치를_안_바꾼다`.
4. 실험04 처럼 `FINALS` 일부만 `hand` 를 받는 실험을 `--final` 없이 돌리면 앞 완성본만 뽑고 터지면 안 된다 — 렌더 전에 전부 검사. → Task 2 `test_hand_를_못_받는_빌더는_이름을_다_대고_멈춘다`.
5. 다시 뽑은 PDF 가 타임스탬프만 다르면 커밋하지 않는다(메모리 규칙) — 스킬 문서 절차에 쪽 수·텍스트 해시 비교를 적는다. → Task 3 Step 1.

---

### Task 1: 실험05 완성본 빌더가 `hand`·`hand_guide` 를 받는다

**Files:**
- Modify: `보고서/실험05/결선도/배치.py:105-117` (`build_e5_bcd`), `:195-209` (`build_e5_xs3`)
- Test: `tests/test_breadboard_hand.py` (새 클래스 `HandRenderE5`)

**Interfaces:**
- Produces: `build_e5_bcd(output_path, template_path=None, stage=None, baseline=None, layer=None, hand=None, hand_guide=False) -> BreadboardRenderer`, `build_e5_xs3(...)` 같은 꼴. `hand` 가 있고 `stage` 가 있으면 `ValueError('hand 는 완성본(stage=None)에만 준다')`.

- [ ] **Step 1: 실패하는 시험을 쓴다** — `HandRenderE5(unittest.TestCase)`, `setUpClass` 에서 `cls.mod = _load(); cls.board = cls.mod.load_board(5)`. 헬퍼 `_render(self, name, hand, guide=False)` 는 `getattr(self.board, name)(str(tmp / 'x.png'), hand=hand, hand_guide=guide)` 를 돌려준다(tmp 는 `addCleanup` 으로 지움). `_count` 는 `HandRender._count` 와 같은 식.

```python
BUILDERS = ('build_e5_bcd', 'build_e5_xs3')

def test_실험05_hand_는_배치를_안_바꾼다(self):
    for name in BUILDERS:
        a, b = self._render(name, None), self._render(name, 42)
        for attr in ('steps', '_segments', '_leads', 'tag_boxes', 'chips', 'leds', 'resistors', 'inputs'):
            self.assertEqual(getattr(a, attr), getattr(b, attr), (name, attr))

def test_실험05_단계에_hand_는_거절(self):
    with self.assertRaises(ValueError):
        self.board.build_e5_bcd(str(Path(tempfile.mkdtemp()) / 'x.png'), stage=1, hand=1)

def test_실험05_부품과_입력_이름은_비운다(self):
    for name in BUILDERS:
        plain, bb = self._render(name, None), self._render(name, 42)
        for rgba in [(30, 33, 36, 255), (220, 20, 20, 240), (225, 195, 145, 255)]:
            self.assertGreater(self._count(plain, rgba), 0, (name, rgba))
            self.assertEqual(self._count(bb, rgba), 0, (name, rgba))
        self.assertGreater(self._count(bb, self.mod.INPUT), 0, name)

def test_실험05_안내판_선은_회색(self):
    for name in BUILDERS:
        bb = self._render(name, 42, guide=True)
        for col in self.mod.WIRE.values():
            self.assertEqual(self._count(bb, col), 0, (name, col))
        self.assertGreater(self._count(bb, self.mod.KEEP), 0, name)
        self.assertGreater(self._count(bb, (30, 33, 36, 255)), 0, name)   # 칩은 색
```

(몸통 RGBA 가 v2 에서 다르면 `renderer.py` `_draw_chip`·`_draw_led`·`_draw_resistor` 의 채움 색을 읽어 바꾸고 ledger 에 Ruling.)

- [ ] **Step 2: 돌려 실패를 본다**
Run: `.venv/bin/python -m pytest tests/test_breadboard_hand.py -k 실험05 -v`
Expected: FAIL — `TypeError: build_e5_bcd() got an unexpected keyword argument 'hand'` (거절 시험도 TypeError 라 실패).

- [ ] **Step 3: 두 빌더에 인자를 단다** — 시그니처 끝에 `hand=None, hand_guide=False`, 첫 줄 가드 옆에 `if hand is not None and stage is not None: raise ValueError('hand 는 완성본(stage=None)에만 준다')`, `BreadboardRenderer(..., hand=hand, hand_guide=hand_guide)`. `build_e4_mux` 의 꼴을 그대로 따른다.

- [ ] **Step 4: 시험 통과**
Run: `.venv/bin/python -m pytest tests/test_breadboard_hand.py -v`
Expected: PASS 33개(기존 29 + 새 4).

- [ ] **Step 5: `hand=None` 픽셀 불변** — scratchpad 의 `px.py`(이번 세션 것: 각 빌더 렌더를 sha256 으로 찍음)를 실험05 `BOARDS`·`FINALS` 전 장으로 넓혀 `git stash` 상태와 지금 상태에서 각각 돌리고 `diff`.
Expected: 해시 줄 차이 0(임시 경로 줄만 다름).

- [ ] **Step 6: 커밋**
```bash
git add 보고서/실험05/결선도/배치.py tests/test_breadboard_hand.py
git commit -m "feat(실험05): 완성본 빌더가 손그림 모사 hand·hand_guide 를 받는다"
```

---

### Task 2: `hand_sim` 이 실험 하나로 PDF 둘을 낸다

**Files:**
- Modify: `scripts/lab/hand_sim.py` (통째로 다시 씀 — 아래 인터페이스가 최종 파일 형태)
- Test: `tests/test_breadboard_hand.py` (`HandSimScript` 고침)

**Interfaces:**
- Consumes: Task 1 의 실험05 빌더 시그니처, 기존 `build_e4_mux(..., hand, hand_guide)`.
- Produces (최종 `hand_sim.py` 의 공개 이름):
  - `LEGEND: str` — 지금 값 그대로.
  - `CSS: str` — `@page { size: 210mm 420mm; margin: 12mm 10mm; }`, `.page { break-after: page; } .page:last-child { break-after: auto; }`, 손그림모사 그림 `img.sim { max-height: 390mm }`, 안내판 그림 `img.guide { max-height: 250mm }`, 표는 지금 9pt 그대로.
  - `hand_seed(filename: str) -> int` — 그대로.
  - `guide_rows(bb) -> list[tuple[str, str, str]]` — 그대로.
  - `output_paths(experiment: int) -> tuple[Path, Path]` — `(…/팀원전달용/실험NN_손그림모사.pdf, …/실험NN_부품그리기.pdf)`, 경로는 `trace_guide.output_path` 와 같은 식(`config.experiment_dir`, `config.experiment_folder_name`, `trace_guide.OUT_DIR`).
  - `render_final(fn, final_name: str, work_dir: Path) -> tuple[bb, Path, Path]` — `(안내판 bb, 손그림모사 png, 부품그리기 png)`; png 이름은 `final_name` 의 `'결선도'` 를 `'손그림모사'`·`'부품그리기'` 로.
  - `render_handout_html(title: str, pages: list[tuple[str, str]]) -> str` — `pages = [(쪽 제목, 이미지 이름)]`.
  - `render_guide_html(title: str, pages: list[tuple[str, str, list]]) -> str` — `pages = [(쪽 제목, 이미지 이름, guide_rows)]`; 쪽 제목은 `f'{bb.title} — 부품 그리기'`, 손그림모사 쪽 제목은 `bb.title`.
  - `check_pdf(path, n: int) -> None` — 쪽별 그림 수가 `[1] * n` 이 아니면 `ValueError(f'{path.name} 가 {len}쪽(쪽별 그림 {counts})이다 — 완성본 {n}장에 한 쪽씩이어야 한다')`. (`check_guide_pdf` 는 없앤다.)
  - `make_pdfs(finals: list[tuple[str, callable]], handout_out: Path, guide_out: Path, title: str) -> tuple[Path, Path]` — 렌더·HTML·`html_to_pdf`·`check_pdf` 둘 다 `TemporaryDirectory` 안에서, 둘 다 통과한 뒤에만 `out` 으로 복사(부모 폴더는 `mkdir(parents=True, exist_ok=True)`). `title` 은 `f'{folder} 손그림모사'` 식 문서 제목의 머리.
  - `main(argv=None) -> tuple[Path, Path]` — CLI `--experiment N`(필수), `--final NAME`(`action='append'`, 생략이면 `FINALS` 전부), `--out-dir DIR`(생략이면 `output_paths(N)`, 주면 그 폴더에 같은 파일 이름). 순서: ① 없는 `--final` → `SystemExit` 에 가능한 이름 목록(기존 문구), ② 고른 빌더 중 `hand_guide` 를 안 받는 것 전부의 `__name__` 을 모아 `SystemExit(f'{names} 가 hand_guide 를 안 받는다 — make-hand-sim 스킬 §빌더 단계로 배치.py 에 인자를 단다')` — 아무것도 렌더하기 전에, ③ `make_pdfs`, `ValueError` → `SystemExit(str(e))`.

- [ ] **Step 1: 시험을 새 CLI 에 맞춰 고쳐 쓴다** — `HandSimScript` 에서 `test_완성본_한_장을_뽑는다`·`test_안내_PDF_는_한_쪽에_그림_하나`·`test_넘친_PDF_는_거절한다`·`test_안내판을_못_받는_빌더는_이름과_함께_멈춘다` 를 아래로 바꾼다. 나머지(`시드`, `없는_완성본`, `부품표…` 둘)는 둔다.

```python
def _run(self, *args):
    from scripts.lab import hand_sim
    tmp = Path(tempfile.mkdtemp()); self.addCleanup(shutil.rmtree, tmp)
    return hand_sim.main([*args, '--out-dir', str(tmp)]), tmp

def test_기본_출력은_팀원전달용(self):
    from scripts.lab import hand_sim
    sim, guide = hand_sim.output_paths(5)
    base = ROOT / '보고서/실험05/결선도/팀원전달용'
    self.assertEqual((sim, guide), (base / '실험05_손그림모사.pdf', base / '실험05_부품그리기.pdf'))

def test_실험04_MUX_한_장(self):
    from pypdf import PdfReader
    (sim, guide), tmp = self._run('--experiment', '4', '--final', '실험04_1-1_결선도_4x1MUX.png')
    self.assertEqual(sorted(p.name for p in tmp.iterdir()), ['실험04_부품그리기.pdf', '실험04_손그림모사.pdf'])
    self.assertEqual([len(p.images) for p in PdfReader(str(sim)).pages], [1])
    pages = PdfReader(str(guide)).pages
    self.assertEqual([len(p.images) for p in pages], [1])
    text = pages[0].extract_text()
    for s in ('회색 선은 이미 그려져 있어요', '다리', '74HC04'):
        self.assertIn(s, text)

def test_실험05_PDF_둘은_완성본마다_한_쪽(self):
    from pypdf import PdfReader
    (sim, guide), _ = self._run('--experiment', '5')
    self.assertEqual([len(p.images) for p in PdfReader(str(sim)).pages], [1, 1])
    pages = PdfReader(str(guide)).pages
    self.assertEqual([len(p.images) for p in pages], [1, 1])
    self.assertIn('74HC42', pages[0].extract_text())
    self.assertIn('74HC20', pages[1].extract_text())

def test_PDF_검사가_실패하면_아무것도_안_쓴다(self):
    from unittest import mock
    from scripts.lab import hand_sim
    with mock.patch.object(hand_sim, 'check_pdf', side_effect=ValueError('넘침')):
        with self.assertRaises(SystemExit) as cm:
            self._run('--experiment', '4', '--final', '실험04_1-1_결선도_4x1MUX.png')
    self.assertIn('넘침', str(cm.exception))
    self.assertEqual(list(self._last_tmp.iterdir()), [])

def test_넘친_PDF_는_거절한다(self):
    # 빈 쪽 두 장짜리 PDF 를 만드는 부분은 기존 시험 그대로
    with self.assertRaises(ValueError):
        hand_sim.check_pdf(tmp / 'two.pdf', 1)

def test_hand_를_못_받는_빌더는_이름을_다_대고_멈춘다(self):
    with self.assertRaises(SystemExit) as cm:
        self._run('--experiment', '4')          # FINALS 중 DMUX 가 hand 를 안 받는다
    self.assertIn('build_e4_dmux', str(cm.exception))
    self.assertIn('make-hand-sim', str(cm.exception))
```

`_run` 은 `main` 을 부르기 전에 `self._last_tmp = tmp` 를 남긴다 — 실패 시험이 빈 폴더를 확인하는 데 쓴다. DMUX 빌더 이름 `build_e4_dmux` 는 실험04 `배치.py:470` 에서 확인했다.

- [ ] **Step 2: 돌려 실패를 본다**
Run: `.venv/bin/python -m pytest tests/test_breadboard_hand.py -k HandSimScript -v`
Expected: 새·고친 시험이 FAIL(`unrecognized arguments: --out-dir`, `output_paths` 없음 등). `시드`·`없는_완성본`·`부품표` 시험은 PASS.

- [ ] **Step 3: `scripts/lab/hand_sim.py` 를 위 인터페이스로 다시 쓴다** — 모듈 docstring 을 새 CLI(`--experiment 5` 한 줄 예시, 두 PDF, PNG 는 임시 폴더)로 바꾼다. `--guide`·`--out`·`check_guide_pdf`·`make_guide_pdf` 는 없앤다.

- [ ] **Step 4: 시험 통과**
Run: `.venv/bin/python -m pytest tests/test_breadboard_hand.py -v`
Expected: 전부 PASS.

- [ ] **Step 5: 전체 시험**
Run: `.venv/bin/python -m pytest -q > <workspace>/suite.txt 2>&1; tail -5 <workspace>/suite.txt`
Expected: 실패는 기존 둘(실험06 `test_완성본끼리_빌더를_공유하지_않는다`, `test_review_pack_work_table`)뿐.

- [ ] **Step 6: 커밋**
```bash
git add scripts/lab/hand_sim.py tests/test_breadboard_hand.py
git commit -m "feat(hand-sim): 실험 하나로 손그림모사·부품그리기 PDF 둘을 팀원전달용에 낸다"
```

---

### Task 3: `make-hand-sim` 스킬 문서 + 실험05 실물

**Files:**
- Create: `.claude/skills/make-hand-sim/SKILL.md`
- Create (생성물): `보고서/실험05/결선도/팀원전달용/실험05_손그림모사.pdf`, `…/실험05_부품그리기.pdf`

**Interfaces:**
- Consumes: Task 2 의 CLI(`python -m scripts.lab.hand_sim --experiment N [--final NAME]... [--out-dir DIR]`)와 오류 문구 속 `make-hand-sim 스킬 §빌더`.

- [ ] **Step 1: `SKILL.md` 를 쓴다** — 꼴은 `.claude/skills/make-trace-guide/SKILL.md` 를 따른다(frontmatter → 한 단락 요약 → 인자 → 고치는 파일 → 절차 → 규칙과 근거 → 넓힐 때 손볼 곳). 반드시 들어갈 내용:
  - frontmatter `name: make-hand-sim`; `description` 에 트리거 "손그림모사 만들어줘", "부품 그리기 안내", "팀원이 칩·LED·저항만 그리게", "/make-hand-sim", 그리고 구분 문구 "(결선도 전체를 따라 그리게 하는 것은 make-trace-guide, 그린 결과 검토는 review-hand-diagram)".
  - 인자 `<실험번호|N주차> [회로 이름]` — 주차 해석은 make-trace-guide 와 같은 규칙(문단을 그대로 옮기지 말고 "make-trace-guide §인자 와 같다" + `config.experiments_in_week` 한 줄).
  - 고치는 파일: 그 주차 `배치.py` 완성본 빌더의 `hand`·`hand_guide` 인자, `팀원전달용/` 의 두 PDF — 이 둘뿐. 엔진·`hand_sim.py`·공용 시험이 실패하면 고치지 말고 명령·출력 끝을 보고하고 멈춘다.
  - §빌더: 시그니처 끝에 `hand=None, hand_guide=False`, `stage` 와 함께면 `ValueError`, `BreadboardRenderer(..., hand=hand, hand_guide=hand_guide)` — 실험05 `build_e5_bcd` 를 예로 가리킨다.
  - §실행: `.venv/bin/python -m scripts.lab.hand_sim --experiment N`.
  - §눈으로 확인: 두 PDF 를 쪽마다 `Read` 로 연다. 손그림모사 — 칩·LED·저항·입력 이름 배지·번호 원이 없고 보라 입력선은 있다. 부품그리기 — 색 선이 하나도 없고(전부 회색), 칩·LED·저항·입력 이름이 색이며, 부품표가 쪽 안에서 끝난다.
  - §커밋: 다시 뽑은 PDF 는 쪽 수·`extract_text` 해시가 커밋본과 같으면 되돌린다(`git checkout`) — 타임스탬프만 다른 재생성은 커밋하지 않는다.
  - 규칙과 근거(이 세션 기록): 선만 코드가 긋고 칩·LED·저항·글자는 사람이 그린다(사용자 결정, 521a17a 로 손글씨·윤곽 흉내 되돌림 — 다시 제안하지 않는다) · 입력 점퍼선은 남기고 이름 배지만 비운다(5187ba6) · 비우기는 `_blank_parts` + `_NullDraw` — 픽셀만 버리고 기록·배치는 같아 `verify()` 불변 · 안내판은 같은 시드의 흔들림을 `KEEP` 회색으로, `_in_parts` 안의 배지만 제 색(cbca160) · 범례의 "회색 다리도 부품과 함께" 는 리뷰에서 팀원이 다리를 빠뜨릴 위험으로 올려 고침(cfe7219) · 시드 = 손그림모사 파일 이름의 sha256 → 다시 뽑아도 같다 · PNG 는 `결선도/` 에 두지 않는다(도장·사이드카 없는 PNG 를 검사가 정본으로 읽는다) · 판형: 실험05~ 는 v2(`config.BOARD_V2_FROM`), 실험04 MUX(v1)는 시험판 고정용 · 쪽은 210×420mm 태블릿 판.
  - 넓힐 때 손볼 곳: `connect_unused_inputs` 의 곧은 선(`renderer.py` `draw.line`), `instrument` 프로브 리드·원·번호가 안내판에서도 제 색, `_in_parts` 가 중첩 호출에 안전하지 않음, 실험04 DMUX 는 `hand` 를 아직 안 받음.

- [ ] **Step 2: 실험05 를 뽑는다**
Run: `.venv/bin/python -m scripts.lab.hand_sim --experiment 5`
Expected: 종료 코드 0, `보고서/실험05/결선도/팀원전달용/` 에 두 PDF.

- [ ] **Step 3: 쪽 검사와 눈 확인**
Run: `.venv/bin/python -c "from pypdf import PdfReader; import sys; [print(p, [len(x.images) for x in PdfReader(p).pages]) for p in sys.argv[1:]]" 보고서/실험05/결선도/팀원전달용/실험05_손그림모사.pdf 보고서/실험05/결선도/팀원전달용/실험05_부품그리기.pdf`
Expected: 둘 다 `[1, 1]`. 그다음 두 PDF 4쪽을 `Read` 로 열어 Step 1 §눈으로 확인 항목을 하나씩 확인하고 결과를 ledger 에 적는다. 어긋나면 엔진 결함 — Task 1·2 로 돌아가 시험부터 쓴다.

- [ ] **Step 4: `git status` 로 `결선도/` 에 새 PNG·JSON 이 없는지 확인**
Expected: 새 파일은 `SKILL.md` 와 두 PDF 뿐.

- [ ] **Step 5: 커밋**
```bash
git add .claude/skills/make-hand-sim/SKILL.md 보고서/실험05/결선도/팀원전달용/실험05_손그림모사.pdf 보고서/실험05/결선도/팀원전달용/실험05_부품그리기.pdf
git commit -m "feat(make-hand-sim): 손그림모사·부품 그리기 PDF 스킬을 쓰고 실험05 로 뽑는다"
```
