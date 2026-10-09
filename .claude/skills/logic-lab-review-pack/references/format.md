# 저작 계약 v1

기계 계약 정본은 scripts/lab/review_pack/manifest.py다. 최소 예는 tests/fixtures/review_pack/manifest.json.
run/manifest.json(발행본은 `자료/manifest.json`), run/sections/<topic-id>.html, run/problems/<problem-id>.html, run/figures/를 저작한다.
ID는 영어 문자로 시작하며 영문·숫자·하이픈·밑줄만 쓴다. source/topic/problem 전체에서 유일해야 한다.
재생성은 이전 manifest를 읽고 자료·문항 ID를 재사용한다. 순서 변경은 ID 변경 사유가 아니다. 조건이 바뀐 문제는 새 ID.

- sources: id, 저장소 상대 POSIX path, 파일 내용 sha256, kind(manual/quiz/theory/report/record/datasheet/stt/notice), edition(current/archive/unknown).
- topics: id, title, requires(선수 토픽 ID), sources, fragment. 선수 관계는 순환 금지.
- problems: id, kind(past/unknown/predicted/practice), status(included/duplicate/held/other_experiment), reason, topics, sources, duplicate_of, scope(current/supplement/unknown), given_answer, derived_answer, answer_status(verified/disputed/unresolved), fragment.
- sources 참조: source_id, pdf_page(1부터 시작하는 실제 PDF 페이지; 비PDF는 null), printed_page(인쇄 쪽수 문자열 또는 null), question(선택적 원문 문항 번호).
- practice만 source 없이 허용. held라도 판독을 시도한 원문 위치는 남긴다. duplicate에는 원문 위치·대표 문항 ID·중복 판단 이유가 필요하다.
- checks: source_visual/content/independent/browser 각각 pass/fail/not_run/self_review. independent=self_review는 블라인드 검증이 아니다.
- edition_status: current/archive/unknown/general. 출처 없는 일반 이론은 general.
- generated_files는 build가 기록하며 사용자 메모를 이 목록에 임의로 넣지 않는다.

본문 fragment는 article/h1 없이 작성한다. 조립기가 article ID·제목을 붙인다.
다른 페이지 링크는 {{NOTE_HREF}}#토픽ID, {{REVIEW_HREF}}#문항ID.
힌트·풀이는 각각 details/summary. 풀이에는 단계, 최종 답, 검산, 흔한 실수를 쓴다.
수식은 MathML math[data-tex]를 사용한다. data-tex에는 동일한 LaTeX를 넣는다. SVG는 접근 가능한 제목·대체 설명을 제공한다.
표는 .table-wrap으로 감싼다. 위젯은 .controls와 .static-equivalent를 분리하며 정적 자료만으로도 이해되어야 한다.
inline script, 외부 CSS/JS/폰트/이미지는 금지. 공통 widgets.js만 동작 코드를 가진다.

## 은행 수입 manifest

schema_version=1을 유지하며 bank_import가 없는 legacy manifest도 지원한다.
bank_import는 bank_id/schema_version/source_path/sha256/snapshot_path/index_path의 정확히 여섯 필드를 갖는다.
source_path는 원래 은행의 저장소 상대 경로, snapshot_path는 evidence/question-bank.json, index_path는 authoring-index.json이다.
은행 실험 번호와 manifest 실험 번호가 같아야 한다. 중복 JSON 키를 거절한다.

수입 문제는 id=bank_question_id=원래 question ID, kind는 은행 값 그대로다. 모든 occurrence의 source 위치와 original_number를 sources에 보존한다.
은행 sources의 ID/path/hash와 수입 문항을 삭제하지 않는다. 추가 교안 source·topic·독립 풀이·선별 상태는 저작한다.
초기 문제는 held/topics=[]/given_answer=null/derived_answer=null/answer_status=unresolved다. 미작성 held에는 fragment가 없다.
제공 답안 전체는 snapshot/index/원문 안내에 보존하므로 scalar given_answer로 하나를 자동 선택하지 않는다.

authoring-index 고정 필드는 은행과 검사로 대조한다. authoring_status·selection_reason만 변경 가능하다.
not_selected/held에는 selection_reason이 필요하다. manifest에서도 미수록·보류 이유를 기록한다.
문제 fragment에는 div.problem이 정확히 하나 있어야 한다. 답 노출 원문은 details.original/solution 안에만 두고 hint에 넣지 않는다.
답 노출 그림은 details의 summary에 넣지 않고 open 속성 없이 시작한다. srcset 후보와 스타일 URL도 답 노출 검사 대상이다.
evidence/와 인덱스·안내는 build의 generated_files에 포함한다(발행본에서는 `자료/evidence/`, `자료/authoring-index.json`, 루트의 원문과_저작안내.md). 템플릿을 수정해 출처 검사를 우회하지 않는다.
