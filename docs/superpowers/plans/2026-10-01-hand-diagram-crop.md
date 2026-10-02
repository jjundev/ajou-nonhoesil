# Hand Diagram Semantic Crop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 사용자와 합의한 의미 기반 크롭 규칙을 스킬·추출 코드에 반영하고, fresh 실행 결과를 수동 크롭과 대조한다.

**Architecture:** 에이전트가 전체 PDF를 보고 의미 있는 보존 영역을 페이지 좌표 JSON으로 기록한다. Python은 JSON을 검증하고 합집합·2% 여백을 계산해 결정론적으로 렌더링한다. 별도 fresh 실행자가 정답을 보지 않고 이 절차를 재현하고 평가자가 수동 예시와 비교한다.

**Tech Stack:** Python, PyMuPDF(fitz), Pillow, unittest, Markdown, Codex fresh subagent.

**Spec:** `docs/superpowers/specs/2026-10-01-hand-diagram-crop.md`

## Global Constraints

- 기본 추출은 전체 페이지를 유지하고, `--crop`에만 새 규칙을 적용한다.
- 전원 단자 3개·극성·연결선, 보드 전체 외곽·모든 홀·행 번호를 보존한다.
- 외부 신호 이름·핀 번호·연결 화살표까지 포함하도록 페이지별로 범위를 조정한다.
- 판형 구분선·하단 캡션·불필요한 주변 공간은 제외한다.
- 제목·설명 때문에 범위를 넓히지는 않되, 안에 걸친 조각은 허용한다.
- 상하좌우에 각각 보드 너비의 약 2% 여백을 붙인다.
- 외부 필기의 분류가 애매하면 후보 영역을 보여주고 사용자 확인을 기다린다. 다른 명확한 페이지는 계속 처리한다.
- 외부 API·OCR·새 패키지 의존성은 추가하지 않는다.
- 원본과 기존 정본 PNG는 덮어쓰지 않는다. 검증 출력은 `output/validation/hand-diagram-crop/roundNN/`에 둔다.
- 기존 파일명/netlist 매핑, 페이지 선택, 300 DPI 기본값을 유지한다.
- 이 작업 외의 기존 변경을 수정하거나 커밋하지 않는다. 커밋/푸시는 별도 사용자 요청 시 수행한다.

## Review Focus

- PDF가 바뀐 뒤 이전 좌표 JSON을 재사용하는 입력: 해시/페이지 크기 불일치를 출력 전에 거절한다(Task 1).
- 회전 페이지와 다른 렌더 DPI: 동일한 시각적 영역을 보존하고 좌표계를 혼동하지 않는다(Task 1, 2).
- 페이지 끝에 붙은 주석: 내용은 보존하고 제한된 여백을 명시한다(Task 1).
- 명확한 쪽과 애매한 쪽이 섞인 PDF: 명확한 쪽은 저장하고 애매한 쪽만 pending 처리한다(Task 2).
- 잘못된 좌표/중복 페이지/누락 페이지: 빈 이미지 또는 임의 고정 크롭으로 성공하지 않는다(Task 1, 2).

---

## 현재 상태와 파일 구조

- `.agents/skills/export-hand-diagram`은 `.claude/skills/export-hand-diagram`의 symlink다. 후자만 편집한다.
- `scripts/lab/export_hand_diagrams.py`: 고정 좌표 상수와 crop 분기를 교체하고 `--crop-plan`을 연결한다. 파일명 매칭은 건드리지 않는다.
- **Create** `scripts/lab/hand_crop.py`: JSON 로딩/검증, 좌표 계산, 결과 보고 및 후보 생성에 필요한 순수 함수.
- **Create** `tests/test_hand_crop.py`: 외부 PDF 없는 합성 입력으로 좌표·오류 검증.
- **Modify** `tests/test_export_hand_diagrams.py`: 합성 2쪽 PDF를 쓰는 crop 통합 테스트 추가. 기존 round8 기반 이름/전체페이지 테스트 유지.
- **Modify** `.claude/skills/export-hand-diagram/SKILL.md`: 원본 시각 판독→plan 작성→실행→검증/질문 절차.
- **Create** `.claude/skills/export-hand-diagram/references/crop-plan.md`: JSON 스키마·좌표 변환·pending 예시. 실제 실험 좌표나 정답 이미지 경로는 넣지 않는다.
- **Create** `docs/verify/export-hand-diagram-crop.md`: baseline/fresh 검증 요약, 판정과 산출물 경로.
- 검증 PNG/원본 복사/로그/JSON은 위 round 디렉토리로 한정한다.

시작 시 기존 dirty 파일: `.claude/skills/review-hand-diagram/SKILL.md`, `scripts/lab/hand_compare.py`, `scripts/lab/hand_transcript.py`, `tests/test_hand_compare.py`, `보고서/실험04/output/`. 새로 확인한 git status를 기록하고 모두 보존한다.

### Task 1: 크롭 좌표 계약과 순수 계산

**Files:** Create `scripts/lab/hand_crop.py`, `tests/test_hand_crop.py`.

**Interfaces:**
- `load_crop_plan(path: str | Path, pdf_path: str | Path, pages: list[int]) -> dict[int, dict]`: 입력 JSON 1-based 페이지를 반환 dict의 0-based 키로 변환. 선택된 모든 쪽을 검증한다.
- `crop_box(page_rect: tuple[float,float,float,float], board_box: tuple[float,float,float,float], keep: list[tuple[float,float,float,float]]) -> tuple[float,float,float,float]`: pt 좌표 합집합+여백, 페이지 경계 제한.
- `pixel_box(box: tuple[float,float,float,float], page_rect: tuple[float,float,float,float], image_size: tuple[int,int]) -> tuple[int,int,int,int]`: 실제 렌더 크기로 변환하며 시작 floor, 끝 ceil.

- [x] **Step 1: 합성 좌표 테스트를 먼저 추가한다.**

```python
import unittest
from scripts.lab.hand_crop import crop_box, pixel_box

class TestCropGeometry(unittest.TestCase):
    def test_external_label_and_bottom_are_preserved(self):
        self.assertEqual(
            crop_box((0, 0, 600, 800), (100, 200, 500, 700),
                     [(250, 80, 400, 160), (40, 300, 100, 340)]),
            (32, 72, 508, 708))

    def test_margin_clamps_only_at_page_edge(self):
        self.assertEqual(crop_box((0,0,600,800), (5,5,505,795), []),
                         (0,0,515,800))

    def test_render_rounds_outward(self):
        self.assertEqual(pixel_box((1.1,2.1,9.1,10.1), (0,0,100,100),
                                   (200,200)), (2,4,19,21))

    def test_invalid_boxes_are_rejected(self):
        for box in [(10,10,5,50), (-1,10,50,50),
                    (10,10,float('nan'),50), (10,10,610,50)]:
            with self.subTest(box=box), self.assertRaises(ValueError):
                crop_box((0,0,600,800), box, [])
```

- [x] **Step 2: RED를 확인한다.**

Run: `python3 -m unittest discover -s tests -p test_hand_crop.py -v`
Expected: 새 모듈 import 실패. 로그를 round00에 보관한다.

- [x] **Step 3: 계산 함수를 구현한다.**

```python
import math

def crop_box(page_rect, board_box, keep):
    px0, py0, px1, py1 = page_rect
    if not all(math.isfinite(v) for v in page_rect) or px0 >= px1 or py0 >= py1:
        raise ValueError('invalid page rectangle')
    boxes = [board_box, *keep]
    for box in boxes:
        if len(box) != 4 or not all(math.isfinite(v) for v in box):
            raise ValueError('invalid crop box')
        x0, y0, x1, y1 = box
        if not (px0 <= x0 < x1 <= px1 and py0 <= y0 < y1 <= py1):
            raise ValueError('crop content outside page or empty')
    margin = (board_box[2] - board_box[0]) * 0.02
    return (max(px0, min(b[0] for b in boxes)-margin),
            max(py0, min(b[1] for b in boxes)-margin),
            min(px1, max(b[2] for b in boxes)+margin),
            min(py1, max(b[3] for b in boxes)+margin))

def pixel_box(box, page_rect, image_size):
    x0, y0, x1, y1 = page_rect
    w, h = image_size
    sx, sy = w/(x1-x0), h/(y1-y0)
    return (max(0, math.floor((box[0]-x0)*sx)),
            max(0, math.floor((box[1]-y0)*sy)),
            min(w, math.ceil((box[2]-x0)*sx)),
            min(h, math.ceil((box[3]-y0)*sy)))
```

JSON contract (synthetic example; source hash calculated from actual bytes):

```json
{
  "schema": "hand-crop/v1",
  "source_sha256": "64 lowercase hexadecimal characters",
  "pages": [{
    "page": 1,
    "page_rect": [0, 0, 600, 800],
    "board_box": [100, 200, 500, 700],
    "keep": [{"label": "power terminals", "box": [250, 80, 400, 160]}],
    "excluded": [{"label": "title", "reason": "not a connection label"}],
    "ambiguous": []
  }]
}
```

`load_crop_plan`은 `hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()` 일치를 확인한다. schema 불일치, 중복 page, 선택 page 누락, page_rect 불일치, 잘못된 타입, 비유한 값은 ValueError로 거절한다. `fitz.open`으로 page.rect를 읽고 각 board/keep/ambiguous 좌표를 crop_box로 검증한다. 선택하지 않은 페이지는 출력하지 않는다.

- [x] **Step 4: JSON 검증 테스트를 추가한다.** 아래 코드로 합성 PDF와 오류 사례를 만든다.

```python
import fitz, hashlib, json, tempfile
from pathlib import Path
from scripts.lab.hand_crop import load_crop_plan

with tempfile.TemporaryDirectory() as tmp:
    pdf = Path(tmp)/'source.pdf'
    doc = fitz.open()
    doc.new_page(width=600, height=800)
    doc.save(pdf)
    doc.close()
    entry = dict(page=1, page_rect=[0,0,600,800],
                 board_box=[100,200,500,700], keep=[], excluded=[], ambiguous=[])
    plan = dict(schema='hand-crop/v1',
                source_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(), pages=[entry])
    path = Path(tmp)/'plan.json'
    path.write_text(json.dumps(plan))
    assert load_crop_plan(path, pdf, [0])[0]['board_box'] == entry['board_box']
    for change in [dict(source_sha256='0'*64), dict(pages=[]),
                   dict(pages=[entry,entry]),
                   dict(pages=[dict(entry, page_rect=[0,0,800,600])])]:
        path.write_text(json.dumps(dict(plan, **change)))
        try:
            load_crop_plan(path, pdf, [0])
        except ValueError:
            pass
        else:
            raise AssertionError(change)
```

같은 합성 PDF에 `page.set_rotation(90)`을 적용한 사례도 추가한다. page_rect가 `[0,0,800,600]`이 되고 해당 좌표계의 올바른 plan이 허용되는지 확인한다.
Run Step 2 command. Expected: PASS.

### Task 2: exporter 연결, pending 처리와 스킬 개정

**Files:** Modify `scripts/lab/export_hand_diagrams.py`, `tests/test_export_hand_diagrams.py`, `.claude/skills/export-hand-diagram/SKILL.md`; Create `.claude/skills/export-hand-diagram/references/crop-plan.md`.

**Interfaces:** Task 1의 세 함수를 사용한다. `export_hand_diagrams(..., crop_plan: Optional[str | Path] = None) -> List[Path]`를 제공한다. `--crop-plan`은 crop JSON 경로다. `crop-report.json`은 `{schema: "hand-crop-report/v1", source_sha256, dpi, pages: [{page,status,box,output,margin_clipped,candidates}]}` 형태다. status는 saved/pending이며 box/output은 pending에서 null이다.

- [x] **Step 1: 현재 스킬 baseline을 fresh 에이전트로 실행한다.** `fork_turns="none"`, 실험04 원본 PDF와 기존 스킬, `--out output/validation/hand-diagram-crop/round00/baseline`만 제공한다. 수동 예시/설계/새 규칙은 제공하지 않는다. 기존 고정 크롭의 하단 손실을 full-page와 대조해 기록한다. 에이전트는 코드 수정 금지. 아직 업데이트 전이라는 점을 로그에 적는다.
- [x] **Step 2: 합성 PDF 통합 테스트를 먼저 추가하고 RED를 확인한다.** 신규 테스트 class에는 round8 의존 setUp을 사용하지 않는다. 2쪽 합성 PDF 각 쪽에 아래 직사각형을 그려 저장한다.

```python
page.draw_rect(fitz.Rect(100,200,500,700), color=(0,0,0))
page.draw_rect(fitz.Rect(250,80,400,160), color=(1,0,0))
page.draw_rect(fitz.Rect(40,300,100,340), color=(0,0,1))
```

Task 1 JSON entry의 keep에 단자와 외부 표기를 넣는다. 아래 호출과 검증을 unittest 메서드로 추가한다.

```python
paths = ehd.export_hand_diagrams(99, pdf, out_dir=out, dpi=72,
                                crop_board=True, crop_plan=plan_path)
self.assertEqual(len(paths), 2)
with Image.open(paths[0]) as im:
    self.assertEqual(im.size, (476,636))
report = json.loads((Path(out)/'crop-report.json').read_text())
self.assertEqual([p['status'] for p in report['pages']], ['saved','saved'])
```

2쪽에 `ambiguous=[{"label":"unclear note","box":[510,300,560,340],"reason":"signal or prose unclear"}]`를 설정한 사례는 최종 PNG 1개, 후보 2개, CLI 종료 코드 2를 assert한다. 승인 후 ambiguous를 keep으로 옮기고 `--pages 2`로 재실행하면 2쪽만 saved가 되는지 확인한다. 후보는 `candidates/p002-include.png`, `p002-exclude.png`, 전체 페이지 경계 미리보기는 `p002-boundaries.png`로 저장하며 final 파일명은 사용하지 않는다.

다음 종료 코드도 테스트한다:
```python
self.assertEqual(ehd.main(['99',str(pdf),'--out',str(out),'--crop']), 1)
self.assertEqual(ehd.main(['99',str(pdf),'--out',str(out),'--crop','--no-crop']), 0)
```
DPI 72/144에서 크기가 (476,636)/(952,1272)인지 확인한다. 회전된 합성 페이지는 page_rect에 맞는 box를 제공하고 최종 PNG를 확인한다. `--pages 2` 보고서의 page 번호는 2이며 다시 0이나 1로 매기지 않는다.

Run: `python3 -m unittest discover -s tests -p test_export_hand_diagrams.py -v`
Expected: crop_plan 인자 미지원으로 새 테스트 FAIL.

- [x] **Step 3: crop 분기를 교체한다.** 고정 BOARD_CROP 상수를 제거한다. 선택 페이지의 plan을 저장 전에 모두 검증하고 명확한 페이지의 crop 분기를 다음 코드로 교체한다.

```python
entry = crop_entries[p_num]
box = crop_box(tuple(entry['page_rect']), tuple(entry['board_box']),
               [tuple(item['box']) for item in entry['keep']])
im = im.crop(pixel_box(box, tuple(entry['page_rect']), im.size))
```

pending 분기는 keep만 포함한 box와 keep+ambiguous를 포함한 box를 같은 함수로 계산해 후보를 저장한다. Pillow ImageDraw로 원본 위 두 경계를 색으로 구분한다. 후보는 최종 목록에 넣지 않고 보고서에 남긴다. 같은 이름의 기존 final은 건드리지 않으며 pending 보고서에 기존 파일 미갱신으로 기록한다. `crop-report.json`에는 이번 실행에서 선택한 페이지 상태만 기록한다. CLI는 이번 보고서에 pending이 있으면 2, 일반 예외는 1을 반환한다. pending이 있는데 전체 성공이라고 출력하지 않는다.

- [x] **Step 4: 스킬 본문과 JSON 참조 문서를 갱신한다.** 실행 순서는 전체 페이지 렌더→시각 판독→crop-plan 생성→추출→최종 PNG 시각 확인이다. 사용자에게 JSON 수작성을 요청하지 않는다. 좌표 변환, 2%의 정의, 보드 전체 보존, 제목 조각 허용, 애매할 때 후보와 질문, `--pages` 재개를 명시한다. `--crop`이 없으면 현행 절차를 유지한다. 특정 실험 좌표·색·신호 이름에 의존한 규칙은 금지한다.

문서에 넣을 명령:
```bash
python3 -m scripts.lab.export_hand_diagrams 4 input.pdf --crop --crop-plan crop-plan.json --out output/crop
python3 -m scripts.lab.export_hand_diagrams 4 input.pdf --crop --crop-plan crop-plan.json --pages 2 --out output/crop
```
실행할 때 `input.pdf`/plan은 에이전트가 확인한 실제 사용자 파일 경로로 바꾼다.

- [x] **Step 5: 기존 cropped 테스트를 새 계약으로 갱신하고 회귀 검증한다.** round8 PDF 테스트의 단순 세로 비율 검증을 crop plan 필수 계약 검증으로 바꾼다. 새 내용 보존 검증은 합성 PDF 테스트가 담당한다. 파일명·전체 페이지 테스트는 삭제하지 않는다.
Run: `python3 -m unittest discover -s tests -p 'test_*hand*.py' -v`
Expected: 변경 대상 테스트 전체 PASS. 기존 dirty의 hand_compare/transcript에서 실패하면 이번 변경과 분리해 기록하고 무관한 수정은 하지 않는다.

### Task 3: fresh 실행과 수동 crop 비교

**Files:** Create `docs/verify/export-hand-diagram-crop.md`, round01 아래 `fresh/`, `comparison/`, `inputs.json`, `result.md`.

**Interfaces:** 갱신 스킬/CLI를 fresh 실행자에게 제공한다. 평가자는 출력 확정 후 PNG/JSON과 사용자 JPEG 두 장을 사용한다.

- [x] **Step 1: 문맥을 상속하지 않는 fresh 실행자를 시작한다.** spawn_agent의 `fork_turns="none"`을 사용한다. 아래 프롬프트에서 저장소 절대 경로만 실행 checkout에 맞춘다.

```text
실험04 손그림 PDF를 export-hand-diagram 스킬에 따라 --crop으로 PNG 추출하세요.
작업 root: /Users/hyunjun_macbook_pro/Documents/Univ/논회실
원본: /Users/hyunjun_macbook_pro/Downloads/논회실 mux_261001_152503.pdf
스킬: .agents/skills/export-hand-diagram/SKILL.md
출력: output/validation/hand-diagram-crop/round01/fresh/
필요한 코드·스킬 참조·netlist만 읽고 실행하세요.
대화 이력, docs/superpowers, 수동 crop 이미지, 이전 validation 출력, 평가 보고서를 읽지 마세요.
코드·스킬을 수정하거나 독자적인 고정 좌표 fallback을 만들지 마세요.
애매한 곳은 스킬대로 후보를 생성하고 필요한 질문을 부모 에이전트에 반환하세요.
읽은 파일 목록, 실행 명령, 판단 근거, 생성 파일을 기록하세요.
```

- [x] **Step 2: 출력을 확정한다.** 실행자가 PNG/plan/report를 저장하면 hash를 기록한다. pending이 있으면 부모가 사용자에게 해당 후보만 제시하고 응답을 전달해 재개한다. 수동 JPEG를 사용자 응답 대신 사용하지 않는다.

```python
import hashlib, json
from pathlib import Path
root = Path('output/validation/hand-diagram-crop/round01/fresh')
hashes = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in sorted(root.rglob('*')) if p.is_file()}
(root.parent/'frozen-hashes.json').write_text(json.dumps(hashes, indent=2))
```

- [x] **Step 3: 평가 단계에 수동 crop을 공개한다.** 별도 fresh 평가자를 fork_turns=none으로 시작한다. Spec과 확정된 fresh 출력, 원본, 수동 JPEG 두 장을 제공한다. 스킬 수정/재크롭을 금지한다. 이미지를 직접 열어 각 페이지에 대해 아래 표를 채운다.

|항목|판정|증거|
|---|---|---|
|전원 단자 3개·극성·배선|PASS/FAIL|원본/출력 위치|
|마지막 행 홀과 하단 외곽|PASS/FAIL|하단 확대|
|행 번호와 외부 신호 표기|PASS/FAIL|좌우 확대|
|불필요한 구분선과 캡션 제외|PASS/FAIL|상단/하단|
|페이지별 범위와 2% 여백|PASS/FAIL|pt 계산과 pixel 차이|
|제목 조각 처리|PASS/FAIL|조각 존재 자체는 결함 아님|
|수동 crop과 경계 차이|수치|상하좌우/보드 너비|

비교 이미지는 Pillow로 보드 너비를 맞춰 나란히 배치한다. 원본/각 이미지에서 네 모서리를 읽고 정렬 근거를 기록한다. 리사이즈는 비교 이미지에만 적용하고 fresh PNG는 변경하지 않는다. 원시 pixel의 SSIM이나 일치율로 합격을 정하지 않는다.

- [x] **Step 4: 별도 애매한 사례를 검증한다.** 두 페이지가 모두 명확했더라도 합성 메모를 추가한 복사본을 별도 fresh 실행자에게 제공한다. 보드 밖에 의미가 애매한 물음표 메모를 더한 합성 PDF로 후보·질문 절차를 확인한다. 사용자 원본은 수정하지 않는다. 수동 비교 합격과 애매한 경우 처리 합격은 분리해서 기록한다.
- [x] **Step 5: 결과를 기록한다.** baseline/fresh별, 페이지별 PASS/FAIL, 실제 열람 파일, 각 agent ID, 로그, hash, 한계(공유 filesystem, 2페이지 표본)를 기록한다. FAIL이면 해당 Task로 돌아가 회귀 테스트/스킬을 보완하고 새 fresh 에이전트와 round02에서 재실행한다. 실패 round는 지우지 않는다.
- [x] **Step 6: 최종 검토와 전달.** `git diff --check`, 대상 테스트, 변경 범위 diff를 확인한다. 실제 이미지 비교를 확인한 뒤에만 스킬 검증 완료를 보고한다. 사용자에게 변경 요약, 테스트 결과, 두 페이지 비교 이미지, 미해결 사항을 전달한다. commit/push는 하지 않는다.

## Self-review

- 모든 요구를 Task 1(좌표/여백), Task 2(기본값/의미 판단/pending), Task 3(독립 재현/비교)에 배정했다.
- 수동 JPEG를 fresh 생성 전에 읽히지 않는다. 코드 테스트 성공을 수동 예시와의 비교 대신 사용하지 않는다.
- 고정 좌표 변경이나 색상 기반 의미 분류로는 요구를 충족할 수 없어 에이전트 판독과 결정론적 크롭을 분리했다.
- crop-plan 필수 도입에 따른 직접 CLI 호출 변경을 Spec/Task 2에 명시했다.
- 구현 전 사용자에게 계획 검토를 요청한다. 부모가 구현하고 fresh 에이전트가 독립 crop/비교를 담당한다.

## 실행 기록

구현과 검증 기록: `docs/verify/export-hand-diagram-crop.md`, `output/validation/hand-diagram-crop/progress.md`. 통합 테스트는 독립 합성 fixture를 위해 `tests/test_hand_crop_export.py`에 분리했다. 최종 비교 결과는 round02/comparison에 보존한다. 전체 검사의 기존 config 경로 실패 1건은 별도 재현했고 수정 범위에서 제외했다.
