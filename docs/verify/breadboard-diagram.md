# `breadboard-diagram` 격리 재생성 런북

**질문.** `breadboard-diagram/SKILL.md` 의 규칙(슬롯·기준선·단계·파일명)만 읽은
에이전트가 실험01 결선도 13장을 승인본과 같은 넷으로 다시 그리는가. 갈리는
자리 = SKILL.md 에 더 적어야 할 규칙. 새 주차(실험03)를 저작하기 전에 안다.

`verify-draft-lab-spec` 의 틀(답안 제거 → 격리 실행 → 자동 대조 → 사람이 판정)을
빌린다. 그 스킬의 §절대 규칙 1~7 이 그대로 적용된다. 답안은 파일 하나 —
`보고서/실험01/결선도/배치.py`(실험01 결선)다. 엔진 `render_breadboard.py` 는 주차를 모르므로
그대로 남는다(2026-09-15 분리 전에는 엔진 파일에서 실험01 구간을 잘라냈다). 대조는
`scripts/lab/breadboard_compare.py`.

## 절대 규칙 (verify-draft-lab-spec 과 같다 — 여기 다시 적는 이유는 그 스킬 폴더가
격리 트리에서 지워지기 때문이다)

1. 답안지를 전부 뺀 트리에서만 돈다. 목록은 §답안지 목록.
2. 못 빼는 누출은 적는다. 형제 문서 `주차별.md` 의 회로 ID 목록·SKILL.md §4a 「슬롯·기준선·단계」·
   「파일명 규칙」 문단, `docs/schema/lab-netlist-v2.md` 의 `E1_SLOTS` 언급,
   그리고 **netlist.md 의 `## 단계` 표 자체**(`c7→c9`·`b19`·`a8→a18` 같은 홀
   주소를 적는다 — 그것이 입력이다)는 계약서라 못 뺀다. 판정.md 1절에 적고
   그 자리의 일치는 합격 근거로 세지 않는다.
3. 프롬프트에 사유와 합격 조건을 쓰지 않는다. 이력 명령도 금지.
4. 규칙이 막았는지 검사(`verify()`)가 잡았는지를 가른다. 에이전트 보고 3항이
   근거다. 첫 렌더 통과인데 승인본과 갈렸으면 규칙도 검사도 없는 자리다.
5. 자동 합격은 없다. 치명 0 은 넷이 같다는 뜻일 뿐이다.
6. 아무것도 고치지 않는다 — SKILL.md 도 승인본도. 갈린 자리는 묻고 멈춘다.
7. 세션 메모리 주입을 판정.md 첫 줄에 적는다(`judge()` 가 넣는다).

## 실행 절차

0. **통제군과 작업 트리를 확인한다.**

   ```bash
   python -c "
   from pathlib import Path
   from scripts.lab import config
   d = Path(config.experiment_dir(1))
   for f in ('결선도/netlist.md', '결선도/배치.py', '체크리스트/명세.md'):
       print('O' if (d / f).exists() else 'X', d / f)
   print(len(list((d / '결선도').glob('*.png'))), 'png (13 이어야 한다)')
   print('E1_SLOTS' in (d / '결선도/배치.py').read_text(encoding='utf-8'), '승인본 빌더 있음')
   "
   git status --porcelain .claude/skills/breadboard-diagram scripts/lab docs/schema 보고서/실험01
   ```

   `X`·13 아님·`False`·비어 있지 않은 status 중 하나라도 있으면 멈춘다 —
   격리 트리는 `git archive HEAD` 다.

1. **격리 트리를 만든다.** 답안지 목록은 §답안지 목록을 **그대로** 옮긴다.

   ```bash
   python -c "
   import tempfile
   from pathlib import Path
   from scripts.lab.isolate import build_isolated_tree
   KEYS = [
       '.claude/skills/verify-draft-lab-spec', '.claude/skills/verify-write-result-report',
       '.claude/skills/review-hand-diagram', '.claude/skills/export-hand-diagram',
       '.claude/skills/write-pre-report', '.claude/skills/prep-lab-checklist',
       'docs/verify', 'docs/plans', 'docs/study', 'docs/rule-friction',
       'docs/notion-feedback', 'docs/corpus-audit', 'docs/강의노트_이론_실험_매핑_정리.md',
       'scripts/lab/hand_compare.py', 'scripts/lab/hand_transcript.py',
       'scripts/lab/export_hand_diagrams.py', 'scripts/lab/contact_sheet.py',
       'scripts/lab/breadboard_compare.py',
       'scripts/lab/isolate.py', 'scripts/lab/regen_compare.py', 'scripts/lab/specdiff.py',
       'scripts/lab/report_compare.py', 'tests',
       '보고서/실험01/결선도/배치.py', '보고서/실험01/결선도/*.png', '보고서/실험01/결선도/손그림',
       '보고서/실험01/체크리스트/체크리스트.html', '보고서/실험01/체크리스트/체크리스트.pdf',
       '보고서/실험01/실험사진', '보고서/실험01/실험중있었던일.md',
       '보고서/실험01/*예비보고서*.pdf', '보고서/실험01/*결과보고서*.pdf',
   ]
   dest = Path(tempfile.gettempdir()) / 'iso-실험01-bb'
   build_isolated_tree(Path('.'), dest, 1, KEYS, clear_subdirs=('output',))
   print(dest)
   "
   ```

   남는 것: `breadboard-diagram/` 의 `SKILL.md` 와 형제 문서 셋(`v1.md`·`주차별.md`·`연혁.md`)·엔진 `render_breadboard.py`(주차 결선 없음)·
   `.claude/assets/Breadboard.jpg`·`보고서/실험01/결선도/netlist.md`(입력)·
   `체크리스트/{명세,기록}.md`·`docs/schema/`·`강의노트/`·`.claude/데이터시트_출처.md`·
   `draft-lab-spec` 등 나머지 스킬·`scripts/lab/` 나머지·다른 실험 폴더.

2. **누출을 훑는다.**

   ```bash
   python -c "
   import tempfile
   from pathlib import Path
   from scripts.lab.isolate import leak_scan
   dest = Path(tempfile.gettempdir()) / 'iso-실험01-bb'
   TOKS = ['E1_SLOTS', '_e1_', 'build_e1', '결선도_3입력', '결선도_복합',
           '1단계_', '좌 7행', '좌 18행', '우 10행', 'c7→c9', 'a25', 'c9→c14', 'b19']
   hits = leak_scan(dest, TOKS)
   Path('tmp/verify-artifacts').mkdir(parents=True, exist_ok=True)
   Path('tmp/verify-artifacts/누출-실험01-bb.txt').write_text('\n'.join(hits), encoding='utf-8')
   for h in hits: print(h)
   print(len(hits), '건')
   "
   ```

   **정상(구조적 누출)**: `.claude/skills/breadboard-diagram/` 의 `SKILL.md`·`주차별.md`·`연혁.md`(「줄이기 전 원문」),
   `docs/schema/lab-netlist-v2.md`, `보고서/실험01/결선도/netlist.md`,
   `.claude/skills/draft-lab-spec/SKILL.md`(파일명 예시), `scripts/lab/render.py`·
   `validate.py`(단계 표 열 이름), `보고서/실험01/체크리스트/{명세,기록}.md`, 엔진
   조각 `engine/renderer.py`·`engine/placer.py` 의 `hashlib.sha256(` 줄(`leak_scan` 이 부분 문자열 매칭이라
   토큰 `a25` 가 `sha256` 의 부분 문자열로 걸리는 거짓 양성), 그리고
   **다른 실험 폴더**(`보고서/실험02/`·`실험03/` …)의 `배치.py`·`netlist.md`·`명세.md`·`기록.md` —
   슬롯 관례(`좌 7행` 등)와 단계 파일명(`1단계_`)이 겹친다. 다른 주차는 예시로 남기는 것이라
   빼지 않고 판정.md 1절에 적는다(분리 전에는 같은 문구가 엔진 파일의 실험02·03 구간에 있었다).
   엔진(진입점 `render_breadboard.py` 와 `engine/` 조각)은 §답안지 목록에 넣지 않는다 — 엔진에서 걸리면 그 줄을
   읽고, 진짜 홀 주소·주차 이름이면 엔진을 고친다(도구 변경, 따로 커밋한다).
   **그 밖의 파일**이 나오면 §답안지 목록에 더하고 1단계부터 다시 한다.

3. **대조 도구를 자기대조로 점검한다.**

   ```bash
   python -m unittest tests.test_lab_breadboard_compare.Rendered.test_자기대조는_치명_기능_0건 tests.test_lab_breadboard_compare.Rendered.test_자리표는_빌더가_앉힌_자리와_같다 2>&1 | tail -3
   ```

   `OK` 여야 한다.

4. **에이전트를 띄운다.** Agent 도구, 기본 모델, 백그라운드. §에이전트 프롬프트를
   글자 그대로 쓰고 `<작업 디렉토리>` 만 1단계가 찍은 경로로 채운다. 기다리는
   동안 격리 트리와 승인본은 건드리지 않는다. 형제 검증의 실측은 305k 토큰·21분.

5. **산출물을 보존한다.** 끝나면 격리 트리에서 저장소 `tmp/verify-artifacts/
   실험01-breadboard-격리-<YYYY-MM-DD>/` 로 복사한다: `보고서/실험01/결선도/`
   (재생성 PNG 와 재생성 빌더 `배치.py`), `tmp/격리보고.md`,
   2단계의 `누출-실험01-bb.txt`, 그리고 격리 트리의 엔진 — 진입점
   (`.claude/skills/breadboard-diagram/scripts/render_breadboard.py`)을
   `render_breadboard.py` 로, 조각 폴더(같은 곳의 `engine/`)를 `engine/` 으로
   복사한다 — 에이전트가 엔진에 헬퍼를 더했으면(대개 `engine/helpers.py`) 그
   신호가 여기 없으면 사라진다. 격리 트리를 지우기 전에 한다.

6. **판정 초안을 낸다.** 두 `배치.py` 는 저장소 엔진 하나로 불러온다
   (`breadboard_compare.load_board_at`). 템플릿 경로는 명시해 넘긴다.

   ```bash
   python -c "
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.breadboard_compare import judge
   art = Path('tmp/verify-artifacts/실험01-breadboard-격리-<YYYY-MM-DD>')
   leaks = [l for l in (art / '누출-실험01-bb.txt').read_text(encoding='utf-8').splitlines() if l]
   report = (art / '격리보고.md').read_text(encoding='utf-8') if (art / '격리보고.md').exists() else ''
   out = art / '판정.md'
   out.write_text(judge(1, Path(config.experiment_dir(1)) / '결선도/배치.py', art / '결선도/배치.py',
                        Path(config.experiment_dir(1)) / '결선도/netlist.md', art / '결선도',
                        str(Path('.claude/assets/Breadboard.jpg').resolve()),
                        leak_hits=leaks, agent_report=report), encoding='utf-8')
   print(out.read_text(encoding='utf-8'))
   "
   ```

   재생성 모듈에 `BOARDS` 가 없으면 2절이 그렇게 말한다. 그러면 재생성
   `배치.py` 를 읽어 `[(파일명, 빌더, stage)]` 목록을 손으로 만들어
   `render_chain` 에 넘기는 짧은 스크립트로 3~6절을 다시 낸다 — 그 사실 자체가
   「주차 빌더를 쓸 때」 문단의 판정 재료다.

   그다음 엔진 변경 신호를 본다: 5단계가 복사한 격리 트리 엔진을 저장소 엔진과
   대조한다.

   ```bash
   git diff --no-index .claude/skills/breadboard-diagram/scripts/render_breadboard.py \
       tmp/verify-artifacts/실험01-breadboard-격리-<YYYY-MM-DD>/render_breadboard.py
   git diff --no-index .claude/skills/breadboard-diagram/scripts/engine \
       tmp/verify-artifacts/실험01-breadboard-격리-<YYYY-MM-DD>/engine
   ```

   둘 중 하나라도 차이가 있으면(조각 폴더에 새 파일이 생긴 것도) 판정.md 에 "엔진 변경(도구 변경)" 으로 적는다 — 에이전트가
   엔진에 헬퍼를 더했다는 뜻이고, `judge()` 의 넷·자리·전환 대조는 저장소
   엔진으로 다시 잰 것이니 그 헬퍼가 판정에 반영되지 않았을 수 있다.

7. **사람이 본다.** 판정.md 9절을 하나씩 짚고, 재생성 PNG 13장을 승인본과
   나란히 눈으로 본다(회색 기준선이 실제로 회색인지, 번호가 새 배선에만
   붙었는지). 결과를 판정.md 끝에 "## 10. 판정" 으로 적는다: 넷·자리·전환·
   파일명의 일치 여부, 갈린 자리와 그 자리에 규칙·검사가 있었는지, 원본 쪽 결함.

8. **기록 표에 행을 붙인다.** 이 문서 `## 기록` 표 마지막 행 뒤에 한 줄. 커밋은
   사용자 결정.

9. **보고한다.** 세 가지 — 일치한 것, 갈린 자리와 규칙·검사 유무, 원본·도구 쪽
   결함. 갈린 자리마다 SKILL.md 의 어느 절에 무엇을 더 쓰면 닫히는지 **제안**
   하고 사용자에게 묻는다. SKILL.md 수정은 이 런북 밖이다. 격리 트리를 지운다.

## 답안지 목록

격리 트리에서 지우는 것. 정본은 이 절이고 1단계의 `KEYS` 는 이것을 옮긴 것이다.

- `.claude/skills/verify-draft-lab-spec/`·`verify-write-result-report/` — 시험
  형식과 답안지 목록·합격 조건
- `.claude/skills/review-hand-diagram/` — H 규칙 표와 실험01 판정 사례
- `.claude/skills/export-hand-diagram/` — 손그림 파일명 규칙(결선도와 같은 틀)의 실험01 예시
- `.claude/skills/write-pre-report/`·`prep-lab-checklist/` — 실험01 배치·파일명 예시
- `docs/verify/`·`docs/plans/` — 이 런북·설계·계획. 합격 조건과 승인본 수치 표
- `docs/study/`·`docs/rule-friction/`·`docs/notion-feedback/`·`docs/corpus-audit/`·
  `docs/강의노트_이론_실험_매핑_정리.md` — 파생 서술
- `scripts/lab/hand_compare.py`·`hand_transcript.py`·`export_hand_diagrams.py`·
  `contact_sheet.py` — 실험01 회로 ID 와 배치를 안다
- `scripts/lab/breadboard_compare.py`·`isolate.py`·
  `regen_compare.py`·`specdiff.py`·`report_compare.py` — docstring 이 채점 기준
- `tests/` — 실험01 값을 픽스처로 단언한다
- `보고서/실험01/결선도/배치.py` — 실험01 결선 그 자체(엔진 `render_breadboard.py` 는 남는다)
- `보고서/실험01/결선도/*.png`·`결선도/손그림/` — 답 그 자체와 손그림 스캔
- `보고서/실험01/체크리스트/체크리스트.{html,pdf}` — 단계 그림이 박혀 있다
- `보고서/실험01/output/` 내용물 전부 — 예비보고서 md 가 파일명 13개를 싣는다.
  손그림검토 라운드에 전사 JSON 과 판정이 있다
- `보고서/실험01/실험사진/`·`실험중있었던일.md`·`*예비보고서*.pdf`·`*결과보고서*.pdf` — 실물
  보드 사진·실험실 기록·제출본(결과보고서 PDF 에는 보드 사진이 실린다)

## 누출 토큰

`E1_SLOTS`·`_e1_`·`build_e1`·`결선도_3입력`·`결선도_복합`·`1단계_`·
`좌 7행`·`좌 18행`·`우 10행`·`c7→c9`·`a25`·`c9→c14`·`b19`. 2단계가 이 목록을 쓴다.

## 승인본 기준 수치 (사람이 읽는 참고값 — 판정은 6단계가 같은 함수로 다시 잰다)

| 보드 | steps | kept | removed | swaps | partial |
|---|---|---|---|---|---|
| 실험01_1-1_결선도_3입력_AND.png | 16 | 0 | 0 | 0 | False |
| 실험01_1-2_결선도_3입력_OR_1단계_칩교체.png | 1 | 16 | 0 | 1 | False |
| 실험01_2-1_결선도_3입력_NAND_1단계_앞단AND.png | 3 | 13 | 3 | 1 | True |
| 실험01_2-1_결선도_3입력_NAND_2단계_뒷단NAND.png | 4 | 16 | 0 | 1 | False |
| 실험01_2-2_결선도_3입력_NOR_1단계_앞단OR.png | 1 | 15 | 4 | 1 | True |
| 실험01_2-2_결선도_3입력_NOR_2단계_뒷단NOR.png | 4 | 16 | 0 | 1 | False |
| 실험01_3_결선도_복합논리회로_1단계_인버터.png | 8 | 11 | 8 | 1 | True |
| 실험01_3_결선도_복합논리회로_2단계_AND.png | 4 | 18 | 1 | 1 | True |
| 실험01_3_결선도_복합논리회로_3단계_OR.png | 11 | 22 | 0 | 1 | False |

설계 문서 `docs/plans/2026-09-12-결선도-단계화-슬롯고정-설계.md` §슬롯과 단계 표의
"새 배선/걷는 배선" 은 배선 가닥 수이고, 위 `steps` 는 칩 교체·삽입 줄과 부품 줄을
포함한 **번호 받은 줄 수**라 값이 다르다. 둘을 섞지 않는다.

## 에이전트 프롬프트

```
작업 디렉토리: <작업 디렉토리>

이 저장소에 `breadboard-diagram` 스킬이 있다.
`.claude/skills/breadboard-diagram/SKILL.md` 를 읽고 **그 문서의 규칙 그대로** 다음 요청을 수행하라:

> `보고서/실험01/결선도/netlist.md` 가 기술한 실험1 회로 다섯 개(C1~C5)의 빌더와 보드 사슬을 `보고서/실험01/결선도/배치.py` 에 작성하고, `render_breadboard.py --experiment 1` 로 `보고서/실험01/결선도/` 에 렌더하라.

너에게 주어진 것은 그 스킬 문서와 이 저장소뿐이다. 다른 맥락은 없다. 한국어로 작업하고 보고한다.

금지:
- 위 작업 디렉토리 밖으로 나가지 마라. 밖의 파일을 읽지도 쓰지도 마라.
- `python -m unittest discover` 나 `pytest` 를 돌리지 마라. 렌더러의 `verify()` 가 유일한 검사다.
- `git commit` / `git add` / `git log` / `git show` / `git diff` / `git stash` / `git checkout` / 브랜치 조작을 하지 마라. 이 작업과 무관하다. 트리 상태 확인이 필요하면 `git status --porcelain` 만 쓴다.
- 스킬 문서와 이 저장소 밖의 지식으로 핀 번호·홀 자리를 채우지 마라. 근거가 저장소 안 파일이면 그 경로를 적는다.
- `netlist.md` 를 고치지 마라. 그것이 입력이다.

환경: 파이썬은 작업 디렉토리에서 `python ...` 로 돌린다 — 스킬 문서의 `python3` 는 `python` 으로 읽는다. Pillow 는 설치돼 있다. `pdftotext`·`pdftoppm`·`pdfinfo` 는 `C:\Users\Hyunjun\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin` 에 있다. 판독 노트·시험 렌더 같은 스크래치는 작업 디렉토리 안 `tmp/` 아래에 둔다.

끝나면 아래 형식으로 보고하라. 같은 내용을 작업 디렉토리 안 `tmp/격리보고.md` 에도 저장하라.

1. 만든·고친 파일 경로 전부. 렌더한 PNG 파일명 전부.
2. 빌더·보드 사슬·완성본 목록의 이름과 각 빌더가 맡은 회로·단계.
3. `verify()` 결과: 빌더마다 **첫 렌더**에서 AssertionError 가 났는지 원문 그대로, 그것을 어떻게 고쳤는지, 몇 번 되돌렸는지. **첫 렌더에서 한 번에 통과했으면 그렇다고 명시하라.** 홀 자리를 옮긴 곳마다 옮기기 전 자리와 이유.
4. 단계 그림마다 회색(기준선)이 된 배선 수와 "앞 단계에서 걷는다" 표에 오른 항목.
5. 막혔거나 규칙이 안 맞아 스스로 판단으로 메운 자리 (없으면 "없음"). SKILL.md 의 어느 절이었는지.
6. SKILL.md 에서 모호하거나 서로 어긋난다고 느낀 문장 (없으면 "없음"). 원문 인용과 함께.
7. 이번 작업에서 읽은 저장소 파일 전부. 다른 실험 폴더의 파일을 참고했으면 무엇을 어디에 썼는지.
```

## 기록

| 날짜 | HEAD | 시나리오 | 결과 |
|---|---|---|---|
| 2026-09-12 | `40a29a5` | V1 — 실험01 결선도 13장 재생성 | 넷 13/13 치명·기능 0(표기는 H9 브리지 행만)·칩 자리 일치·removed 9/9 일치·파일명 13/13 일치·첫 렌더 13장 통과. 규칙 없음 1자리(끝점 없는 레일의 브리지 — 승인본이 29·33행에 여분 브리지를 둔다, 원본 결함)·문서 모호 3문장(§4a partial 범위, §4a 임시 점퍼 함수, §5 `_input_jumper(col='a')`). 판정: tmp/verify-artifacts/실험01-breadboard-격리-2026-09-12/판정.md |
