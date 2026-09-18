---
name: verify-write-result-report
description: write-result-report 와 review-lab-report 를 답안 없는 격리 트리에서 다시 실행시키고 승인된 결과보고서와 자동 대조해 판정 초안과 런북 기록 행을 낸다. 사용자가 "결보 격리 재생성 돌려", "실험1 결과보고서로 스킬 검증", "write-result-report 고쳤으니 검증해" 등을 요청하거나 /verify-write-result-report 를 호출할 때 쓴다. 승인된 결과보고서가 노션에 올라간 실험(통제군)만 잰다. 아무것도 고치지 않는다 — 갈린 자리는 규칙 제안 표로 사용자에게 묻는 데서 끝난다.
---

# verify-write-result-report

`verify-draft-lab-spec` 의 결과보고서 판이다. ④ `write-result-report` 문서는
컴파일도 실행도 되지 않으므로 결함은 규칙만 주고 격리 에이전트에게 실행시켜야
나온다. 이 스킬은 그 실행을 `/` 한 번으로 만들고, 재생성물을 승인본과 여섯
갈래(구조·표 셀·참고문헌·문체·사실 토큰·산문)로 대조한다. 대조 도구는
`scripts/lab/report_compare.py` 이고 갈래의 뜻은 그 docstring 이 정본이다.

## 인자

`<실험N>`

- 번호 토큰이 없으면 한 줄로 되묻고 중단한다.
- 통제군 조건: `<실험NN>/output/<실험NN>_결과보고서.md` 가 있고, 같은 폴더
  `notion.json` 에 `결과보고서` 레코드가 있으며, 그 최신 판본의
  `_notion_baseline_v<N>.md` 와 원본이 `report_compare` 로 산문 밖 0건이어야
  한다(0단계가 잰다). 하나라도 아니면 "통제군이 없다" 로 거절한다.
  2026-09-12 기준 자격이 있는 것은 실험01(v5) 뿐이다.

## 절대 규칙

1. **답안지를 전부 뺀 트리에서만 돈다.** 목록은 §답안지 목록이고 첫 줄이 이
   스킬 자신이다. 목록을 줄이지 않는다.
2. **못 빼는 누출은 적는다.** ④ `write-result-report/SKILL.md` 자체가 실험01
   사례(핀 1 고착-1, 2-1 의 011, 칩 불량 경위)를 규칙 예시로 싣는다. 시험
   대상이라 못 뺀다. 2단계의 누출 결과를 판정.md 7절에 "구조적 누출" 로
   적고, **그 자리의 일치는 합격 근거로 세지 않는다.**
3. **프롬프트에 사유와 합격 조건을 쓰지 않는다.** 이력 명령(`git log`·`show`·
   `diff`)도 금지한다. §에이전트 프롬프트를 글자 그대로 쓰고 자리표시자만
   채운다.
4. **규칙이 막았는지 검사가 잡았는지를 가른다.** 에이전트 보고 3항(⑤ 첫 실행의
   error/warn/info 원문)이 근거다. 검사가 잡은 항목은 ④ 문서의 빈 자리로
   취급한다. 첫 실행 error 0 인데 승인본과 갈렸으면 **규칙도 검사도 없는
   자리**다 — 통제군 대조만이 그것을 본다.
5. **자동 합격은 없다.** 도구는 갈래별로 세기만 한다. 사실 토큰 차이의 세
   갈래(`규칙 없음`·`검사 없음`·`환경`)와 산문은 사람이 원본과 나란히 읽고
   표시한다. **산문 일치율은 기준 밖이다** — 문장이 같기를 요구하면 승인본
   문장을 규칙에 베끼는 과적합으로 간다.
6. **아무것도 고치지 않는다.** ④ 도 ⑤ 도 승인본도 규칙도. 갈린 자리는 ⑦
   `sync-report-to-notion` 의 분류 표 형식(무엇 / 분류 / 반영 대상 파일·절)으로
   **제안**하고 멈춘다. 커밋하지 않는다.
7. **세션 메모리 주입을 명시한다.** 하네스가 컨트롤러의 세션 메모리를
   서브에이전트에 주입한다. 막을 수 없으니 판정.md 첫 줄에 적는다 —
   `judgment_markdown` 이 자동으로 넣는다.
8. **회차 상한은 세션당 3회다.** 재실행 사유는 판정에서 `규칙 없음`·`검사
   없음` 으로 표시된 차이가 남아 있고 사용자가 그 규칙 제안을 승인해 ④·⑤ 를
   고쳐 커밋한 경우뿐이다. 산문만 다른 것은 재실행 사유가 아니다.

## 실행 절차

0. **실험 번호를 폴더로 옮기고 통제군을 확인한다.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config, notion
   from scripts.lab.report_compare import approved_report_path, compare_reports, counted
   d = Path(config.experiment_dir(<실험번호>))
   ap = approved_report_path(<실험번호>)
   recs = [r for r in notion.load_records(d / 'output') if r['kind'] == '결과보고서']
   print('O' if ap.exists() else 'X', ap)
   print('O' if recs else 'X', '노션 결과보고서 레코드', len(recs), '건')
   base = d / 'output' / f\"{ap.stem}_notion_baseline_v{recs[-1]['version']}.md\" if recs else None
   print('O' if base and base.exists() else 'X', base)
   if ap.exists() and base and base.exists():
       diff = compare_reports(ap.read_text(encoding='utf-8'), base.read_text(encoding='utf-8'))
       print('원본↔baseline 산문 밖 차이', counted(diff), '건')
   "
   ```

   `X` 가 하나라도 있거나 차이가 0 이 아니면 거절한다 — 원본이 승인본이 아니다.

   ```bash
   git status --porcelain .claude/skills scripts/lab 보고서/<실험NN>
   ```

   출력이 비어 있지 않으면 멈추고 사용자에게 묻는다 — 격리 트리는
   `git archive HEAD` 로 **HEAD** 를 푸므로 커밋 안 한 수정은 재지지 않는다.

1. **격리 트리를 만든다.** 시스템 임시 폴더 아래에 둔다. 답안지 목록은
   §답안지 목록을 **그대로** 옮긴다. `output/` 은 통째로 비운 뒤 예비보고서 md
   만 되살린다 — "예비보고서와의 비교" 절의 입력이다.

   ```bash
   python3 -c "
   import tempfile
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.isolate import build_isolated_tree
   exp = config.experiment_dir(<실험번호>)
   name = config.experiment_folder_name(<실험번호>)
   KEYS = [
       '.claude/skills/verify-write-result-report', '.claude/skills/verify-draft-lab-spec',
       'docs/verify', 'docs/plans', 'docs/notion-feedback', 'docs/rule-friction',
       'docs/corpus-audit', 'docs/study', 'docs/강의노트_이론_실험_매핑_정리.md',
       'scripts/lab/report_compare.py', 'scripts/lab/specdiff.py',
       'scripts/lab/regen_compare.py', 'scripts/lab/isolate.py', 'tests',
       f'{exp}/*결과보고서*.pdf',
   ]
   dest = Path(tempfile.gettempdir()) / f'iso-{name}'
   build_isolated_tree(Path('.'), dest, <실험번호>, KEYS,
                       clear_subdirs=('output',),
                       keep=[f'{exp}/output/{name}_예비보고서.md'])
   print(dest)
   "
   ```

   `체크리스트/`·`결선도/`·`실험사진/`(시트 포함)·`실험중있었던일.md` 는 남는다
   — ④ 의 입력이다. 이 트리는 `HEAD` 의 사본이다.

2. **누출을 훑는다.** 승인본 문장(25자 이상)과 사례 토큰으로 트리를 훑는다.

   ```bash
   python3 -c "
   import tempfile
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.isolate import leak_scan, leak_sentences
   from scripts.lab.report_compare import approved_report_path
   dest = Path(tempfile.gettempdir()) / f'iso-{config.experiment_folder_name(<실험번호>)}'
   for h in leak_sentences(approved_report_path(<실험번호>), dest): print('문장', h)
   for h in leak_scan(dest, ['고착-1', 'A=B=1', '칩 불량']): print('토큰', h)
   "
   ```

   **정상으로 보는 것**: ④ `write-result-report/SKILL.md`(규칙 예시 사례, §절대 규칙 2)·
   `보고서/<실험NN>/체크리스트/기록.md`(종료 메모의 사실), 그리고 설계상 공유되는
   입력 — 참고문헌 인용 줄(③ `write-pre-report/SKILL.md`·`.claude/데이터시트_출처.md`·
   예비보고서 md; ④ §절대 규칙 10 이 기본 목록을 예비보고서와 같게 한다), 예비보고서의
   헤딩 조각(`<empty-block/> ## 실험 N-N)`), `scripts/lab/validate.py` 의 규칙 예시
   문자열. **재격리 사유**는 그 밖의 파일에서 승인본 **본문 문장**이 나오는 것뿐이다 —
   그러면 §답안지 목록에 더하고 1단계부터 다시 한다. 결과는 어느 쪽이든 6단계의
   판정.md 7절에 넣는다.

3. **대조 도구를 자기대조로 점검한다.** 승인본을 승인본과 대조해 0건, 승인본을
   최신 baseline 과 대조해 산문 밖 0건이어야 다음 단계의 숫자를 믿을 수 있다.

   ```bash
   python3 -c "
   from scripts.lab.report_compare import approved_report_path, compare_reports, counted
   t = approved_report_path(<실험번호>).read_text(encoding='utf-8')
   print('self', counted(compare_reports(t, t)))
   "
   ```

   `self 0` 이어야 한다. baseline 대조는 0단계가 이미 찍었다.

4. **에이전트를 띄운다.** Agent 도구, 기본 모델, 백그라운드. §에이전트 프롬프트를
   글자 그대로 쓰고 `<작업 디렉토리>`·`<실험번호>`·`<파이썬 명령>`·`<poppler 경로>`
   만 채운다. 파이썬 명령과 poppler 경로는 이 PC 에서 `where python`·`where
   pdftoppm` 으로 확인한 값을 쓴다(macOS 면 `which`). 기다리는 동안 **격리
   트리와 승인본은 건드리지 않는다.** 형제 스킬의 실측은 305k 토큰·21분이다.

5. **산출물을 보존한다.** 끝나면 격리 트리의 `보고서/<실험NN>/output/` 과
   `tmp/격리보고.md` 를 저장소 `tmp/verify-artifacts/<실험NN>-결보격리-<YYYY-MM-DD>/`
   로 복사한다(`tmp/` 는 gitignore). 격리 트리를 지우기 전에 한다.

6. **판정 초안을 낸다.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.report_compare import judgment_markdown
   name = config.experiment_folder_name(<실험번호>)
   art = Path('tmp/verify-artifacts/<실험NN>-결보격리-<YYYY-MM-DD>')
   report = (art / '격리보고.md').read_text(encoding='utf-8') if (art / '격리보고.md').exists() else ''
   leaks = <2단계 출력 줄 목록>
   out = art / '판정.md'
   out.write_text(judgment_markdown(<실험번호>, art / 'output' / f'{name}_결과보고서.md',
                                    leak_hits=leaks, agent_report=report), encoding='utf-8')
   print(out.read_text(encoding='utf-8'))
   "
   ```

7. **사람이 본다.** 판정.md 5절의 사실 토큰 차이마다 세 칸 중 하나에 표시하고,
   6절의 산문은 절마다 원본과 나란히 읽는다. 에이전트 보고 3항으로 §절대 규칙
   4 의 갈림을 가른다. 결과를 판정.md 끝에 "## 8. 판정" 으로 적는다: 구조·셀·
   참고문헌·문체의 일치 여부, `규칙 없음`·`검사 없음` 으로 표시한 자리와 그
   근거, 원본 쪽 결함.

   **알려진 차이:** 실험01 승인본은 2026-09-18 결선도 규칙(④ §사진 배치) 이전
   판이라 실험 사진 소절마다 결선도 그림이 없다. 재생성본에 결선도가 한 장씩 더
   있는 것은 `규칙 없음`·`검사 없음` 이 아니라 원본 쪽 사정으로 적는다.

8. **런북 기록 표에 행을 붙인다.** `docs/verify/write-result-report.md` 의
   `## 기록` 표 마지막 행 뒤에 한 줄:

   `| <YYYY-MM-DD> | \`<git rev-parse --short HEAD>\` | V1 — 실험NN 무인자 재생성 + ⑤ | <한 줄 요약>. 판정: tmp/verify-artifacts/<실험NN>-결보격리-<날짜>/판정.md |`

9. **보고한다.** 네 가지를 낸다 — 일치한 갈래, `규칙 없음`·`검사 없음` 자리와
   그 근거, `환경` 으로 뺀 자리, 원본 쪽 결함. `규칙 없음`·`검사 없음` 자리마다
   ⑦ 분류 표 형식으로 **제안**한다(무엇 / 분류 / 반영 대상 파일·절). 규칙 신설과
   승인본 수정은 이 스킬 밖이다. 격리 트리를 지운다. 사용자가 제안을 승인해
   ④·⑤ 를 고치고 커밋하면 같은 명령을 다시 돈다(§절대 규칙 8).

## 답안지 목록

격리 트리에서 지우는 것. 정본은 이 절이고 코드는 받기만 한다. 첫 줄이 이 스킬
자신이다.

- `.claude/skills/verify-write-result-report/` — 이 문서. 합격 조건과 프롬프트가
  있다
- `.claude/skills/verify-draft-lab-spec/` — 형제 스킬. 같은 시험 형식과 답안지
  목록을 싣는다
- `docs/verify/` — 런북. 시나리오와 회차 기록
- `docs/plans/` — 결보 v4 계획에 논증 원문 전부가 있다
- `docs/notion-feedback/` — 되읽기 분류 로그. 규칙이 왜 생겼는지를 문장으로 적는다
- `docs/rule-friction/`·`docs/study/`·`docs/corpus-audit/`·
  `docs/강의노트_이론_실험_매핑_정리.md` — 실험 내용의 파생 서술과 과거 제출본 감사
- `scripts/lab/report_compare.py`·`scripts/lab/specdiff.py`·
  `scripts/lab/regen_compare.py`·`scripts/lab/isolate.py` — docstring 이 대조
  기준을 적는다
- `tests/` — 승인본 결보 문장을 픽스처로 읽는 테스트가 있다
- `보고서/<실험NN>/output/` **내용물 전부** — 결과보고서 md·baseline·되읽기·
  리뷰 라운드·`notion.json`. 예비보고서 md 한 파일만 함수가 되살린다
- `보고서/<실험NN>/*결과보고서*.pdf` — 제출본 PDF. grep 은 PDF 를 못 보므로
  목록으로 막는다

남기는 것: `체크리스트/{명세,기록}.md`·`결선도/`·`실험사진/`(시트 포함)·
`실험중있었던일.md`·`강의노트/`·`.claude/데이터시트_출처.md`·
`.claude/과목정보.md`·`.claude/보고서양식.md`·`docs/schema/`·`scripts/lab/`
나머지·④ ⑤ `export-photo-sheet` 를 비롯한 다른 스킬·다른 실험 폴더. ④·⑤ 가
참조하거나 그 절차가 실물로 드는 것들이다.

## 에이전트 프롬프트

```
작업 디렉토리: <작업 디렉토리>

이 저장소에 `write-result-report` 스킬과 `review-lab-report` 스킬이 있다.
`.claude/skills/write-result-report/SKILL.md` 를 읽고 **그 문서의 절차 그대로** 다음 요청을 수행하라:

> 실험<실험번호> 결과보고서를 써라

md 를 낸 뒤 `.claude/skills/review-lab-report/SKILL.md` 를 읽고 **그 문서의 절차 그대로** `실험<실험번호> result round1` 로 검토하라. error 가 남으면 `write-result-report` 의 규칙대로 md 를 고치고 다음 라운드로 다시 검토한다. error 0 이 될 때까지 반복한다.

너에게 주어진 것은 두 스킬 문서와 이 저장소뿐이다. 다른 맥락은 없다. 한국어로 작업하고 보고한다.

금지:
- 위 작업 디렉토리 밖의 파일을 읽지도 쓰지도 마라. 예외는 `.claude/데이터시트_출처.md` 에 적힌 URL 의 데이터시트를 내려받는 것뿐이다 — 그 파일은 작업 디렉토리 안 `tmp/` 아래에 둔다.
- `python3 -m unittest discover` 나 `pytest` 를 돌리지 마라. 스킬 절차가 지정하는 표적 검증 명령만 쓴다.
- `git commit` / `git add` / `git log` / `git show` / `git diff` / `git stash` / `git checkout` / 브랜치 조작을 하지 마라. 이 작업과 무관하다. 트리 상태 확인이 필요하면 `git status --porcelain` 만 쓴다.
- 스킬 문서와 이 저장소 밖의 지식으로 관찰값·수치를 채우지 마라. 근거가 저장소 안 파일이면 그 경로를 적는다.
- 스킬 절차가 사용자에게 묻도록 한 자리에 이르면 묻지도 지어내지도 마라 — 그 절차가 정한 대로 그 자리를 비우고 아래 5항에 적는다. 단 `기록.md` 에 이미 "사용자 확인" 으로 적힌 사실은 확인된 것으로 본다.

환경: 파이썬은 작업 디렉토리에서 `<파이썬 명령> ...` 로 돌린다 — 스킬 문서의 `python3 -c` 는 `<파이썬 명령> -c` 로 읽는다. `pdftotext`·`pdftoppm`·`pdfinfo` 는 `<poppler 경로>` 에 있다. 데이터시트 URL 은 브라우저 User-Agent 헤더를 붙여 내려받는다(`curl -A "Mozilla/5.0" …` — 기본 UA 는 Access Denied 로 막힌다). 판독 노트·렌더 PNG·내려받은 데이터시트 같은 스크래치는 작업 디렉토리 안 `tmp/` 아래에 둔다.

끝나면 아래 형식으로 보고하라. 같은 내용을 작업 디렉토리 안 `tmp/격리보고.md` 에도 저장하라.

1. 만든 파일 경로 전부 (없으면 "없음"). 어느 강의노트 판본(경로·쪽수)을 열었는지.
2. 두 스킬 문서의 마지막 절차 단계가 요구하는 안내 전부.
3. 검증 단계마다(`write-result-report` 의 검증 단계와 `review-lab-report` 의 각 라운드): **첫 실행**에서 error / warn / info 가 각각 무엇이 나왔는지 원문 그대로, 그것을 어떻게 처리했는지, 몇 번 반복했는지. **첫 실행에서 error 0 으로 한 번에 통과했으면 그렇다고 명시하라.**
4. `review-lab-report` 의 "사람이 확인할 것" 항목 각각과 처리.
5. 막혔거나 규칙이 안 맞아 스스로 판단으로 메운 자리, 사용자에게 물어야 했으나 묻지 못한 자리 (없으면 "없음"). 어느 규칙·단계였는지 번호로.
6. 두 스킬 문서에서 모호하거나 서로 어긋난다고 느낀 문장 (없으면 "없음"). 원문 인용과 함께.
7. 이번 작업에서 읽은 저장소 파일 전부. 다른 실험 폴더의 파일을 참고했으면 무엇을 어디에 썼는지.
8. 실제로 연 데이터시트 (경로·URL). 열지 못한 것과 그 이유.
```

## 비-목표

- **`write-result-report` 를 고치지 않는다. `review-lab-report` 도.** 갈린
  자리는 제안하고 멈춘다.
- **승인본을 고치지 않는다. 커밋하지 않는다.**
- **노션에 올리지 않는다.** 재생성물은 `tmp/` 에만 남는다.
- **`write-pre-report` 를 재지 않는다.** 예비보고서 검증은 별개다.
- **기록.md 비어 있음·필기 PDF 전사 같은 다른 시나리오를 돌리지 않는다.**
  무인자 재생성(V1)만이다.
