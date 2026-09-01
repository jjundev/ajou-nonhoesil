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
rm -rf <경로>/docs/verify <경로>/docs/plans \
       <경로>/scripts/lab/specdiff.py <경로>/tests/test_lab_specdiff.py          # 답안지를 시험장에서 뺀다
# 답안지를 지우면 `git status --porcelain` 이 그 삭제(D)로 가득 찬다.
# "아무것도 안 만들어야 정상" 인 시나리오(V4~V6)는 공란이 아니라
# **이 기준선과 같은지**로 판정한다.
git -C <경로> status --porcelain > "<경로>.baseline"
# 필요하면 대상 산출물을 지운다
# 판정을 마쳤으면 worktree 를 지우기 전에 재생성물을 보존한다 — 이
# 프로젝트는 "격리 재생성이 스킬 결함을 찾는 유일한 방법" 이라는 전제
# 위에 있으므로 그 산출물은 근거물이다. 저장소 안이지만 커밋되지는
# 않는 tmp/ 아래에 둔다(.gitignore 의 `tmp/`). 산출물이 실제로 생기는
# 시나리오(V1·V2·V3)에서 의미가 있다 — V4~V6 처럼 아무것도 안 만들어야
# 정상인 시나리오에서는 생략해도 된다. `<시나리오>` 는 v1·v2 처럼 이
# 절차를 쓰는 시나리오 이름이다.
mkdir -p "tmp/verify-artifacts/<시나리오>-$(date +%F)"
cp -r <경로>/실험NN "tmp/verify-artifacts/<시나리오>-$(date +%F)/" 2>/dev/null || true
git worktree remove --force <경로>
```

**`docs/verify/` 를 지우는 것이 선택이 아니다.** 이 파일이 worktree 안에
있으면 격리 에이전트가 저장소를 뒤지다 자기 합격 조건을 읽는다 — 2026-08-31
회차에서 실제로 둘이 그렇게 했다고 보고했다. 그 상태의 합격은 스킬이
아니라 이 문서를 따른 결과라 아무것도 증명하지 않는다.

**답안지가 이 파일 하나뿐이라고 가정하지 마라.**
`docs/plans/2026-08-31-검증기계-신뢰회복.md` 와
`docs/plans/2026-08-31-스킬-실행-검증.md` 에도 V1~V6 시나리오의 합격
조건이 표와 문장으로 그대로 들어 있다 — `docs/verify/` 만 지우고
`docs/plans/` 를 남기면 여전히 답안지를 넘긴 것이다. 스킬 절차
(`.claude/skills/draft-lab-spec/SKILL.md`)는 `docs/plans/` 를 참조하지
않으므로, 지워도 스킬 실행에는 지장이 없다.

**답안지는 이미 문서 밖에도 있다.** `scripts/lab/specdiff.py` 의 docstring 에는
`compare_specs` 가 어느 필드를 대조하고(`capture` 표·산문은 보지 않는다)
`"차이 0건 = 합격"` 이라는 채점 기준이 통째로 들어 있다. `tests/test_lab_specdiff.py`
도 마찬가지로 **이전 재생성이 무엇을 했는지**를 적는다 — 예를 들어
`"실측(실험06 재생성 2건): 교안 p5 이론표를 T2 로 끼워 넣으면"` 같은 대목이 있다.
스킬은 `specdiff` 를 한 번도 참조하지 않고, `scripts/lab/__init__.py` 는 비어
있으므로 지워도 스킬이 다른 모듈을 import 하는 데는 지장이 없다.
**판정 도구는 본 저장소에서 돈다** — worktree 안에 있을 이유가 없다.

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
- `docs/verify/` 를 읽지 마라. 이 시험의 합격 조건이 거기 있다.
- `docs/plans/` 를 읽지 마라. 이 시험의 합격 조건이 거기에도 있다.
- `scripts/lab/specdiff.py` 와 `tests/test_lab_specdiff.py` 를 읽지 마라. 이 파일들에 채점 기준과 이전 재생성이 한 일이 적혀 있다.

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
rm -rf /tmp/v1/docs/verify /tmp/v1/docs/plans \
       /tmp/v1/scripts/lab/specdiff.py /tmp/v1/tests/test_lab_specdiff.py
rm /tmp/v1/실험06/체크리스트/명세.md /tmp/v1/실험06/결선도/netlist.md
```

인자: `6주차 명세와 결선도를 만들어라`

합격 조건은 **`차이 0건` 이고, 아래 목록을 사람이 눈으로 대조했을 때만**
통과다. `compare_specs` 는 계약 필드만 보므로(`specdiff.py` 모듈
docstring 참고), 다음 셋은 값이 달라도 `차이 0건` 그대로 나온다 —
**대조 밖:**

- **표 제목.** `_TABLE_FIELDS` 에 `title` 이 없다. 2026-09-01 회차에서
  다섯 표 제목이 전부 달랐는데(원본 `특성표` / 재생성 `진리표`) 차이
  0건이었다(아래 기록 참고).
- **산문**(`expected` 필드·본문 서술).
- **머리말**(첫 `## T` 헤딩 앞) 표. `spec_parser.parse_spec` 이
  `heads[0].start()` 이전을 스캔하지 않아 `LabSpec.tables` 에 실리지
  않는다. 실험06 은 여기 **토큰 규약표** 가 있다 — `0->1` 이 라이징
  엣지라는 정의가 그 표에만 있어서, 뜻을 뒤집어도 `compare_specs` 는
  차이 0건을 낸다. **이제 `uncovered_tables` 가 이것을 짚는다** — 실측:

  ```bash
  zsh -c 'PYTHONPATH=. python3 -c "
  from scripts.lab.specdiff import uncovered_tables
  for n in (\"01\",\"06\",\"10\"): print(n, uncovered_tables(f\"실험{n}/체크리스트/명세.md\"))
  "'
  # 01 []
  # 06 ['머리말(첫 `## T` 헤딩 앞)에 마크다운 표가 1개 있다 — ...']
  # 10 ['표 T1: 셀이 없어 대조가 성립하지 않는다 — `expected` 산문을 사람이 읽어야 한다']
  ```

  **이 알림은 자동 합격도 자동 불합격도 아니다** — 짚힌 표(머리말 표는
  표 자체를, capture 표는 `expected` 산문을)를 원본과 재생성물 양쪽에서
  사람이 직접 읽고 판단한다.

`source_manual` 은 위 목록에 **없다 — 이제 대조된다.** 프론트매터 필드
목록에 `week`·`experiment` 와 나란히 들어가, 명세가 참조한 교안 파일이
바뀌면 차이로 뜬다.

V1 의 실제 판정 명령(`compare_specs` 와 `uncovered_tables` 를 재생성물에
함께 건다):

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

- `차이 0건` 이고, 위 대조 밖 세 항목을 사람이 눈으로 봐서 이상이
  없으면 명세 쪽은 합격이다.
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

**이 `error 0` 은 자기정합 검사다 — 원본 결선도와는 대조하지 않는다.**
`check_netlist(재생성 netlist, 재생성 spec)` 은 재생성 결선도가 재생성
명세와 아귀가 맞는지만 본다. 저장소에 netlist 대 netlist 비교 도구가
없다(`grep -rn "def compare" scripts/lab/` 로 확인하면 `specdiff.py`
의 `compare_specs` 하나뿐이고, 그것도 명세끼리만 비교한다). 재생성
결선도가 핀을 원본과 전부 다르게 배정해도, 자기 명세와만 맞으면 이
판정은 통과한다. §결선도 골격의 `# 공통 규칙` 이 적듯 이 과목의 대표
실패 원인이 플로팅 입력·핀 오배정이므로, **핀 배정 자체는 사람이 원본
`실험06/결선도/netlist.md` 와 재생성물을 나란히 놓고 대조해야 한다** —
이 스크립트는 그것을 대신하지 않는다.

### V2 — `명세만`

```bash
rm -f /tmp/v2-명세-사본.md                        # 지난 회차 잔재 제거
git worktree add --detach /tmp/v2 HEAD
rm -rf /tmp/v2/docs/verify /tmp/v2/docs/plans \
       /tmp/v2/scripts/lab/specdiff.py /tmp/v2/tests/test_lab_specdiff.py
rm /tmp/v2/실험06/체크리스트/명세.md /tmp/v2/실험06/결선도/netlist.md
```

인자: `6주차 명세만 만들어라`

합격 조건: `/tmp/v2/실험06/체크리스트/명세.md` 가 생기고
`/tmp/v2/실험06/결선도/netlist.md` 는 **없다.**

**V2 가 끝나면, V3 의 에이전트를 띄우기 전에** 이 시점의 명세를 사본으로
남겨 둔다 — V3 의 판정이 바로 이 사본과 견준다. mtime 도 함께 적어
둔다 — V3 에서 이번 회차 것인지 대조하는 유일한 실마리다(2026-08-31
누출은 `/tmp/v2-명세-사본.md` 에 지난 회차 사본이 그대로 남아 있었고
그 mtime 이 `Aug 31 15:44` 였다):

```bash
cp /tmp/v2/실험06/체크리스트/명세.md /tmp/v2-명세-사본.md
ls -la /tmp/v2-명세-사본.md    # mtime 을 적어 둔다
```

### V3 — `결선도만`

**V2 의 worktree 를 이어서 쓴다.** 명세는 있고 netlist 는 없는 상태다.
(사본은 위 V2 의 마지막 단계에서 이미 만들어 뒀다.)

인자: `6주차 결선도만 만들어라`

합격 조건: netlist 가 생기고, 명세는 V2 직후(위 사본)와 **바이트 단위로
같다.** 이것이 주 기준이다 — `diff`/`cmp` 로 실제로 잰다. 그 전에 사본이
**이번 회차 것인지** 먼저 확인한다 — mtime 이 방금 V2 에서 적어 둔
시각과 다르면(특히 오늘 날짜가 아니면) 지난 회차 잔재를 보고 있는
것이므로 여기서 멈추고 V2 부터 다시 돌린다:

```bash
ls -la /tmp/v2-명세-사본.md    # 위 V2 단계의 mtime 과 같은지 확인
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
rm -rf /tmp/v4/docs/verify /tmp/v4/docs/plans \
       /tmp/v4/scripts/lab/specdiff.py /tmp/v4/tests/test_lab_specdiff.py
git -C /tmp/v4 status --porcelain > /tmp/v4.baseline
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
아니다. 저장소 다른 곳에 남은 것이 있으면 따로 보고 판단한다. 이 범위
없는 보조 판정은 답안지 삭제(`D`)로 가득 차므로 기준선과 견준다:

```bash
diff <(git -C /tmp/v4 status --porcelain) /tmp/v4.baseline && echo "무변경"
```

그리고 에이전트가 "이미 있어서 멈췄다" 를 보고해야 한다 — 조용히
아무것도 안 한 것과 규칙을 알고 멈춘 것은 다르다.

### V5 — 거절 (중간고사·FPGA)

worktree 를 각각 따로 만든다. 거절은 아무것도 만들지 않으므로 판정이
"트리가 그대로인가" 다 — 한 worktree 에 섞으면 어느 쪽이 썼는지 못 가른다.

```bash
git worktree add --detach /tmp/v5a HEAD
rm -rf /tmp/v5a/docs/verify /tmp/v5a/docs/plans \
       /tmp/v5a/scripts/lab/specdiff.py /tmp/v5a/tests/test_lab_specdiff.py
git -C /tmp/v5a status --porcelain > /tmp/v5a.baseline
git worktree add --detach /tmp/v5b HEAD
rm -rf /tmp/v5b/docs/verify /tmp/v5b/docs/plans \
       /tmp/v5b/scripts/lab/specdiff.py /tmp/v5b/tests/test_lab_specdiff.py
git -C /tmp/v5b status --porcelain > /tmp/v5b.baseline
```

인자: `8주차 명세를 만들어라` / `14주차 명세를 만들어라`

합격 조건: 두 worktree 모두 `git status --porcelain` 이 기준선과
같아야 한다 — **반드시 `-C` 로 대상을 지정한다.** 인자 없이 저장소
루트에서 돌리면 worktree 가 아니라 본 저장소를 재므로, 본 저장소는
항상 깨끗해 합격이 위조된다:

```bash
diff <(git -C /tmp/v5a status --porcelain) /tmp/v5a.baseline && echo "v5a 무변경"
diff <(git -C /tmp/v5b status --porcelain) /tmp/v5b.baseline && echo "v5b 무변경"
```

그리고 거절 사유가 각각 중간고사·FPGA 여야 한다. `config.folder_for_week(8)`
은 `ValueError`, `(14)` 는 `프로젝트` 를 돌려주므로 **거절 경로가 서로
다르다.**

### V6 — 거절 (폴더 없음)

실험07 은 폴더가 없다(9주차).

```bash
git worktree add --detach /tmp/v6 HEAD
rm -rf /tmp/v6/docs/verify /tmp/v6/docs/plans \
       /tmp/v6/scripts/lab/specdiff.py /tmp/v6/tests/test_lab_specdiff.py
git -C /tmp/v6 status --porcelain > /tmp/v6.baseline
```

인자: `9주차 명세를 만들어라`

합격 조건은 둘이다.

```bash
diff <(git -C /tmp/v6 status --porcelain) /tmp/v6.baseline && echo "v6 무변경"
ls -d /tmp/v6/실험07 2>&1
```

`git status` 가 기준선과 같고 `ls` 가 `No such file or directory` 여야
한다. **`git status` 만으로는 부족하다** — git 은 빈 디렉토리를 추적하지 않으므로,
에이전트가 `실험07/체크리스트/` 를 만들고 멈춰도 `git status` 는 공란이다.
"폴더도 만들지 않아야 한다" 를 실제로 재는 것은 `ls` 쪽이다.

그리고 `init-lab-experiment` 를 안내해야 한다.

### V7 — 인자 토큰 없는 한쪽 발화

§인자의 **"이 토큰이 없어도 사용자 말이 둘 중 한쪽만 가리키면 그쪽으로
읽는다"** 를 잰다. 이 문장은 2026-09-01 최종 전체-브랜치 리뷰(I4)로 새로
쓴 것이다. 그 전에는 토큰이 없으면 무조건 "둘 다" 로 떨어져서 —

1. 1단계 규칙 13 검사에서 `명세.md` 가 이미 있다
2. "그 자리에 저작하지 않는다 … `diff` 를 보여준 뒤 멈춘다"
3. **사용자는 결선도를 못 받고 명세 diff 를 받는다**

는 함정이 있었다. 그 함정이 닫혔는지 본다. 스킬 프론트매터
`description` 이 **"결선도 만들어줘"** 를 트리거 예시로 싣고 있으므로,
이것은 가상의 발화가 아니라 스킬 자신이 광고하는 입구다.

```bash
git worktree add --detach /tmp/v7 HEAD
rm -rf /tmp/v7/docs/verify /tmp/v7/docs/plans \
       /tmp/v7/scripts/lab/specdiff.py /tmp/v7/tests/test_lab_specdiff.py
rm /tmp/v7/실험06/결선도/netlist.md
```

**명세는 지우지 않는다.** 명세가 있고 결선도가 없는 상태가 이 시나리오의
전제다 — V3 과 같은 전제이되 **인자에 토큰이 없다.**

인자: `6주차 결선도 만들어줘`

합격 조건은 둘이다.

```bash
git -C /tmp/v7 status --porcelain -- 실험06/체크리스트/
ls /tmp/v7/실험06/결선도/netlist.md 2>&1
```

**첫 줄이 공란**(명세를 한 글자도 안 건드렸다)이고 **`netlist.md` 가
존재**해야 한다.

- 명세 쪽에 출력이 있으면 **불합격** — `결선도만` 으로 안 읽고 명세까지
  건드렸다.
- `netlist.md` 가 없고 에이전트가 "명세가 이미 있어서 멈췄다" 를
  보고했으면 **I4 의 함정이 그대로다** — §인자의 새 문장이 안 먹었다.
- 에이전트가 무엇을 할지 되물었으면 그것도 **불합격**이다. §인자가
  되묻으라고 한 것은 *번호* 토큰이 없을 때이고, "결선도 만들어줘" 는
  한쪽만 가리키는 발화의 **본보기로 §인자에 이름까지 적혀 있다.**
- 그리고 결선도가 `check_netlist` 의 `error` 0 이어야 한다 — 명령은
  §V1 의 마지막 블록에서 경로만 `/tmp/v7` 로 바꿔 쓴다. **그 `error 0`
  은 자기정합 검사다**(§V1 의 같은 단락 참고).

## 기록

| 날짜 | SKILL.md 판본 | 돌린 시나리오 | 결과 |
|---|---|---|---|
| 2026-08-31 | `48f8495` | V1~V6 전부 | **5 합격 / 1 불합격** — `명세만`(V2) 이 결선도까지 만들었다. 아래 참조 |
| 2026-09-01 | `240b964` | V2·V3 재실행 | **2 합격** — `명세만` 이 결선도를 안 만들었다. 아래 참조 |

### 2026-08-31 회차 상세

| 시나리오 | 판정 | 근거 |
|---|---|---|
| V1 재생성 | 합격 | 원본과 공유하는 다섯 표가 셀 단위 일치(쪽 번호로 정렬). p9·p11 지뢰 둘 다 `0->1`, p7·p8·p10 의 진짜 `1` 은 `1` 유지. 결선도 error 0 |
| V2 `명세만` | **불합격** | 명세와 결선도를 **둘 다** 만들었다. 내용 자체는 정확했다(다섯 표 일치) |
| V3 `결선도만` | 합격 | 명세가 바이트 동일(md5), netlist 만 생성 |
| V4 덮어쓰기 금지 | 합격 | 교안을 열기 **전에** 1단계에서 걸렸다. 저장소 무변경, 스크래치패드로 산출 |
| V5a 8주차 | 합격 | `ValueError`(중간고사), 0단계 중단 |
| V5b 14주차 | 합격 | `folder_for_week` 가 `프로젝트` 반환(FPGA), 0단계 중단 |
| V6 폴더 없음 | 합격 | 1단계 중단, `init-lab-experiment` 안내, 폴더도 안 만듦 |

**이 회차가 드러낸 이 런북 자신의 결함:** 격리 worktree 안에 이 파일이
함께 들어가서, 에이전트 둘이 저장소를 뒤지다 자기 합격 조건을 읽었다.
worktree 를 만들 때 `docs/verify/` 를 지우거나 프롬프트에서 금지해야 한다.

**`compare_specs` 의 한계도 드러났다:** 재생성물이 표를 정당하게 하나 더
실으면 ID 가 밀려 내용 오류 0건인데 19건이 뜬다. 쪽(`source`) 기준으로
다시 맞춰 보기 전까지는 차이 목록을 내용 오류로 읽지 마라.

### 2026-09-01 회차 상세 — V2·V3 재실행

인자 처리를 고친 뒤(실행 절차 5·7·8단계에 가드) 그 둘만 다시 돌렸다.
**V1 은 다시 안 돌렸다 — 그런데 "무인자 경로라 이번 고침이 no-op"
이라는 근거는 틀렸다.** `git diff 48f8495..240b964 --
.claude/skills/draft-lab-spec/SKILL.md` 로 확인하면 무인자 경로도
걸리는 변경이 셋 있다:

- **§절대 규칙 13 본문이 다시 쓰였다**(`기존 산출물을` →
  `<실험NN>/ 안의 기존 산출물을`, "저작 자체는 한다" 추가) — **V4 가
  재는 것이 바로 이 규칙이다.**
- **0단계 `ValueError` 문구가 둘로 갈렸다**(중간고사 / 매핑 밖) —
  **V5a·V5b 가 재는 것이 바로 이 거절 사유다.**
- **1단계 머리가 새로 붙었다**("이번 실행이 쓸 대상을 확정한 뒤…") —
  무인자로 돌려도 이 문장을 읽는다.

즉 **V1·V4·V5·V6 의 08-31 결과는 `48f8495` 판본 결과이지, `240b964`
판본을 다시 잰 것이 아니다.** 결과가 실제로 바뀌었다고 단정하지는
않는다 — 아무도 다시 돌려 보지 않았다. **다음 회차는 V1·V4·V5·V6
넷을 현재 판본으로 재실행해야 한다** — 현재 판본은
`git log -1 --format=%h -- .claude/skills/draft-lab-spec/SKILL.md`
로 확인한다. 이 문서를 고치는 오늘(2026-09-01) §인자 절도 함께
바뀌었으므로(최종 리뷰 I4), 다음 재실행은 그 이후 판본을 기준으로
한다.

| 시나리오 | 판정 | 근거 |
|---|---|---|
| V2 `명세만` | **합격** | `체크리스트/명세.md` 만 생기고 `결선도/` 는 비었다. 지난 회차 불합격의 원인(7단계가 "error 0 까지 반복" 으로 결선도를 만들라고 떠밀던 것)이 닫혔다 |
| V3 `결선도만` | **합격** | 명세가 V2 직후 사본과 바이트 동일(md5 `96a640df…`), netlist 만 생성. `check_netlist` finding 0건 |

**판정 도구를 실제 재생성물에 걸었다:** `compare_specs` **차이 0건**.
지뢰도 셀 단위로 맞았다 — p9(T3)·p11(T5) 의 `C` 열이 `0->1`, p7·p8·p10 의
진짜 `1` 은 `1` 그대로. 이번 재생성은 지난 두 회차와 달리 **교안 p5
이론표를 끼워 넣지 않아** ID 밀림 자체가 없었다.

`uncovered_tables` 는 회차 당시 0건이었으나, **그 뒤 최종 리뷰(I1)가
머리말 표를 짚도록 고쳤다.** 보존해 둔 재생성물에 지금 판본을 다시 걸면
**1건** — 「머리말에 마크다운 표가 1개 있다」 다. 아래 "1." 이 말하는
바로 그 사각지대를 이제 도구가 소리 내어 알린다. 회차 당시의 `0건` 은
도구가 그때 그것을 볼 줄 몰랐다는 뜻이지 사각지대가 없었다는 뜻이 아니다.

#### 이 회차가 드러낸 것

**1. `차이 0건` 이 "같다" 는 뜻이 아니다.** 다섯 표의 **제목이 전부
다르다** — 원본은 `특성표`, 재생성은 `진리표`. `compare_specs` 의
`_TABLE_FIELDS` 에 `title` 이 없어서 한 줄도 안 나왔다. 둘 다 옳은
이름이라 이번엔 무해했지만, 재생성이 표를 **엉뚱한 이름으로** 달아도
같은 침묵이 난다. 합격 판정을 `차이 0건` 하나에 걸지 마라 — 제목과
산문은 사람이 따로 읽어야 한다.

**2. `git status` 가 답안지 목록을 흘린다.** V2 에이전트가
`git status --short` 를 한 번 돌렸고, `docs/verify/`·`docs/plans/`·
`specdiff.py`·`test_lab_specdiff.py` 가 **삭제 상태(D)** 로 뜨는 것을
보고 "이 실행이 격리 검증 설정" 임을 알아챘다고 스스로 보고했다(내용은
열지 않았다고 밝혔다). 파일을 지우는 것으로는 **이름까지는 못 지운다.**
다음 회차에 더 가리려면 worktree 를 `--detach` 대신 지운 상태로 커밋한
임시 커밋 위에 만들어야 한다. 이번엔 그 에이전트가 정직하게 신고했고
판독·저작을 바꾸지 않았다고 했으므로 판정을 유지한다.

**3. 교안 p10 의 74HC10 핀 라벨이 데이터시트와 안 맞는다.** V3 에이전트가
K 게이트를 `입력 3,4,5 → 출력 8` 로 읽었는데, 표준 74HC10 은
`3,4,5→6` 이거나 `9,10,11→8` 이다. 어느 쪽이 교안 오기인지 단정하지
않고 미확정(M2)으로 올렸다 — 실물 확인이 필요하다. 지난 회차의
"p11 `CLK` 핀 6 에 반전 버블" 과 같은 계열의 교안 내부 모순이다.

#### 에이전트가 지적한 스킬 문서의 모호함

- **3단계가 `결선도만` 에서도 대상인지 명시가 없다.** 4단계만 "건너뛴다"
  가 붙어 있어, V3 에이전트는 "핀아웃 근거가 거기서 나온다" 는 이유로
  건너뛰지 않기로 스스로 판단했다. 그 판단이 옳지만 문서가 확인해 주지
  않는다.
- **4단계 "머리말에 토큰 표를 둔다" 의 "머리말"이 어디인가.** 프론트매터
  자체인지 그 뒤 첫 산문 영역인지 안 적혀 있다(전자는 표를 넣을 수 없다).
- **결선도 골격에서 `핀아웃 출처` 부재는 "메울 구멍", `계측` 부재는 그냥
  "없다"** — 거의 같은 문장 형태인데 하나만 결함이라 판단이 한 번 필요했다.
  지난 회차에 V2·V4 가 독립적으로 같은 곳을 지적했다.
- **§절대 규칙 4(셀은 교안 원문 그대로)가 표·항목 *제목* 표기에는 기준이
  없다.** 위 "1." 의 제목 불일치와 같은 뿌리다.
