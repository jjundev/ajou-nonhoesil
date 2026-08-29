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

1. **주차·명세·결선도 확인.** `<실험NN>/체크리스트/명세.md` 가 없으면 거절하고
   `init-lab-experiment` 또는 명세 작성(교안 판독)을 안내한다. `<실험NN>/결선도/netlist.md`
   가 없으면 §3 의 `check_netlist` 가 "결선도 netlist 파일이 없다" error 를 내는데,
   그 자리까지 미루지 않고 여기서 먼저 정직하게 보고하고 멈춘다 — **회로 결선도
   절(§섹션별 재료)은 이 파일 없이는 채울 근거가 없다.** 없는 근거를 지어내지
   않는다는 §절대 규칙 5 와 같은 이유다. netlist.md 를 만드는 자동 생성 스킬은
   없으므로, 교안 회로도를 vision 으로 직접 읽어 먼저 만들도록 안내한다.

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
   spec = parse_spec('<실험NN>/체크리스트/명세.md')
   findings = (validate.validate_spec(spec)
               + validate.check_netlist('<실험NN>/결선도/netlist.md', spec))
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

6. **md 저장.** `<실험NN>/output/<실험NN>_예비보고서.md` 에 쓴다. 별도
   markdown→HTML 라이브러리는 쓰지 않는다 — 본문 HTML 은 직접 작성한다
   (①과 동일 원칙).

7. **조 편성 확인 → 표지 여부 분기 (결정만 한다).** 실제 표지 생성·병합은
   **10단계로 미룬다.** 예전에는 이 단계에서 바로 합쳤는데, 그 뒤 8단계가
   본문을 **같은 파일명**으로 다시 렌더·변환하면서 방금 합친 표지를 조용히
   덮어썼다 — 병합은 반드시 이 스킬이 그 경로에 쓰는 **마지막** PDF 작업이어야
   한다.

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   info = config.load_course_info(config.find_project_root(Path('.')))
   print('미확정:', config.missing_identity(info) or '없음')
   "
   ```

   판정은 ⑥ `make-lab-report-cover` 1b 단계와 **같은 함수**를 쓴다 — 두 곳이
   따로 판정하면 한쪽만 고쳐지고 다른 쪽이 `None` 을 표지에 찍는다.

   - **`미확정: 없음` 이면(조 편성 확정):** 표지가 필요하다고 기록해 둔다.
     생성·병합은 10단계에서 한다.
   - **하나라도 `~` 면(조 편성 미확정):** 표지를 만들지 않는다. 본문 서두에
     "표지는 조 편성 확정 후 결합 예정" 안내를 (헤딩이 아닌 인용문/문단으로)
     남긴다 — 안내 문장이 `#` 로 시작하면 섹션으로 오인돼 ⑤ 검증을 오염시킨다.

8. **HTML 렌더 + PDF 변환 (본문).** `template.html` 의 4개 placeholder
   (`{{TITLE}}`, `{{COURSE}}`, `{{DATE}}`, `{{CONTENT}}`) 를 채운다. `COURSE`·
   `DATE`·`chrome` 은 한 번에 읽는다.

   **HTML 은 반드시 `<실험NN>/output/<실험NN>_예비보고서.html` 자리에 만들고 그
   자리에서 PDF 로 변환한다 — 스크래치패드 등 다른 디렉토리에서 렌더하지 않는다.**
   `{{CONTENT}}` 안의 상대 경로(브레드보드 이미지 `../../.claude/assets/...`)는
   **HTML 파일이 실제로 놓인 위치** 기준으로 풀린다. 다른 곳에서 렌더해 PDF 로만
   `output/` 에 복사하면 이미지 경로가 풀리지 않아 그림이 깨진 채 PDF 로 굳는데,
   `extract_text()` 로는 이 결함이 전혀 보이지 않는다 — 실제로 이렇게 커밋된 적이
   있다(§8b 가 이걸 기계로 잡는다).

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
   html_to_pdf('<실험NN>/output/<실험NN>_예비보고서.html',
               '<실험NN>/output/<실험NN>_예비보고서.pdf',
               chrome=info.get('chrome') or DEFAULT_CHROME)
   "
   ```

   **`chrome=` 를 반드시 넘긴다** — 안 넘기면 `과목정보.md` 의 `chrome` 필드가
   선언만 되고 아무 효과가 없다 (⑥·② 와 같은 규칙). 실패하면 에러를 그대로
   보여주고 **HTML 은 남긴다.**

8b. **렌더된 HTML 을 검사한다.** 보고서 본문은 사람(또는 에이전트)이 마크다운을
    HTML 로 옮기므로, 산문의 코드 스팬만 `<code>` 로 바꾸고 **표 셀을 빠뜨리는**
    실수, 그리고 위 §8 규칙을 어겨 그림이 깨지는 실수가 실제로 일어난다. 둘 다
    텍스트 추출로는 안 보이므로 기계로 잡는다.

    ```bash
    python3 -c "
    from scripts.lab import validate
    html = '<실험NN>/output/<실험NN>_예비보고서.html'
    for f in validate.check_rendered_html(html) + validate.check_embedded_images(html):
        print(f)
    "
    ```

    기대: 출력 없음. 백틱·`**` 가 남았다고 나오면 **표 셀을 포함해 모든 텍스트
    노드**의 인라인 마크다운을 다시 확인한다 — 산문만 고치고 표를 빠뜨리면 이
    검사를 다시 통과하지 못한다. 이미지 오류가 나오면 §8 의 위치 규칙을 어긴
    것이다. 둘 다 고치고 PDF 를 다시 낸다.

9. **A4 실측 (본문 PDF).** 이 시점의 `<실험NN>_예비보고서.pdf` 는 아직 본문뿐이다
   (표지가 필요해도 10단계 전에는 합쳐지지 않는다).

   ```bash
   python3 -c "
   from pypdf import PdfReader
   for p in PdfReader('<실험NN>/output/<실험NN>_예비보고서.pdf').pages:
       print(round(float(p.mediabox.width)/72*25.4,1),
             round(float(p.mediabox.height)/72*25.4,1))
   "
   ```

10. **표지 병합 — 이 스킬이 최종 경로에 쓰는 마지막 PDF 작업.** 7단계 판정이
    "조 편성 확정"이었을 때만 한다.

    - **조 편성 미확정이었으면 이 단계를 건너뛴다** — 7단계에서 이미 본문에
      "표지 결합 예정" 안내를 남겼다. `<실험NN>_예비보고서.pdf` 는 지금
      상태(본문만)가 최종본이다.
    - **조 편성이 확정이었으면:** ⑥ `make-lab-report-cover` 로
      `<실험NN>/output/<제목> 표지.pdf` 를 만든 뒤, 8단계가 낸 본문 PDF 와
      페이지 단위로 합쳐 **같은 파일명에 덮어쓴다:**

      ```bash
      python3 -c "
      from pypdf import PdfReader, PdfWriter
      writer = PdfWriter()
      for src in ['<실험NN>/output/<제목> 표지.pdf',
                  '<실험NN>/output/<실험NN>_예비보고서.pdf']:
          writer.append(PdfReader(src))
      writer.write('<실험NN>/output/<실험NN>_예비보고서.pdf')
      "
      ```

      **이후 어떤 단계도 이 경로에 다시 쓰지 않는다.** 8단계로 되돌아가
      PDF 를 다시 내야 하면(예: 11단계에서 본문 누락이 발견됐다면), 8·8b·9
      를 다시 거쳐 본문을 새로 낸 **다음** 이 10단계를 다시 실행해 표지를
      다시 합친다 — 합친 뒤 상태에 본문만 다시 덧씌우지 않는다.

11. **⑤ 로 검증하고 error 0 까지 반복한다.** (`.md` 를 보므로 표지 병합
    여부와 무관하다.)

    ```bash
    python3 -c "
    from pathlib import Path
    from scripts.lab import config, validate
    root = config.find_project_root(Path('.'))
    fmt = config.load_report_format(root)
    for f in validate.check_report_sections('<실험NN>/output/<실험NN>_예비보고서.md', fmt.pre):
        print(f)
    " | tee <실험NN>/output/pre_review_round1.md
    ```

    출력이 없으면 모든 섹션이 존재하는 것이다. 누락이 나오면 본문을 고치고
    `round2`, `round3`... 로 다시 돌린다 — 8단계부터 다시 돌면 10단계(표지
    병합)도 다시 돌아야 한다는 뜻이다.

12. `과목정보.md` 의 `ai_usage_log` 가 `~` 가 아니면 그 경로에 로그 한 줄을
    남긴다. `~` 면 아무것도 하지 않는다.

13. **결과 안내.** md·pdf 링크, 섹션 검증 결과(error 0 여부), 표지 결합 여부를
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
| 실험 부품 | 명세 `ics` + `ic칩.txt` + 핀아웃 이미지. **그 주 명세의 `items[].device` 를 먼저 확인한다** — `LED` 면 330Ω 직렬·미사용핀 처리를 포함하고, `oscilloscope`·`DMM`·`7segment` 등이면(예: 3주차 실험2 CMOS 특성처럼 `capture` 중심 실험) LED·저항 서술 대신 그 장비를 재료로 쓴다 |
| 실험 과정 및 예상 결과 | 명세의 표 전부 + `source` 각주 |
| 회로 결선도 | `<실험NN>/결선도/netlist.md` 표 + 크롭된 브레드보드 |
| 출처 및 참고문헌 | 교안 쪽 번호, 데이터시트, 이론 교재. **실제로 본 것만** |

`ic칩.txt` 처럼 원천 자료 자체에 오류가 있을 수 있다 — 발견하면 조용히 정정해
쓰지 말고, 무엇을 왜 정정했는지 각주로 남긴다 (§절대 규칙 5 의 연장).

## 비-목표

- 결과를 예측해 실험 결과 섹션을 채우지 않는다 (④의 영역이다).
- 고찰을 쓰지 않는다 (예보엔 없고, 결보에서도 본인 경험이 재료다).
- 표지를 이 스킬 안에서 새로 디자인하지 않는다 (⑥ `make-lab-report-cover` 의
  영역이다). 조 편성이 미확정이면 표지 없이 본문만 내고, 결합은 조 편성 확정
  이후로 미룬다 — 표지를 억지로 채우지 않는다.
