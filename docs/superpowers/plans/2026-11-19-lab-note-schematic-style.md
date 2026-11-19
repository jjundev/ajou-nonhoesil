# 논회실 실험 6~10 회로도 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 전자회로2의 회로도 작도 규칙을 `logic-lab-review-pack`에 반영하고, 실험 6~10 실험설명의 회로·배선 블록도 23개를 갱신한다.

**Architecture:** 실험별 그림 원고에서 배치와 노드 의미를 지정하고 공용 SVG 출력 함수에서 글꼴과 테마를 적용한다. 발행 팩의 생성 파일을 별도 stage에 복사해 실험설명 갱신분을 조립하고 기존 `check`와 `publish`를 사용한다.

**Tech Stack:** Python, 기존 `Fig` 작도 원고, SVG, Pretendard SemiBold WOFF2, FontTools, Playwright Chromium, pytest.

**Spec:** 같은 채팅에서 작성한 `grill-yourself` 설계의 권장안 A를 이 문서의 [적용 명세](#적용-명세)에 옮겼다. 전자회로2 원본 기준은 [회로 배치](/Users/hyunjun_macbook_pro/Documents/Univ/전자회로2/.claude/skills/ec2-review-pack/references/content-rules.md:25)와 [회로 표기](/Users/hyunjun_macbook_pro/Documents/Univ/전자회로2/.claude/skills/ec2-review-pack/references/solution-style.md:396)를 참조한다.

## Global Constraints

- 범위는 실험 6~10 발행 노트가 참조하는 35개 고유 외부 SVG 중 아래 표의 23개다. 실험별 수량은 순서대로 `6 / 2 / 4 / 4 / 7`이다.
- 입력 왼쪽·출력 오른쪽이 기본이다. 같은 전기적 노드의 점과 라벨은 같은 색으로 묶는다. 라벨–도선 간격은 첨자를 포함한 글자 외곽 기준 최소 `0.6em`이다.
- 회로 라벨은 실제 Pretendard `600` 정체, 첨자는 native `<tspan baseline-shift="sub" font-size="78%">` 또는 `baseline-shift="super"`다. 디지털 핀 이름과 핀 번호는 교안 표기를 따르고 보수·반전 표현은 뜻이 보존되어야 한다.
- 실험설명 HTML과 MD는 같은 SVG를 사용한다. 브라우저 검수는 `375px / 1280px × light / dark`다. 테마 전환과 그림 불러오기는 로컬 자원으로 작동해야 한다.
- 발행 전 교안·기존 설명과 핀, 전기적 연결, 극성, 클록 엣지, 비트 순서, 소자값을 대조한다. 독립 검토 상태는 실제 검토 결과로 기록한다.
- 발행 차이는 승인된 파일 목록으로 확인한다. 본문·토픽 ID·읽음 저장 키, 문제설명 HTML·MD·원고, 기출 PDF·payload·자산, 확인문제와 원문 증거의 해시를 기준선과 비교한다.

## Review Focus

1. 흰 바탕의 기존 색이나 설치된 시스템 폰트 없이 열었을 때도 회로 선과 한글·첨자가 읽힌다. OS 설정을 라이트로 고정하고 HTML 토글로 SVG 색 전환을 확인한다. Task 1, 4.
2. 같은 엣지·핀 표기에도 교차점의 잘못된 점 하나가 다른 넷을 만들 수 있다. 교차·분기·반전 버블을 각각 대조하고 공통 클록과 되먹임을 추적한다. Task 2.
3. 375px에서 넓은 `ram2bit`·`dac-block`의 한쪽 열이나 하단 핀을 읽기 어려울 수 있다. 모든 필수 라벨을 실제 화면 크기에서 검사하고 두 그림의 배선을 끝까지 확인한다. Task 2, 3, 4.
4. 실험 6의 `tff-from-jk.svg`와 실험 7~10의 함수는 노트 외 출력에서도 쓰인다. 노트의 새 참조와 기존 문제설명·워크북용 SVG의 해시를 함께 검사한다. Task 2, 3, 4.
5. 기존 문제설명 CSS 불일치가 새 오류를 가릴 수 있고, 발행 사본에 확인문제나 사용자 추가 파일이 섞여 있다. stage의 `generated_files` 일치 및 최종 팩의 전체 허용 차이를 확인한다. Task 4.

---

## 적용 명세

실제 분기, 입력·출력 단자, 이름 붙은 내부 노드를 표시한다. 비접속 교차, 이름 없이 도선 중간에 찍힌 장식 점, 접지 기호에 바로 붙은 비분기 점은 생략한다. 반전 버블은 게이트나 클록 기호의 일부로 구분한다. 주요 신호는 인접 라벨이 구별되도록 파랑과 빨강을 고르고, 같은 넷의 점과 라벨에는 같은 `data-node`와 `data-node-color`를 넣는다. 도선·부품값은 기본색을 쓴다. 읽기에 필요한 신호명, 부품과 핀, 값, 극성을 SVG에 쓰고 회로 동작을 설명하는 문장은 기존 `figcaption`에 둔다. 교안의 확인된 모순·보충 모형 표기는 해당 토픽의 주의와 MD 근거를 따른다.

| 실험 | SVG 파일명과 생성 진입점 | 원문 대조에서 특히 볼 연결 |
|---|---|---|
| 06, 6개 | `not-loop` → `not_loop`, `sr-basic-nand`·`sr-latch-enable`·`d-latch` → `latch`, `jk-latch` → `jk_latch`, `tff-from-jk-note` → `tff_fig` | NAND 교차 되먹임, D와 보수, Enable, T의 J/K 분기와 클록 버블 |
| 07, 2개 | `shift` → `chain`, `internal` → `internal` | D 시프트 모형의 공통 클록과 Q→다음 D, 7496의 직렬·프리셋 신호와 기존 판본 주의 |
| 08, 4개 | `ripple-block` → `ripple_block`, `sync-block` → `sync_block`, `decoder-and` → `decoder`, `7490-block` → `block7490` | A→다음 CLK와 공통 CLK의 차이, 디코더의 보수 조합, QA 12번→CLKB 1번 |
| 09, 4개 | `nand-latch` → `nand_latch`, `ram1bit` → `ram1`, `ram2bit` → `ram2`, `opendrain` → `opendrain` | 1비트 RAM의 Input/보수 및 Read/Write, 2비트 RAM의 WR1 Set·WR0 Reset, 10kΩ 풀업과 출력 |
| 10, 7개 | `opamp-inv` → `opamp_inv`, `summing` → `summing`, `network` → `network`, `oc` → `oc`, `dac-block` → `dac`, `comparator` → `comparator`, `flash` → `flash` | 가산점·피드백, 가중 저항과 R–2R, OC 풀업, DAC 비트 순서·저항값·핀, 비교기 `+`/`−`, Flash 임계값 |

실험 6의 `tff-from-jk-note.svg`만 새 파일명을 사용한다. `tff-from-jk.svg`는 문제설명 링크가 가리키는 기존 파일이다. 파형, 상태도, 핀 배치도, 개념 흐름도, 세그먼트 표시는 이번 변경 범위를 확인할 때 대조할 자산이다.

## 파일 책임

| 파일 | 책임 |
|---|---|
| `.claude/skills/logic-lab-review-pack/SKILL.md`, `references/authoring.md`, `references/verification.md` | 작성 진입점, 회로도 세부 규칙, 원문·화면 검증 기준 |
| `scripts/lab/review_pack/note_schematic.py`, `requirements-dev.txt` | 외부 SVG의 테마와 실제 글꼴을 공급하는 함수와 저작 의존성 |
| `docs/learning-pack-source/실험06/{figs.py,build_run.py,sections.py}` | 실험 6 노트 그림 진입점, RUN 연동, 새 T 플립플롭 자산 참조 |
| `docs/learning-pack-source/실험07/figures.py`, `실험08/figures.py`, `실험09/figures.py`, `실험10/figures.py` | 각 실험 노트 그림 생성부와 기존 `build(run, m)` 연동 |
| `tests/test_review_pack_note_schematic_style.py` | 글꼴·SVG 계약, 실험별 산출 목록, 테마·모바일 회귀 검사 |
| `복습노트/실험NN/실험NN_실험설명.html`, `.pack/실험NN_실험설명.md`, `.pack/figures/`, `.pack/assets/note-template.html`, `.pack/manifest.json`, `.pack/검증결과.md` | stage에서 갱신하는 발행 파일과 검증 기록. `NN=06,07,08,09,10` |

### Task 1 · 공용 SVG 출력과 스킬 기준

**파일:** `scripts/lab/review_pack/note_schematic.py`와 `tests/test_review_pack_note_schematic_style.py`를 만든다. `requirements-dev.txt`와 위 스킬 문서 3개를 수정한다.

**인터페이스:** `style_note_schematic(svg: str, *, font_path: Path) -> str`. 입력은 `viewBox`, `title`, 의미가 지정된 점·글자 및 작도 기호를 가진 네이티브 SVG다. 출력은 페이지 CSS를 따로 읽을 필요 없이 `<img>`와 독립 열기에서 작동하는 SVG다. 실험 코드에서 `font_path`는 저장소의 `.claude/skills/logic-lab-review-pack/assets/vendor/pretendard/Pretendard-SemiBold.woff2`를 넘긴다.

- [ ] `test_svg_embeds_real_semibold_and_keeps_node_and_subscript`를 작성한다. SVG 표본에 점과 `V<tspan baseline-shift="sub" font-size="78%">o</tspan>`를 넣고 `data-node="out"`, `data-node-color="blue"`가 둘에 있는지 확인한다. `@font-face`에 담긴 WOFF2를 디코딩해 `TTFont`의 `OS/2.usWeightClass == 600`과 `getBestCmap()`의 `V`, `o`, `Ω`, `출` 네 글리프를 검사한다. `Ω`와 `출`은 표본의 다른 라벨에 넣는다.
- [ ] `test_svg_embedded_as_image_follows_parent_color_scheme`을 작성한다. `color_scheme="light"`인 Chromium에서 외부 SVG를 `<img>`로 붙인다. 부모 `color-scheme`을 `light`와 `dark`로 바꾼 두 화면에서 `img.decode()`가 성공하고 배경과 기본 선의 픽셀이 서로 구분되며 테마마다 달라지는지 단색 영역을 샘플링한다.
- [ ] `requirements-dev.txt`에 `fonttools[woff]`를 추가하고 같은 저장소 `.venv`에 설치한다. 계획 작성 시 이 venv에는 FontTools와 Brotli가 없었다.
- [ ] `.venv/bin/python -m pytest -q -n 0 tests/test_review_pack_note_schematic_style.py`를 실행해 함수 미구현 실패를 확인한다.
- [ ] `style_note_schematic`을 구현한다. 기존 `viewBox`·`title`·`desc`·기하를 사용하고, 회로 원고가 명시한 `fig-ink`, `fig-text`, `fig-dot`과 노드 속성에 색과 글꼴을 적용한다. 독립 SVG에서 `@media (prefers-color-scheme: dark)`와 기본 팔레트를 제공한다. 입력 SVG의 `<text>`·`<tspan>` 문자를 모아 600 WOFF2를 서브셋으로 포함한다. `TTFont`의 `recalcTimestamp=False`로 재생성 바이트를 결정적으로 유지하고 기존 vendored 폰트와 LICENSE를 사용한다. 노드 ID와 접속점은 회로 원고에서 명시한다.
- [ ] `SKILL.md`의 SVG 단락을 `authoring.md`의 `회로도 작도` 절로 연결한다. 해당 절에 [적용 명세](#적용-명세)의 배치·기호·글꼴 규칙을 적고 `verification.md`에 회로별 원문·화면 점검 항목을 적는다.
- [ ] 같은 pytest 명령을 다시 실행한다. 두 테스트가 통과하고 브라우저 테스트가 실제 실행되었으면 이 작업을 로컬 커밋으로 묶는다.

### Task 2 · 실험 6~9 논리 회로도 16개

**파일:** 실험 06의 `figs.py`, `build_run.py`, `sections.py`, 실험 07·08·09의 `figures.py`, 공용 테스트 파일을 수정한다.

**인터페이스:** 해당 그림 모듈 각각이 `draw_note_schematics(output_dir: Path) -> tuple[Path, ...]`를 제공한다. `output_dir` 바로 아래에 적용 표의 이름으로 `.svg`를 쓰고 생성한 경로를 반환한다. 실험 06 `build_run.py`와 실험 07~09 `build(run, m)`에서 기존 노트 SVG 출력 다음에 호출한다. 노트 자산만 생성할 때는 각 실험의 소스 폴더를 `sys.path`에 추가한 별도 Python 프로세스에서 이 함수를 호출한다. `figlib`·`figures` 모듈명이 실험 간에 겹친다.

- [ ] `test_digital_note_schematic_inventory_and_reproducibility`를 작성한다. 06~09를 순회해 각각 새 임시 디렉터리 두 곳을 받는 별도 프로세스로 생성한다. 파일명 집합을 적용 표와 대조하고 `6 / 2 / 4 / 4`와 두 실행의 SVG 해시 일치를 assert한다. 실험 6의 대상 집합에는 `tff-from-jk-note.svg`가 있고 `tff-from-jk.svg`는 없는지 확인한다.
- [ ] `.venv/bin/python -m pytest -q -n 0 tests/test_review_pack_note_schematic_style.py -k digital`을 실행해 진입점 미구현 실패를 확인한다.
- [ ] 적용 표의 16개를 기존 `Fig` 원고에서 다시 배치하고 각 생성 진입점을 연결한다. 예전 그림 함수가 `register()`에도 쓰이면 노트용 옵션·분기만 추가해 기본 호출의 SVG 바이트를 비교한다. 실험 06 `sections.py`에서 새 T 플립플롭 파일명을 사용한다.
- [ ] 교안의 실제 페이지와 [적용 명세](#적용-명세)의 연결을 대조한다. `실험8_Counter_회로정정본.pdf`를 실험 8 기준으로 삼는다. 06 래치의 교차, 07 공통 CLK, 08 QA→CLKB, 09 WR1/WR0의 입력부터 출력까지를 점과 반전 기호로 추적하고 그림별 페이지·판정을 작업 기록에 남긴다. 375px에서 `ram2bit`는 A/B 두 칸 모두 배선을 읽을 수 있도록 필요한 경우 높이와 여백을 늘린다.
- [ ] 같은 pytest 명령의 통과와 기존 워크북 그림 경로의 SVG 바이트 일치를 확인하고 이 작업을 로컬 커밋으로 묶는다.

### Task 3 · 실험 10 DAC·ADC 회로도 7개

**파일:** `docs/learning-pack-source/실험10/figures.py`와 공용 테스트 파일을 수정한다.

**인터페이스:** Task 2와 같은 `draw_note_schematics(output_dir: Path) -> tuple[Path, ...]`를 사용한다. 파일명은 적용 표의 실험 10 행을 따른다.

- [ ] `test_dac_note_schematic_inventory_and_summing_node`를 작성한다. 실험 10의 산출 파일명 집합이 적용 표의 7개와 같고 `stair.svg`가 없는지 확인한다. `summing.svg`의 이름 있는 가산점에 `data-node="summing"`을 두고 점과 전압 라벨의 `data-node-color` 값이 같은지 assert한다.
- [ ] `.venv/bin/python -m pytest -q -n 0 tests/test_review_pack_note_schematic_style.py -k dac`를 실행해 진입점 미구현 실패를 확인한다.
- [ ] 7개 회로도를 갱신하고 `build(run, m)`에서 새 노트 출력을 연결한다. 교안 `강의노트/실험10. DAC & ADC.pdf`와 노트의 가중 저항을 대조한다. `dac-block.svg`의 `22.6kΩ`, `10.5kΩ`, `4.5kΩ`, `1.5kΩ`, `R_f`, 비트 순서, 가산점과 기준 전압 연결을 따라간다. 비교기·Flash의 입력 극성과 기준 전압은 원문의 해당 그림을 읽어 확인한다.
- [ ] 같은 pytest 명령의 통과와 `summing-given`, `network-given`, `dac-given*`, `comparator-given`의 기존 출력 바이트 일치를 확인하고 이 작업을 로컬 커밋으로 묶는다.

### Task 4 · 실험설명 stage 검사와 발행

**파일:** 파일 책임 표의 `복습노트/실험NN/` 항목과 공용 테스트 파일을 수정한다. 일회성 검증 코드와 스크린샷은 `tmp/review-pack/`의 새 실행 폴더를 사용한다.

**인터페이스:** `check_pack(folder)`의 성공은 빈 오류 목록이다. 발행은 `python -m scripts.lab.review_pack publish --root . --stage STAGE --experiment N`으로 실행한다. 기존 발행기가 생성 파일만 포함한 stage를 받고, 목적지의 생성 목록 밖 파일과 교체 전 백업을 보존한다.

- [ ] 원본 팩별 상대경로·SHA-256·`generated_files`를 기록한다. 원본의 `.pack/manifest.json`에 기록된 `generated_files`만 새 stage에 복사하고 공용 `.vendor`를 stage의 형제 위치에 둔다. 전체 `check` 실패가 정확히 `explanation_html: explanation differs from authored content` 한 건인지 팩별로 비교한다.
- [ ] stage 다섯 개의 `.pack/assets/note-template.html:260`에서 `body { height: 100vh; height: 100dvh;`로 시작하는 한 줄을 스킬 원본 같은 위치의 `html { height: 100%; } body { height: 100%;` 줄로 동기화한다. `check`가 이 시점에서 정상 통과하고 발행 상태의 문제설명 HTML·MD 해시와 stage 복사본이 일치하는지 확인한다.
- [ ] `test_published_note_schematic_sources_and_theme`을 작성한다. 실험 6~10을 375·1280과 두 테마로 매개변수화한다. 각 그림의 토픽으로 이동해 `img.decode()`와 이미지 경계가 노트 콘텐츠 영역 안에 드는지 확인한다. 원격 요청은 차단한다. 실험 6의 실험설명 HTML/MD는 새 T 플립플롭 파일명을, 문제설명 HTML/MD는 기존 파일명을 참조해야 한다. 테스트는 `LAB_NOTE_STAGE_PARENT` 환경변수가 있으면 그 경로의 `실험NN`, 없으면 저장소의 `복습노트/실험NN`을 읽는다.
- [ ] `LAB_NOTE_STAGE_PARENT=STAGE_PARENT .venv/bin/python -m pytest -q -n 0 tests/test_review_pack_note_schematic_style.py -k published`를 실행한다. 실험 6의 기존 T 플립플롭 참조에서 새 경로 검사가 실패하는지 확인한다.
- [ ] Task 2~3의 SVG를 각 stage `.pack/figures/`에 생성한다. 실험 6 HTML의 `src=".pack/figures/tff-from-jk.svg"` 한 곳만 `tff-from-jk-note.svg`로 연결한다. 필요한 그림 설명 문구는 해당 `figcaption`과 생성 원고에서 함께 갱신한다. 기존 `html2md.convert_pack()`으로 stage 노트 MD를 동기화하고 새 파일은 실험 6의 `generated_files`에 등록한다.
- [ ] `LAB_NOTE_STAGE_PARENT=STAGE_PARENT .venv/bin/python -m pytest -q -n 0 tests/test_review_pack_note_schematic_style.py`를 실행한다. 실제 Chromium 통과와 375px/1280px, 라이트/다크에서 23개의 라벨·접속점·클리핑을 눈으로 확인한다. 특히 `ram2bit`·`dac-block`은 가장자리 핀과 두 신호 경로를 모두 판독한다. 글꼴 확인은 SVG를 직접 열어 `document.fonts.ready` 뒤 실제 로드된 600 face와 첨자를 검사한다.
- [ ] 다섯 stage의 `.pack/검증결과.md`에 그림명·교안 쪽·실제 검토 결과를 기록하고 `manifest.checks`를 갱신한다. 파일 차이는 표의 23개 SVG 경로와 실험설명 HTML/MD의 그림 관련 변경, 템플릿 한 줄, manifest, 검증 기록으로 제한한다. 문제설명·기출·확인문제·근거 파일의 발행 전 해시와 비교한다. 모든 stage의 `check`가 `OK (mechanical checks only)`이고 생성 파일 목록과 실제 파일 목록이 일치하는지 확인한다.
- [ ] 다섯 stage가 검사된 뒤 N=6,7,8,9,10에 기존 `publish`를 실행한다. 각 명령이 반환한 백업 경로를 기록한다. 최종 경로에서 전체 `check` 다섯 번과 `LAB_NOTE_STAGE_PARENT`를 설정하지 않은 pytest를 다시 실행한다. stage와 발행본의 변경 파일 해시가 같고 생성 목록 밖 확인문제 및 사용자 파일까지 기준선과 일치하면 발행 갱신을 로컬 커밋으로 묶는다.
