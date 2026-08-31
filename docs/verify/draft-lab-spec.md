# `draft-lab-spec` 실행 검증 런북

스킬 문서는 컴파일도 실행도 되지 않는다. `tests/test_skill_docs.py` 가
보는 것은 상호참조·번호·열 폭 같은 **구조**뿐이고, 그 문서가 좋은 명세를
만드는지는 검사하지 않는다. 이 저장소에서 스킬 결함을 실제로 찾아낸 것은
매번 **격리 재생성**이었다.

**스킬 문서(`SKILL.md`)를 고치면 이 런북을 다시 돌린다.** 어느 판본으로
무엇을 돌렸는지 아래 기록 표에 남긴다 — 지금 판본을 아무도 안 돌려 본
상태가 한 번 있었고, 그것을 알아채는 데 시간이 걸렸다.

## 공통 — 격리 worktree

재생성 시나리오는 저장소를 건드리지 않기 위해 worktree 안에서 돈다.

```bash
git worktree add --detach <경로> HEAD
# 필요하면 대상 산출물을 지운다
git worktree remove --force <경로>
```

**worktree 안에서 `unittest discover` 를 돌리지 않는다.**
`test_lab_spec_parser.py`·`test_lab_md.py`·`test_lab_record.py`·
`test_lab_render.py` 가 실험06·10 명세를 경로로 참조하므로, 그것을 지운
worktree 에서는 스킬과 무관한 실패가 난다.

## 공통 — fresh 에이전트 프롬프트

**이 세션의 맥락을 넘기지 않는다.** 넘기면 통제군이 아니다. 특히 합격
조건(무엇이 나와야 하는지)을 알려주면 시험이 성립하지 않는다.

```
작업 디렉토리: <worktree 경로>

이 저장소에 `draft-lab-spec` 스킬이 있다.
`.claude/skills/draft-lab-spec/SKILL.md` 를 읽고 **그 문서의 절차 그대로**
<인자> 를 수행하라.

너에게 주어진 것은 그 스킬 문서와 이 저장소뿐이다. 다른 맥락은 없다.

금지:
- <worktree 경로> 밖으로 나가지 마라.
- `python3 -m unittest discover` 를 돌리지 마라. 이 작업 트리는 일부
  픽스처가 없어 무관한 실패가 난다. 스킬 절차가 지정하는 표적 검증
  명령만 쓴다.
- `git commit` / `git add` / 브랜치 조작을 하지 마라.

환경: `pytest` 없다. 파이썬은 `zsh -c 'PYTHONPATH=. python3 ...'` 로
돌린다. `pdftotext`·`pdftoppm` 은 `/opt/homebrew/bin/` 에 있다.

끝나면 보고하라:
1. 만든 파일 경로 (없으면 "없음")
2. 스킬 문서의 마지막 절차 단계가 요구하는 세 목록
3. 막혔거나 규칙이 안 맞아 스스로 판단으로 메운 자리 (없으면 "없음")
4. 스킬 문서에서 모호하거나 서로 어긋난다고 느낀 문장 (없으면 "없음")
```

## 시나리오

### V1 — 재생성 (무인자)

지금 판본이 지뢰를 밟는지 본다. 실험06 을 쓰는 이유는 판정이 **이진**이기
때문이다 — 교안 p9·p11 의 `C` 열은 텍스트 추출로 리터럴 `1` 이 나오고
vision 으로는 라이징 엣지다. 그리고 11쪽으로 가장 싸다.

```bash
git worktree add --detach /tmp/v1 HEAD
rm /tmp/v1/실험06/체크리스트/명세.md /tmp/v1/실험06/결선도/netlist.md
```

인자: `6주차 명세와 결선도를 만들어라`

합격 조건:

```bash
zsh -c 'PYTHONPATH=. python3 -c "
from scripts.lab.specdiff import compare_specs, uncovered_tables
d = compare_specs(\"실험06/체크리스트/명세.md\",
                  \"/tmp/v1/실험06/체크리스트/명세.md\")
print(f\"차이 {len(d)}건\")
for x in d: print(\"  \", x)
u = uncovered_tables(\"/tmp/v1/실험06/체크리스트/명세.md\")
print(f\"대조 밖 표 {len(u)}건\")
for x in u: print(\"  \", x)
"'
```

- `차이 0건` 이면 통과.
- 차이가 있으면 **재생성이 틀렸다고 단정하지 않는다.** 각 줄에 대해
  교안으로 어느 쪽이 맞는지 가른다. 원본도 사람이 손으로 만든 것이다.
- 그리고 결선도가 `check_netlist` 의 `error` 0 이어야 한다. `check_netlist`
  는 두 번째 인자로 **파싱된 spec 객체**를 요구하고(`parse_spec` 을 먼저
  부른다), `error`·`warn`·`info` 가 섞인 `Finding` 목록을 돌려준다 —
  **목록이 비었는지가 아니라 `error` 만 걸러 센다.** 건강한 결선도도
  `warn`·`info` 를 낸다:

```bash
zsh -c 'PYTHONPATH=. python3 -c "
from scripts.lab.spec_parser import parse_spec
from scripts.lab.validate import check_netlist
spec = parse_spec(\"/tmp/v1/실험06/체크리스트/명세.md\")
findings = check_netlist(\"/tmp/v1/실험06/결선도/netlist.md\", spec)
errors = [f for f in findings if f.level == \"error\"]
print(f\"error {len(errors)}건\")
for f in errors: print(\"  \", f)
"'
```

- `uncovered_tables` 가 표를 짚으면(실험06 에는 capture 표가 없어 지금은
  빈 리스트다) `compare_specs` 가 그 표를 판정하지 못했다는 뜻이다 —
  **자동 합격도 자동 불합격도 아니다.** 그 표의 `expected` 산문을 원본과
  재생성물 양쪽에서 사람이 직접 읽고 판단한다.

### V2 — `명세만`

```bash
git worktree add --detach /tmp/v2 HEAD
rm /tmp/v2/실험06/체크리스트/명세.md /tmp/v2/실험06/결선도/netlist.md
```

인자: `6주차 명세만 만들어라`

합격 조건: `/tmp/v2/실험06/체크리스트/명세.md` 가 생기고
`/tmp/v2/실험06/결선도/netlist.md` 는 **없다.**

**V2 가 끝나면, V3 의 에이전트를 띄우기 전에** 이 시점의 명세를 사본으로
남겨 둔다 — V3 의 판정이 바로 이 사본과 견준다:

```bash
cp /tmp/v2/실험06/체크리스트/명세.md /tmp/v2-명세-사본.md
```

### V3 — `결선도만`

**V2 의 worktree 를 이어서 쓴다.** 명세는 있고 netlist 는 없는 상태다.
(사본은 위 V2 의 마지막 단계에서 이미 만들어 뒀다.)

인자: `6주차 결선도만 만들어라`

합격 조건: netlist 가 생기고, 명세는 V2 직후(위 사본)와 **바이트 단위로
같다.** 이것이 주 기준이다 — `diff`/`cmp` 로 실제로 잰다:

```bash
diff -q /tmp/v2-명세-사본.md /tmp/v2/실험06/체크리스트/명세.md && echo "바이트 동일"
```

**출력이 `바이트 동일`이 아니면 불합격이다.** 어디가 달라졌는지 읽는 데는
`compare_specs` 를 보조로 쓴다 — 단 이 함수는 **계약 필드만** 보고 산문·
프론트매터 순서·공백은 보지 않으므로(`specdiff.py` 자체가 그렇게 명시한다),
여기서 `0`이 나와도 위 바이트 검사가 실패했다면 **여전히 불합격이다**:

```bash
zsh -c 'PYTHONPATH=. python3 -c "
from scripts.lab.specdiff import compare_specs
print(len(compare_specs(\"/tmp/v2-명세-사본.md\",
                        \"/tmp/v2/실험06/체크리스트/명세.md\")))
"'
```

### V4 — 덮어쓰기 금지

**파일을 지우지 않는다.** 이것이 요점이다.

```bash
git worktree add --detach /tmp/v4 HEAD
```

인자: `6주차 명세와 결선도를 만들어라`

합격 조건:

```bash
git -C /tmp/v4 status --porcelain -- 실험06/
```

**출력이 비어야 한다.** 두 파일이 한 글자도 안 바뀌었다는 뜻이다.
범위를 `실험06/` 로 좁히는 이유는, 규칙 13 이 "스크래치패드에 내고 diff 를
보여준다" 이므로 에이전트가 사본을 어딘가에 만들 수 있기 때문이다 —
**금지되는 것은 산출물을 제자리에서 덮어쓰는 것**이지 사본을 만드는 것이
아니다. 저장소 다른 곳에 남은 것이 있으면 따로 보고 판단한다:

```bash
git -C /tmp/v4 status --porcelain
```

그리고 에이전트가 "이미 있어서 멈췄다" 를 보고해야 한다 — 조용히
아무것도 안 한 것과 규칙을 알고 멈춘 것은 다르다.

### V5 — 거절 (중간고사·FPGA)

worktree 를 각각 따로 만든다. 거절은 아무것도 만들지 않으므로 판정이
"트리가 그대로인가" 다 — 한 worktree 에 섞으면 어느 쪽이 썼는지 못 가른다.

인자: `8주차 명세를 만들어라` / `14주차 명세를 만들어라`

합격 조건: `git status --porcelain` 이 공란. 그리고 거절 사유가 각각
중간고사·FPGA 여야 한다. `config.folder_for_week(8)` 은 `ValueError`,
`(14)` 는 `프로젝트` 를 돌려주므로 **거절 경로가 서로 다르다.**

### V6 — 거절 (폴더 없음)

실험07 은 폴더가 없다(9주차).

인자: `9주차 명세를 만들어라`

합격 조건: `git status --porcelain` 공란 — **폴더도 만들지 않아야 한다.**
그리고 `init-lab-experiment` 를 안내해야 한다.

## 기록

| 날짜 | SKILL.md 판본 | 돌린 시나리오 | 결과 |
|---|---|---|---|
| (여기에 한 줄씩 남긴다) | | | |
