---
name: prep-lab-checklist
description: 논리회로실험 주차 명세에서 실험실에 들고 갈 체크리스트를 만든다. 인쇄용 A4 PDF 와 전사용 기록.md 를 항상 쌍으로 낸다. 사용자가 "2주차 체크리스트", "실험실 들고 갈 거 만들어줘", "뭐 측정해야 해", "체크리스트 뽑아줘" 등을 요청하거나 /prep-lab-checklist 를 호출할 때 사용한다. 결선 절차·진리표 확인 칸·브레드보드 작도면·사진 대조란을 포함한다.
---

# prep-lab-checklist

`<N>주차/체크리스트/명세.md` 하나에서 실험실용 산출물 전부를 파생한다.

**PDF 와 md 를 항상 쌍으로 만든다.** 태블릿에 PDF 를 띄워 펜으로 채우고,
끝나면 `기록.md` 로 전사한다(④가 vision 으로 돕는다).

## 실행 절차

1. **주차 폴더·명세 확인.** `<N>주차/체크리스트/명세.md` 가 없으면 **거절한다.**
   폴더가 없으면 `init-lab-week` 를, 명세가 없으면 교안 판독이 먼저임을 안내한다.
   **명세를 지어내지 않는다.**

2. **먼저 검증한다.** 틀린 진리표를 인쇄해서 실험실에 들고 가는 것이 최악이다.

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

   **error 가 하나라도 있으면 인쇄하지 말고 보고한다.** warn 은 알리고 진행한다.

3. **기록 템플릿 파생.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab.record import derive_record
   from scripts.lab.spec_parser import parse_spec
   spec = parse_spec('<N>주차/체크리스트/명세.md')
   Path('<N>주차/체크리스트/기록.md').write_text(derive_record(spec), encoding='utf-8')
   "
   ```

4. **인쇄본 렌더 + PDF.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.render import render_checklist
   from scripts.lab.spec_parser import parse_spec
   from scripts.lab.html2pdf import DEFAULT_CHROME, html_to_pdf
   root = config.find_project_root(Path('.'))
   info = config.load_course_info(root)
   spec = parse_spec('<N>주차/체크리스트/명세.md')
   netlist = Path('<N>주차/결선도/netlist.md').read_text(encoding='utf-8')
   tmpl = Path('.claude/skills/prep-lab-checklist/template.html').read_text(encoding='utf-8')
   out = Path('<N>주차/체크리스트/체크리스트.html')
   out.write_text(render_checklist(spec, netlist, tmpl), encoding='utf-8')
   html_to_pdf(out, out.with_suffix('.pdf'),
               chrome=info.get('chrome') or DEFAULT_CHROME)
   "
   ```

   **`chrome=` 를 반드시 넘긴다** — 안 넘기면 `과목정보.md` 의 `chrome` 필드가
   선언만 되고 아무 효과가 없다 (⑥ 표지 스킬과 같은 규칙이다).

5. **A4 실측.** 아래를 돌려 210×297mm 인지 확인한다. 아니면 CSS 를 고치고 다시 낸다.

   ```bash
   python3 -c "
   from pypdf import PdfReader
   for p in PdfReader('<N>주차/체크리스트/체크리스트.pdf').pages:
       print(round(float(p.mediabox.width)/72*25.4,1),
             round(float(p.mediabox.height)/72*25.4,1))
   "
   ```

6. **결과 안내.** `기록.md` · `체크리스트.pdf` 링크와 표 개수·행 수를 한 줄로.

## 인쇄물 구성 (이 순서를 지킨다)

1. **결선 절차** — VCC/GND/미사용핀 박스가 맨 위. 배선을 끝내야 표를 채운다
2. **표** — kind 별 레이아웃, 각 표에 `출처` 노출
3. **결선도 | 회로 2열 대조** — 항목마다
4. **브레드보드 작도면** — netlist 가 요구하는 행 수만큼 크롭

## kind 별 칸

| kind | 기록 칸 | 사진 |
|---|---|---|
| `truth-table` | 행마다 세로 정렬 확인 칸, 예상값 좌측 병기 | 항목당 완성 회로 1장 + **불일치 행 필수** |
| `stepped` | 스텝이 행. 명세에서 빈 열이 채울 칸 | **스텝마다** (진행이 요점이다) |
| `capture` | 스케치 격자 + 캡션 줄 | 사진 자체가 결과물 |

사진 파일명은 `T<n> row<m>.jpg` 로 찍는다 — ④가 T번호로 표에 자동 배치한다.

## 비-목표

- 명세를 만들지 않는다 (교안 판독은 사람의 일이다).
- 자동 배선도를 그리지 않는다 (netlist + 빈 브레드보드만 준다).
- 캐시 신선도 로직(mtime 비교·SOURCES 블록)을 만들지 않는다.
  소스가 고정이므로 그냥 다시 만드는 게 싸고 안전하다.
