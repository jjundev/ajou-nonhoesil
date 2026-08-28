---
name: write-pre-report
description: 논리회로실험 예비보고서를 `.claude/보고서양식.md` 의 섹션 목록대로 작성하고 표지와 묶어 PDF 로 낸다. 사용자가 "2주차 예비보고서 써줘", "예보 작성", "예비보고서 만들어줘" 등을 요청하거나 /write-pre-report 를 호출할 때 사용한다. 실험 목적·이론·부품·과정 및 예상 결과·결선도·참고문헌을 명세와 교안에 근거해 채운다.
---

# write-pre-report

## 절대 규칙

1. **섹션 목록을 이 문서에 적지 않는다.** `.claude/보고서양식.md` 에서 읽는다.
   양식은 연도마다·학생마다 다르고 이번 학기 것이 미확정이다 (R1).
2. **예상값의 출처를 항상 밝힌다.** 명세의 `source` 를 각주로 노출한다.
3. **자동 배선도를 그리지 않는다.** netlist 표 + 크롭된 브레드보드 템플릿까지다.
4. **과거 제출본을 베끼지 않는다.** 권위 5순위 코퍼스이고 알려진 오염이 있다.
   참고하려면 다수결로, 연도를 밝히고.
5. **없는 근거를 지어내지 않는다.** 예: `74HC08`·`74HC32` 핀아웃 데이터시트는
   저장소에 없다. 표준 DIP-14 배치임을 밝히고 실물 대조를 권고한다.

## 실행 절차

1. **주차·명세 확인.** `<N>주차/체크리스트/명세.md` 가 없으면 거절하고
   `init-lab-week` 또는 명세 작성(교안 판독)을 안내한다.

2. **양식 로드** (§절대 규칙 1). `repeat: per-item` 인 섹션은 항목마다 반복한다.

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   root = config.find_project_root(Path('.'))
   fmt = config.load_report_format(root)
   print('프리셋:', fmt.preset)
   for s in fmt.pre:
       flag = ' (항목마다 반복)' if s.repeat == 'per-item' else ''
       skip = '' if s.generate else '  [생성 안 함]'
       print(f'  - {s.name}{flag}{skip}')
   "
   ```

3. **명세 로드 및 검증.**

   ```bash
   python3 -c "
   from scripts.lab.spec_parser import parse_spec
   from scripts.lab import validate
   spec = parse_spec('<N>주차/체크리스트/명세.md')
   findings = (validate.validate_spec(spec)
               + validate.check_netlist('<N>주차/결선도/netlist.md', spec))
   print('\n'.join(str(f) for f in findings) or '문제 없음')
   "
   ```

   **error 가 있으면 작성을 멈추고 보고한 뒤 사용자 판단을 기다린다.** warn 은
   알리고 진행한다.

4. **섹션별 작성.** 아래 §섹션별 재료 표를 따른다. `role: reference` 표는
   실험 이론 절의 재료이지 실험 과정 절의 기록 대상이 아니다 — ②
   `prep-lab-checklist` 가 체크리스트·`기록.md` 양쪽에서 이미 같은 표를
   제외하는 것과 같은 구분이다. `kind: capture` 표는 셀 표 대신 `expected`
   산문을 싣는다.

5. **보수 표기 (R5).** 저작은 `'`, 부울식만 오버바로 승격한다.

   ```bash
   python3 -c "
   from scripts.lab.notation import to_overbar_html
   print(to_overbar_html(\"(A'·B)'\"))   # 중첩 스코프도 지원한다
   "
   ```

   **표 헤더·신호명·셀 값에는 절대 부르지 않는다** — `normalize_cell` 이 돌려주는
   `CellValue` 를 넘기면 `TypeError` 가 난다. 이건 버그가 아니라 안전장치다.

6. **md 저장.** `<N>주차/output/<N>주차_예비보고서.md` 에 쓴다. 별도
   markdown→HTML 라이브러리는 쓰지 않는다 — 본문 HTML 은 직접 작성한다
   (①과 동일 원칙).

7. **조 편성 확인 → 표지 여부 분기.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   info = config.load_course_info(config.find_project_root(Path('.')))
   print('team=', info.get('team'), '/ ids=', info.get('student_ids'),
         '/ names=', info.get('student_names'))
   "
   ```

   - **셋 다 `~` 가 아니면(조 편성 확정):** ⑥ `make-lab-report-cover` 로
     `<N>주차/output/<제목> 표지.pdf` 를 먼저 만든다. 본문을 `template.html` 로
     렌더해 `<N>주차/output/<N>주차_예비보고서.pdf` 로 변환한 뒤, 두 PDF 를
     페이지 단위로 합쳐 하나로 낸다:

     ```bash
     python3 -c "
     from pypdf import PdfReader, PdfWriter
     writer = PdfWriter()
     for src in ['<N>주차/output/<제목> 표지.pdf',
                 '<N>주차/output/<N>주차_예비보고서.pdf']:
         writer.append(PdfReader(src))
     writer.write('<N>주차/output/<N>주차_예비보고서.pdf')
     "
     ```

   - **하나라도 `~` 면(조 편성 미확정):** 표지를 만들지 않는다. 본문만 PDF 로
     내고, 본문 서두에 "표지는 조 편성 확정 후 결합 예정" 안내를 (헤딩이 아닌
     인용문/문단으로) 남긴다 — 안내 문장이 `#` 로 시작하면 섹션으로 오인돼
     ⑤ 검증을 오염시킨다.

8. **HTML 렌더 + PDF 변환.** `template.html` 의 4개 placeholder
   (`{{TITLE}}`, `{{COURSE}}`, `{{DATE}}`, `{{CONTENT}}`) 를 채운다. `COURSE`·
   `DATE`·`chrome` 은 한 번에 읽는다:

   ```bash
   python3 -c "
   from pathlib import Path
   from datetime import datetime
   from scripts.lab import config
   info = config.load_course_info(config.find_project_root(Path('.')))
   print(info['course'])
   print(datetime.now().strftime(info['date_format']))
   print(info.get('chrome'))
   "
   ```

   ```bash
   python3 -c "
   from scripts.lab import config
   from scripts.lab.html2pdf import DEFAULT_CHROME, html_to_pdf
   info = config.load_course_info(config.find_project_root(Path('.')))
   html_to_pdf('<N>주차/output/<N>주차_예비보고서.html',
               '<N>주차/output/<N>주차_예비보고서.pdf',
               chrome=info.get('chrome') or DEFAULT_CHROME)
   "
   ```

   **`chrome=` 를 반드시 넘긴다** — 안 넘기면 `과목정보.md` 의 `chrome` 필드가
   선언만 되고 아무 효과가 없다 (⑥·② 와 같은 규칙). 실패하면 에러를 그대로
   보여주고 **HTML 은 남긴다.**

9. **A4 실측.**

   ```bash
   python3 -c "
   from pypdf import PdfReader
   for p in PdfReader('<N>주차/output/<N>주차_예비보고서.pdf').pages:
       print(round(float(p.mediabox.width)/72*25.4,1),
             round(float(p.mediabox.height)/72*25.4,1))
   "
   ```

10. **⑤ 로 검증하고 error 0 까지 반복한다.**

    ```bash
    python3 -c "
    from pathlib import Path
    from scripts.lab import config, validate
    root = config.find_project_root(Path('.'))
    fmt = config.load_report_format(root)
    for f in validate.check_report_sections('<N>주차/output/<N>주차_예비보고서.md', fmt.pre):
        print(f)
    " | tee <N>주차/output/pre_review_round1.md
    ```

    출력이 없으면 모든 섹션이 존재하는 것이다. 누락이 나오면 본문을 고치고
    `round2`, `round3`... 로 다시 돌린다.

11. `과목정보.md` 의 `ai_usage_log` 가 `~` 가 아니면 그 경로에 로그 한 줄을
    남긴다. `~` 면 아무것도 하지 않는다.

12. **결과 안내.** md·pdf 링크, 섹션 검증 결과(error 0 여부), 표지 결합 여부를
    한 줄로.

## 섹션별 재료

**아래 표는 절 이름 목록이 아니라 내용별 재료 안내다.** 왼쪽 열은 오늘
`.claude/보고서양식.md` 의 `교집합` 프리셋에 있는 이름을 그대로 썼을 뿐이고,
실행 시 실제로 몇 개의 절을 무슨 이름으로 쓸지는 항상 §실행 절차 2 에서 읽은
`fmt.pre` 를 따른다 (§절대 규칙 1). 조교 안내로 절 이름이 달라져도 이 표는
"목적/이론/부품/과정/결선/출처"라는 개념 대응만 유지하면 되고, 실행 로직은
전혀 손댈 필요가 없다.

| 섹션 | 재료 |
|---|---|
| 실험 목적 | 교안 p2 "목적" 슬라이드 |
| 실험 이론 | 교안 이론 슬라이드 + `논회 강의노트/Ch*.pdf` + `docs/study/` + 명세의 **`role: reference` 표**(실험1 T6~T9 = 2입력 이론표, `encoding: H/L`). **`H/L` 을 `0/1` 로 바꾸지 말 것** |
| 실험 부품 | 명세 `ics` + `ic칩.txt` + 핀아웃 이미지. LED 330Ω·미사용핀 처리 포함 |
| 실험 과정 및 예상 결과 | 명세의 표 전부 + `source` 각주 |
| 회로 결선도 | `<N>주차/결선도/netlist.md` 표 + 크롭된 브레드보드 |
| 출처 및 참고문헌 | 교안 쪽 번호, 데이터시트, 이론 교재. **실제로 본 것만** |

`ic칩.txt` 처럼 원천 자료 자체에 오류가 있을 수 있다 — 발견하면 조용히 정정해
쓰지 말고, 무엇을 왜 정정했는지 각주로 남긴다 (§절대 규칙 5 의 연장).

## 비-목표

- 결과를 예측해 실험 결과 섹션을 채우지 않는다 (④의 영역이다).
- 고찰을 쓰지 않는다 (예보엔 없고, 결보에서도 본인 경험이 재료다).
- 표지를 이 스킬 안에서 새로 디자인하지 않는다 (⑥ `make-lab-report-cover` 의
  영역이다). 조 편성이 미확정이면 표지 없이 본문만 내고, 결합은 조 편성 확정
  이후로 미룬다 — 표지를 억지로 채우지 않는다.
