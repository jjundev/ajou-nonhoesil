# 퀴즈 유형 연습: 전체 저작의 필수 단계

새 팩 생성 또는 전체 갱신에서 기출 선별 다음에 적용한다. 다음 JSON은 저작 정책 요약이며 counts/apply_to/preserve_on을 manifest 필드로 복사하지 않는다.

```json
{
  "quiz_practice_version": 1,
  "counts": {"true_false": 4, "fill_blank": 3, "breadboard": 1, "short_answer": 2},
  "apply_to": ["new", "full_regeneration"],
  "preserve_on": ["rerender", "pdf_export", "navigation_only", "explanation_only"]
}
```

사용자가 2026-10-17 실험01~05 퀴즈에서 이 네 유형을 관찰했다. 이 사실은 유형 선택의 배경이며 개별 정답의 근거가 아니다. 10문항과 T/F의 참 2·거짓 2는 학습용 저작 기본값으로 실제 시험 비율이나 출제를 보장하지 않는다.

## 저작 순서

1. 현재 교안과 사용할 칩 자료를 직접 읽는다. 학습목표·기출이 다루는 개념·새 유형·근거 페이지를 RUN에 표로 기록한다. 교안의 `sw 인버터` 같은 표현은 뜻을 확인한 뒤 사용한다. 불명확한 약어를 추정해 출제하지 않는다.
2. 기존 기출·은행 고정 필드를 유지한다. 은행 예상문제의 개념 공백 기준은 그대로다. 자체 practice는 같은 개념을 새 유형으로 연습해도 된다. 기존 자체 문항과 조건이 같으면 ID를 재사용하고, 조건이 바뀌면 새 ID를 쓰며 대체 문항은 사유와 함께 비수록으로 남긴다.
3. 기존 included 문항 뒤에 T/F 4·빈칸 3·작도 1·서술형 2를 저작한다. 정해진 문장 10개를 복제하는 코드나 외부 출제 API를 만들지 않는다. 모든 새 문항은 kind=practice, question_type, scope=current, topics와 확인한 sources를 가진다. given_answer=null, bank_question_id 없음. ID 예: `q-qp-e07-tf-01`.
4. 정답을 독립 계산하고 조건·반례·진리표·답의 허용 범위를 검토한다. 확인한 뒤에만 answer_status=verified와 derived_answer를 쓴다. 자료나 답이 부족하면 held와 이유를 남긴다. 할당량이 부족하면 build/publish가 실패하므로 부족 유형과 근거를 보고하고 기존 팩을 보존한다.
5. 작도 회로·칩 명세·빈 보드·완성 보드·연결표를 만든다. 아래 그림 계약을 따른다.
6. 새 문항까지 모든 included 문항에 문제설명 v2의 일곱 layer와 sum을 저작한다. 기존 문제설명 스킬을 사용하고 ID·순서를 일치시킨다. schema_version=1, review_presentation_version=2, problem_explanation_version=2, quiz_practice_version=1이다.
7. 새 stage로 build/check, 내용·브라우저·그림 검토를 수행하고 publish 후 두 PDF를 다시 만든다. 구조 검사 통과를 내용 정확성으로 보고하지 않는다. 실제 독립 리뷰가 없으면 independent=self_review 또는 not_run이다. 검토 후 내용 변경은 관련 검토를 다시 수행한다.

## 유형별 문제와 해설

예시는 이상적인 모델의 작성 형태이며 실제 팩에서는 해당 실험의 교안·소자 조건으로 바꾼다. 힌트는 접근 단서만 주며 최종 답이나 완성 배선을 노출하지 않는다.

| question_type | 문제 예와 작성 기준 | solution.steps 필수 label과 답 |
|---|---|---|
| true_false | “이상적인 CMOS 인버터의 입력이 High이면 NMOS는 도통한다. T/F.”처럼 판단할 주장 하나와 조건을 명시 | `판정 근거`, `문장 확인`; answer의 순수 텍스트는 derived_answer와 같은 `T` 또는 `F`. F는 바른 문장, T는 성립 조건을 확인 |
| fill_blank | “이상적 CMOS 인버터 입력 High: (PMOS/NMOS)가 도통하고, (PMOS/NMOS)가 차단된다.” | `빈칸별 근거`; 순서대로 NMOS/PMOS와 이유·동의어 인정 범위. 복수 빈칸은 번호를 붙여 대응 |
| short_answer | “선택선이 있는 MUX의 기능과 출력이 결정되는 원리를 몇 문장으로 설명하시오.” | 모범 답과 `채점 핵심`, `허용 표현`; 기능·원리·인과를 채점 요소로 제시하고 동치 표현 인정 |
| breadboard | “주어진 회로도와 핀 명세를 사용해 빈 보드에 전원·입출력·배선을 작도하시오.” | `연결 기준`, `완성 결선도`; 완성 그림과 핀 연결표, 전원·GND·미사용 핀·극성 검토. IC 위치/홀 좌표가 달라도 전기적 넷과 부품 조건이 같으면 인정 |

공통 solution에는 비어 있지 않은 steps와 answer가 필요하다. 위 label은 JSON 계약이다. 제시된 정답·채점 요소가 교안과 맞는지는 사람이 읽어 검토한다. 최종 문제·해설 제목에는 “기출문제와 퀴즈 유형 연습” / “기출풀이와 퀴즈 유형 연습”, 새 문항 section에는 “퀴즈 유형 연습 — 자체 출제 · 유형”이 자동 표시된다. 기존 파일명은 유지한다.

## 작도 입력과 그림

회로도와 핀 번호·이름·역할 및 전원·부품 조건을 제공한다. IC 배치/방향은 학생이 정하는 것이 기본이다. 칩의 전원·미사용 핀 처리를 생략하거나 정답 핀 연결을 힌트에 주지 않는다.

conditions 안에 다음 구조를 쓴다. 실제 소자의 사용 핀과 전원 핀을 모두 채운다. 빈 보드를 problem_figures에 또 넣지 않고, 별도의 주어진 회로도 ID만 넣는다.

```html
<div class="table-wrap"><table class="chip-spec">
<thead><tr><th>핀</th><th>이름</th><th>역할</th></tr></thead>
<tbody><tr><td>1</td><td>A</td><td>입력</td></tr></tbody>
</table></div>
<div class="work-board"><img src="figures/questions/q-blank.png" alt="작도용 빈 브레드보드"></div>
```

빈 보드는 문제지 중앙에 100mm 너비·PDF 원본 종횡비 유지로 배치된다(최소 너비 90mm). 보드 자체가 작도 공간이다. 칩 명세는 패널에 남고 해설 DOM에서는 빈 보드만 제거된다. 원본 페이지의 여백·잭·홀·레일·글자를 포함한 양식 전체를 유지하고 자르거나 다시 그리지 않는다. 넘침을 숨기려고 보드를 축소하지 않는다.

**사용자 지정 양식(2026-10-17): 모든 퀴즈 작도 문항은 실험 번호와 관계없이 [v1 배포 PDF](../../../../강의노트/공지사항/Breadboard.pdf)를 그대로 사용한다.** v2 판형이나 `.claude/assets/Breadboard.jpg`로 대체하지 않는다. PDF 원본은 수정하지 않는다. 기존 보고서·결선도의 주차별 판형 정책은 그대로 유지한다.

`scripts.lab.review_pack.breadboard_template.template_png()`로 PDF 1쪽 전체를 300dpi PNG로 렌더링한다(반환값: png_bytes, width, height). 빈 보드는 이 PNG를 그대로 쓴다. registry의 SVG는 `viewBox="0 0 {width} {height}"`와 title을 두고, 직계 자식 `<image x="0" y="0" width="{width}" height="{height}" href="data:image/png;base64,..."/>`에 반환 PNG를 삽입한다. 이것은 양식을 보존하기 위한 명시적 예외이며 검사기는 이 원본 렌더링과 바이트가 같은 이미지 하나만 허용한다. 임의 스캔이나 다른 래스터 그림에는 예외를 적용하지 않는다. 완성 보드도 같은 PDF 배경 위에 부품·배선 벡터만 얹고, 그 합성 결과를 PNG로 출력한다. 회로도는 종전대로 벡터 SVG로 저작한다.

[breadboard-diagram](../../breadboard-diagram/SKILL.md)과 [v1 좌표 주의](../../breadboard-diagram/v1.md)를 읽는다. **배포 PDF와 기존 v1 JPG는 가로 홀 위치가 다르므로 JPG 좌표를 그대로 얹지 않는다.** 배포 PDF에서 홀·레일·잭 좌표를 측정하고 양식 좌표와 엔진 검증 좌표 사이의 대응을 기록한다. v2 geometry는 사용하지 않는다. 기존 엔진의 verify()/nets()로 IC·연결 넷을 검토한 뒤, PDF 위의 배선 끝점도 실제 홀과 일치하는지 따로 확대 확인한다. 회로도·빈 보드는 problem/none, 완성 보드는 solution/present다. 양식 PDF도 manifest.sources에 등록하고 source_refs에 1쪽을 기록한다. derivation에는 원본 경로·SHA256·300dpi 변환·좌표 대응을 기록하고, review_notes 및 SVG/PNG hash를 registry에 기록한다. 시각 확인 전에 review_status=pass를 쓰지 않는다.

완성 그림은 `완성 결선도` 단계 안의 등록 img로 넣고 읽을 수 있는 width를 지정한다. 연결 기준에는 모범 넷과 핀 연결표를 함께 둔다. 회로·명세·그림의 핀 번호/극성, 레일 분리, 전원·GND·미사용 입력, LED 방향·저항을 대조한다. 동등 넷은 인정하지만 학생 답안 자동 채점기는 추가하지 않는다.

## 적용 경계와 완료

기존 팩은 자동 소급 수정하지 않는다. rerender, PDF만 내보내기, 목차만 갱신, 문제설명만 갱신, 부분 수정은 기존 policy와 문항을 보존하며 새 문제를 추가하지 않는다. 다음 전체 재저작 때 같은 ID를 재사용해 10문항을 유지하고 누적 추가하지 않는다.

문제·해설·문제설명 HTML/MD에서 ID·순서와 조건이 같아야 한다. 문제 payload에는 solution/notes를 넣지 않는다. 작도 보드 1회 표시, 해설의 완성 그림과 최종 답, T/F·빈칸·서술형 대표 문항을 1280/375px·offline·A4 가로 PDF로 확인한다. data-ready=true, data-overflow='', 깨진 그림·수식·콘솔 오류 0을 요구한다. PDF에서 핀·홀·레일의 가독성을 확대 확인한다. 미실행 검사는 not_run이며 skip을 pass로 보고하지 않는다.
