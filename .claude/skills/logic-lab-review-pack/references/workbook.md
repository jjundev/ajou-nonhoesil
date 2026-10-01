# 전자회로2 템플릿의 문제지·해설지

원본 HTML은 assets/workbook/의 problem.html과 answer.html이다. 원본 바이트·해시를 유지하고 생성 시 JSON과 로컬 자원 URL만 바꾼다. 생명과학 note-template은 실험설명에 계속 사용한다.

manifest.schema_version=1, review_presentation_version=2, figure_manifest='figures/redraw-manifest.json'을 지정한다. included 문항에는 workbook_fragment='workbook/<id>.json'을 지정한다. 은행 고정 필드와 원문 이미지는 수정하지 않는다.

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

회로는 figures/questions/<id>-given-01.svg/.png와 figures/solutions/<id>-solution-01.svg/.png로 구분한다. 새 그림을 원문 자산이라고 표시하지 않는다. registry에는 ID/문항/role/두 파일의 hash/인쇄 mm/source_asset_ids/source_refs/derivation/answer_exposure/review_status/review_notes를 기록한다. 문제 그림은 problem/none 및 원문 safe_problem_asset_ids를 사용한다. source_refs와 도출 설명은 실제로 확인한 자료에 결합한다. 시각 검토 전에 pass로 표시하지 않는다.

해설 그림은 solution.steps[].html 안에 넣는다:

```html
<p><img src="figures/solutions/q-mux2-solution-01.png" width="400"
style="max-width:100%;height:auto" alt="2×1 MUX 완성 회로"></p>
```

문제지 JSON에는 solution·notes·증거를 넣지 않는다. 해설지는 동일 문제 데이터에 단계/답/대조 기록/개념 링크를 추가한다. source evidence는 원문과_저작안내.md에서 접근한다. 두 판의 문항 번호·ID·조건·힌트·문제 그림은 일치해야 한다.

세 HTML/세 MD를 같은 작성 데이터로 생성한다. JavaScript 템플릿 전체를 정적 HTML→MD에 넣지 않는다. 변환기는 실험설명에만 사용하고 workbook MD는 payload에서 생성하며 본문·TeX·표 셀·이미지·anchor 보존을 별도로 검사한다.

검증: 1280×900/375×812, 로컬 글꼴·KaTeX·이미지, data-ready=true, data-overflow='', 깨진 이미지·콘솔·수식 오류 0. 넓은 표·해설 그림·최종 답이 페이지 밖으로 나가지 않아야 한다. A4 가로 인쇄를 페이지별로 렌더링해 확인한다. 오류가 남은 stage는 publish하지 않는다. 그림을 바꾸면 hash와 시각 검토를 갱신하고 관련 checks도 다시 수행한다.
