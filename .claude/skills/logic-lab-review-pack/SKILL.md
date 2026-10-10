---
name: logic-lab-review-pack
description: 논리회로실험 1~10의 실험 설명, 예습·복습 자료, 기출 풀이, 학습팩을 요청할 때 사용한다. 보고서 작성과 측정 체크리스트는 해당 전용 스킬을 사용한다.
---

# 논리회로실험 학습팩

오래전에 논리회로를 배운 학생이 기초부터 회로를 이해하고 기출을 풀 수 있게 한다.
기존 보고서에 등장하는 용어를 안다고 가정하지 않는다. 완전판 설명+앞부분 요약과 고유 기출 전체가 기본이다.
새 워크북 학습팩은 실험설명·기출문제·기출풀이·문제설명 HTML 네 개와 같은 내용의 MD 네 개를 만든다. 사용자에게 중간 메뉴를 반복해서 묻지 않는다.

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

RUN/sections/<id>.html, RUN/workbook/<id>.json, RUN/figures/를 작성한다. 새 문제지·해설지는 manifest.review_presentation_version=2로 지정하고 [문제지·해설지 계약](references/workbook.md)을 따른다. 기존 표시 버전 없는 팩은 RUN/problems/<id>.html을 쓰는 legacy 형식으로 계속 읽을 수 있다.
새 실험설명에는 manifest.note_presentation_version=2를 지정한다. 본문·요약·힌트·그림 설명을 생명과학 정리노트처럼 짧고 다정한 ‘~해요’체로 쓴다. 정의·성립 조건·인과는 줄이지 않는다.
실험설명 HTML에는 출처와 ‘이 개념으로 풀 문제’를 넣지 않는다. 출처는 topics[].sources, 연결 문제는 included 문항의 topics에서 MD에 자동으로 붙인다. 추가 판본·재제작 근거는 topics[].md_notes에 Markdown으로 기록한다.
실험설명의 모든 설명 그림은 원문을 읽어 직접 SVG로 다시 제작하고 진리표는 텍스트 표로 쓴다. 스캔/스크린샷을 설명 그림으로 첨부하지 않는다. 원문·문제은행 증거와 기출풀이 원본 이미지는 보존한다.
설명은 완성 예제→일부 단계 연습→기출 풀이로 이어진다. 문제에는 필요한 개념으로 돌아가는 링크를 넣는다.
실험설명은 생명과학 note-template.html에서 가져온 논회실 로컬 템플릿을 사용한다. upstream 원본은 보존하고 논회실의 탐색 개선은 로컬 템플릿·생성기·검사기에 함께 반영한다. 문제지·해설지는 전자회로2 workbook/templates의 problem.html·answer.html 스냅샷(해시 고정)을 쓰고, 생성 시 workbook_render의 LOCAL_PATCHES(표 테두리 CSS, 빈 조건 블록 생략)와 TEMPLATE_PATCHES(문제지의 채울 표를 work-table 표지로 풀이 칸 맨 위에 옮김)만 덧씌운다. 워크북 템플릿 디자인을 재작성하지 않는다. 기출의 회로·블록도는 문제용과 풀이용을 구분하여 별도 SVG와 300dpi PNG로 직접 재작성하고, 원문 증거는 evidence/에 보존한다.

**탐색 계약.** 실험설명과 legacy 기출풀이의 왼쪽 패널에는 현재 문서 목차만 둔다. `자료 이동` 제목·문서 링크·pack-nav·구분선을 추가하지 않는다. 패널의 `목차` 제목 바로 아래에 토픽/문항 목록만 둔다. `실험 이해` 등 섹션 링크를 목차에 넣지 않는다. `이 페이지 목차` 소제목, 읽은 토픽/푼 문제 합계와 진행 막대를 표시하지 않는다. `<nav class="toc" aria-label="이 페이지 목차">` 안에 `<ol class="toc-list">`와 토픽/문항 hash 링크를 정적으로 생성한다. 들여쓰기는 0이며 JS는 기존 링크를 화면·읽음 체크와 연결한다. JS 비활성에서도 전체 토픽 링크를 제공한다. 문서 링크를 TOC에 혼합하거나 모든 링크를 section으로 해석하지 않는다. 잘못된 hash 인코딩은 예외를 처리한다. 개별 토픽/문항의 읽음·풂 체크는 유지하되 진행 합계는 표시하지 않는다. 현재 토픽의 기존 `aria-current="true"`와 읽음/풂 저장 키·IDs를 유지한다. 모바일에서는 목차 선택 후 drawer를 닫는다. 별도 A4 워크북은 이 패널 계약의 대상이 아니다.
우측 요약은 div.sum, 도움말은 details.hint/solution을 사용한다. 자세한 마크업은 authoring.md.

## 4. 조립과 MD 생성

```powershell
python -m scripts.lab.review_pack build --root . --run RUN --stage STAGE
python -m scripts.lab.review_pack check --folder STAGE
```

build는 problem_explanation_version=1인 새 워크북에서 네 HTML, 네 MD, 출처와_문항목록.md를 실험 폴더 루트에, manifest.json·figures/·assets/를 `자료/`에 만든다. legacy 팩은 두 HTML·두 MD를 유지한다.
은행 수입 팩에는 원문과_저작안내.md(루트)와 evidence/·authoring-index.json(`자료/`)도 복사한다.
RUN(저작 작업 폴더)은 이 규칙의 대상이 아니다. RUN 안에서는 manifest.json·figures/·evidence/를 예전처럼 RUN 루트에 둔다. build가 `자료/` 로 옮긴다.
build/publish는 원래 은행·원문·자산 해시를 대조한다. 변경 시 새 import 후 관련 내용을 재검토한다.
생명과학 저장소의 원본 템플릿은 그대로 보존하고, 논회실 로컬 템플릿으로 생성한 결과에서 CDN URL을 번들된 로컬 자원으로 바꾼다.
MD에는 힌트·풀이·정적 위젯 설명을 모두 남긴다. 오류가 나면 fragment를 수정하고 새 stage로 다시 build한다.

## 5. 검증

[verification.md](references/verification.md)를 따른다.
원문 대조·독립 계산·노트의 풀이 충분성을 확인한다. 정답지와 충돌하면 양쪽을 재검토하고 미확정이면 그대로 표시한다.
독립 리뷰어가 실제로 검토하지 않았으면 independent=pass를 쓰지 않는다.
실험설명은 브라우저에서 375px/1280px, 다크모드, 이전/다음, 목차, 우측 요약과 위젯을 확인한다. 새 문제지·해설지는 전자회로2의 A4 가로 페이지·화면 축소·Hint 링크·인쇄 동작을 검증한다. data-ready=true, data-overflow 빈 문자열, 깨진 그림·수식 오류 0, 표와 마지막 답의 잘림 없음을 확인한다. raw HTML에 문항 article가 없는 것은 JS 템플릿의 정상 동작이며 payload와 실제 DOM을 모두 확인한다.
RUN/검증결과.md에 확인한 대상·결과·미해결을 남기고 manifest.checks를 실제 결과로 갱신한다.
업데이트 후 새 stage로 build한다. 최종 stage와 검사 대상이 같아야 한다. 검토 후 내용 변경은 관련 검토를 다시 수행한다.
수정은 최대 2회. 이후 남은 결함은 정직하게 보고하고 검증되지 않은 초안으로 기존 팩을 교체하지 않는다.

## 6. 저장과 보고

```powershell
python -m scripts.lab.review_pack publish --root . --stage STAGE --experiment 4
```

**저장 규칙.** `복습노트/실험NN/` 루트에는 문서(.md·.html·.pdf)와 `자료/` 폴더만 둔다.
문서 외 모든 파일은 `자료/` 안에 둔다: manifest.json, authoring-index.json, assets/, evidence/, figures/.
HTML·MD가 이 파일을 부를 때는 문서 기준 상대경로 `자료/figures/..`, `자료/assets/vendor/..` 로 쓴다. 폴더 이름은 `scripts/lab/config.py` 의 `PACK_DATA_DIR` 한 곳에서 정한다.
manifest 안의 경로(figure_manifest, snapshot_path, workbook_fragment)는 `자료/` 기준 상대경로 그대로 둔다(`figures/redraw-manifest.json`). generated_files 만 실험 폴더 루트 기준이라 `자료/figures/..` 로 적힌다.
RUN 의 저작 조각(sections·workbook JSON)은 `figures/..` 라고 쓰면 build 가 `자료/figures/..` 로 바꾼다.
`check` 는 루트에 남은 assets·evidence·figures·manifest.json·authoring-index.json 을 오류로 본다. 새 종류의 파일을 만들면 루트가 아니라 `자료/` 에 둔다.
옛 구조(자료/ 없는 팩)는 읽지 않는다. 남아 있으면 `python -m scripts.lab.migrate_pack_layout`(dry-run)으로 보고 `--apply` 로 옮긴다.

저장은 복습노트/실험NN. 교체 전 원문 해시·검증 상태를 확인하고 기존 팩을 백업한다.
사용자 추가 파일이 생성 파일과 충돌하면 덮어쓰지 않는다. 백업은 삭제하지 않는다.
최종 경로에서 문항 링크·원문 PDF 링크를 다시 확인한다.
publish 뒤 태블릿용 PDF를 만든다: `python -m scripts.lab.workbook_pdf 실험NN`. `복습노트/실험NN/`에 실험NN_기출문제.pdf·실험NN_기출풀이.pdf가 생기고(A4 가로, 쪽 수·크기·넘침 검사와 인쇄 결과의 원문 LaTeX·답 상자 밑 그림 검사 포함) 실패하면 성공이라 하지 않는다. publish·rerender로 HTML 내용이 바뀌면 PDF를 다시 만든다. 링크 경로만 바뀐 경우(자료/ 이전)는 PDF 내용이 같으므로 다시 만들지 않는다.
보고: 문제설명 포함 여덟 학습 파일 링크(기존 워크북은 여섯 개, legacy는 네 개), 판본, 포함·중복·보류 수, 답안 충돌, 검토 종류, 미해결, 백업 경로.
파일 생성 완료를 학생의 이해 완료라고 표현하지 않는다.

## 후속 요청과 경계

특정 부분에 대한 질문은 기존 팩을 읽고 설명한다. 질문만으로 파일을 수정하지 않는다.
'고쳐줘/보충해줘'는 같은 팩을 갱신한다. PDF 요청은 위 workbook_pdf 스크립트로 만든다. **워크북** 템플릿 패치나 해설 단계를 바꾼 뒤 이미 저장된 팩에 반영할 때는 `python -m scripts.lab.review_pack rerender --folder 복습노트/실험NN`(워크북 payload에서 HTML·MD 재생성 후 검사)을 쓴다. 이 명령은 실험설명을 재생성하지 않는다.

**기존 목차 일괄 갱신.** `python -m scripts.lab.review_pack.navigation_upgrade --all`로 dry-run 목록을 확인하고 `python -m scripts.lab.review_pack.navigation_upgrade --all --apply --backup-dir <새 백업 폴더>`로 적용한다. 한 팩은 `--all` 대신 `--folder 복습노트/실험NN`을 쓴다. 명령은 모든 대상의 구조를 사전 검사하고 전체 팩을 백업한 뒤 탐색 부분과 동봉 note/review 템플릿만 바꾼다. 알 수 없는 HTML은 쓰기 전에 실패하며 본문·IDs·워크북 payload는 보존한다. 재실행의 변경 목록은 0이어야 한다. 적용 후 각 팩의 check와 브라우저 검증을 수행한다. 이미 내보낸 standalone HTML이 있으면 갱신한 원본으로 다시 내보낸다.
보고서·체크리스트·노션 업로드·FPGA 프로젝트를 자동으로 시작하지 않는다.

## 문제풀이 입문 설명

새 워크북은 `problem_explanation_version=1`, 각 included 문항에 `explanation_fragment=problem-explanations/<id>.html`을 설정한다. `explanation_checks`는 source_visual/content/independent/browser를 별도로 not_run으로 초기화한다. 기존 팩과 legacy는 선택적 버전이 없어도 계속 읽는다.

이론을 한 번 읽었지만 문제풀이 경험이 없는 학생에게 모든 문항·소문항을 설명한다. 첫 줄·이유·완성 답·검산을 생략하거나 기존 짧은 답안을 복사하는 것으로 끝내지 않는다. 저작 마크업과 검증은 references/authoring.md, format.md, verification.md를 따른다.

`실험NN_문제설명.html/.md`는 실험설명의 같은 note-template, article.topic, eli5/formal/warn, 우측 sum, 목차와 이전/다음을 사용한다. 풀이·정답은 본문에 모두 펼친다. 읽음 RANGE는 `logic-lab-NN-problem-explanation`이며 기존 실험설명과 분리한다. 자료 이동 영역·진행 합계·학습 잠금·자동 채점은 넣지 않는다. 불확실성·성립 조건은 HTML에, 상세 출처는 MD에 둔다.

기존 팩은 저작 RUN을 복원하거나 기존 HTML/MD/PDF를 다시 생성하지 않는다. `python -m scripts.lab.review_pack explain-stage --folder 복습노트/실험NN --author-root docs/learning-pack-source/실험NN/problem-explanations --stage <신규 stage>`로 소유 파일만 복사하고 설명을 추가한다. 사용자 파일은 기존 폴더에서 publish가 보존한다. 새 stage의 원문·내용·브라우저를 확인하여 explanation_checks를 갱신한 뒤 기존 publish로 발행한다. 문제지/해설지의 바이트가 그대로면 PDF도 다시 만들지 않는다. 백업을 남기고 기존 파일 보존 해시를 기록한다.
