# 칩 문제 5지선다 전환 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 실행 방식: 사용자 선택에 따라 Native로 직접 구현하고 마지막에 별도 읽기 전용 리뷰를 수행했다.

**Goal:** 실험01~05 칩 연습 30문항을 생명과학 복습문제처럼 선택·즉시 채점·보기별 해설·다시 풀기가 가능한 단일 정답 5지선다로 전환한다.

**Architecture:** 기존 Python 생성기와 노트 셸을 유지한다. 객관식 원고는 별도 JSON에 두고 기존 Q에 ID로 병합한다. 문제풀이와 문제설명은 동일 원고에서 생성하고, 작은 로컬 JS/CSS를 HTML 안에 삽입해 오프라인 동작을 유지한다.

**Tech Stack:** Python 표준 라이브러리 unittest/HTMLParser, HTML/CSS, vanilla JavaScript, Playwright Chromium.

**Spec:** 이 대화의 2026-10-16 「칩 문제 5지선다 전환 설계」. 독립 실행에 필요한 요구사항을 아래에 전재한다. 별도 설계 파일은 만들지 않는다.

## Global Constraints

- 실험01~05의 기존 30문항을 보기 5개 중 정답 하나를 고르는 객관식으로 바꾼다.
- 보기 클릭 즉시 채점한다. 채점 후 보기 클릭은 해설을 펼치거나 접는다. 답 변경은 ‘다시 풀기’를 통해서만 한다.
- 선택한 보기와 정답의 해설을 자동으로 펼친다. 정답·내 선택은 색상 외 문자로도 표시한다.
- 문제설명 HTML에는 동일한 발문·보기와 다섯 보기의 판단 근거를 제공한다.
- 정답 위치는 고정 순서로 배치하되 ①~⑤ 각 6문항이다. 실행 시 무작위 배치하지 않는다.
- 같은 탭의 새로고침에서 풀이를 복원한다. 저장 실패 시 현재 화면에서 계속 사용한다.
- 전체 핀맵 유지, 문제 그림은 답이 드러나지 않게 표시한다.
- 문제풀이는 문제·보기, 문제설명은 정답·해설까지 인쇄한다. 인쇄 후 풀이 상태를 복구한다.
- 외부 런타임 의존성 없이 기존 로컬 폰트·테마·모바일·목차·앵커 탐색을 유지한다.
- 정리노트 내용, 원본 교안, 실험별 기존 HTML, 다른 미추적 파일은 수정하지 않는다.
- 자동 푸시하지 않는다. 아래 커밋은 실행 시 사용자 승인 범위에 맞춰 수행하며 대상 파일만 명시한다.

## Review Focus

1. 답한 뒤 다른 보기를 클릭하거나 빠르게 연속 클릭해도 첫 답은 유지되어야 한다. Task 3 브라우저 테스트.
2. 저장 차단·손상 JSON·오래된 보기 ID가 있어도 문제가 열리고 채점되어야 한다. Task 3 저장 실패 테스트.
3. 논리값 0/1만으로 다섯 보기를 억지 구성하거나 동치 배선으로 복수 정답이 생기지 않아야 한다. Task 1 원고 검토 및 계산 테스트.
4. 같은 문항의 두 HTML에서 보기 순서·정답·해설이 달라지거나 화면 요약에서 정답이 새지 않아야 한다. Task 2 DOM 대조 테스트.
5. 답하지 않은 상태와 답한 상태 모두 인쇄 내용이 같고, 인쇄 취소 후 선택·해설 열림 상태가 돌아와야 한다. Task 4 인쇄 테스트.

---

## 파일 구조와 사전 확인

모든 명령은 저장소 루트 `C:\Users\Hyunjun\Desktop\현준대학\26-2\논회실`에서 PowerShell로 실행한다. 현재 브랜치와 미추적 파일을 먼저 `git status --short`로 확인한다. 이 계획 작성 시 브랜치는 `hand-sim-natural-strokes`이며 별도 기능 워크트리를 강제하지 않는다. 실행 시 격리가 필요하면 using-git-worktrees 절차를 적용한다.

| 파일 | 책임 |
|---|---|
| `복습노트/칩 정리/.pack/mcq.json` (신규) | 30문항 객관식 발문, 고정 보기 5개, 보기별 해설, 정답 ID |
| `.pack/mcq.py` (신규, 이하 같은 폴더) | 원고 검증·Q 병합·두 화면의 동일 보기 마크업 생성 |
| `.pack/mcq.js`, `.pack/mcq.css` (신규) | 선택·채점·해설·저장 및 접근성/인쇄 스타일 |
| `.pack/test_mcq.py` (신규) | 원고 계약, 잘못된 원고 거부, 생성된 두 HTML 대조 |
| `.pack/verify_mcq.py` (신규) | 사용자 동작·저장·모바일·키보드·인쇄 Chromium 검증 |
| `.pack/build.py:60-85,110-140` (수정) | 기존 Q에 객관식 병합, 원고와 런타임 삽입, 생성 JSON 반영 |
| `.pack/verify.py:73-79,87-93` (수정) | 구 주관식 답 펼치기 테스트를 새 객관식 출력에 맞춤 |
| `문제풀이.html`, `문제설명.html`, `.pack/questions.json` | 생성 결과 |
| `.pack/검증결과.md`, `.pack/browser-results.json`, 화면 캡처 | 새 기능의 실제 검증 증거 갱신 |

사전 참고:

- `build.py:60-85`: Q 선언 30개. `answer`는 기존 검증된 의미 정답으로 유지한다.
- `build.py:110-119`: 두 HTML이 동일 Q를 사용하므로 별도 원고를 이중 관리하지 않는다.
- `audit_check.py:65`: Q10 입력 4개·출력 10개 완전성 검사를 보존한다.
- `../생명과학/복습노트/1015/복습문제_1015_Genomics_and_CRISPR.html:1390-1475`: 첫 선택 고정, 정답/선택 해설 자동 열림, 다시 풀기 동작 참고. 내보내기와 학습 기록 기능 전체를 복사하지 않는다.

### Task 1: 검증 가능한 객관식 원고

**Files:** Create `.pack/mcq.json`, `.pack/mcq.py`, `.pack/test_mcq.py`; Modify `.pack/build.py:86` (COMMON 선언 전 병합).

**Interfaces:**
- Consumes: 기존 `Q: list[dict]`, `CHIPS: list[dict]` (build.py).
- Produces: `merge_mcq(questions: list[dict], rows: list[dict]) -> list[dict]`. 원본 목록은 변경하지 않고 병합 사본을 반환한다.
- 원고 행: `{id, prompt, correctChoiceId, choices:[{id,text,explanation}]}`. 보기 ID는 문자열 `1`~`5`이고 각 ID는 실제 표시 번호와 일치한다.

- [x] **Step 1: 원고 계약의 실패 테스트를 작성한다.**

```python
import copy, json, unittest
from collections import Counter
from pathlib import Path
from mcq import merge_mcq
P = Path(__file__).resolve().parent

class McqDataTest(unittest.TestCase):
    def setUp(self):
        self.q = json.loads((P/'questions.json').read_text(encoding='utf-8'))
        self.rows = json.loads((P/'mcq.json').read_text(encoding='utf-8'))
    def test_contract(self):
        out = merge_mcq(self.q, self.rows)
        self.assertEqual(len(out), 30)
        self.assertEqual(Counter(x['correctChoiceId'] for x in out),
                         Counter({str(i):6 for i in range(1,6)}))
        self.assertEqual([x['answer'] for x in out], [x['answer'] for x in self.q])
    def test_reject_duplicate_text(self):
        rows = copy.deepcopy(self.rows)
        rows[0]['choices'][1]['text'] = rows[0]['choices'][0]['text']
        with self.assertRaises(ValueError): merge_mcq(self.q, rows)
    def test_reject_wrong_key(self):
        rows = copy.deepcopy(self.rows); rows[0]['correctChoiceId'] = '6'
        with self.assertRaises(ValueError): merge_mcq(self.q, rows)
```

- [x] **Step 2: `python -m unittest discover -s '복습노트/칩 정리/.pack' -p test_mcq.py -v`를 실행한다.** `mcq` 모듈 부재로 실패해야 한다.
- [x] **Step 3: `merge_mcq`를 구현하고 원고를 작성한다.**

```python
def merge_mcq(questions, rows):
    ids = [q['id'] for q in questions]
    if len(rows) != len(ids) or {r['id'] for r in rows} != set(ids):
        raise ValueError('문항 ID 누락 또는 중복')
    by_id = {r['id']:r for r in rows}
    out = []
    for q in questions:
        r = by_id[q['id']]; choices = r['choices']
        if [c['id'] for c in choices] != ['1','2','3','4','5']:
            raise ValueError(q['id'] + ': 보기 ID')
        if len({c['text'].strip() for c in choices}) != 5:
            raise ValueError(q['id'] + ': 중복 보기')
        if r['correctChoiceId'] not in {'1','2','3','4','5'}:
            raise ValueError(q['id'] + ': 정답 ID')
        if not r['prompt'].strip() or any(not c['text'].strip() or
            not c['explanation'].strip() for c in choices):
            raise ValueError(q['id'] + ': 빈 원고')
        out.append({**q, **r})
    return out
```

정답 번호는 고정 배열 `2,5,1,4,3,5,4,2,1,3,4,1,3,5,2,1,2,5,3,4,3,4,2,1,5,2,3,4,5,1`을 사용한다. 각 번호가 6번 등장하며 단순 반복 정답 추측을 피한다. 각 문항은 기존 의미 정답을 해당 위치에 놓고, 나머지 네 위치에 아래 혼동 기준으로 서로 다른 거짓 보기를 직접 저작한다. 정답 문장 길이만으로 고를 수 없도록 보기 형식을 맞춘다. 각 해설은 단순 ‘틀림’ 대신 잘못된 기능·핀·논리값을 명시한다.

| 문항 | 정답 의미와 오답 구성 기준 |
|---|---|
| q01~q06 | 00 NAND,02 NOR,04 NOT,08 AND,32 OR,86 XOR의 기존 내부 구성. 다른 칩 기능과 입력 수/개수를 혼동시킨다. |
| q07 | 14 Schmitt 인버터 6개. 일반 NOT, 비반전 버퍼, 게이트 개수 혼동. |
| q08 | 11 AND 3입력 3개. 08/20의 입력 수와 개수 혼동. |
| q09 | 20 NAND 4입력 2개. AND, 2입력, 4개 혼동. |
| q10 | 42 BCD→Decimal, 입력4·Active Low 출력10. 4→16, 극성, 입출력 역전 혼동. |
| q11 | 2입력08 / 3입력11. ‘각각 한 게이트’ 조건 유지. |
| q12 | 08 VCC14 GND7 / 42 VCC16 GND8. 전원/접지 및 패키지 교환. |
| q13 | 위에서 노치↑: 1·7·8·14. 좌우 반전/시계 방향 혼동. |
| q14 | 08 A1 B2 Y3 VCC14 GND7. A/B의 동치 교환을 오답으로 만들지 않는다. 출력/전원 역할 교환. |
| q15 | 02 입력2·3 출력1. 08배치와 다른 게이트 번호 혼동. |
| q16 | 04 1번0 → 2번1. 출력 핀과 논리값 조합. |
| q17 | 두 입력1: 32 출력1 / 86 출력0. 네 값 조합 + 잘못된 출력 핀 조합. |
| q18 | 11 입력1·2·13 → 출력12. 연속 핀과 둘째/셋째 게이트 혼동. |
| q19 | 20 입력1·2·4·5 / 출력6 / NC3·11. NC를 입력으로 세는 배치. |
| q20 | 발문을 ‘6번 출력값과 그 이유로 옳은 것은?’으로 변경. 정답 ‘1 — AND 결과0을 반전’. 오답 ‘0 — 모든 입력1’, ‘0 — NAND가 AND와 같음’, ‘1 — 모든 입력1’, ‘0 — 하나라도0이면 NAND0’. |
| q21 | A→1 B→2 3→4 C→5 Y6. 출력끼리 연결/입력끼리 연결 오답. A/B 동치 교환 제외. |
| q22 | XOR86 AND08 OR32. 기능별 번호 교환. |
| q23 | 04/14 핀배치 같음,14 상승/하강 문턱 다름. 두 속성을 함께 비교. |
| q24 | 미사용 CMOS입력 확정 논리값 / 출력·NC 미연결. 출력 전원 단락과 입력 부유 혼동. |
| q25 | ‘남는 입력의 고정값과 이유’로 변경. 정답 ‘1 — A·B·C·1=A·B·C’. 오답 ‘0 — AND 항등원’, ‘미연결 — CMOS 자동1’, ‘출력에 연결 — 자동 보정’, ‘0 — NAND 항상0’. |
| q26 | 42 D C B A=0101 / 핀12·13·14·15=0·1·0·1. 비트 순서/자리 가중치 혼동. |
| q27 | Y5·6번 LOW, 해당 LED 켜짐. 출력명·핀·극성 조합. |
| q28 | BCD1010 → Y10없음, Y0~9 모두1. 4→16/Active High 혼동. |
| q29 | 실험04 게이트 MUX=04·20. 보충 전용153 및 DMUX 조합 혼동. |
| q30 | DMUX04·11 / Excess-3 04·20. 전용139·148 및 두 조합 교환. |

원고 예시(q01 정답1):

```json
{"id":"q01","prompt":"74HC00의 기능과 내부 구성으로 옳은 것은?","correctChoiceId":"1","choices":[
 {"id":"1","text":"2입력 NAND 게이트 4개","explanation":"맞아요. 두 입력이 모두 1일 때만 출력이 0인 NAND가 네 개예요."},
 {"id":"2","text":"2입력 AND 게이트 4개","explanation":"74HC08의 구성이에요. 00은 AND 결과를 반전해요."},
 {"id":"3","text":"2입력 NOR 게이트 4개","explanation":"74HC02의 구성이에요. NOR는 두 입력이 모두 0일 때만 1이에요."},
 {"id":"4","text":"4입력 NAND 게이트 2개","explanation":"74HC20의 구성이에요. 00은 게이트당 입력이 두 개예요."},
 {"id":"5","text":"인버터 6개","explanation":"74HC04의 구성이에요. 인버터는 입력 한 개를 반전해요."}]}
```

병합 위치는 모든 q() 호출 후, COMMON 전이다:

```python
from mcq import merge_mcq, render_choices
Q = merge_mcq(Q, json.loads((PACK/'mcq.json').read_text(encoding='utf-8')))
```

- [x] **Step 4: 원고 계약 테스트를 재실행한다.** PASS 후 기존 `chips.json`·`audit-reference.json`과 위 정답/오답 150개를 대조한다. 특히 q14/q21의 교환 가능한 입력과 q20/q25의 이유까지 검사한다. 단일 정답 여부는 문자열 중복 검사만으로 보장되지 않는다.
- [x] **Step 5: Task 1 대상 파일만 커밋한다.** `git add -- '복습노트/칩 정리/.pack/mcq.json' '복습노트/칩 정리/.pack/mcq.py' '복습노트/칩 정리/.pack/test_mcq.py' '복습노트/칩 정리/.pack/build.py'` 후 `git commit -m 'feat: define chip five-choice questions'`. 단, 다음 Task 2의 render_choices가 아직 없으면 import는 그 작업에서 연결하여 중간 생성기를 깨뜨리지 않는다.

### Task 2: 동일 데이터로 문제와 해설 생성

**Files:** Modify `.pack/mcq.py`, `.pack/build.py:110-140`, `.pack/test_mcq.py`; regenerate `문제풀이.html`, `문제설명.html`, `.pack/questions.json`.

**Interfaces:** Consumes merged Q. Produces `render_choices(q: dict, explain: bool=False) -> str`. DOM 루트 `.mcq[data-question-id][data-correct]`, 보기 `.mcq-choice[data-choice-id]`, 해설 `.mcq-reason`, 채점 알림 `.mcq-status`, 초기화 `.mcq-reset`. 해설 화면 루트에는 `data-explain="true"`.

- [x] **Step 1: 같은 q14를 두 방식으로 렌더링하는 실패 테스트를 추가한다.**

```python
def test_render_shared_choices(self):
    from mcq import render_choices
    from html import escape
    q = merge_mcq(self.q, self.rows)[13]
    practice, explain = render_choices(q), render_choices(q, explain=True)
    for c in q['choices']:
        self.assertIn(escape(c['text']), practice)
        self.assertIn(escape(c['text']), explain)
        self.assertIn(escape(c['explanation']), explain)
    self.assertEqual(practice.count('class="mcq-choice"'), 5)
    self.assertIn('role="status"', practice)
```

- [x] **Step 2: unittest를 실행하여 render_choices 미정의로 실패하는지 확인한다.**
- [x] **Step 3: 마크업을 구현하고 생성기에 연결한다.**

```python
from html import escape as E
def render_choices(q, explain=False):
    cards = []
    for c in q['choices']:
        correct = c['id'] == q['correctChoiceId']
        label = '정답' if correct else '정답 아님'
        hidden = '' if explain else ' hidden'
        cards.append(f'''<li><button type="button" class="mcq-choice"
          data-choice-id="{c['id']}" aria-expanded="{str(explain).lower()}"
          aria-controls="{q['id']}-reason-{c['id']}">{c['id']}. {E(c['text'])}</button>
          <span class="mcq-label"{hidden}>{label}</span>
          <div class="mcq-reason" id="{q['id']}-reason-{c['id']}"{hidden}>{E(c['explanation'])}</div></li>''')
    return f'''<div class="mcq" data-question-id="{q['id']}"
      data-correct="{q['correctChoiceId']}" data-explain="{str(explain).lower()}">
      <ol class="mcq-choices">{''.join(cards)}</ol>
      <p class="mcq-status" role="status" aria-live="polite"></p>
      <button type="button" class="mcq-reset" hidden>다시 풀기</button></div>'''
```

표시 번호는 Python의 `['①','②','③','④','⑤'][int(c['id'])-1]`로 출력한다. 위 예시의 `{c['id']}.`를 이 기호로 대체한다.

`short`는 발문·빈 핀 그림·`render_choices(x)`·기존 힌트·관련 링크로 구성하고 기존 work-space와 수동 practice-answer를 제거한다. `long`은 발문·같은 그림·`render_choices(x, explain=True)`·기존 의미 정답과 steps/wrong/링크를 유지한다. 문제의 오른쪽 요약에는 정답이 포함되지 않아야 한다. CSS/JS는 생성 시 PACK에서 읽어 HTML 안에 삽입한다.

- [x] **Step 4: unittest와 build를 실행한다.**

```powershell
python -m unittest discover -s '복습노트/칩 정리/.pack' -p test_mcq.py -v
python '복습노트/칩 정리/.pack/build.py'
```

생성 HTML을 HTMLParser 또는 Playwright로 분석하여 각 문항의 보기 ID·텍스트·정답 ID를 두 HTML 사이에서 비교한다. 문제풀이 초기 화면은 `.mcq-reason:not([hidden])`가 0개이고 요약의 정답 노출이 없어야 한다. 정리노트는 `git diff -- '복습노트/칩 정리/정리노트.html'`가 비어야 한다.

- [x] **Step 5: 원고·생성기·생성 HTML·테스트 파일만 커밋한다.** `git commit -m 'feat: render consistent chip choices and explanations'`.

### Task 3: 선택·채점·다시 풀기·저장

**Files:** Create `.pack/mcq.js`, `.pack/mcq.css`, `.pack/verify_mcq.py`; Modify `.pack/build.py` (inline 삽입).

**Interfaces:** Consumes Task 2 DOM. `sessionStorage` key `chip-mcq-v1:<questionId>:<contentSignature>`; signature는 발문/보기/정답을 포함하여 원고 변경 시 구 답안을 무시한다. 저장값은 보기 ID 문자열 또는 null. data-selected는 첫 선택, reason.hidden은 보기별 펼침 상태다. 해설 모드는 클릭 채점/저장을 적용하지 않는다.

- [x] **Step 1: Chromium 실패 테스트를 작성한다.** 아래 코드를 verify_mcq.py의 기본 흐름으로 사용한다.

```python
from pathlib import Path
from playwright.sync_api import sync_playwright
P=Path(__file__).resolve().parent
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page(viewport={'width':375,'height':900})
    page.goto((P.parent/'문제풀이.html').as_uri()+'#q14')
    box=page.locator('#q14 .mcq')
    correct=box.get_attribute('data-correct')
    wrong=next(str(i) for i in range(1,6) if str(i)!=correct)
    box.locator(f'[data-choice-id="{wrong}"]').click()
    assert box.get_attribute('data-selected')==wrong
    assert '정답이 아니에요' in box.locator('.mcq-status').inner_text()
    box.locator(f'[data-choice-id="{correct}"]').click()
    assert box.get_attribute('data-selected')==wrong
    page.reload()
    assert box.get_attribute('data-selected')==wrong
    box.locator('.mcq-reset').click()
    assert box.get_attribute('data-selected') is None
    btn=box.locator(f'[data-choice-id="{correct}"]')
    btn.focus(); page.keyboard.press('Enter')
    assert '정답이에요' in box.locator('.mcq-status').inner_text()
    browser.close()
```

- [x] **Step 2: `python '복습노트/칩 정리/.pack/verify_mcq.py'`로 data-selected 미설정 실패를 확인한다.**
- [x] **Step 3: 상태 전이를 구현한다.** 핵심 paint/select 동작은 다음 계약을 따른다.

```javascript
function selectChoice(box, id, state, save, paint) {
  if (state.selected !== null) {
    if (state.expanded.has(id)) state.expanded.delete(id);
    else state.expanded.add(id);
  } else {
    state.selected = id;
    state.expanded.add(id);
    state.expanded.add(box.dataset.correct);
    save(id);
  }
  paint();
}
function readChoice(key, allowed) {
  try {
    const value = JSON.parse(sessionStorage.getItem(key));
    return allowed.includes(value) ? value : null;
  } catch { return null; }
}
function writeChoice(key, value) {
  try { sessionStorage.setItem(key, JSON.stringify(value)); } catch {}
}
```

`mount`는각 `.mcq[data-explain="false"]`에 `state={selected:readChoice(...), expanded:new Set()}`를 생성한다. 복원 시 selected와 correct 해설을 연다. `paint`는 selected가 null이면 data-selected를 삭제하고 모든 라벨과 해설을 숨긴다. 답한 상태는 data-selected·‘내 선택’·‘정답’·‘정답 아님’·`.mcq-status` 및 aria-expanded를 갱신한다. reset은 state.selected=null, expanded.clear(), writeChoice(key,null), paint(), 첫 보기.focus() 순서다. 피드백은 정답 ‘정답이에요.’, 오답 ‘정답이 아니에요. 보기별 이유를 확인해 보세요.’다.

```css
.mcq-choices{list-style:none;padding:0}
.mcq-choice{width:100%;min-height:44px;padding:14px;text-align:left;
  color:var(--ink);background:var(--surface);border:1px solid var(--line);
  white-space:normal;overflow-wrap:anywhere;font:inherit;cursor:pointer}
.mcq-choice:focus-visible,.mcq-reset:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
.mcq-label{display:block;font-weight:700;margin-top:6px}
.mcq-reason{padding:12px 0}
.mcq [hidden]{display:none!important}
.mcq-choice[data-result="correct"]{border:3px solid var(--accent)}
.mcq-choice[data-result="selected"]{border:3px solid var(--danger,var(--ink))}
```

- [x] **Step 4: 동작 및 저장 실패 테스트를 실행한다.** verify_mcq.py를 확장하여 전30문항에서 정답과 오답 각각 선택 후 초기화, 375/1280px 가로 넘침 없음, Enter/Space 입력을 검사한다. 새 컨텍스트에 아래 init script를 주입해도 클릭·다시 풀기·콘솔 오류 없음이 통과해야 한다.

```javascript
Object.defineProperty(window,'sessionStorage',{get(){throw new Error('blocked')}});
```

정상 저장에 손상 문자열 `'{broken'` 및 JSON 문자열 `'"6"'`를 각각 넣어 새로고침하고 미응답으로 시작하는지 확인한다. 원고 signature를 변경한 key는 이전 답을 사용하지 않는다. 클릭 후 다른 보기 두 번 클릭해도 data-selected가 바뀌지 않아야 한다.

- [x] **Step 5: 런타임·CSS·브라우저 테스트·생성 결과를 명시해 커밋한다.** `git commit -m 'feat: add interactive chip answer feedback'`.

### Task 4: 인쇄·회귀 검증과 결과 기록

**Files:** Modify `.pack/mcq.css`, `.pack/mcq.js`, `.pack/verify.py`, `.pack/verify_mcq.py`, `.pack/검증결과.md`; regenerate HTML·화면 캡처·browser-results.json.

**Interfaces:** Task 3 DOM/state. print CSS는 응답 상태와 무관하게 작동하며 JS state는 변경하지 않는다. 기존 build.py의 details beforeprint/afterprint 복구 훅은 유지한다.

- [x] **Step 1: 인쇄 회귀 실패 테스트를 추가한다.**

```python
page.emulate_media(media='print')
page.evaluate("dispatchEvent(new Event('beforeprint'))")
assert page.locator('.mcq-choice:visible').count()==150
assert page.locator('.mcq-reason:visible').count()==0
page.evaluate("dispatchEvent(new Event('afterprint'))")
page.emulate_media(media='screen')
assert box.get_attribute('data-selected')==correct
page.goto((P.parent/'문제설명.html').as_uri())
page.emulate_media(media='print')
page.evaluate("dispatchEvent(new Event('beforeprint'))")
assert page.locator('.mcq-choice:visible').count()==150
assert page.locator('.mcq-reason:visible').count()==150
```

- [x] **Step 2: verify_mcq.py를 실행하여 아직 구현되지 않은 인쇄 동작 실패를 확인한다.**
- [x] **Step 3: 인쇄 CSS와 기존 검증을 갱신한다.**

```css
@media print{
  .mcq-status,.mcq-reset,.mcq-label{display:none!important}
  .mcq[data-explain="false"] .mcq-reason{display:none!important}
  .mcq[data-explain="true"] .mcq-reason{display:block!important}
  .mcq-choice{border:0!important;background:none!important;padding:4px 0;min-height:0}
}
```

기존 verify.py의 `.practice-answer` 클릭과 count==30 검사는 제거하고 `.mcq` 30개/보기150개 및 문제·해설의 인쇄 계약으로 교체한다. `answer in HTML` 검사 대신 questions.json의 의미 정답을 문제설명의 정답 블록에서 검사한다. 문제풀이에는 정답을 숨긴 DOM에 보유할 필요가 없다. `audit_check.py`의 Q10과 핀 검사는 그대로 통과해야 한다.

- [x] **Step 4: 전체 검증 명령을 순서대로 실행한다.**

```powershell
python '복습노트/칩 정리/.pack/build.py'
python -m unittest discover -s '복습노트/칩 정리/.pack' -p test_mcq.py -v
python '복습노트/칩 정리/.pack/audit_check.py'
python '복습노트/칩 정리/.pack/verify.py'
python '복습노트/칩 정리/.pack/verify_mcq.py'
git diff --check
git diff -- '복습노트/칩 정리/정리노트.html'
```

모든 검증이 PASS이고 정리노트 diff가 없어야 한다. 375/1280px·라이트/다크에서 q14/q19/q26의 선택 전후 캡처를 직접 확인한다. 긴 보기의 잘림, 핀맵 글자, 정오답 표식, 포커스, 정답 누출을 확인한다. 미응답 및 응답 후 인쇄에서 선택 표식이 사라지고 복귀 후 동일 상태인지 확인한다. 인쇄 CSS 검사와 실제 PDF/종이 육안 검사를 구분해 검증결과.md에 수행 사실만 기록한다.

- [x] **Step 5: 체크박스와 검증 기록을 갱신하고 대상 파일만 커밋한다.** `git commit -m 'test: verify chip choice printing and regression'`. 최종 보고에는 변경 HTML 링크, 30문항·150보기, 검증 결과와 실제 수행하지 않은 검사의 한계를 짧게 적는다. 사용자가 별도 요청하기 전에는 푸시하지 않는다.

## 계획 자체 검토

- 설계 요구사항 7개 결정은 Task 1(원고/분포), Task 2(같은 데이터/핀맵), Task 3(상호작용/저장), Task 4(인쇄)에 대응한다.
- 원고 병합 함수와 렌더 함수, DOM 클래스, 저장값 타입은 전 작업에서 동일하다.
- Review Focus의 다섯 실패 조건은 각 소유 작업에 검증 절차를 지정했다.
- 새 기능 구현·실행·자동 커밋·푸시는 이 계획 작성 단계에서 수행하지 않는다.

## 실행 결과 — 2026-10-16

- 사용자 선택: 직접 구현. Task 1~4 완료, unittest 4개·기존 핀 검증·기존 브라우저 회귀·신규 객관식 브라우저 검증 모두 PASS.
- 정리노트 HTML과 원본 칩/출처 데이터 변경 없음. 문제풀이·문제설명 및 원고/검증만 수정.
- 판단 기록: Bash 전용 관리 스크립트 대신 PowerShell로 계획별 진행 기록을 유지했다. 기존 기능 브랜치를 재사용했다.
- 판단 기록: 중간에 렌더 함수를 분리하지 않고 같은 mcq.py에서 구현했고, 전체 검증 후 한 커밋으로 묶었다. 설명 HTML은 클릭하지 않는 정적 보기 요소를 쓴다.
- 판단 기록: 보기 순서는 고정·균형 분포를 유지하되 계획 초안의 단순 ①~⑤ 반복은 피했다. 이 회귀 검사는 실패를 확인한 후 원고를 수정하여 통과했다.
- 시각 검토: 대표 q14의 선택 후, q19/q26의 선택 전 화면을 375/1280px와 두 테마로 캡처했다. 전 문항 선택 전후 동작은 자동 검사했다.
- 별도 리뷰: 150보기의 정답 유일성과 코드 검토에서 Critical/Important 문제 없음. 데이터시트 신규 다운로드·실물 칩·Chromium 외 브라우저·실제 종이/PDF 육안 검사는 이 작업 범위에서 수행하지 않았고 한계로 기록했다.
- 이전 계획의 커밋 단계 4개는 최종 커밋 한 개로 통합한다. 사용자 요청 전 푸시하지 않는다.
