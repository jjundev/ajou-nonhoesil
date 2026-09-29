# 저작 계약 v1

기계 계약 정본은 scripts/lab/review_pack/manifest.py다. 최소 예는 tests/fixtures/review_pack/manifest.json.
run/manifest.json, run/sections/<topic-id>.html, run/problems/<problem-id>.html, run/figures/를 저작한다.
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
