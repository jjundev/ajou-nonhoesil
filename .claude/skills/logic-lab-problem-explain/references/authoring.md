# 문제에서 방법을 떠올리는 설명 저작

본문·제목·요약·캡션은 짧고 다정한 '~해요'체로 써요. 정의·성립 조건·인과와 원문 식·기호는 생략하거나 바꾸지 않아요. 문제 읽기(원문/조건/구할 것/그림)는 문제지 payload에서 자동으로 가져오므로 추가 조각은 article/h1 없이 작성해요.

v2에서는 다음 직계 data-explanation 구역을 각각 하나씩 이 순서로 둬요.

- understand(eli5): 무엇을 하는 문제인지, 기호의 뜻과 쉬운 직관.
- recall(formal): 제목은 '이 문제를 봤을 때 떠올릴 개념과 공식'. 아래 다섯 의미 기준을 연결해요.
- start(formal): 이 문제에서 실제로 쓰는 첫 식·첫 행·작은 입력 예와 {{NOTE_HREF}}#토픽ID 개념 링크.
- solve(formal): 모든 소문항의 단계별 판단 이유와 완성 표·식·회로.
- verify(formal): 최종 답과 구체적인 독립 계산/검산 방법.
- pitfall(warn): 문항의 실수와 이유. disputed는 '답안 충돌', unresolved는 '정답 미확정' 경고 및 적용 조건을 보존해요.
- retry(formal): 설명을 닫고 재현할 순서 1~3개의 li.

recall의 다섯 의미 기준은 ① 원문 표현·조건 중 방법 선택의 단서 ② 그 단서로 떠올릴 개념의 뜻 ③ 필요한 공식·기호의 의미와 비트 순서/극성 ④ 공식·판단이 성립하는 조건 ⑤ 이 문항에서 적용하는 이유예요. 정성 문항은 정의·판단 기준으로 설명하고 수식을 강제하지 않아요. 공통 개념은 한 번 설명하되 서로 다른 개념이 필요한 소문항은 구분해요. 개념 개수는 고정하지 않아요. recall은 선택 근거, start는 실제 풀이의 첫 실행이므로 긴 개념 설명을 반복하지 않아요.

아래는 원문 대조 후 사용하는 형식 예예요. 실제 문제 조건을 대신하지 않아요.

```html
<div class="layer formal" data-explanation="recall">
  <span class="layer-title">이 문제를 봤을 때 떠올릴 개념과 공식</span>
  <p>'입력 하나만 켜진다'는 조건에서 one-hot 입력의 인코더를 떠올려요. 켜진 선의 번호를 이진 코드로 바꿔요.</p>
  <p>A=D2+D3, B=D1+D3에서 A는 상위 비트, B는 하위 비트예요. '+'는 논리 OR를 뜻해요.</p>
  <p>입력 둘 이상이 동시에 켜지면 이 간단한 식이 우선순위를 정해 주지는 않아요. NAND 지정 조건은 드모르간 법칙으로 연결해요.</p>
</div>
```

직계 div.sum[hidden]에 기존 시작 방법·핵심 판단·검산과 함께 본문의 핵심 개념/공식을 짧게 담은 `<p data-summary="recall">...</p>`를 정확히 하나 둬요. 제목·hidden·aria-hidden=true 텍스트만 있는 recall/요약은 본문이 아니에요. 본문 풀이를 details나 hidden으로 접지 않아요.

새 그림은 problem-explanations/figures/<name>.svg에 직접 제작해요. viewBox/title, 최소 18px 라벨과 양쪽 테마 대비를 확인해요. 기존 직접 제작 SVG 재사용은 가능해요. 발행 그림 경로는 자료/problem-explanations/figures/.. 또는 기존 자료/figures/..예요. 표는 table-wrap 텍스트 표로 쓰고 해석·주의 문장은 밖에 둬요. 렌더러는 표를 table-card로 감싸며 기존 wrap·값·빈칸·병합 셀과 명시적 카드를 보존해요.

독립 식은 설명과 문단을 분리해요. 렌더러가 식만 있는 일반 부울식/LaTeX p를 equation-card로 감싸요. 감지되지 않는 식은 `<div class="equation-card" role="group" aria-label="수식">`로 명시해요. 식 번호·내용은 보존하고 해석·조건·주의는 카드 밖에 써요.
