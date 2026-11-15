---
name: logic-lab-problem-explain
description: 논리회로실험의 기존 학습팩으로 문제의 단서·떠올릴 개념과 공식·첫 줄·풀이 이유·완성 답·검산을 펼친 문제설명 HTML과 MD를 만든다. 문제해설·입문 풀이 설명·핵심 개념 보충 또는 /logic-lab-problem-explain [실험번호|범위|팩경로]에 사용한다. 전체 학습팩에서도 문제설명 저작 단계에 이 스킬을 사용한다.
---

# 논리회로실험 문제설명

이론을 읽었지만 문제풀이 경험이 부족한 학생에게 단서에서 방법을 고르는 과정까지 설명해요. 기존 워크북 v2의 included 문항을 같은 ID·번호·순서로 사용해요. 새 문제·PDF·영상·보고서는 만들지 않아요. 설명은 에이전트가 저작하고 CLI는 조립·검증·발행해요.

REPO는 scripts/lab/config.py가 있는 저장소 루트예요. PowerShell 작업 디렉터리를 REPO로 두고 실제 Python 3.11 이상 실행 파일을 확인해요. 명령의 NN·N·STAGE는 실제 값으로 바꾸고 STAGE는 기존 폴더와 겹치지 않는 새 경로를 써요.

## 1. 기존 팩 선택

번호·범위는 각 번호를 scripts.lab.config.experiment_folder_name으로 검증한 뒤 REPO/복습노트/실험NN에 연결해요. 경로 인자는 resolve한 결과가 이 저장소의 복습노트 바로 아래 정규 이름 `실험[0-9]{2}`인 폴더일 때만 받아요. manifest의 experiment와 폴더 번호도 대조해요.

인자 없음은 그 정규식에 전체 일치하고 .pack/manifest.json의 review_presentation_version=2인 디렉터리 중, included 문항과 읽을 수 있는 문제지 payload·설명에 필요한 원문 증거를 가진 최대 번호를 선택해요. backup suffix·legacy·자료 부족 후보는 기본 대상으로 고르지 않아요. 번호는 config로 다시 검증해요. 날짜로 다음 실험을 고르지 않아요.

명시한 팩이 없거나 워크북 v2/필수 자료가 없으면 해당 팩의 워크북 준비가 필요하다고 안내하고 그 팩 작업을 보류해요. 자동으로 원문을 재추출하거나 학습팩 전체를 만들지 않아요. 범위에서는 준비된 팩을 각각 진행하고 보류 대상을 따로 보고해요.

전체 학습팩의 같은 실행에서 호출되었다면 부모 스킬이 선택한 RUN/manifest.json과 RUN/workbook을 사용해요. 기본 대상 선택을 다시 하지 않아요. 기존 팩용 explain-stage 대신 부모의 build/check/publish 흐름으로 돌아가요.

## 2. 원고 저작

[형식 계약](references/format.md)을 읽고 manifest와 문제지 payload의 included ID·번호·순서 및 원문 소문항을 대조해요. [저작 기준](references/authoring.md)을 읽고 모든 included 조각의 실제 설명 내용을 작성해요. 기존 팩은 docs/learning-pack-source/실험NN/problem-explanations/<id>.html에 저작하고, 전체팩은 RUN/problem-explanations/<id>.html에 저작해요. 제목뿐인 빈 recall이나 기존 답 복사로 완료하지 않아요.

실험06의 정본은 docs/learning-pack-source/실험06/explanations.py와 recall.py예요. 보충할 때 HTML만 고치지 말고 해당 Python 원고도 갱신해요. standalone import로 explanations.E를 읽어 problem-explanations/<id>.html 조각만 새 stage 입력용으로 출력하고 각 조각을 version=2로 검증하며 E와 바이트 일치를 확인해요. 설명 갱신 때문에 전체 build_run.py를 실행해 다른 문서를 다시 생성하지 않아요.

원문·문제은행·답안 상태·문항 분류는 보존해요. 기존 원고 보충은 understand/start/solve/verify/pitfall/retry와 경고를 전후 비교하고 핵심 개념 보충 외 변경의 이유를 검토해요. 실제 원문 대조와 계산 증거는 저작 폴더의 검증결과.md에 남겨요.

요약은 풀이 본문의 판단 조건·결론·단서를 압축하고 항목 수의 고정 상한을 두지 않아요. 풀이에 없는 사실을 요약에만 추가하지 않고 보충의 범위·출처·불확실성을 보존해요. 중앙 문항 제목과 고정 패널 제목을 유지하며 우측에 문항 제목을 반복하지 않아요. 부모 note-template의 .sums 컨테이너에 유일한 sum-for ID를 두고 제목 복사 JavaScript를 추가하지 않아요. 원고와 기존 동반 MD를 함께 맞추고 [본문–요약 감사와 패널 검증](references/verification.md#본문요약-감사와-패널-검증)을 따라요.

## 3. 새 stage와 검토

기존 팩은 원고를 완성한 뒤 실행해요. explain-stage 기본값은 v2예요.

```powershell
python -m scripts.lab.review_pack explain-stage --folder 복습노트/실험NN --author-root docs/learning-pack-source/실험NN/problem-explanations --stage STAGE
python -m scripts.lab.review_pack check --folder STAGE
```

stage 성공은 구조 검사예요. 내용 검토 pass를 기록하지 않아요. explanation_checks는 모두 not_run으로 초기화돼요. [검증 절차](references/verification.md)에 따라 실제 원문·내용·브라우저 검토를 수행하고 STAGE/.pack/manifest.json의 별도 상태와 STAGE/.pack/problem-explanations/검증결과.md를 갱신해요. 독립 검토 미실시는 그대로 남겨요. 원고가 바뀌면 새 stage를 만들고 검토를 다시 해요.

## 4. 발행과 보고

검토 기록 후 같은 최종 stage를 check하고 발행해요.

```powershell
python -m scripts.lab.review_pack check --folder STAGE
python -m scripts.lab.review_pack publish --root . --stage STAGE --experiment N
```

실패한 팩은 교체하지 않아요. 기존 HTML/MD/PDF·그림·원문·사용자 파일의 해시와 백업·충돌 보호를 유지하고 최종 경로의 링크를 확인해요. 설명만 갱신했을 때 워크북을 rerender하거나 PDF를 다시 만들지 않아요. 문제설명 HTML/MD 두 링크, 대상·문항 수·검토 종류·미해결·백업 경로를 보고해요. 전체팩 흐름은 부모의 HTML 두 개·PDF 두 개·MD 네 개 링크 보고를 유지해요.
