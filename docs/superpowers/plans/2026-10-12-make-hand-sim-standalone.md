# make-hand-sim 독립 스킬화 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `make-hand-sim` 을 SKILL.md 하나만 읽고 끝까지 실행할 수 있게 한다 — `make-trace-guide` 문서 참조 두 곳을 본문으로 옮기고, `hand_sim.py` 의 `trace_guide` import 를 끊는다.

**Architecture:** 동작은 바뀌지 않는다. SKILL.md 는 글만, `hand_sim.py` 는 상수 정의 한 줄만 바뀐다. breadboard-diagram 엔진 의존(`hand_grid.load_renderer`)은 그대로 둔다.

**Tech Stack:** Markdown, Python 3 (`.venv`), unittest/pytest, pymupdf.

**Spec:** 2026-10-12 세션의 grill-yourself 설계(채팅). 아래 '설계 요약' 이 그 사본이다 — N1 = 문서 + import 만, N2 = 다른 스킬 이름 언급 유지.

## 설계 요약

- 끊는 것:
  - SKILL.md §인자(22행) "`make-trace-guide` §인자와 같다" → 규칙을 본문에 적는다.
  - SKILL.md 절차 5(56행) "`make-trace-guide` 절차 7 의 `sig()`" → 코드 블록을 본문에 적는다.
  - SKILL.md 32행 "(`breadboard-diagram` 규칙)" → 괄호만 지운다(규칙 문장은 이미 본문에 있다).
  - SKILL.md 10행 "(따라그리기와 같다)" → 지운다.
  - `scripts/lab/hand_sim.py:29` `from scripts.lab.trace_guide import OUT_DIR` → 같은 파일 안 `OUT_DIR = '팀원전달용'`. 34행 주석의 `trace_guide` 언급도 지운다.
- 남기는 것: description 의 구분 문구(make-trace-guide·review-hand-diagram), 보고 끝 안내(export/review-hand-diagram), 엔진 import, 생성기 거절 메시지(자기 스킬 §빌더를 가리킨다).
- 이번 회차 밖: 엔진 분리, `sig()` 비교를 생성기 안으로 옮기기, make-trace-guide 수정.

## Global Constraints

- 작업 자리: 저장소 루트 `main` 에 바로. push 하지 않는다.
- 파이썬은 `.venv/bin/python`, 시험은 `.venv/bin/python -m pytest`.
- 커밋은 하나 — SKILL.md 와 `hand_sim.py`, 시험 파일. 메시지 `refactor(make-hand-sim): make-trace-guide 의존을 걷어 독립 스킬로`, 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- 재생성 확인 PDF 는 스크래치 폴더에만 쓴다 — `--out-dir` 없이 `hand_sim` 을 부르지 않는다. `팀원전달용/` 의 PDF 는 커밋하지 않는다.
- SKILL.md 의 다른 문장(규칙·근거·흔한 실수 표)은 손대지 않는다.

## Review Focus

1. `hand_sim.OUT_DIR` 와 `trace_guide.OUT_DIR` 가 한쪽만 바뀌면 두 묶음이 다른 폴더로 갈린다 — 둘이 같다는 단언을 시험에 둔다(시험만 둘을 함께 안다). → Task 1 `test_출력_폴더는_따라그리기와_같다`.
2. import 를 끊었는데 다른 경로로 `trace_guide` 가 다시 딸려 오면 독립이 아니다 — 새 인터프리터에서 `hand_sim` 만 import 하고 `sys.modules` 를 본다. → Task 1 `test_hand_sim_은_trace_guide_를_안_불러온다`.
3. 상수를 옮기다 출력 경로가 바뀌면 커밋된 PDF 옆에 엉뚱한 폴더가 생긴다 — 기존 `test_기본_출력은_팀원전달용`(tests/test_breadboard_hand.py:254)이 지킨다. → Task 1 Step 4.
4. 옮겨 적은 `sig()` 가 원본과 달라지면 재생성 판정이 어긋난다 — 원본(make-trace-guide SKILL.md 57~61행)과 글자 그대로 같게 적는다. → Task 1 Step 6.
5. 동작이 바뀌지 않았다는 증거 — 실험06 을 스크래치에 다시 뽑아 커밋본과 `sig()` 가 같아야 한다. → Task 1 Step 7.

---

### Task 1: make-trace-guide 의존 걷기

**Files:**
- Modify: `scripts/lab/hand_sim.py:29`, `:34`
- Modify: `.claude/skills/make-hand-sim/SKILL.md:10`, `:22-24`, `:32`, `:56-58`
- Test: `tests/test_breadboard_hand.py` (클래스 `HandSimScript` 에 둘 추가)

**Interfaces:**
- Consumes: 없음
- Produces: `scripts.lab.hand_sim.OUT_DIR: str == '팀원전달용'` (모듈 수준 상수, `output_paths` 가 쓴다)

- [ ] **Step 1: 실패하는 시험 둘을 `HandSimScript` 에 쓴다**

```python
    def test_hand_sim_은_trace_guide_를_안_불러온다(self):
        import subprocess, sys
        out = subprocess.run(
            [sys.executable, '-c',
             "import sys, scripts.lab.hand_sim; print('scripts.lab.trace_guide' in sys.modules)"],
            cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(out, 'False')

    def test_출력_폴더는_따라그리기와_같다(self):
        from scripts.lab import hand_sim, trace_guide
        self.assertEqual(hand_sim.OUT_DIR, '팀원전달용')
        self.assertEqual(hand_sim.OUT_DIR, trace_guide.OUT_DIR)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `.venv/bin/python -m pytest tests/test_breadboard_hand.py -q -k "trace_guide_를_안 or 따라그리기와_같다"`
Expected: `test_hand_sim_은_trace_guide_를_안_불러온다` FAIL (`'True' != 'False'`), 다른 하나는 PASS(지금은 import 한 같은 객체다).

- [ ] **Step 3: `hand_sim.py` 를 고친다**

29행 import 를 지우고 `LEGEND` 위에 `OUT_DIR = '팀원전달용'` 을 둔다(주석 한 줄: `# 팀원 전달용 PDF 폴더 — 결선도/ 아래`). 34행 주석은 `# 부품그리기 안내판 — 태블릿 판. 손그림모사는 \`board_page\` 판` 으로.

- [ ] **Step 4: 시험 파일 전부를 돌린다**

Run: `.venv/bin/python -m pytest tests/test_breadboard_hand.py -q`
Expected: 전부 PASS(새 둘 + 기존 `test_기본_출력은_팀원전달용` 포함).

- [ ] **Step 5: SKILL.md 10·22~24·32행을 고친다**

- 10행: `부품그리기 쪽은 210×420mm 태블릿 판이다.` 로 끝낸다.
- 22~24행(§인자 본문)을 아래로 바꾼다 — 정확한 문구:

```markdown
`<실험번호|N주차> [회로 이름]`. 번호 토큰이 없으면 한 줄로 되묻고 멈춘다.
- "실험N"·"N" → 실험 N.
- "N주차" → `.venv/bin/python -c "from scripts.lab import config; print(config.experiments_in_week(N))"`.
  결과가 **정확히 하나**일 때만 진행한다. 비었거나 둘 이상이면 후보를 들어 한 줄로 되묻고
  멈춘다 — 같은 번호의 실험 폴더(`실험0N`)가 있으면 첫 후보로 든다.
- 회로 이름을 말하면 그 완성본 PNG 이름을 `--final` 로 넘겨 그것만 뽑는다. 이름이 `FINALS` 에
  없으면 생성기가 `FINALS 에 없는 완성본: … — 가능한 이름: …` 으로 멈춘다 — 그 후보를 들어 되묻는다.
- 회로 이름을 말하지 않았으면 그 실험 `FINALS` 전부를 싣는다.
```

- 32행: `— 도구 결함은 도구 커밋으로 따로 고친다.` 로 끝낸다(괄호 삭제).

- [ ] **Step 6: SKILL.md 절차 5(56~58행)를 고친다 — 정확한 문구**

```markdown
5. **다시 뽑은 경우.** 3 의 사본과 새 PDF 를 쪽별로 잰다(쪽 텍스트 + 그림 md5):
   ```python
   import pymupdf, hashlib
   def sig(f):
       d = pymupdf.open(f)
       return [(p.get_text(), [hashlib.md5(d.extract_image(x[0])['image']).hexdigest()
                               for x in p.get_images()]) for p in d]
   ```
   같으면 사본을 제자리로 복사해(`cp <사본> <PDF>`) 그대로 두고 "바뀐 것 없음" 으로 보고한다 —
   타임스탬프만 다른 재생성은 커밋하지 않는다. `git checkout` 은 쓰지 않는다 — 커밋 안 된 최신본
   대신 옛 커밋본이 돌아온다.
```

`sig()` 본문은 `.claude/skills/make-trace-guide/SKILL.md` 57~61행과 글자 그대로 같아야 한다.

- [ ] **Step 7: 의존이 남지 않았고 산출물이 같은지 잰다**

```bash
grep -nE "make-trace-guide|breadboard-diagram|trace_guide|따라그리기" .claude/skills/make-hand-sim/SKILL.md scripts/lab/hand_sim.py
```
Expected: SKILL.md 3행(description)만 나온다.

```bash
.venv/bin/python -m scripts.lab.hand_sim --experiment 6 --out-dir <스크래치>/e6
```
그다음 Step 6 의 `sig()` 로 `<스크래치>/e6/실험06_손그림모사.pdf`·`실험06_부품그리기.pdf` 를
`보고서/실험06/결선도/팀원전달용/` 의 같은 이름 PDF 와 대조한다.
Expected: 두 쌍 모두 `sig(a) == sig(b)` 가 `True`. `git status` 에 `팀원전달용/` 변화 없음.

- [ ] **Step 8: 커밋한다**

```bash
git add .claude/skills/make-hand-sim/SKILL.md scripts/lab/hand_sim.py tests/test_breadboard_hand.py
git commit -m "refactor(make-hand-sim): make-trace-guide 의존을 걷어 독립 스킬로" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
