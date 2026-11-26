# 문제에서 방법을 떠올리는 설명 저작

개념을 공부한 학생이 풀이를 재현할 수 있는 분량으로 '~해요'체를 써요. 문장을 지웠을 때 풀이법 선택, 답을 가르는 조건, 소문항의 답안 재현, 검산이나 경고 중 하나가 빠지면 남겨요. 교안에서 배운 일반 정의는 개념 노트 링크로 연결해요. 정의 자체를 묻거나 기호·극성 해석에 따라 답이 달라지는 문항에는 필요한 뜻을 바로 써요.

문제 원문·조건·구할 것·그림은 문제지 payload에서 가져와요. 해설에서는 문제를 다시 풀어쓰는 부분과 여러 구역에 반복된 판단을 걷어내요. 기존 표·식·회로와 식·기호의 의미를 보존해요. 한 규칙을 여러 행에 적용하면 답이 갈리는 대표 행의 근거와 완성표를 두고, 독립된 소문항마다 필요한 판단과 답을 확인해요. 글자 수와 문장 수는 문항에 맞춰요.

v2에서는 다음 직계 `data-explanation` 구역을 각각 하나씩 이 순서로 둬요.

- **understand**(eli5)는 제출할 결과나 풀이 범위를 짧게 잡아요.
- **recall**(formal)은 문제 단서가 왜 그 방법으로 이어지는지 적어요. 제목은 '이 문제를 봤을 때 떠올릴 개념과 공식'이에요. cue는 자식 태그 없는 1~60자 평문이며 `$$`를 쓰지 않아요. cue 뒤에 판단 이유 문단을 둬요.
- **start**(formal)는 실제 첫 식·첫 행·배선이나 판정 한 가지와 `{{NOTE_HREF}}#토픽ID` 개념 링크를 둬요.
- **solve**(formal)는 각 소문항에서 답을 가르는 판단과 완성 표·식·회로를 보여줘요. 완성표에서 바로 읽히는 행은 표에서 확인하게 해요.
- **verify**(formal)는 최종 답을 짧게 쓰거나 이미 완성한 표·회로를 가리키고, 잘못된 판단이 드러나는 입력·경계·독립 확인을 써요.
- **pitfall**(warn)은 문항에서 실제로 답이 달라지는 착각·예외를 짚어요. disputed는 '답안 충돌', unresolved는 '정답 미확정' 경고와 적용 조건을 보존해요. 검증된 문항에 출처별 답안 차이가 있으면 차이와 판정 근거를 남겨요.
- **retry**(formal)는 설명을 덮고 바로 실행할 행동을 1~3개의 li로 써요. 한 줄로 재현할 수 있으면 한 줄을 써요.

recall은 ① 방법 선택의 단서 ② 필요한 개념 ③ 풀이에 쓰는 공식·기호·순서·극성 ④ 적용 조건 ⑤ 이 문항에 적용하는 이유를 확인해요. 서로 이어지는 항목은 한 문장에 묶어요. 정성 문항은 정의·판단 기준으로 답하고, 서로 다른 판단이 필요한 소문항은 구분해요. 답을 바꾸는 극성·엣지·초기 상태·비동기 우선순위는 처음 적용하는 곳에 명시해요.

예를 들어 JK를 T로 쓰는 문항의 recall에는 “유지와 반전에는 JK 표의 00과 11만 필요해요”를, start에는 “J=K=T로 연결해요”를 둬요. 풀이의 표는 두 출력을 보여 주고 검산은 T=1에서 하강 엣지를 여러 번 넣어 Q를 확인해요. 작도 문항은 핀 선택과 되먹임 방향을 설명하고 완성 연결표와 그림에서 필요한 넷을 모두 확인하게 해요.

cue가 있으면 직계 div.sum[hidden]의 첫 문단은 `<p><strong>떠올릴 것:</strong> 같은 cue</p>`로 유지해요. 직계 div.sum[hidden]에 기존 시작 방법·핵심 판단·검산과 함께 본문의 핵심 개념/공식을 짧게 담은 `<p data-summary="recall">...</p>`를 정확히 하나 둬요. 제목·hidden·aria-hidden=true 텍스트만 있는 recall/요약은 본문이 아니에요. 본문 풀이를 details나 hidden으로 접지 않아요.

새 그림은 problem-explanations/figures/<name>.svg에 직접 제작해요. viewBox/title, 최소 18px 라벨과 양쪽 테마 대비를 확인해요. 기존 직접 제작 SVG 재사용은 가능해요. 발행 그림 경로는 .pack/problem-explanations/figures/.. 또는 기존 .pack/figures/..예요. 표는 table-wrap 텍스트 표로 쓰고 해석·주의 문장은 밖에 둬요. 렌더러는 표를 table-card로 감싸며 기존 wrap·값·빈칸·병합 셀과 명시적 카드를 보존해요.

독립 식은 설명과 문단을 분리해요. 렌더러가 식만 있는 일반 부울식/LaTeX p를 equation-card로 감싸요. 감지되지 않는 식은 `<div class="equation-card" role="group" aria-label="수식">`로 명시해요. 식 번호·내용은 보존하고 해석·조건·주의는 카드 밖에 써요.


### 문제설명 표 배치

`problem-explanations/table-layout.json`(version=1)에 모든 표를 `<문항ID>/<original|conditions|ask|explanation>/<0부터 순번>` key로 기록한다. expected_headers는 원래 최하위 열 머리글, columns는 role(index/control/input/intermediate/output/description), kind(signal/bus/expression/text/connector/index), 한국어 group 및 선택적 min_rem이다. 이름으로 역할을 추측하지 않는다. boundaries는 left(왼쪽 열의 0부터 번호)와 kind(major/minor)로 명시한다.

signal은 같은 표에서 같은 폭(하한 3rem), bus/수식은 내용 기반으로 줄바꿈 없이, text는 가용 폭을 공유한다. 경계 여백은 major 양쪽 0.5rem씩, minor 양쪽 0.25rem씩 기본 여백에 더한다. 짧은 표는 필요한 폭만 쓴다. 같은 열 구성의 빈 표·완성 표는 같은 pair를 지정하여 너비를 공유한다. 열 구성이 다르면 pair를 지정하지 않는다. 겹치는 병합 셀·머리글 불일치는 빌드 오류다. 그룹 머리글은 생성기가 추가하고 MD에는 원래 행만 내보낸다.

기존 팩은 explain-stage의 `--sync-explanation-template`으로 표시된 문제설명 CSS 블록만 동기화한다. 관리 대상 표의 첫 열 최소 폭은 해제하며 모바일 가로 스크롤은 table-card 한 곳만 사용한다. 글자 축소·열 숨김·간격용 빈 열은 금지한다. JSON 없는 legacy 입력은 종전 표를 보존한다.
