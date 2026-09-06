---
name: prep-lab-checklist
description: 논리회로실험 주차 명세에서 실험실에 들고 갈 체크리스트를 만든다. 인쇄용 A4 PDF 와 전사용 기록.md 를 항상 쌍으로 낸다. 사용자가 "2주차 체크리스트", "실험실 들고 갈 거 만들어줘", "뭐 측정해야 해", "체크리스트 뽑아줘" 등을 요청하거나 /prep-lab-checklist 를 호출할 때 사용한다. 결선 절차·진리표 확인 칸·브레드보드 작도면·사진 대조란을 포함한다.
---

# prep-lab-checklist

`<실험NN>/체크리스트/명세.md` 하나에서 실험실용 산출물 전부를 파생한다.

**PDF 와 md 를 항상 쌍으로 만든다.** 태블릿에 PDF 를 띄워 펜으로 채우고,
끝나면 `기록.md` 로 전사한다(④가 vision 으로 돕는다).

## 실행 절차

0. **주차로 불렸으면 폴더를 코드로 옮긴다.** 사용자는 "2주차 …" 처럼 주차로
   부르는데 아래 절차의 경로는 `<실험NN>/` 이다. **매핑은 1:1 이 아니다** —
   실험4는 7주차다. 손으로 옮기지 말고 아래를 돌린다.

   ```bash
   python3 -c "
   from scripts.lab import config
   print(config.folder_for_week(<N>))
   "
   ```

   출력이 이후 모든 경로의 `<실험NN>` 이다. 사용자가 `실험N` 으로 불렀으면
   `config.experiment_dir(<N>)` 을 대신 쓴다. `ValueError` 가 나면(중간고사·범위
   밖) 그 메시지를 그대로 사용자에게 전하고 중단한다. 13~15주차는 `실험NN`
   대신 `프로젝트` 를 돌려준다 — 그 뒤로는 모든 경로에서 `<실험NN>/` 자리에
   `프로젝트/` 를 쓴다.

1. **주차 폴더·명세 확인.** `<실험NN>/체크리스트/명세.md` 가 없으면 **거절한다.**
   폴더가 없으면 `init-lab-experiment` 를, 명세가 없으면 `draft-lab-spec` 을
   안내한다. **명세를 지어내지 않는다.**

2. **먼저 검증한다.** 틀린 진리표를 인쇄해서 실험실에 들고 가는 것이 최악이다.

   ```bash
   python3 -c "
   from scripts.lab.spec_parser import parse_spec
   from scripts.lab.netlist_parser import parse_netlist
   from scripts.lab import validate
   spec = parse_spec('<실험NN>/체크리스트/명세.md')
   netlist = parse_netlist('<실험NN>/결선도/netlist.md')
   findings = (validate.validate_spec(spec)
               + validate.check_netlist('<실험NN>/결선도/netlist.md', spec)
               + validate.check_netlist_circuits(netlist, spec))
   print('\n'.join(str(f) for f in findings) or '문제 없음')
   "
   ```

   **error 가 하나라도 있으면 인쇄하지 말고 보고한다.** warn 은 알리고 진행한다.

   `parse_netlist` 가 `NetlistError` 를 던지면 그 결선도에 회로 메타가 없는
   것이다. **예외 메시지를 그대로 사용자에게 전하고 멈춘다** — 옛 방식으로
   대충 렌더하지 않는다. 백필 방법은 메시지가 담고 있고 계약은
   `docs/schema/lab-netlist-v2.md` 다.

3. **기록 템플릿 파생.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab.record import derive_record
   from scripts.lab.spec_parser import parse_spec
   spec = parse_spec('<실험NN>/체크리스트/명세.md')
   Path('<실험NN>/체크리스트/기록.md').write_text(derive_record(spec), encoding='utf-8')
   "
   ```

4. **인쇄본 렌더 + PDF.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.render import render_checklist
   from scripts.lab.spec_parser import parse_spec
   from scripts.lab.netlist_parser import parse_netlist
   from scripts.lab.html2pdf import DEFAULT_CHROME, html_to_pdf
   root = config.find_project_root(Path('.'))
   info = config.load_course_info(root)
   spec = parse_spec('<실험NN>/체크리스트/명세.md')
   netlist = parse_netlist('<실험NN>/결선도/netlist.md')
   tmpl = Path('.claude/skills/prep-lab-checklist/template.html').read_text(encoding='utf-8')
   out = Path('<실험NN>/체크리스트/체크리스트.html')
   out.write_text(render_checklist(spec, netlist, tmpl), encoding='utf-8')
   html_to_pdf(out, out.with_suffix('.pdf'),
               chrome=info.get('chrome') or DEFAULT_CHROME)
   "
   ```

   **`chrome=` 를 반드시 넘긴다** — 안 넘기면 `과목정보.md` 의 `chrome` 필드가
   선언만 되고 아무 효과가 없다 (⑥ 표지 스킬과 같은 규칙이다).

5. **인쇄본 자체 검사.** 마크다운 표기가 벗겨지지 않고 남는 경우가 있다 —
   실험02 인쇄본이 `**` 10개를 담은 채 커밋된 적이 있다. 이 절차가
   `check_rendered_html` 을 안 돌려서 아무도 못 봤다.

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import validate
   for f in validate.check_rendered_html(Path('<실험NN>/체크리스트/체크리스트.html')):
       print(f)
   "
   ```

   **error 가 0 이 아니면 인쇄하지 않는다** — 마크다운을 HTML 로 옮길 때 표
   셀을 빠뜨리면 인쇄본에 그대로 찍힌다.

6. **A4 실측.** 아래를 돌려 쪽 크기를 본다.

   **기대값은 `209.9 297.0` 이다.** Chrome 헤드리스가 A4 로 내는 mediabox 는
   `594.95996 × 841.91998pt` = `209.889 × 297.011mm` 로 고정이다 — 폭이 이름값
   210mm 보다 0.11mm 좁다. **이것은 결함이 아니다.** 2026-09 재설계 전후 PDF 가
   같은 값이었다. 210.0 을 맞추려고 CSS 를 건드리지 않는다. 이 값에서 눈에 띄게
   벗어날 때만(예: Letter 로 나와 215.9) `@page { size: A4 }` 를 확인하고 다시 낸다.

   ```bash
   python3 -c "
   from pypdf import PdfReader
   for p in PdfReader('<실험NN>/체크리스트/체크리스트.pdf').pages:
       print(round(float(p.mediabox.width)/72*25.4,1),
             round(float(p.mediabox.height)/72*25.4,1))
   "
   ```

7. **AI 활용 로그.** `과목정보.md` 의 `ai_usage_log` 가 `~` 가 아니면 그 경로에
   한 줄 추가한다(⑥·③·④ 와 같은 규칙). `~` 면 아무것도 하지 않는다. 이 스킬도
   저장소 안에 PDF 를 만드므로 빠뜨리면 그 값이 채워지는 순간 로그가 조용히
   불완전해진다.

8. **결과 안내.** `기록.md` · `체크리스트.pdf` 링크와 표 개수·행 수를 한 줄로.

## 인쇄물 구성 (이 순서를 지킨다)

**1. 공통면 (1쪽)** — 한 번만 보면 되는 것
- 전원 박스 (미사용 입력핀 플로팅 금지 문구 포함) + `kind` 별 범례 3줄
  (진리표 · 스텝표 · 파형)
- 오늘의 흐름 표 (회로 순서 · 이름 · 쓰는 IC · 기록할 표)
- 공통 규칙 (`kind: common`)
- 참조 핀아웃 표 (`kind: lookup`)
- 실험실 확인 체크박스 (`kind: open-issues`)
- `kind: sources` 는 **인쇄하지 않는다** — ③ 의 참고문헌 재료다

**2. 회로 페이지** — `kind: circuit` 마다 하나. 강제 개쪽
- 머리글 `회로 3/5 · 이름 · 기록: T3`
- 칩 교체 배너 (앞 회로와 IC 를 비교해 뺄 칩·꽂을 칩). 회로에 `continues` 가
  있으면 "앞 회로(제목)를 그대로 두고 이어 붙인다 — 점퍼선을 걷지 않는다"
  문구로 바뀐다 — `continues` 는 **바로 앞** 회로만 가리킬 수 있다
- 결선도 (없으면 빈 브레드보드 크롭)
- 칩별 배선 상자 — 두 형식이 있다. 불릿형(`- U<n> = <칩>` 아래 들여쓴
  `- ` 배선)은 번호 목록 + 체크박스, 헤딩형(`## U<n> = <칩>` 아래 마크다운
  표)은 표 + 선행 체크박스 열. **상자 안은 원문 순서다** — 표와 산문이
  섞여 있으면 쓰인 순서 그대로 찍힌다
- 미사용핀 강조 박스 (칩마다 따로)
- 이 회로의 유의사항 산문
- 측정표 + 사진 지시 + 미니표 (`kind` 마다 다르다 — 아래 표 참고)
- `refs` 로 가리킨 참조표(role: reference) — 회로 페이지에 읽기 전용으로
  실리고 기록 칸·미니표를 받지 않는다

**3. 종료면 (1쪽)** — 실험실을 나오기 전 확인 목록

**결선도를 그리지 않는다.** `diagram:` 이 가리키는 PNG 를 싣기만 한다.
그림이 필요하면 `breadboard-diagram` 을 **먼저 따로** 돌린다. 인쇄가 렌더러에
묶이면 회로 ID 가 없는 주차에서 조용히 실패한다.

## kind 별 칸

| kind | 기록 칸 | 사진 | 미니표 |
|---|---|---|---|
| `truth-table` | 행마다 세로 정렬 확인(`.check`) 칸, 예상값 좌측 병기 | 항목당 완성 회로 1장 + **불일치 행 필수** | 불일치 기록(예상·실제·사진 파일·짐작된 원인) |
| `stepped` | **확인 열 없음** — 대조할 예상값이 없다. 명세가 저작해 둔 빈 셀이 기록(`.fill`) 칸이고, 계측기 설정 줄(모드·레인지·단위)이 따라붙는다 | **스텝마다** (진행이 요점이다) | 이상 스텝 기록(관찰한 것·짐작된 원인) |
| `capture` | 예상 상자 + 스케치 격자 + 판독 조건 줄(V/div·time/div·프로브·모드) + 캡션·사진 파일 줄 + 예상과 다른 점 상자 | 사진 자체가 결과물 | 없음 — `예상과 다른 점` 상자가 그 자리를 맡는다 |

사진 파일명은 `T<n> row<m>.jpg` 로 찍는다 — ④가 T번호로 표에 자동 배치한다.

## 비-목표

- 명세를 만들지 않는다. 없으면 `draft-lab-spec` 이 교안에서 저작한다.
- 결선도를 그리지 않는다. `netlist` 의 `diagram:` 이 가리키는 PNG 를 소비할 뿐이고,
  없으면 빈 브레드보드로 대신하며 검증이 warn 을 낸다. 그림은
  `breadboard-diagram` 이 별도로 만든다.
- 캐시 신선도 로직(mtime 비교·SOURCES 블록)을 만들지 않는다.
  소스가 고정이므로 그냥 다시 만드는 게 싸고 안전하다.
