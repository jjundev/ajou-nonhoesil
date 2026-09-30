---
name: logic-lab-review-pack
description: 논리회로실험 1~10의 실험 설명, 예습·복습 자료, 기출 풀이, 학습팩을 요청할 때 사용한다. 보고서 작성과 측정 체크리스트는 해당 전용 스킬을 사용한다.
---

# 논리회로실험 학습팩

오래전에 논리회로를 배운 학생이 기초부터 회로를 이해하고 기출을 풀 수 있게 한다.
기존 보고서에 등장하는 용어를 안다고 가정하지 않는다. 완전판 설명+앞부분 요약과 고유 기출 전체가 기본이다.
설명·기출 풀이 HTML 두 개와 같은 내용의 MD 두 개를 만든다. 사용자에게 중간 메뉴를 반복해서 묻지 않는다.

REPO는 scripts/lab/config.py가 있는 저장소 루트. SKILL은 이 폴더. RUN은 REPO/tmp/review-pack/<실험NN>-<고유실행ID>.
셸 작업 디렉터리를 REPO로 두고 Python 모듈을 실행한다. 실제 사용 가능한 Python 실행 파일을 확인한다.
명령 예의 RUN/STAGE는 실제 경로로 치환한다. 기존 디렉터리 재사용 없이 새 stage를 쓴다.

## 1. 대상 결정

번호·번호 범위·주차를 해석해 scripts.lab.review_pack.sources.resolve_experiments를 사용한다.
아무 대상이 없거나 '다음 실험'이면 현재 날짜로 다음 실험을 선택한다. 같은 날짜에 둘이면 둘 다 만든다.
빈 목록이면 실험 없는 주차·학기 종료를 안내한다. FPGA는 이번 범위 밖이며 실험11로 바꾸지 않는다.
보고서 폴더가 없어도 진행한다. config.experiment_dir는 선택적 명세·기록의 위치를 찾을 때만 쓴다.

## 2. 자료 확인

### 완료된 문제은행을 저작에 연결

기출 원문 추출은 [문제은행 계약](references/question-bank.md)과
[새 추출 세션 절차](references/question-bank-extraction-session.md)를 따른다.
문제은행 JSON은 manifest.json과 다른 계약이다. 완료된 은행이 있으면 재추출하지 않고 새 RUN으로 가져온다.
실험 번호에 맞는 문제은행/실험NN/question-bank.json이 complete 또는 complete_with_holds인지 먼저 검사한다.

```powershell
python -m scripts.lab.review_pack.question_bank_cli check --root . --bank 문제은행/실험04/question-bank.json
python -m scripts.lab.review_pack import-bank --root . --bank 문제은행/실험04/question-bank.json --run RUN
```

import는 원문 증거·인덱스·모든 문항이 held인 manifest만 만든다. 독립 풀이와 설명은 이어서 저작한다.
RUN/evidence/question-bank.json과 authoring-index의 고정 필드는 수정하지 않는다.
기출·미확인·예상·부분 판독·후보 답안 연결을 유지하고, 예상문제 선별 이유는 index와 manifest에 남긴다.
은행이 없으면 아래 원자료 탐색 절차를 사용한다. 초안 은행(draft)을 완료 은행으로 가장하지 않는다.
문제은행 추출 요청에서는 여기의 학습팩 build/publish 절을 실행하지 않는다.
기존 임시 분석을 검증된 문제은행으로 사용하지 않는다.

[sources.md](references/sources.md)를 읽고 자료를 목록화한다.

```powershell
python -m scripts.lab.review_pack sources --root . --experiment 4
```

현재 교안 우선, 과거 판본은 명확히 표시. STT는 선택적이다.
회로·부울식·표·엣지를 PDF 이미지로 읽고 원문 페이지를 기록한다.
원문 자료, 보고서, 측정 기록, 결선도, 과거 프리뷰는 수정하지 않는다.
교안이 없으면 일반 이론임을 표시하고 실제 실험 부품·조건을 지어내지 않는다.

## 3. 문항 감사와 저작

[format.md](references/format.md), [authoring.md](references/authoring.md)를 읽는다.
RUN/manifest.json에 자료·판본·토픽·문항·출처·답안 상태를 기록한다.
자료 탐색 결과를 전부 사용했다고 주장하지 말고 실제로 참조한 자료만 최종 manifest에 남긴다.
은행에서 가져온 sources와 문항·모든 원문 위치는 유지한다. 위 규칙은 추가로 탐색한 자료의 선택에 적용한다.
기출·미확인·예상·새 연습을 구분한다. 원본_docx 포함 전체 후보를 감사하고 중복·보류의 이유를 남긴다.
문항을 재정렬해도 ID를 유지한다. 예상문제는 기출의 개념 공백만 보충한다.
수입 문항의 bank_question_id/id/kind/sources는 고정이며 새 practice 문항은 별도 ID로 만든다.
부분 판독 문항은 원래 은행에서 확인을 해결한 뒤 새 import를 한다. 문제의 조건을 추측해 채우지 않는다.
원문 자산의 present/unknown 답 노출 상태를 안전으로 바꾸거나 정답을 지워 원문 증거라고 표시하지 않는다.
문제용은 role=problem/answer_exposure=none 자산만 사용한다. 답 노출 증거는 details.original/solution에 둔다.

RUN/sections/<id>.html, RUN/problems/<id>.html, RUN/figures/를 작성한다.
설명은 완성 예제→일부 단계 연습→기출 풀이로 이어진다. 문제에는 필요한 개념으로 돌아가는 링크를 넣는다.
생명과학의 note-template.html/review-template.html과 동일한 화면을 사용한다. 템플릿 디자인을 재작성하지 않는다.
우측 요약은 div.sum, 도움말은 details.hint/solution을 사용한다. 자세한 마크업은 authoring.md.

## 4. 조립과 MD 생성

```powershell
python -m scripts.lab.review_pack build --root . --run RUN --stage STAGE
python -m scripts.lab.review_pack check --folder STAGE
```

build는 두 HTML, 두 MD, manifest, 출처와_문항목록.md, figures, assets를 만든다.
은행 수입 팩에는 evidence/, authoring-index.json, 원문과_저작안내.md도 복사한다.
build/publish는 원래 은행·원문·자산 해시를 대조한다. 변경 시 새 import 후 관련 내용을 재검토한다.
생명과학 원본 템플릿은 그대로 보존하고, 생성 결과에서만 CDN URL을 번들된 로컬 자원으로 바꾼다.
MD에는 힌트·풀이·정적 위젯 설명을 모두 남긴다. 오류가 나면 fragment를 수정하고 새 stage로 다시 build한다.

## 5. 검증

[verification.md](references/verification.md)를 따른다.
원문 대조·독립 계산·노트의 풀이 충분성을 확인한다. 정답지와 충돌하면 양쪽을 재검토하고 미확정이면 그대로 표시한다.
독립 리뷰어가 실제로 검토하지 않았으면 independent=pass를 쓰지 않는다.
브라우저에서 375px/1280px, 다크모드, 이전/다음, 목차, 우측 요약·힌트·풀이, 위젯과 인쇄를 확인한다.
RUN/검증결과.md에 확인한 대상·결과·미해결을 남기고 manifest.checks를 실제 결과로 갱신한다.
업데이트 후 새 stage로 build한다. 최종 stage와 검사 대상이 같아야 한다. 검토 후 내용 변경은 관련 검토를 다시 수행한다.
수정은 최대 2회. 이후 남은 결함은 정직하게 보고하고 검증되지 않은 초안으로 기존 팩을 교체하지 않는다.

## 6. 저장과 보고

```powershell
python -m scripts.lab.review_pack publish --root . --stage STAGE --experiment 4
```

저장은 복습노트/실험NN. 교체 전 원문 해시·검증 상태를 확인하고 기존 팩을 백업한다.
사용자 추가 파일이 생성 파일과 충돌하면 덮어쓰지 않는다. 백업은 삭제하지 않는다.
최종 경로에서 문항 링크·원문 PDF 링크를 다시 확인한다.
보고: 네 학습 파일 링크, 판본, 포함·중복·보류 수, 답안 충돌, 검토 종류, 미해결, 백업 경로.
파일 생성 완료를 학생의 이해 완료라고 표현하지 않는다.

## 후속 요청과 경계

특정 부분에 대한 질문은 기존 팩을 읽고 설명한다. 질문만으로 파일을 수정하지 않는다.
'고쳐줘/보충해줘'는 같은 팩을 갱신한다. PDF 요청은 HTML의 인쇄 기능을 안내한다.
보고서·체크리스트·노션 업로드·FPGA 프로젝트를 자동으로 시작하지 않는다.
