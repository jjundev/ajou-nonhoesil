# export-hand-diagram 스킬 구현 계획 (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 손그림 결선도 PDF 로부터 300 DPI 크롭 PNG 를 추출하고, `netlist.md` 메타데이터 및 검토 전사를 기반으로 전 실험(01~10)에 걸쳐 표준 국문 파일명으로 정본 아카이빙하는 독자 스킬 `export-hand-diagram` 을 구축한다.

**Architecture:** 
1. `scripts/lab/export_hand_diagrams.py` 모듈을 일반화하여 `netlist_parser` 로부터 동적으로 회로 정보(`id`, `item`, `diagram`, `title`)를 추출하고, 검토 전사(`p*.json`)가 있으면 페이지 셔플에도 완벽히 대응하는 동적 파일명 도출 로직을 작성한다.
2. 템플릿 크롭 지오메트리(`ix: [20, 565]`, `iy: [30, 740]`)를 모듈 상수로 정의하여 상단 검은선/헤더/하단캡션을 일관되게 제거하고 회로/전원잭/배선/행라벨만 타이트하게 남긴다.
3. `.agents/skills/export-hand-diagram/SKILL.md` 및 `.claude/skills/export-hand-diagram/SKILL.md` 문서를 저작하고, `review-hand-diagram` 완료 안내문에 연계 호출을 등록한다.

**Tech Stack:** Python 3.14 · PyMuPDF (`fitz`) · Pillow (`PIL`) · `unittest` · Markdown (Agent Skills)

**Spec:** `docs/plans/2026-09-10-review-hand-diagram-칩자리-설계.md` 및 2026-09-10 대화 설계안

## Global Constraints

- **파일명 규격**: `{실험폴더명}_{소단원}_손그림_{회로명}.png` (예: `실험01_1-1_손그림_3입력_AND.png`, `실험01_3_손그림_복합논리회로.png`).
- **크롭 영역**: 300 DPI 기준 템플릿 좌표 `ix in [20, 565]`, `iy in [30, 740]`.
- **저장 디렉토리**: `보고서/실험NN/결선도/손그림/`.
- **무결성/회귀**: `tests/test_export_hand_diagrams.py` 및 `tests/test_skill_docs.py` 통과 필수.
- **스킬 쌍둥이 원칙**: `.agents/skills/` 와 `.claude/skills/` 양쪽에 동일하게 등록.

---

### Task 1: `scripts/lab/export_hand_diagrams.py` 일반화 (`netlist.md` 연동 및 동적 파일명 도출)

**Files:**
- Modify: `scripts/lab/export_hand_diagrams.py`
- Test: `tests/test_export_hand_diagrams.py`

**Interfaces:**
- Consumes:
  - `scripts.lab.netlist_parser.parse_netlist(netlist_path)`
  - `scripts.lab.config.experiment_dir(exp)`
  - `scripts.lab.config.experiment_folder_name(exp)`
  - `scripts.lab.hand_grid.board_image`, `render_page`
- Produces:
  - `BOARD_CROP_TEMPLATE_X: tuple = (20, 565)`
  - `BOARD_CROP_TEMPLATE_Y: tuple = (30, 740)`
  - `resolve_circuit_filenames(experiment: int, page_count: int, round_dir: Optional[Path] = None) -> List[str]`
  - `export_hand_diagrams(experiment: int, pdf_path: Optional[str|Path]=None, out_dir: Optional[str|Path]=None, dpi: int=300, crop_board: bool=True) -> List[Path]`

- [ ] **Step 1: 실패하는 단위 테스트 작성**

`tests/test_export_hand_diagrams.py` 에 다음 테스트 함수들을 추가한다:
```python
    def test_resolve_circuit_filenames_from_netlist(self):
        filenames = ehd.resolve_circuit_filenames(1, 5)
        expected = [
            "실험01_1-1_손그림_3입력_AND.png",
            "실험01_1-2_손그림_3입력_OR.png",
            "실험01_2-1_손그림_3입력_NAND.png",
            "실험01_2-2_손그림_3입력_NOR.png",
            "실험01_3_손그림_복합논리회로.png",
        ]
        self.assertEqual(filenames, expected)

    def test_resolve_circuit_filenames_fallback(self):
        # netlist.md 가 없는 가상의 실험 번호 99
        filenames = ehd.resolve_circuit_filenames(99, 2)
        self.assertEqual(filenames, ["실험99_손그림_p1.png", "실험99_손그림_p2.png"])
```

- [ ] **Step 2: 테스트 실행하여 실패 확인**

Run: `python3 -m unittest tests/test_export_hand_diagrams.py -k test_resolve`
Expected: FAIL (`AttributeError: module ... has no attribute 'resolve_circuit_filenames'`)

- [ ] **Step 3: `scripts/lab/export_hand_diagrams.py` 에 일반화 로직 구현**

1. 하드코딩 `EXPERIMENT_CIRCUIT_NAMES` 딕셔너리 제거.
2. `BOARD_CROP_TEMPLATE_X = (20, 565)` 및 `BOARD_CROP_TEMPLATE_Y = (30, 740)` 상수 정의.
3. `resolve_circuit_filenames` 구현:
   - `netlist.md` 로드 및 파싱 (`parse_netlist`).
   - `s.kind == "circuit"` 섹션 순회:
     - `s.item` 에서 소단원 번호 추출 (`re.sub(r'^[A-Za-z0-9]+\.P?', '', s.item)`).
     - `s.diagram` 에서 회로명 추출: `결선도` 제거, `_\d+단계.*` 스텝 제거, 확장자 제거.
     - 기본 파일명 패턴: `{folder}_{sub_item}_손그림_{circuit_name}.png`.
   - `round_dir/전사/p{i+1}.json` 이 존재할 경우:
     - 전사 파일 내 `circuit` 키(예: `e1_and`) 또는 `title` 을 `netlist` 섹션과 매칭하여 페이지 번호 순서에 맞게 배치 (셔플 대응).
   - `netlist` 없거나 페이지 수 초과 시 `f"{folder}_손그림_p{i+1}.png"` 로 graceful fallback.
4. `export_hand_diagrams` 에서 `round_dir` 감지 및 `resolve_circuit_filenames` 호출, 크롭 상수를 사용하여 저장.

- [ ] **Step 4: 테스트 실행하여 성공 확인**

Run: `python3 -m unittest tests/test_export_hand_diagrams.py`
Expected: PASS (모든 테스트 통과)

- [ ] **Step 5: 커밋**

```bash
git add scripts/lab/export_hand_diagrams.py tests/test_export_hand_diagrams.py
git commit -m "feat(lab): netlist.md 연동 및 전사 기반 손그림 동적 파일명 도출 일반화"
```

---

### Task 2: `export-hand-diagram` 스킬 문서 저작

**Files:**
- Create: `.agents/skills/export-hand-diagram/SKILL.md`
- Create: `.claude/skills/export-hand-diagram/SKILL.md`

**Interfaces:**
- Consumes: `python3 -m scripts.lab.export_hand_diagrams`
- Produces: Agent skill definition for Antigravity & Claude Code

- [ ] **Step 1: 스킬 문서 초안 작성**

`.claude/skills/export-hand-diagram/SKILL.md` 와 `.agents/skills/export-hand-diagram/SKILL.md` 에 공통 작성:
- Frontmatter:
  ```yaml
  ---
  name: export-hand-diagram
  description: 손그림 결선도 PDF(검토 완료본)의 각 쪽을 브레드보드 본체 영역으로 정밀 크롭한 300 DPI PNG 로 일괄 추출하여 결선도/손그림/ 에 정본으로 아카이빙한다. 사용자가 "손그림 png 뽑아줘", "손그림 결선도 추출", "결선도 아카이빙", "/export-hand-diagram" 등을 요청할 때 사용한다.
  ---
  ```
- 인자 규격: `<실험번호|주차> [PDF경로] [--out DIR] [--dpi DPI] [--full-page]`
- 실행 절차:
  1. 실험 번호를 폴더 이름으로 변환 (`scripts.lab.config`).
  2. 최신 승인본 PDF 자동 감지 (`output/손그림검토/round<max>/hand.pdf` 우선).
  3. `python3 -m scripts.lab.export_hand_diagrams` 실행.
  4. 생성된 PNG 파일 확인 및 회로명·해상도·용량 보고.

- [ ] **Step 2: 스킬 불변식 테스트 확인**

Run: `python3 -m unittest tests/test_skill_docs.py`
Expected: PASS

- [ ] **Step 3: 커밋**

```bash
git add .agents/skills/export-hand-diagram/SKILL.md .claude/skills/export-hand-diagram/SKILL.md
git commit -m "feat(skills): 손그림 결선도 크롭 및 아카이빙 스킬 (export-hand-diagram) 등록"
```

---

### Task 3: `review-hand-diagram` 스킬에 연계 안내 1줄 추가

**Files:**
- Modify: `.claude/skills/review-hand-diagram/SKILL.md`
- Modify: `.agents/skills/review-hand-diagram/SKILL.md`

**Interfaces:**
- Consumes: None
- Produces: 안내 문구 추가

- [ ] **Step 1: 안내 문구 추가**

`review-hand-diagram/SKILL.md` 의 "5. 판정문을 쓴다" 절 하단 결과 보고 안내에 다음 문장을 추가:
> 모든 쪽이 '제출 가능'으로 판정되면, 보고서 및 노션 첨부용 300 DPI 크롭 PNG 를 생성하기 위해 `/export-hand-diagram <실험번호>` 실행을 사용자에게 안내한다.

- [ ] **Step 2: 테스트 확인**

Run: `python3 -m unittest tests/test_skill_docs.py`
Expected: PASS

- [ ] **Step 3: 커밋**

```bash
git add .agents/skills/review-hand-diagram/SKILL.md .claude/skills/review-hand-diagram/SKILL.md
git commit -m "docs(skills): review-hand-diagram 완료 후 export-hand-diagram 연계 안내 추가"
```

---

### Task 4: 통합 검증 (실험01 대상 실제 실행)

**Files:**
- Verify: `보고서/실험01/결선도/손그림/*.png`

- [ ] **Step 1: 모듈 CLI 직접 실행**

Run: `python3 -m scripts.lab.export_hand_diagrams 1`
Expected: 5개 파일 추출 성공 로그 출력.

- [ ] **Step 2: 추출된 5개 파일 속성 검증**

Run:
```bash
python3 -c "
from pathlib import Path
from PIL import Image

pdir = Path('보고서/실험01/결선도/손그림')
expected = [
    '실험01_1-1_손그림_3입력_AND.png',
    '실험01_1-2_손그림_3입력_OR.png',
    '실험01_2-1_손그림_3입력_NAND.png',
    '실험01_2-2_손그림_3입력_NOR.png',
    '실험01_3_손그림_복합논리회로.png',
]
for name in expected:
    p = pdir / name
    assert p.is_file(), f'파일 누락: {name}'
    with Image.open(p) as img:
        assert img.size == (1817, 2368), f'해상도 불일치: {img.size}'
print('[VERIFIED] 5개 파일 모두 1817x2368 정상 규격 확인 완료.')
"
```
Expected: `[VERIFIED] 5개 파일 모두 1817x2368 정상 규격 확인 완료.`

- [ ] **Step 3: 전체 회귀 테스트 통과 확인**

Run: `python3 -m unittest discover -s tests -p "test_*.py"`
Expected: 모든 테스트 PASS.
