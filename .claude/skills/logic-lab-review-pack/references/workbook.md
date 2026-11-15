# 전자회로2 템플릿의 문제지·해설지

원본 HTML은 assets/workbook/의 problem.html과 answer.html이다. 원본 바이트·해시를 유지하고 생성 시 JSON, 로컬 자원 URL, workbook_render.LOCAL_PATCHES(표 테두리 CSS·빈 조건 블록 생략·그림 load 대기·쉼표 식 목록 줄바꿈·맞춤 뒤 잘림 훑기, 모든 템플릿 공통)와 TEMPLATE_PATCHES(문제지의 채울 표를 풀이 칸으로 옮기기·넘침 검사, problem.html에만)를 적용한다. 정책 v1에서는 아래 퀴즈 전용 패치도 적용한다. 패치 anchor가 사라지면 렌더가 실패한다. 생명과학 note-template은 실험설명에 계속 사용한다.

manifest.schema_version=1, review_presentation_version=2, figure_manifest='figures/redraw-manifest.json'을 지정한다(발행본에서는 `.pack/` 기준이다). 문제지·해설지 HTML 속 그림 링크는 build가 `.pack/figures/..` 로 쓴다. included 문항에는 workbook_fragment='workbook/<id>.json'을 지정한다. 은행 고정 필드와 원문 이미지는 수정하지 않는다.

문항 JSON 예:

```json
{
  "original": "<p>게이트로 MUX 회로를 설계하시오.</p>",
  "conditions": "<p>NOT 1, AND 2, OR 1을 사용해요.</p>",
  "ask": "<p>회로와 논리식을 작성하세요.</p>",
  "problem_figures": [],
  "hints": [{"label": "접근 순서", "html": "<p>선택선의 두 상태를 따로 생각하세요.</p>"}],
  "solution": {"steps": [{"label": "회로", "html": "<p>입력마다 경로를 만든 뒤 합쳐요.</p>"}], "answer": "<p>해설의 선택 조건을 확인하세요.</p>"},
  "notes": []
}
```

원문 조건·표·문장은 텍스트로 보존한다. 학생이 채울 출력란만 비우고 이미 답이 있는 원문을 옮긴 표면 그 사실을 명시한다. 힌트에는 접근 순서만 쓰고 완성 배선·최종 답을 그대로 쓰지 않는다.

학생이 채울 표(빈 `<td>`가 있는 표)는 `<div class="table-wrap work-table">`로 쓴다. 문제지에서는 이 표가 좌측 패널이 아니라 가운데 풀이 칸 맨 위에 나온다. 표지는 손으로 달지 말고 `mark_work_tables`(scripts/lab/review_pack/work_table.py)로 단다. 생성기가 JSON을 쓸 때 부르고, 이미 쓴 JSON은 `python -m scripts.lab.review_pack.work_table <폴더>`로 단다. 빈 칸이 있는데 표지가 없거나, 표지가 있는데 빈 칸이 없으면 build가 거부한다. 해설 단계의 완성된 표(`solution`)에는 표지를 달지 않는다. 해설지는 풀이 단계가 들어갈 높이를 지키려고 빈 표를 패널에 남긴다. 배선표처럼 빈 칸이 없는 표도 패널에 남는다. 이미 발행된 팩은 `python -m scripts.lab.review_pack rerender --folder 복습노트/실험NN`이 표지를 달아 다시 만든다. 표가 칸에 안 들어가면 `data-overflow`로 드러나며 글자를 줄이지 않는다.

긴 논리식(`$$…$$` 40자 초과)은 관계 기호(`=`·`\approx` 등)마다 줄을 바꿔 세로로 맞춘다. 여러 식이 쉼표로 이어진 목록(`O_0=…,\ O_1=…`)은 식마다 한 줄(`aligned` 행)로 나뉘고, 각 식의 관계 기호는 그 줄 안에서만 이어진다. 조각마다 최상위 `=` 가 있을 때만 나누고(말미 쉼표가 남긴 빈 조각은 무시) `f(a,b)=…` 의 괄호 안 쉼표나 관계 기호가 없는 조각이 낀 목록은 나누지 않는다. 이 규칙은 `workbook_render.LOCAL_PATCHES` 의 `EQUATION_NEW`(`splitEquationList`)에 있고 테스트는 `tests/test_workbook_equations.py` 다.

맞춤이 끝난 뒤 잘린 식·표(단 사이 여백 밖으로 나가거나 잘리는 표)·넘친 풀이 단계가 남으면 `data-overflow` 에 해당 쪽 id 가 오른다. 훑기는 `.page--problem` 마다 한 번, 맞춤이 모두 끝난 뒤에만 돈다. display 식은 `.katex` 블록이 아니라 내용 범위(`.katex-html` Range)가 display 박스 오른쪽을 넘는지로 잰다. 줄바꿈 지점이 없는 인라인 식(`$\overline{…}$`·긴 `\mathrm{…}`)은 맞춤이 줄이지 않고 흐름이 잘라 내므로, 그 식이 놓인 글 상자(`.sol-step-body`·`.prose`·`td`·`th`·`.hint-strip-item`·`.sol-answer`·`.block` 중 가장 가까운 것) 오른쪽 + 1 과 비교한다. 표는 `.table-wrap` 이 없어도(생 `<table>`) 잰다. wrap 보다 넓다는 것만으로는 걸지 않고, 가장 가까운 clip 조상의 오른쪽을 넘거나, 다단 풀이 흐름에서 다음 단의 왼쪽(현재 단 오른쪽 + column-gap)을 넘거나, 단일 단에서 flow 오른쪽을 넘을 때만 센다(단 사이 여백 안에서 끝나는 표는 보이고 옆 글과 겹치지 않아 통과). 구현은 `workbook_render.LOCAL_PATCHES` 의 `CLIP_HELPER`(`hasClippedContent`·`tableClipped`)·`CLIP_SCAN` 이고 테스트는 `tests/test_workbook_clip_gate.py` 다.

훑기가 보지 않는 곳(한계): 문제 쪽 Hint 띠의 식(`.hint-strip-formula`, 따로 70% 까지 줄이며 그 뒤 넘침은 못 알린다), 풀이 단계가 없고 답 칸(`.sol-answer`)만 큰 해설(`fitSolution` 도 단계 검사도 비어 있어 답이 칸 아래로 넘쳐도 못 알린다. 답 안의 식·표만 위 규칙으로 본다), 왼쪽 가장자리로 잘리는 경우(오른쪽 가장자리만 잰다), Hint 쪽(`.page--hint`)의 display 식이 카드 밖으로 번지는 경우(잘림은 아니라 보지 않는다). 현재 게시본에는 해당이 없다(`hint-strip-formula` 0개, `steps=[]` 0개).

회로는 figures/questions/<id>-given-01.svg/.png와 figures/solutions/<id>-solution-01.svg/.png로 구분한다. 새 그림을 원문 자산이라고 표시하지 않는다. registry에는 ID/문항/role/두 파일의 hash/인쇄 mm/source_asset_ids/source_refs/derivation/answer_exposure/review_status/review_notes를 기록한다. 문제 그림은 problem/none 및 원문 safe_problem_asset_ids를 사용한다. source_refs와 도출 설명은 실제로 확인한 자료에 결합한다. 시각 검토 전에 pass로 표시하지 않는다.

해설 그림은 solution.steps[].html 안에 넣는다:

```html
<p><img src="figures/solutions/q-mux2-solution-01.png" width="400"
style="max-width:100%;height:auto" alt="2×1 MUX 완성 회로"></p>
```

문제지 JSON에는 solution·notes·증거를 넣지 않는다. 문제 본문·조건·구할 것·힌트의 작성 HTML에는 하이퍼링크를 넣지 않는다. 해설지는 동일 문제 데이터에 단계/답을 추가한다. 「원문 대조·다시 볼 개념」 단계와 개념·원문 링크는 두지 않는다(답안 상태는 쪽 머리 section에만 남긴다). source evidence는 원문과_저작안내.md에서 접근한다. 두 판의 문항 번호·ID·조건·힌트·문제 그림은 일치해야 한다.

세 HTML/세 MD를 같은 작성 데이터로 생성한다. JavaScript 템플릿 전체를 정적 HTML→MD에 넣지 않는다. 변환기는 실험설명에만 사용하고 workbook MD는 payload에서 생성하며 본문·TeX·표 셀·이미지·anchor 보존을 별도로 검사한다.

검증: 1280×900/375×812, 로컬 글꼴·KaTeX·이미지, data-ready=true, data-overflow='', 깨진 이미지·콘솔·수식 오류 0. 넓은 표·해설 그림·최종 답이 페이지 밖으로 나가지 않아야 한다. A4 가로 인쇄를 페이지별로 렌더링해 확인한다. 오류가 남은 stage는 publish하지 않는다. 그림을 바꾸면 hash와 시각 검토를 갱신하고 관련 checks도 다시 수행한다.

## 문제설명 연결

문제설명 전용 기준은 [전용 format 문서](../../logic-lab-problem-explain/references/format.md)를 읽는다. 전체팩은 같은 실행에서 새 설명 v2를 저작하며 기존 워크북 projection·문항 정보와 실험설명·문제설명 HTML, 문제지·해설지 PDF, MD 네 개 출력은 유지한다.

## 정책이 있는 퀴즈 유형 연습

[quiz-practice.md](quiz-practice.md)의 조건·chip-spec·work-board·필수 해설 label 계약을 따른다. quiz_practice_version=1인 payload에만 quiz_practice_patches가 추가된다. 원본 스냅샷과 정책 없는 렌더 바이트는 보존한다. 빈 보드는 중앙의 작도 공간이며 해설 DOM에서만 제거한다. payload의 문제 조건은 양쪽에서 같다.
