---
name: verify-draft-lab-spec
description: draft-lab-spec 스킬을 답안 없는 격리 트리에서 다시 실행시키고 승인본과 자동 대조해 판정 초안과 런북 기록 행을 낸다. 사용자가 "격리 재생성 돌려", "실험1 로 스킬 검증", "draft-lab-spec 고쳤으니 검증해" 등을 요청하거나 /verify-draft-lab-spec 을 호출할 때 쓴다. 승인된 명세·결선도가 있는 실험(통제군)만 잰다. 아무것도 고치지 않는다 — 갈린 자리는 근거를 모아 사용자에게 묻는 데서 끝난다.
---

# verify-draft-lab-spec

## 산출물 이름 (실험07부터)

파일 경로는 `scripts.lab.config.artifact_path(실험폴더, 종류, 확장자)`로 정한다.
실험07 이상은 `실험NN_실험_제목_산출물종류.확장자`이고, 실험01~06은 기존 이름 그대로다.
실험 제목은 명세의 `title`에서 읽는다. 문서 안의 제목·내부 그림 이름은 바꾸지 않는다.
이 문서의 `기록.md`·`체크리스트.pdf` 같은 짧은 이름은 종류를 뜻하는 별칭이며,
실제 생성·존재 확인·전사·검증·결과 링크에는 반드시 공통 함수가 반환한 경로를 쓴다.
종류는 `체크리스트`, `기록`, `예비보고서`, `결과보고서`, `예비보고서표지`,
`결과보고서표지`, `손그림모사`, `부품그리기`, `따라그리기`, `예상결과`다.
저장 위치·예외·이력 보존 규칙은 `docs/schema/lab-artifact-naming.md`를 따른다.

`draft-lab-spec` 문서는 컴파일도 실행도 되지 않는다. 결함은 문서를 읽어서는
안 나오고, 규칙만 주고 격리 에이전트에게 실행시켜야 나온다 — 이 저장소가
2026-08-30 이후 매 회차 확인한 사실이다. 이 스킬은 그 실행을 `/` 한 번으로
만든다. 시나리오 V1(무인자 재생성)만 맡는다. V2~V7 은
`docs/verify/draft-lab-spec.md` 가 그대로 맡는다.

## 인자

`<실험N>`

- 번호 토큰이 없으면 한 줄로 되묻고 중단한다.
- 그 실험의 `체크리스트/명세.md` 와 `결선도/netlist.md` 가 둘 다 있어야
  한다 — 그것이 통제군이다. 하나라도 없으면 "통제군이 없다" 로 거절한다.
  2026-09-14 기준 자격이 있는 것은 실험01·02·03 이다(셋 다 2026-2 배포본
  강의노트로 저작했다). 실험04 이후는 아직 저작 전이다.

## 절대 규칙

1. **답안지를 전부 뺀 트리에서만 돈다.** 목록은 §답안지 목록이고 첫 줄이
   이 스킬 자신이다. 목록을 줄이지 않는다 — 2026-08-31 회차에서 에이전트
   둘이 `docs/verify/` 를 읽고 자기 합격 조건을 따랐다. 그 합격은 아무것도
   증명하지 않는다.
2. **못 빼는 누출은 적는다.** `draft-lab-spec/SKILL.md` 와
   `docs/schema/lab-spec-v2.md` 는 실험01 을 예시로 든다(항목 제목·T5
   파생식·`74HC02` 출력핀). 계약서라 못 뺀다. 누출 grep 결과를 판정.md
   에 "구조적 누출" 로 적고, **그 자리의 일치는 합격 근거로 세지 않는다.**
3. **프롬프트에 사유와 합격 조건을 쓰지 않는다.** "읽지 마라 — 합격 조건이
   거기 있다" 는 첫 줄부터 채점되는 시험임을 알린다. 이력 명령
   (`git log`·`show`·`diff`)도 금지한다. §에이전트 프롬프트를 글자 그대로
   쓴다.
4. **규칙이 막았는지 검사가 잡았는지를 가른다.** 에이전트 보고 3항(첫 실행의
   error/warn/info 원문)이 그 근거다. 검사가 잡은 항목은 전부 스킬 문서의
   빈 자리로 취급한다. 첫 실행 error 0 인데 승인본과 갈렸으면 **규칙도
   검사도 없는 자리**다 — 통제군 대조만이 그것을 본다.
5. **자동 합격은 없다.** 도구는 차이를 분류하고 세기만 한다. 제목 갈림의
   옳고 그름(런북 V1 절의 title 기준), 머리말 표, 산문은 사람이 원본과
   나란히 읽는다.
6. **아무것도 고치지 않는다.** `draft-lab-spec` 도, 승인본도, 규칙도. 갈린
   자리는 근거를 모아 사용자에게 묻고 멈춘다. 커밋하지 않는다.
7. **세션 메모리 주입을 명시한다.** 하네스가 컨트롤러의 세션 메모리를
   서브에이전트에 주입한다(런북 2026-09-01 누출 (2)). 막을 수 없으니
   판정.md 첫 줄에 적는다 — `judgment_markdown` 이 자동으로 넣는다.

## 실행 절차

0. **실험 번호를 폴더로 옮기고 통제군을 확인한다.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   d = Path(config.experiment_dir(<실험번호>))
   for f in ('체크리스트/명세.md', '결선도/netlist.md'):
       print('O' if (d / f).exists() else 'X', d / f)
   "
   ```

   `X` 가 하나라도 있으면 거절한다.

   ```bash
   git status --porcelain .claude/skills/draft-lab-spec docs/schema scripts/lab
   ```

   출력이 비어 있지 않으면 멈추고 사용자에게 묻는다 — 격리 트리는
   `git archive HEAD` 로 **HEAD** 를 푸므로 커밋 안 한 수정은 재지지
   않고, 8단계가 적는 HEAD 와도 어긋난다.

1. **격리 트리를 만든다.** 스크래치패드 아래에 둔다. 답안지 목록은
   §답안지 목록을 **그대로** 옮긴다.

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.isolate import build_isolated_tree
   KEYS = [
       '.claude/skills/verify-draft-lab-spec',
       'docs/verify', 'docs/plans', '복습노트', 'docs/superpowers', 'docs/study', 'docs/rule-friction',
       'docs/notion-feedback', 'docs/강의노트_이론_실험_매핑_정리.md',
       'docs/corpus-audit',
       'scripts/lab/specdiff.py', 'scripts/lab/regen_compare.py',
       'scripts/lab/isolate.py', 'scripts/lab/contact_sheet.py',
       'scripts/lab/export_hand_diagrams.py', 'scripts/lab/report_compare.py',
       '.claude/skills/verify-write-result-report', 'tests',
       '.claude/skills/breadboard-diagram',
       '.claude/skills/explain-lab-preview', '.claude/skills/logic-lab-review-pack', '.claude/skills/init-lab-experiment',
       '.claude/skills/make-lab-report-cover', '.claude/skills/prep-lab-checklist',
       '.claude/skills/review-lab-report', '.claude/skills/sync-report-to-notion',
       '.claude/skills/write-pre-report', '.claude/skills/write-result-report',
   ]
   dest = build_isolated_tree(Path('.'), Path('<스크래치>/iso-<실험NN>'), <실험번호>, KEYS)
   print(dest)
   "
   ```

   `보고서/<실험NN>/{체크리스트,결선도,output}/` 내용물은 함수가 비운다.
   폴더는 남는다 — `draft-lab-spec` 1단계가 폴더를 요구한다. 이 트리는
   `HEAD` 의 사본이다 (작업 트리가 아니다).

2. **누출을 훑는다.** 승인본 명세의 항목 id·제목·파생식으로 트리를 grep 한다.

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.isolate import leak_scan, leak_tokens
   toks = leak_tokens(Path(config.experiment_dir(<실험번호>)) / '체크리스트/명세.md')
   for h in leak_scan('<스크래치>/iso-<실험NN>', toks): print(h)
   "
   ```

   남는 자리가 `draft-lab-spec/SKILL.md`·`docs/schema/` 뿐이면 정상이다
   (§절대 규칙 2). 다른 파일이 나오면 §답안지 목록에 더하고 1단계부터
   다시 한다 — 목록이 낡은 것이다.

3. **대조 도구를 자기대조로 점검한다.** 승인본을 승인본과 대조해 0건이
   나와야 다음 단계의 숫자를 믿을 수 있다.

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.regen_compare import compare_netlist_pins
   from scripts.lab.specdiff import compare_specs
   d = Path(config.experiment_dir(<실험번호>))
   print('spec', len(compare_specs(d/'체크리스트/명세.md', d/'체크리스트/명세.md')))
   print('pins', len(compare_netlist_pins(d/'결선도/netlist.md', d/'결선도/netlist.md')))
   "
   ```

   둘 다 `0` 이어야 한다.

4. **에이전트를 띄운다.** Agent 도구, 기본 모델, 백그라운드. §에이전트
   프롬프트를 글자 그대로 쓰고 `<작업 디렉토리>`·`<실험번호>` 만 채운다.
   2026-09-08 실측은 305k 토큰·21분이다. 기다리는 동안 다른 일을 해도 되지만
   **격리 트리와 승인본은 건드리지 않는다.**

5. **산출물을 보존한다.** 끝나면 스크래치의 `보고서/<실험NN>/` 과
   `tmp/격리보고.md`·`tmp/판독노트*.md` 를 저장소 `tmp/verify-artifacts/
   <실험NN>-격리-<YYYY-MM-DD>/` 로 복사한다(`tmp/` 는 gitignore). 격리
   트리를 지우기 전에 한다 — 이 산출물이 근거물이다.

6. **판정 초안을 낸다.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.regen_compare import judgment_markdown
   out = Path('tmp/verify-artifacts/<실험NN>-격리-<YYYY-MM-DD>/판정.md')
   out.write_text(judgment_markdown(<실험번호>, '<스크래치>/iso-<실험NN>/' + config.experiment_dir(<실험번호>),
                                    corpus_dirs=[Path(config.experiment_dir(<실험번호>)) / 'output']), encoding='utf-8')
   print(out.read_text(encoding='utf-8'))
   "
   ```

   2단계의 누출 grep 결과를 판정.md 의 "구조적 누출" 절로 덧붙인다.

7. **사람이 본다.** 판정.md 의 5절(사람이 볼 것) 항목을 하나씩 짚는다 —
   제목 차이는 가리키는 대상이 바뀌었는지(런북 V1 절), 머리말 표와 산문은
   원본과 나란히, 에이전트 보고 3항으로 §절대 규칙 4 의 갈림. 결과를
   판정.md 끝에 "## 6. 판정" 으로 적는다: 셀·핀·IC 의 일치 여부, 갈린
   자리와 그 자리에 규칙·검사가 있었는지, 원본 쪽 결함.

8. **런북 기록 표에 행을 붙인다.** `docs/verify/draft-lab-spec.md` 의
   `## 기록` 표 마지막 행 뒤에 한 줄:

   `| <YYYY-MM-DD> | \`<git rev-parse --short HEAD>\` | V1 — 실험NN 무인자 재생성 | <한 줄 요약>. 판정: tmp/verify-artifacts/<실험NN>-격리-<날짜>/판정.md |`

   상세 절은 사람이 판정.md 를 다듬어 옮긴다. 이 스킬은 행만 붙인다.

9. **보고한다.** 세 가지를 낸다 — 일치한 것, 갈린 자리와 §절대 규칙 4 의
   판정, 원본 쪽 결함. 갈린 자리마다 근거(교안·과거 제출본·코드)를 모아
   사용자에게 **묻는다**. 규칙 신설과 승인본 수정은 이 스킬 밖이다.
   격리 트리를 지운다.

## 답안지 목록

격리 트리에서 지우는 것. 정본은 이 절이고 코드는 받기만 한다. 첫 줄이
이 스킬 자신이다.

- `.claude/skills/verify-draft-lab-spec/` — 이 문서. 합격 조건과 프롬프트가
  있다
- `docs/verify/` — 런북. 시나리오와 회차 기록
- `docs/plans/` — 합격 조건이 표와 문장으로 들어 있다
- `복습노트/`·`docs/superpowers/`·`docs/study/`·`docs/rule-friction/`·`docs/notion-feedback/`·
  `docs/강의노트_이론_실험_매핑_정리.md` — 실험 내용의 파생 서술
- `docs/corpus-audit/` — 과거 제출본 감사. 어느 표가 맞는지를 문장으로 적는다
- `scripts/lab/specdiff.py`·`scripts/lab/regen_compare.py`·
  `scripts/lab/isolate.py` — docstring 이 채점 기준을 적는다
- `scripts/lab/contact_sheet.py`·`scripts/lab/export_hand_diagrams.py` —
  docstring·주석에 실험01 항목 제목과 id 가 예시로 있다 (2026-09-12 회차의
  누출 grep 에서 걸려 추가)
- `scripts/lab/report_compare.py`·`.claude/skills/verify-write-result-report/` —
  결과보고서 검증 도구와 형제 스킬. 같은 시험 형식과 답안지 목록을 싣는다
- `tests/` — 실험01 값을 픽스처로 읽는 테스트가 열 개 넘는다
- `.claude/skills/breadboard-diagram/` — 실험01 배선이 코드로 있다
- `draft-lab-spec` 을 뺀 스킬 아홉 — `write-pre-report` 가 실험01 제목표를
  싣는 등 값이 샌다
- `보고서/<실험NN>/{체크리스트,결선도,output}/` **내용물** — 폴더는 둔다
- `보고서/<실험NN>/` 의 **그 밖의 내용물 전부** — 예비보고서 PDF(승인본 명세가
  그대로 들어 있다), `실험사진/`(파일명 `1-1 000.jpg`·시트 이름 `3입력_AND` 가
  항목 구성과 입력 폭을 알린다), 실험 메모. grep 은 PDF·그림을 못 보므로 목록으로
  막는다 (2026-09-12 회차에서 발견). 함수가 비우는 세 폴더 말고는 실험 폴더에
  아무것도 남기지 않는다

남기는 것: `docs/schema/`·`scripts/lab/` 나머지·
`.claude/데이터시트_출처.md`·`.claude/과목정보.md`·`강의노트/`·
`from_the_past/`·다른 실험 폴더. `draft-lab-spec` 이 참조하거나 그 절차가
실물로 드는 것들이다.

## 에이전트 프롬프트

```
작업 디렉토리: <작업 디렉토리>

이 저장소에 `draft-lab-spec` 스킬이 있다.
`.claude/skills/draft-lab-spec/SKILL.md` 를 읽고 **그 문서의 절차 그대로** 다음 요청을 수행하라:

> 실험<실험번호> 명세와 결선도를 만들어라

너에게 주어진 것은 그 스킬 문서와 이 저장소뿐이다. 다른 맥락은 없다. 한국어로 작업하고 보고한다.

금지:
- 위 작업 디렉토리 밖으로 나가지 마라. 밖의 파일을 읽지도 쓰지도 마라.
- `python3 -m unittest discover` 를 돌리지 마라. 스킬 절차가 지정하는 표적 검증 명령만 쓴다.
- `git commit` / `git add` / `git log` / `git show` / `git diff` / `git stash` / `git checkout` / 브랜치 조작을 하지 마라. 이 작업과 무관하다. 트리 상태 확인이 필요하면 `git status --porcelain` 만 쓴다.
- 스킬 문서와 이 저장소 밖의 지식으로 셀 값·핀 번호를 채우지 마라. 근거가 저장소 안 파일이면 그 경로를 적는다.

환경: `pytest` 없다. 파이썬은 작업 디렉토리에서 `python3 ...` 로 돌린다. `pdftotext`·`pdftoppm`·`pdfinfo` 는 `/opt/homebrew/bin/` 에 있다. 판독 노트·렌더 PNG 같은 스크래치는 작업 디렉토리 안 `tmp/` 아래에 둔다. 스킬 절차 중 다른 에이전트에게 검토를 맡기는 단계가 있으면 Agent 도구로 실제로 맡긴다 — 그 에이전트에게도 위 작업 디렉토리 밖 금지를 그대로 전한다.

끝나면 아래 형식으로 보고하라. 같은 내용을 작업 디렉토리 안 `tmp/격리보고.md` 에도 저장하라.

1. 만든 파일 경로 전부 (없으면 "없음"). 어느 교안 판본(경로·쪽수)을 열었는지.
2. 스킬 문서의 마지막 절차 단계가 요구하는 목록 전부, 그리고 그 단계가 반드시 붙이라는 한 줄.
3. 검증 단계마다: **첫 실행**에서 error / warn / info 가 각각 무엇이 나왔는지 원문 그대로, 그것을 어떻게 처리했는지, 몇 번 반복했는지. **첫 실행에서 error 0 으로 한 번에 통과했으면 그렇다고 명시하라.**
4. 검토 단계를 실제로 돌렸는지, 돌렸으면 지적 각각과 처리.
5. 막혔거나 규칙이 안 맞아 스스로 판단으로 메운 자리 (없으면 "없음"). 어느 규칙·단계였는지 번호로.
6. 스킬 문서에서 모호하거나 서로 어긋난다고 느낀 문장 (없으면 "없음"). 원문 인용과 함께.
7. 이번 작업에서 읽은 저장소 파일 전부. 다른 실험 폴더의 파일을 참고했으면 무엇을 어디에 썼는지.
```

## 비-목표

- **`draft-lab-spec` 을 고치지 않는다.** 갈린 자리는 묻고 멈춘다.
- **승인본을 고치지 않는다. 커밋하지 않는다.**
- **V2~V7 을 돌리지 않는다.** 런북이 맡는다.
- **다른 스킬을 재지 않는다.** `write-pre-report` 의 격리 검증은 별개다.
