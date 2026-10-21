---
name: prep-lab-checklist
description: 논리회로실험 주차 명세에서 실험실에 들고 갈 체크리스트를 만든다. 태블릿용 PDF 와 전사용 기록.md 를 항상 쌍으로 낸다. 사용자가 "2주차 체크리스트", "실험실 들고 갈 거 만들어줘", "뭐 측정해야 해", "체크리스트 뽑아줘" 등을 요청하거나 /prep-lab-checklist 를 호출할 때 사용한다. 결선 절차·진리표 확인 칸·브레드보드 작도면·사진 대조란을 포함한다.
---

# prep-lab-checklist

`<실험NN>/체크리스트/명세.md` 하나에서 실험실용 산출물 전부를 파생한다.

**PDF 와 md 를 항상 쌍으로 만든다.** 태블릿에 PDF 를 띄워 펜으로 채우고,
끝나면 `기록.md` 로 전사한다(④가 vision 으로 돕는다).

## 실행 절차

0. **실험 번호를 폴더 이름으로 옮긴다.** 사용자는 "실험1 …" 또는 "다음 실험 …"
   으로 부르고, 아래 절차의 경로는 `<실험NN>/` 이다. 손으로 `실험1` 이라고
   적지 않는다 — 0 을 안 채우면 `실험10` 이 `실험2` 앞에 정렬된다.

   ```bash
   python3 -c "
   from scripts.lab import config
   print(config.experiment_dir(<실험번호>))
   "
   ```

   **"다음 실험" 처럼 날짜로 물었으면** 아래로 찾는다. 한 날에 실험이 둘일 수
   있어 리스트가 온다(9/18 은 실험2·3 이다).

   ```bash
   python3 -c "
   from scripts.lab import config
   print(config.next_experiments())
   "
   ```

   `None` 이면 학기가 끝난 것이다. FPGA 프로젝트(11/27~12/11)는 실험 번호가
   없어 `config.PROJECT_DIR` 로 간다.

   **주차로 불렸으면**("2주차 체크리스트" 처럼) 아래로 옮긴다. 한 날에
   실험이 둘일 수 있어 리스트가 온다.

   ```bash
   python3 -c "
   from scripts.lab import config
   print(config.experiments_in_week(<N>))
   "
   ```

   - 빈 리스트인데 `config.is_project_week(<N>)` 가 참이면 FPGA 프로젝트
     주차(13~15주차)다. 실험 번호가 없어 `config.PROJECT_DIR` 로 간다.
   - 빈 리스트이고 거짓이면 그 주엔 실험이 없다(1주차 오리엔테이션·4주차
     추석·8주차 중간고사). 그대로 알리고 중단한다.
   - 둘 이상이면 **어느 쪽인지 되묻고 중단한다.** 한 날에 실험이 둘인
     주차가 있고, 그날 안에 둘 다 마쳐야 하므로 두 벌이 다 필요할 수도
     있다.
   - 하나면 그 번호로 위 `config.experiment_dir()` 을 부른다.

1. **실험 폴더·명세 확인.** `<실험NN>/체크리스트/명세.md` 가 없으면 **거절한다.**
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

   `parse_netlist`의 `NetlistError`는 지원 버전·필수 메타·표 머리·행 길이·절차
   문법 오류 등이다. 원인을 회로 메타 누락 하나로 단정하지 않는다. **예외 메시지를 그대로 사용자에게 전하고 멈춘다** — 옛 방식으로
   대충 렌더하지 않는다. 백필 방법은 메시지가 담고 있고 계약은
   `docs/schema/lab-netlist-v2.md`와 `docs/schema/lab-netlist-v3.md`다.

   **v3 순차 관측:** `observed` 노드와 단계의 명시적 확인 절차는 stepped 명세만으로도
   인쇄한다. `expression` 계산 경로는 기존 truth-table 규칙을 따른다. 누락 참조·빈 기대값은
   error로 중단하고, 미생성 보드/입력 위치 warn은 알린다. 마지막 단계·LED 없는 프로브도
   참조한 절차를 생략하지 않는다. 준비·초기화와 조작 조건은 현장판에 남긴다. source·provenance·rationale은
   원본에서 검증하고 HTML/PDF에는 출력하지 않는다.
   행의 순서·중복·clock 에지를 유지한다. LED는 알려진 비트만 극성을 적용하고
   유지/반전/미정/관측 안 함을 LED별로 표시한다. 미정은 소등이 아니다.
   절차 표의 확인 칸은 td.box이며 명세·기록.md의 실측 빈칸/td.check를 늘리거나 채우지 않는다.
   기대값은 저작 데이터이므로 구조 검증과 별도로 논리·초기화 검토를 보고한다.


   **출력 전 유일한 조작 조건을 대조한다.** 회로 앞뒤 산문과 단계의 `todo`·`check`를
   그림·연결 목록·`setup`·조작표와 맞댄다. 원문에만 있는 전원·발생기·초기화·접지·측정 조건은
   해당 준비/관측의 `setup` 또는 조작 셀에 짧게 보완한 다음 생성한다. 조건을 없애지 않는다.

3. **기록 템플릿 파생 — 이미 채워진 기록은 덮지 않는다.**

   ```bash
   python3 -c "
   from scripts.lab.record import derive_record, write_record
   from scripts.lab.spec_parser import parse_spec
   spec = parse_spec('<실험NN>/체크리스트/명세.md')
   print(write_record('<실험NN>/체크리스트/기록.md', derive_record(spec)))
   "
   ```

   **`write_record` 로 쓴다. `Path(...).write_text(...)` 로 쓰지 않는다** —
   파생은 언제나 **빈** 템플릿이라, 손으로 쓰면 체크리스트를 다시 뽑는 것만으로
   실험 기록을 지우는 명령이 된다. 2026-09-20 실험03 재생성이 실제로
   `filled_by: vision`·확인 칸 16개·종료 메모 4문항을 말없이 날렸다(작업자가
   알아채고 `git checkout` 으로 되돌렸다).

   - `created`·`regenerated` 면 그대로 4단계로 간다. 파일이 없거나 손대지 않은
     템플릿이면 지금까지와 똑같이 동작한다.
   - **`RecordExistsError` 가 나면 멈춘다.** 예외 메시지의 근거 목록(확인 칸
     N개 · 종료 메모 N문항 …)을 **그대로 사용자에게 전하고** 판단을 받는다.
     기록을 그대로 둔 채 4단계로 가면 인쇄본(html·pdf)만 다시 나오는데, 대개
     이쪽이 사용자가 원하던 것이다.
   - 사용자가 "빈 템플릿으로 되돌려 달라"고 **명시적으로** 답했을 때만
     `force=True` 로 다시 부른다(`기록.md.bak-<시각>` 백업이 먼저 남는다).
     **스스로 켜지 않는다** — 켜는 순간 이 가드는 없는 것과 같다.

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
   from scripts.lab.assembly import check_structure, check_registry, check_assets
   gates = check_structure(netlist)
   if any(section.assembly_steps for section in netlist.circuits):
       from scripts.lab.place_search import load
       _, board = load(netlist.path.parent / '배치.py')
       gates += (check_registry(netlist, getattr(board, 'ASSEMBLY_BOARDS', {}))
                 + check_assets(netlist))
   if any(f.level == 'error' for f in gates):
       raise ValueError('\\n'.join(str(f) for f in gates))
   tmpl = Path('.claude/skills/prep-lab-checklist/template.html').read_text(encoding='utf-8')
   out = Path('<실험NN>/체크리스트/체크리스트.html')
   out.write_text(render_checklist(spec, netlist, tmpl), encoding='utf-8')
   from scripts.lab.fit_pages import fit_pages
   fit_pages(out, chrome=info.get('chrome') or DEFAULT_CHROME)
   html_to_pdf(out, out.with_suffix('.pdf'),
               chrome=info.get('chrome') or DEFAULT_CHROME)
   "
   ```

   **`fit_pages` 를 빠뜨리지 않는다** — 단계 블록마다 높이를 실측해 블록 하나를 제 높이의
   쪽 하나로 만든다(쪽 길이 wrap_content, 2026-09-28 사용자). 빠뜨리면 단계가 기본 쪽에서
   흘러 그림과 확인 줄·단계 진리표가 쪽 경계에서 갈린다. HTML 을 덮어쓰므로 렌더 직후에
   부른다 — 여러 번 불러도 결과는 같다.

   **`chrome=` 를 반드시 넘긴다** — 안 넘기면 `과목정보.md` 의 `chrome` 필드가
   선언만 되고 아무 효과가 없다 (⑥ 표지 스킬과 같은 규칙이다).

5. **인쇄본 자체 검사.** 마크다운 표기가 벗겨지지 않고 남는 경우가 있다 —
   실험02 인쇄본이 `**` 10개를 담은 채 커밋된 적이 있다. 이 절차가
   `check_rendered_html` 을 안 돌려서 아무도 못 봤다.

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import validate
   html = Path('<실험NN>/체크리스트/체크리스트.html')
   for f in validate.check_rendered_html(html) + validate.check_embedded_images(html):
       print(f)
   "
   ```

   **error 가 0 이 아니면 인쇄하지 않는다** — 마크다운을 HTML 로 옮길 때 표
   셀을 빠뜨리면 인쇄본에 그대로 찍힌다.
   `check_embedded_images` 는 경로가 안 풀려 깨진 결선도 그림을 잡는다 —
   2026-09-14 점검 전까지 이 단계는 마크다운 표기만 보고 그림은 안 봤다.

6. **쪽 크기 실측.** 아래를 돌려 쪽 크기를 본다.

   **폭은 전부 `209.9`, 높이는 블록의 내용에 맞춘다.** 태블릿용 PDF라 쪽 수보다
   그림·조작표의 연결이 중요하다. 일반 안내면·종료면은 없다. 첫 장의 칩 포트 역할 표는 보존한다.
   - 첫 장에 문서 제목·칩별 포트 역할 표·회로 제목·회로 그림을 둔다. 단계 1 · 준비 1은 반드시 다음 쪽에서 시작한다. 단계는 블록마다 한 쪽이다.
   - 완성본과 기록 구역도 `fit_pages`로 실측한다. 제목만 남은 쪽·빈 쪽·그림 잘림이 없어야 한다.

   Chrome 헤드리스의 폭은 이름값 210mm 보다 0.11mm 좁은 `209.889mm` 로 고정이다 —
   **결함이 아니다.** 폭이 눈에 띄게 벗어날 때만(예: Letter 로 나와 215.9)
   `template.html` 의 `@page { size: 210mm 420mm }` 를 확인하고 다시 낸다. 새 주차 완성본
   결선도가 더 길면 `test_가장_긴_결선도도_한_쪽에_폭_그대로_들어간다` 가 먼저 알린다.

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

## 현장판 구성 (2026-10-21)

일반 안내면과 종료 점검면은 만들지 않는다. 첫 장에는 기존 `lookup`의 칩별 포트 역할 표를 보존한다. 원본 문서는 저작·검토용이고 PDF는 작업용이다.
삭제한 내용을 다른 경고 상자나 페이지로 옮겨 되살리지 않는다.

### 회로별 순서

1. 개요 쪽의 문서·회로 제목, 첫 장의 칩 포트 역할 표, 필요한 칩 교체 지시, 강의노트 회로 그림. 준비 1은 다음 쪽에서 시작한다.
2. 준비·걷기·결선 단계마다 그림과 번호별 연결/분리 목록, 필요한 조작·관측표.
3. 완성본 그림. 단계에서 이미 나온 배선 목록과 U1·U2 등의 핀별 배선표는 반복하지 않는다.
4. 필요한 미사용 핀 지시, 기록표·파형 기록 공간·아직 관측하지 않은 노드 표.
5. 회로별 메모 공간 하나. 표마다 붙던 불일치/이상 스텝 3행 빈표는 만들지 않는다.

### 출력하지 않는 것

- 전원·일반 주의 상자, 꼭 읽을 것, 오늘의 흐름, 칩 자리표, 기록법 범례.
- 출처, 교안 전사/유도 구분, 유도 이유, 저작·배치·검증 배경, 그림 파일명 캡션.
- 손그림 따라 그리기 안내, LED 사슬·계측 장문, 작성법·사진 촬영·파일명 안내 문단.
- 입력·LED 위치도 아래 순서·간격·흐린 항목 설명, 유지선 개수, 반복 LED 순서 띠.
- 단계 목록과 관측표에 이미 들어 있는 작업 요약·확인 노드·확인 문장.

### 기록표의 확인 목적

각 기록표(T1, T2 등)의 제목 바로 아래에 무엇을 확인하는지 한 문장으로 적는다.
명세의 표 메타 `- purpose: ...`에 입력 조건과 관찰할 동작을 간단히 저작하고,
생성기는 HTML·PDF와 새 기록 템플릿에 같은 문장을 출력한다.
예: `초기화 후 직렬로 넣은 데이터가 클록 하강 에지마다 한 칸씩 이동하는지 확인한다.`
목적은 표의 조작·예상값을 근거로 쓰며 기존 장문 설명이나 별도 설명 페이지를 추가하지 않는다.
기존 표에 purpose가 없으면 목적을 보완한 뒤 생성하고, 작성된 기록.md는 보존한다.

단계별 프로브·LED 확인 절차(V1, V2 등)에도 제목 아래에 확인 목적 한 문장을 출력한다.
결선도 netlist의 각 `## 확인 절차 V<n>`에 `- purpose: ...`로 저작하고,
입력을 바꿨을 때 어느 핀에 전달되는지 또는 어떤 초기화·저장·이동 동작을 보는지 적는다.
준비·초기화 조건 앞에 출력하며 `setup`·조작표·측정 핀·기대값은 그대로 보존한다.
예: `CLK을 바꾸면 U3의 1번 핀까지 같은 논리값이 전달되는지 확인한다.`

### 입력 변경 강조

중간 프로브·LED 확인 절차(V1 등)와 최종 비교 기록표(T1 등)의 입력 설정에
같은 규칙을 적용한다. inline·split 배치 모두 생성기의 공통 판단을 사용한다.

- 각 표의 첫 행은 전체 검정색이다. 표마다 비교 기준을 새로 시작하며,
  준비 설명·다른 표·실제 측정값을 기준으로 삼지 않는다.
- 고정 입력은 같은 표의 직전 종료 레벨과 비교한다. 달라진 `신호명 = 값`
  전체를 진한 빨강·굵게 표시하고, 유지 입력은 검정색으로 둔다.
- `0->1`·`1->0` 같은 명시적 에지는 매번 수행할 조작이므로 반복되어도 강조한다.
  다음 행은 에지의 종료 레벨과 비교한다. `1->0` 다음 `0`은 유지이므로 검정색이다.
- 같은 표 안의 재초기화도 직전 행과 비교한다. 입력 여러 개가 바뀌면 각각 강조한다.
- 전체 입력값·조작 문장·실행 순서를 보존한다. 반복 하강 에지를 강조해도
  원문에 있는 `0→1→0` 왕복 지시를 생략하지 않는다. 알 수 없는 값은 추론하지 않는다.
- 강조 대상은 입력 설정이다. 조작 문장·예상 출력·LED 상태·실측 빈칸은 강조하지 않는다.
  HTML을 직접 손보지 않고 생성기를 수정해 재생성한다.

검사할 사례: 첫 행·표 경계, 단일/복수 입력 변경, 반복 클록 에지,
에지 뒤 종료 레벨 유지, 중간·최종 표 전체 적용. 기존 행·값·실측 빈칸을 대조하고
PDF에서 빨강 가독성과 줄바꿈·쪽 잘림을 확인한다. 작성된 `기록.md`는 보존한다.

### 반드시 보존하는 것

LED 관측표의 `보는 LED` 대응 안내는 LED 이름과 관측 신호가 다를 때만 출력한다
(예: `②A2 = D0′`). `①BIT1 = BIT1`처럼 같은 이름을 반복하는 항목은 생략하고,
남는 대응이 없으면 안내 줄 전체를 생략한다. 입출력 위치도와 표 안의 LED 번호·이름,
임시 급전의 다른 신호 대응, 극성 안내와 극성을 적용한 점등 판정은 보존한다.

- 단계·그림 순서, 선 번호·양 끝 좌표, 먼저 뽑을 선, 프로브의 연결 위치.
- 초기화·입력 순서·클럭 에지·장비 설정·측정 핀·기대값·LED 극성에 따른 점등 판정.
- 입출력 위치도, 예상과 실제의 구분, 실측 빈칸·단위·계측기 설정 칸, 행별 사진 파일명 열.
- 칩별로 다른 미사용 핀 지시. `없음`만 적힌 항목은 출력하지 않는다.

관측점의 이름·핀은 회로의 `## 노드` 표에서 조회한다. `확인` 칸에 적힌 노드와
절차 참조, 단계 순서를 유지하며 핀을 추측하지 않는다.

유일한 조작 조건이 삭제 대상 산문에만 있으면 기존 단계나 `setup`·조작 셀에 짧게 보완한다.
새 설명 페이지를 추가하지 않는다. 단계가 없는 계측 회로의 유일한 설정·저항망 표는 보존한다.
그림도 단계도 없는 회로는 유일한 배선 정보를 남긴다.

`source`·`provenance`·`rationale`·배선 원본은 삭제하지 않는다. PDF와 record.py가 공유하는
`GUIDE`도 지우지 말고 PDF 출력 호출만 제거한다. 작성된 `기록.md`는 재생성하지 않는다.

재생성은 요청한 실험의 HTML·PDF만 대상으로 한다. 회로·단계·기록 칸 보존 검사와
`fit_pages`, HTML/이미지 검사, PDF 쪽별 시각 검사를 수행한다.
