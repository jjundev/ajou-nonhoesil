# 실험04 기출 문제지·해설지 설계

## 의도와 확정 결정

현재 기출풀이를 전자회로2의 문제지·답안지 템플릿으로 분리하고 오래된 학습용 그림을 직접 다시 제작한다. 학생이 문제지에서 먼저 풀고 해설지에서 회로·단계별 풀이·검산을 확인할 수 있어야 한다.

2026-10-01 grill-yourself 결정 #1은 사용자의 writing-plans 후속 요청으로 권장안 확정: 현재 생성된 실험04 전체에 적용한다. 현재 manifest의 included 12문항과 held 3문항의 선택 상태를 유지한다. 실험01~10 재추출은 포함하지 않는다. 실행 방식은 기존 Native를 유지한다.

## 작업 기준

- 작업 위치: `C:/Users/Hyunjun/.codex/worktrees/logic-lab-review-pack/논회실`.
- 브랜치: `codex/logic-lab-review-pack`; 계획 작성 시 HEAD `175a6f8`.
- 현재 채팅의 `864c` 워크트리는 구현 대상이 아니다.
- 저작 원본: `docs/learning-pack-source/실험04/`; 기존 tmp 초안보다 이 원본을 우선한다.
- 현재 학습팩: `복습노트/실험04/`; 문제은행: `문제은행/실험04/question-bank.json`.
- 기존 실험설명 리프레시 작업과 백업 폴더를 보존한다. 실행 전 최신 상태를 다시 확인한다.

## 공통 제약

- 적용 범위는 실험04의 현재 선별된 12문항이며 held 3문항은 계속 감사 기록에 남긴다.
- Native로 구현하고 Python 표준 라이브러리 기반 생성기를 유지한다. 그림 래스터화·브라우저 검증에 기존 검증 도구를 사용할 수 있다.
- 전자회로2 `workbook/templates/problem.html`과 `answer.html`을 바이트 그대로 복사한다. 생성 결과에서 데이터 삽입과 외부 자원 URL의 로컬 번들 치환만 허용한다.
- 실험설명의 생명과학 템플릿·본문·새 SVG·문체·MD 메타데이터를 유지한다.
- 문제은행·원자료·증거 자산·수입 고정 필드는 수정하지 않는다.
- 새 회로·블록도는 별도 SVG와 300dpi PNG로 저장하고 진리표·문장·수식은 텍스트로 작성한다.
- 문제지의 삽입 JSON·DOM·인쇄에는 해설·최종 답·풀이용 그림·답 노출 증거를 포함하지 않는다.
- 문제지·해설지의 ID·번호·순서·문제 조건은 동일하다. 기존 `기출풀이` 파일명과 문항 ID를 유지한다.
- 원문의 활성 극성·게이트 수·접속·반전·부품명·핀 이름을 보존한다. 판독 불확실성을 추측으로 해소하거나 그림 재제작만으로 verified로 승격하지 않는다.
- 템플릿의 A4 가로형(297mm × 210mm), 배치, 힌트 영역, 서체, 색, 축소·인쇄 동작을 유지한다.
- 브라우저에서 내용 넘침·잘림·깨진 그림·수식 오류가 있으면 발행하지 않는다. 수정은 내용 정리와 그림 크기 조정으로 하며 풀이 삭제나 임의 템플릿 변경을 하지 않는다.
- 새 파일은 별도 stage에서 검증하고 기존 publish의 백업·복구 절차로 발행한다. push·merge·원래 체크아웃 통합은 포함하지 않는다.

## 템플릿 원본

`ec2-review-pack`의 assets에는 정리노트 템플릿만 있다. 해당 스킬이 호출하는 `workbook/build_workbook.py`가 사용하는 아래 두 파일이 사용자 요청의 실제 문제지·해설지 HTML이다.

원본 루트: `C:/Users/Hyunjun/Desktop/현준대학/26-2/ajou-electronic-circuits-2`.

| 파일 | 계획 시 SHA256 |
|---|---|
| `workbook/templates/problem.html` | `77d5e785b3a12ff53deb33d65521d989661b2c7847a51d4df1bc4dfad76da594` |
| `workbook/templates/answer.html` | `8d7d87cc579ee11109f49d77c5beb31b592280bcbcfae97513b8e767e0bc8800` |

실행 시 원본 변경이 있으면 변경 내용을 읽고 새 스냅샷과 실제 해시를 기록한다.

원본 CSS/JS는 수정하지 않는다. `__WORKBOOK_DATA__` 한 곳에 `<`를 `\u003c`로 이스케이프한 JSON을 삽입한다. Pretendard URL은 기존 `assets/vendor/pretendard/pretendard.css`로, KaTeX 0.16.11 URL은 기존 로컬 파일로 치환한다. 원본에 있던 `made by jjundev` 표기도 유지한다.

## 작성 계약과 출력

manifest.schema_version=1을 유지하고 선택 필드 `review_presentation_version=2`를 추가한다. 이 필드가 없는 기존 팩은 기존 HTML·MD 계약으로 생성·검사한다. note_presentation_version=2는 독립적으로 유지한다.

새 included 문항은 `workbook_fragment: "workbook/<id>.json"`을 사용한다. 기존 fragment는 참고 원본으로 보존해도 되지만 새 출력의 입력으로 사용하지 않는다. authored JSON 필드는 `original`, `conditions`, `ask`, `problem_figures`, `hints`, `solution`, `notes`다. 문항 ID·제목·분류·답안 상태·출처·개념 링크는 manifest에서 가져온다. JSON은 HTML 조각을 포함하되 실행 코드와 외부 자원은 허용하지 않는다.

문제지 payload는 허용 필드만 새로 구성하고 `solution`, `notes`, 증거·출처 기록을 직렬화하지 않는다. 문제 조건에 원래 주어진 기능표의 값은 유지하고 학생이 채울 출력란만 비운다. 모든 문항은 original_lang='ko'다. kind에는 실제 기출은 '기출', 예상은 '예상문제', 미확인은 '출처 미확인'을 표시하고, 후자의 색은 템플릿 기본값을 사용한다.

해설지는 동일한 문제 필드에 `solution: {steps: [{label, html}], answer}`를 추가한다. 새 풀이 그림은 해당 step.html의 img로 넣고 문제 그림 배열에 섞지 않는다. 긴 원문 경로는 감사 MD에 두며 필요한 개념 링크와 원문 대조 링크는 해설의 마지막 단계에 넣는다. disputed/unresolved 문항은 헤더 section 및 풀이 단계에 상태·조건 충돌을 명시한다.

| 산출물 | 용도 |
|---|---|
| `실험04_실험설명.html`, `.md` | 기존 설명 유지 |
| `실험04_기출문제.html`, `.md` | 문제지 추가 |
| `실험04_기출풀이.html`, `.md` | 기존 이름으로 해설지 교체 |
| `figures/questions/<id>-given-01.svg`, `.png` | 문제에 주어진 회로 |
| `figures/solutions/<id>-solution-01.svg`, `.png` | 완성 회로·풀이 그림 |
| `figures/redraw-manifest.json` | 그림 출처·용도·해시·검토 상태 |
| 기존 manifest·감사 MD·은행 증거 | 추적성 유지 |

HTML과 MD는 동일한 작성 데이터에서 각각 생성한다. JavaScript 렌더링 템플릿을 기존 정적 DOM 변환기에 넣어 빈 MD가 생기지 않도록 한다. MD는 문제와 해설의 경계를 유지하며 해설 MD에 문항별 출처·개념 링크·held 기록을 보존한다.

## 그림 기록

manifest.figure_manifest='figures/redraw-manifest.json'. 기록은 schema_version=1, figures 배열이며 각 row는 id, question_id, role(problem|solution), svg, png, svg_sha256, png_sha256, w_mm, h_mm, source_asset_ids, source_refs, derivation, answer_exposure(none|present), review_status(not_run|pass|held), review_notes를 갖는다. source_refs는 manifest의 출처 위치 형식이다. 새 작성 파일을 원문 자산으로 등록하지 않는다.

문제 그림은 role=problem, answer_exposure=none이며 도출 답안 배선을 포함하지 않는다. source_asset_ids는 실제 문제은행의 연결된 자산을 기록하며 문제용 재도식은 safe_problem_asset_ids에서 출발한다. 풀이 그림은 원문 조건에서 독립 도출했음을 derivation에 적는다. 기록·해시 검사는 도식의 물리적 정확성을 보증하지 않으므로 원문 시각 대조와 식/표 검산을 별도로 수행한다.

## 검증과 완료 판정

복사 템플릿 해시, legacy 생성, 입력 JSON 중복 키·경로·능동 코드, 문제/해설 순서, JSON 답 노출, 재작성 자산 변조, MD 텍스트·표·수식·링크를 자동 검사한다. dynamic 템플릿의 문항 anchor는 payload ID로 검사하고 브라우저에서 실제 DOM을 확인한다. raw HTML에 article가 없다는 이유로 실패시키거나 빈 script를 MD 통과로 처리하지 않는다.

0문항 입력은 빈 데이터로 템플릿을 렌더링할 수 있으나 실제 실험04 발행에는 included 12문항이 반드시 있어야 한다. 빌드가 부분 실패한 stage는 발행하지 않는다. 새 콘텐츠를 만들 때 기존 checks를 그대로 복사하지 않고 관련 source_visual/content/independent/browser를 not_run으로 재설정한다.

최종 브라우저에서는 1280×900/375×812, 로컬 자원만 사용한 로딩, 그림 decode, KaTeX 오류, 실제 문항 순서·빈칸·해설, Hint 링크, data-ready=true, data-overflow 빈 문자열을 확인한다. 인쇄 PDF는 검증용이며 각 쪽이 A4 가로인지, 글씨·선·최종 답·표가 잘리지 않는지 페이지 렌더로 확인한다. 해설 그림의 단계 내 img는 원본 템플릿이 폭을 제한하지 않으므로 데이터의 img에 width와 max-width:100%, height:auto를 지정하고 실제 쪽에서 점검한다.

Native 구현 후 독립 리뷰 1회를 수행하고 실제 결과만 기록한다. 관련 테스트를 먼저 실행하고 전체 테스트에서 기존 실패와 새 실패를 구분한다. 원문 대조·내용·브라우저 검증을 마친 최종 stage만 publish한다.
