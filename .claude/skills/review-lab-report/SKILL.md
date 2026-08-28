---
name: review-lab-report
description: 논리회로실험 명세·결선도·예비보고서·결과보고서를 검증하고 라운드별 리뷰 문서를 남긴다. 사용자가 "2주차 예비보고서 검토", "명세 검증해줘", "보고서 리뷰", "결과보고서 확인해줘" 등을 요청하거나 /review-lab-report 를 호출할 때 사용한다. 진리표 부울식 역검산, 행 수 대조, source·encoding 누락, netlist 의 VCC/GND/미사용핀 누락, 그리고 `.claude/보고서양식.md` 기준 섹션 대조를 수행한다.
---

# review-lab-report

`scripts/lab/validate.py` 를 불러 검증하고, 결과를 라운드 문서로 남긴다.
**이 스킬은 판단을 새로 만들지 않는다** — 검사 규칙은 전부 코드에 있고 테스트로 고정돼 있다.

## 인자

`<N주차> [pre|result] [round<N>]`

- 주차 토큰이 없으면 한 줄로 되묻고 중단한다.
- `pre`/`result` 가 없으면 `<N>주차/output/` 을 보고 추론한다. 둘 다 있으면 되묻는다.
- `round<N>` 이 없으면 기존 `*_review_round*.md` 중 최대 번호 + 1 을 쓴다.

## 실행 절차

1. **주차 폴더 확인.** `<N>주차/` 가 없으면 **거절하고** `init-lab-week` 를 안내한다.
   폴더를 만들어 주지 않는다.

2. **명세·결선도 검증.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab.spec_parser import parse_spec, SpecError
   from scripts.lab import validate
   try:
       spec = parse_spec('<N>주차/체크리스트/명세.md')
   except SpecError as e:
       print('SPEC-ERROR:', e); raise SystemExit(1)
   for f in validate.validate_spec(spec):
       print(f)
   for f in validate.check_netlist('<N>주차/결선도/netlist.md', spec):
       print(f)
   "
   ```

   `SpecError` 가 나오면 그것을 **첫 번째 finding 으로 보고하고** 나머지 검사는 건너뛴다.

3. **보고서 섹션 대조.** **반드시 `.claude/보고서양식.md` 를 기준으로 한다.**
   목차를 스킬에 하드코딩하지 않는다 — 양식은 연도마다·학생마다 다르고
   이번 학기 것이 미확정이다 (R1).

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config, validate
   root = config.find_project_root(Path('.'))
   fmt = config.load_report_format(root)
   sections = fmt.pre if '<pre|result>' == 'pre' else fmt.result
   for f in validate.check_report_sections('<보고서 경로>', sections):
       print(f)
   "
   ```

4. **코드가 못 보는 것을 사람이 본다.** 아래는 판정하지 말고 **질문으로** 남긴다.

   | 항목 | 왜 코드로 못 하나 |
   |---|---|
   | 고찰이 본인 경험인가 | 배운 점은 학생 것이다. 지어내면 안 된다 |
   | 교안 회로도와 netlist 위상이 맞는가 | PDF 벡터 판독이 필요하다 |
   | 예상값 `source` 가 실제로 그 쪽에 있는가 | 쪽 번호 대조는 사람이 |
   | 표기가 R5·R6 을 지키는가 | 오버바 승격 범위는 문맥 판단이다 |

5. **라운드 문서 작성.** `<N>주차/output/<pre|result>_review_round<N>.md` 에 쓴다.

   ```markdown
   # <N>주차 <예비|결과>보고서 검토 — round<N>

   ## 자동 검사 (scripts/lab/validate.py)

   - ✗ error 3건 / ! warn 1건
   - (findings 를 그대로 나열)

   ## 사람이 확인할 것

   - (§4 표의 항목 중 해당하는 것)

   ## 판정

   - [ ] 제출 가능
   - [x] 수정 필요 — error 가 남아 있다
   ```

6. **error 가 0 이 될 때까지 반복한다.** warn 은 남겨도 되지만 **왜 남기는지 한 줄** 적는다.

## 비-목표

- 보고서를 고쳐 쓰지 않는다. 지적만 한다 (수정은 ③·④ 의 일이다).
- 검사 규칙을 이 문서에 새로 적지 않는다. 규칙은 `validate.py` 에 있고
  거기에 테스트가 붙어 있다. 새 규칙이 필요하면 **테스트부터** 쓴다.
