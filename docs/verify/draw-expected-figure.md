# draw-expected-figure 격리 검증

스킬 문서는 실행되지 않는다. 결함은 답안 없는 트리에서 에이전트에게 돌려야
나온다. 통제군은 셋이다 — 실험01·03(capture 표 없음)과 실험02(capture 표 둘,
승인본 있음).

## 답안지 목록

- `docs/plans/` — 이 스킬의 설계·구현계획이 있다
- `docs/verify/` — 이 문서
- `docs/notion-feedback/`, `docs/rule-friction/`
- `tests/` — 누출 방지 테스트가 통제군 값을 담는다
- `.claude/skills/verify-draft-lab-spec/`, `.claude/skills/verify-write-result-report/`
- `scripts/lab/isolate.py`, `scripts/lab/regen_compare.py`, `scripts/lab/specdiff.py`,
  `scripts/lab/report_compare.py`
- 대상 주차의 `체크리스트/`·`output/` 내용물 — `명세.md` 와 `output/<실험NN>_예비보고서.md`
  만 되살리고, 명세의 `- figure:` 줄은 지운다. `output/notion.json` 도 빠지므로
  에이전트는 "안 올린 보고서" 경로를 탄다

## 트리 만들기

```bash
.venv/bin/python - <<'PY'
import re
from pathlib import Path
from scripts.lab import config
from scripts.lab.isolate import build_isolated_tree
N = <실험번호>
KEYS = [
    'docs/plans', 'docs/verify', 'docs/notion-feedback', 'docs/rule-friction', 'tests',
    '.claude/skills/verify-draft-lab-spec', '.claude/skills/verify-write-result-report',
    'scripts/lab/isolate.py', 'scripts/lab/regen_compare.py', 'scripts/lab/specdiff.py',
    'scripts/lab/report_compare.py',
]
exp = config.experiment_dir(N)
name = Path(exp).name
def strip_figure(dest):
    p = dest / exp / '체크리스트/명세.md'
    p.write_text(re.sub(r'(?m)^- figure:.*\n', '', p.read_text(encoding='utf-8')), encoding='utf-8')
dest = build_isolated_tree(Path('.'), Path('<스크래치>/iso-fig-' + name), N, KEYS,
                           clear_subdirs=('체크리스트', 'output'),
                           keep=[f'{exp}/체크리스트/명세.md', f'{exp}/output/{name}_예비보고서.md'],
                           edit=strip_figure)
print(dest)
PY
```

누출을 훑는다 — 아래가 전부 0 이어야 한다:

```bash
grep -rn "예상결과_\|figure:" '<트리>/보고서/<실험NN>' | wc -l
grep -rln "draw-expected-figure" '<트리>/docs' | wc -l
```

## 에이전트 프롬프트

글자 그대로 쓴다. `<트리>`·`<실험번호>` 만 바꾼다.

```
작업 디렉터리는 <트리> 다. 이 디렉터리 밖의 파일을 읽거나 쓰지 않는다.
git log·git show·git diff 는 쓰지 않는다. 필요하면 git status --porcelain 만 쓴다.

draw-expected-figure 스킬(.claude/skills/draw-expected-figure/SKILL.md)로 실험<실험번호>
을 처리해라. 아티팩트 게시 단계는 건너뛰고, 건너뛰었다고 보고에 적어라.
명령은 <트리> 에서 .venv 없이 python3 로 돌리되 pytest 는 필요 없다.

끝나면 아래를 보고해라.
1. 1단계 출력 원문
2. 만들거나 고친 파일 목록 (git status --porcelain 원문)
3. 숫자 검사 첫 실행 출력 원문과, 몇 번째 실행에서 통과했는지
4. 요소 ↔ 근거 표
5. 10단계 출력 원문
6. 스킬 문서에서 따르기 어려웠거나 모호했던 곳
```

## 대조

| 통제군 | 기대 | 본다 |
|---|---|---|
| 실험01 | 1단계에서 종료 | 보고 1 이 `capture 표가 없어` 를 담는가, 보고 2 가 비었는가 |
| 실험03 | 1단계에서 종료 | 같음 |
| 실험02 | 그림 두 장 | PNG 이름이 `실험02_1-1_예상결과_인버터_입출력특성.png`·`실험02_1-2_예상결과_슈미트트리거_입출력특성.png` 인가 / 그림마다 시간축+X-Y 짝인가 / 그림 속 소수값 집합이 승인본(`1.35 2.1 2.4 3.15` · `0.9 1.4 1.7 2.0 2.38 3.15 0.98`)의 부분집합인가 / 측정 화면 흉내·이미지 안 각주·"그림 N." 이 없는가 / 명세 `figure` 두 줄 / md 두 소절 끝에 그림 줄과 캡션이 들어가고 10단계 error·warn 0 인가 / 보고 3 이 첫 실행 통과인가(아니면 규칙이 아니라 검사가 잡은 것 — 스킬 문서의 빈 자리) |

자동 합격은 없다. 표의 칸마다 일치·갈림·해당 없음을 적고, 갈린 자리는 근거를
모아 사용자에게 묻는다. 기록에 "세션 메모리 주입 아래서 돌았다" 를 적는다.

## 기록

| 날짜 | 통제군 | 커밋 | 결과 | 갈린 자리 |
|---|---|---|---|---|
