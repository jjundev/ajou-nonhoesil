---
name: init-lab-experiment
description: 논리회로실험 실험 폴더를 표준 하위 폴더 골격으로 초기화한다. 사용자가 "실험5 폴더 만들어줘", "5주차 초기화", "다음 실험 폴더 세팅" 등을 요청하거나 /init-lab-experiment 를 호출할 때 사용한다. 주차로 말해도 실험 번호로 옮겨 만든다. 이미 있는 폴더는 건너뛰고 보고만 한다.
---

# init-lab-experiment

`실험NN/` 아래에 하네스가 전제하는 하위 폴더 골격(`config.EXPERIMENT_SUBDIRS`)을 만든다.
다른 스킬은 전부 이 구조가 이미 있다고 가정하고, 없으면 거절한 뒤 이 스킬을 안내한다.

**골격에는 스킬이 쓰기 전에 있어야 하는 폴더와, 스킬보다 사람이 먼저 파일을
넣는 폴더만 든다.** 목록은 이 문서에 베끼지 않는다 — 폴더를 더하거나 뺄 일이
오면 `config.py` 의 튜플 한 줄만 고친다. 빠진 폴더의 사유는 §비-목표에 있다.

## 실험 일정

**표를 여기 베끼지 않는다.** 예전에는 주차↔실험 표를 이 문서에 실었는데,
운영계획이 바뀌자 아홉 스킬에 퍼진 사본 열한 곳이 한꺼번에 거짓이 됐다.
일정이 필요하면 `config.EXPERIMENT_DATES` 를 돌려 그 출력을 보여준다.

```bash
python3 -c "
from scripts.lab import config
for e, d in sorted(config.EXPERIMENT_DATES.items()):
    print(f'실험{e}', d)
"
```

## 실행 절차

1. **번호 추출.** 사용자는 `실험N` 또는 "다음 실험 …" 으로 부른다. 실험
   번호로 왔으면 3단계로 그대로 넘긴다.

   **"다음 실험" 처럼 날짜로 물었으면** 아래로 찾는다. 한 날에 실험이 둘일
   수 있어 리스트가 온다(9/18 은 실험2·3 이다).

   ```bash
   python3 -c "
   from scripts.lab import config
   print(config.next_experiments())
   "
   ```

   - `None` 이면 두 가지 중 하나다 — 학기가 진짜 끝났거나, FPGA 프로젝트
     기간(11/27~12/11) 안이다. `next_experiments` 는 실험 번호(1~10)만
     추적해 FPGA 를 가리키는 일이 없으므로(즉 이 갈래가 직접 FPGA 를
     가리켜 오는 경우는 없다), `None` 하나가 두 상황을 함께 나타낸다 —
     `PROJECT_DATES` 로 가른다.

     ```bash
     python3 -c "
     from datetime import date
     from scripts.lab import config
     print(min(config.PROJECT_DATES) <= date.today() <= max(config.PROJECT_DATES))
     "
     ```

     참이면 FPGA 프로젝트 기간이다 — 실험 번호가 없어 `config.PROJECT_DIR`
     로 가고, 3주치가 한 프로젝트이므로 주차마다 폴더를 만들지 않는다.
     그대로 4단계로 간다. 거짓이면 학기가 끝난 것이다 — 한 줄로 알리고
     중단한다.
   - 리스트에 실험 번호가 둘 이상이면(9/18 처럼) 각각에 대해 3~4단계를
     반복한다.

   **주차로 불렸으면**("5주차 초기화" 처럼) 아래로 옮긴다. 한 날에 실험이
   둘일 수 있어 리스트가 온다.

   ```bash
   python3 -c "
   from scripts.lab import config
   print(config.experiments_in_week(<N>))
   "
   ```

   - 빈 리스트인데 `config.is_project_week(<N>)` 가 참이면 FPGA 프로젝트
     주차(13~15주차)다. `config.PROJECT_DIR` 로 가고, 3주치가 한
     프로젝트이므로 주차마다 폴더를 만들지 않는다. 그대로 4단계로 간다.
   - 빈 리스트이고 거짓이면 그 주엔 실험이 없다(1주차 오리엔테이션·4주차
     추석·8주차 중간고사). 그대로 알리고 중단한다.
   - 리스트에 번호가 둘 이상이면(한 날에 실험이 둘인 주차가 있다) 각각에
     대해 3~4단계를 반복한다 — 되묻지 않는다. 이 스킬은 폴더를 **만들기만** 하고 나머지
     스킬처럼 어느 쪽을 쓸지 고르는 게 아니라서, 둘 다 만들어 둬도 해가
     없다.
   - 하나면 그 번호로 3단계로 넘긴다.

2. **프로젝트 루트 확인.** `.claude/` 를 가진 가장 가까운 상위 디렉토리를 찾는다.
   못 찾으면 거절한다 — 이 스킬은 논회실 프로젝트 안에서만 동작한다.

3. **폴더 이름을 코드로 만든다.** 손으로 `실험5` 라고 적지 않는다 — 0 을 안 채우면
   `실험10` 이 `실험2` 앞에 정렬된다.

   ```bash
   python3 -c "
   from scripts.lab import config
   print(config.experiment_dir(<N>))
   "
   ```

4. **폴더 생성.** 루트에서 돌린다. 하위 폴더 목록은 `config.EXPERIMENT_SUBDIRS`
   에서 읽는다. 이미 있는 폴더는 건드리지 않고, 폴더마다 만들었는지
   건너뛰었는지 한 줄씩 찍는다 — 7단계 보고가 이 출력을 그대로 쓴다.

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   base = Path(config.experiment_dir(<N>))   # FPGA 면 Path(config.PROJECT_DIR)
   for sub in config.EXPERIMENT_SUBDIRS:
       d = base / sub
       print('건너뜀' if d.is_dir() else '만듦', d)
       d.mkdir(parents=True, exist_ok=True)
   "
   ```

5. **일정 안내.** `config.experiment_date(<실험번호>)` 로 그 실험 날짜를 알린다.
   `config.experiments_on(<그 날짜>)` 가 둘 이상이면 **같은 날 다른 실험도
   있다고 함께 알린다** — 9/18 은 실험2·3 을 한 날에 하고 8시 20분까지 둘 다
   마쳐야 한다.

6. **교안 복사는 제안하지 않는다. `강의노트/` 폴더도 만들지 않는다.** 예전에는
   `from_the_past/정리/강의노트/실험N.pdf` 를 `<폴더이름>/강의노트/` 로
   복사할지 물었다. **이제 묻지 않는다** — 그 사본은 과거 학기(2020-2)
   판본인데 후보 순서상 아카이브보다 앞서므로, 복사해 두면 2026-2 배포본이
   있는 주차에서 낡은 판본이 배포본을 가릴 뻔한 자리를 만든다. 실험1 은 두
   판본의 항목 구성 자체가 다르다(13 쪽·3 항목 vs 15 쪽·5 항목). 빈
   `강의노트/` 는 그 사본을 넣으라는 자리처럼 보이므로 폴더째 세우지 않는다.

   대신 `config.manual_candidates(<실험번호>)` 를 돌려 **이 주차가 어느
   판본을 열게 되는지** 한 줄로 알린다. 첫 실재 후보가 아카이브면 "2026-2
   배포본이 아직 없어 2020-2 판을 연다"고 그대로 밝힌다.

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   for p in config.manual_candidates(<실험번호>):
       print('O' if Path(p).exists() else 'X', p)
   "
   ```

7. **결과 보고.** 4단계가 찍은 `만듦`·`건너뜀` 줄을 한 줄로 정리한다.

## 비-목표

- 명세.md 를 생성하지 않는다. 폴더가 선 뒤 `draft-lab-spec` 이 교안에서
  저작한다.
- 기존 파일을 덮어쓰지 않는다.
- 주차 이름 폴더(예: `5주차`)를 만들지 않는다. 규약은 실험 기준이고,
  `validate.check_folder_convention` 이 어긋남을 잡는다.
- 선택 폴더 `강의노트/`·`퀴즈/`·`STT/` 를 만들지 않는다. 읽는 쪽이 전부
  "있으면" 읽는 자리라 빈 폴더와 없는 폴더가 똑같이 동작한다 —
  `manual_candidates` 는 폴더가 아니라 파일 실재를 보고,
  `write-result-report` 8단계의 퀴즈 해설은 양식이 `generate: false` 라 열지도
  않으며, `logic-lab-review-pack` 은 녹취가 있을 때만 읽는다. 셋 다 어느 실험
  폴더에서도 파일이 커밋된 적이 없고, 실험01 은 셋 없이 결과보고서까지
  나갔다. 쓸 날 손으로 만든다.
- 하위 산출물 폴더 `결선도/손그림/`·`실험사진/시트/`·`output/손그림검토/`
  를 미리 만들지 않는다. 그걸 쓰는 스크립트(`export_hand_diagrams`·
  `contact_sheet`·`hand_grid`)가 제 손으로 만든다 — 여기서도 만들면 같은
  경로 규칙이 두 곳에 산다.
