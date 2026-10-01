# 실험04 문제지·해설지 독립 리뷰

검토 범위: `175a6f8 → f41d0ec7bf24b79d0bdc097caea7231c726159e2`. Native 구현의 마지막 독립 리뷰 1회. 리뷰어는 작업 트리를 수정하지 않고 12문항, 9도식, 25쪽 인쇄 PNG와 코드/설계를 검토했다.

## 리뷰 원문

**Strengths**

- Both template snapshots match the actual EC2 originals byte-for-byte. Legacy generation remains separately routed; bank evidence and note source sections are unchanged.
- All 12 questions and solutions preserve their conditions, ordering, classifications, and held records. The nine drawings correctly represent the NAND enable, complementary active Low nOE controls, shared-bus junctions, and specified gate counts. The X/0 dispute remains explicit.
- Inspected all 25 print-page PNGs: no clipped content or missing final answers. Solution drawings are compact but retain usable connections and labels. Independently ran 32 focused tests successfully; the reviewed stage passes mechanical checks.

**Critical:** None.

**Important**

- `scripts/lab/review_pack/workbook_content.py:67–69`: Problem hyperlinks bypass answer-exposure restrictions. `problem=True` validates diagram roles for `src`, but permits any local `href`, including answer-bearing evidence. Reproduced in a temporary source copy by appending `<a href="evidence/assets/s01-p1.jpg">원문 보기</a>` to `q-mux2.original`. That asset is marked `answer_exposure=present`; `load_workbook_content` accepted all 12 questions, assembly and MD conversion succeeded, and `check_pack` returned `[]`. The answer link appeared in question JSON and generated question content. Restrict problem-context links so evidence, audit, and solution targets cannot enter problem fields or hints; add regression coverage. **The current authored 12-question pack does not contain this leak.**

**Minor:** None.

**Declined to judge**

- Whether the 20 full-suite failures reproduce on BASE; the implementer’s baseline comparison was still underway.
- Physical printer output; inspected the supplied PDF page renders.

**Readiness:** Actual workbook content and drawings are ready. Resolve the reproduced problem-link validation gap before declaring the implementation complete, then perform the planned final-stage publication checks.

## 구현자의 판정과 수정

중요 지적은 실제 계약 결함으로 확인했다. 원문·조건·구할 것·힌트에 evidence/solution/감사 문서 링크를 넣는 12개 회귀 입력을 작성해 모두 RED를 확인했고, 문제용 작성 HTML의 href 링크를 차단했다. 현재 문제 본문에는 작성 링크가 없으며 개념·원문 대조 링크는 해설에 유지한다. 문제지 MD의 생성기 제공 파일 이동 링크는 명시적으로 별도 제공한다.

리뷰어가 보류한 기준선 비교는 175a6f8의 별도 코드 사본과 같은 교안 자료에서 20개 실패가 재현됨을 확인했다. 원본 모듈/테스트를 고치지 않았으며 실제 실패 항목은 검증 문서에 남긴다. 물리 프린터 출력은 사용자 요청 범위 밖이며 A4 PDF/PNG 시각 검증을 수행했다.

최종 수정은 새 회귀 RED→GREEN과 관련 전체 검사로 검증한다. 두 번째 리뷰어를 추가하거나 재리뷰하지 않는다. 미반영 Minor는 없다.
