---
name: review-lab-report
description: 논리회로실험 명세·결선도·예비보고서·결과보고서를 검증하고 라운드별 리뷰 문서를 남긴다. 사용자가 "2주차 예비보고서 검토", "명세 검증해줘", "보고서 리뷰", "결과보고서 확인해줘" 등을 요청하거나 /review-lab-report 를 호출할 때 사용한다. 진리표 부울식 역검산, 행 수 대조, 예비보고서 표 머리 대조, source·encoding 누락, netlist 의 VCC/GND/미사용핀 누락, 그리고 `.claude/보고서양식.md` 기준 섹션 대조를 수행한다.
---

# review-lab-report

`scripts/lab/validate.py` 를 불러 검증하고, 결과를 라운드 문서로 남긴다.
**이 스킬은 판단을 새로 만들지 않는다** — 검사 규칙은 전부 코드에 있고 테스트로 고정돼 있다.

## 인자

`<N주차|실험N> [pre|result] [round<N>]`

- 번호 토큰이 없으면 한 줄로 되묻고 중단한다.
- `pre`/`result` 가 없으면 `<실험NN>/output/` 을 보고 추론한다. 둘 다 있으면 되묻는다.
- `round<N>` 이 없으면 기존 `*_review_round*.md` 중 최대 번호 + 1 을 쓴다.

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

   **주차로 불렸으면**("2주차 예비보고서 검토" 처럼) 아래로 옮긴다. 한 날에
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

1. **실험 폴더 확인.** `<실험NN>/` 가 없으면 **거절하고** `init-lab-experiment` 를 안내한다.
   폴더를 만들어 주지 않는다.

2. **폴더 규약·명세·결선도 검증.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab.spec_parser import parse_spec, SpecError
   from scripts.lab import validate
   spec_path = Path('<실험NN>/체크리스트/명세.md')
   try:
       spec = parse_spec(spec_path)
   except SpecError as e:
       print('SPEC-ERROR:', e); raise SystemExit(1)
   for f in validate.check_folder_convention(spec_path, spec):
       print(f)
   for f in validate.validate_spec(spec):
       print(f)
   for f in validate.check_netlist('<실험NN>/결선도/netlist.md', spec):
       print(f)
   "
   ```

   `SpecError` 가 나오면 그것을 **첫 번째 finding 으로 보고하고** 나머지 검사는 건너뛴다.

   폴더 규약 finding 은 "폴더 이름과 명세의 `experiment` 중 하나가 틀렸다"는 뜻이다.
   어느 쪽이 맞는지는 교안으로 확인한다.

3. **판본 확인 — 명세가 지금 열리는 교안에서 나왔는가.**

   이 검사가 없으면 나머지 전부가 무의미해진다. 명세가 통째로 과거 학기
   판본이어도 2단계의 역검산·행 수 대조는 **전부 통과한다** — 명세 안에서만
   닫혀 있기 때문이다.

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config, spec_parser
   spec = spec_parser.parse_spec(Path('<실험NN>/체크리스트/명세.md'))
   live = next((p for p in config.manual_candidates(spec.experiment)
                if Path(p).exists()), None)
   print('명세가 적은 교안:', spec.source_manual)
   print('지금 열리는 교안:', live)
   print('일치' if live and Path(live).as_posix() == Path(spec.source_manual).as_posix() else '✗ 불일치')
   "
   ```

   경로는 `Path.as_posix()` 로 맞춰 비교한다 — Windows 의 `manual_candidates`
   는 `\` 구분자 경로를 돌려주므로 문자열 비교(`str(live) == …`)는 같은 파일도
   항상 `✗ 불일치` 로 냈다(2026-09-12 격리 1회차에서 에이전트가 `samefile` 로
   자체 판단해 넘어갔다).

   **불일치면 error 다.** 명세를 고치지 말고 `draft-lab-spec` 으로 **다시
   저작하라**고 안내한 뒤 그 라운드를 중단한다. 판본이 다르면 항목 구성 자체가
   다를 수 있다 — 실험1 은 아카이브가 13쪽·3항목, 배포본이 15쪽·5항목이다.

   일치하면 **쪽 번호를 실물로 대조한다.** 명세의 `source: manual:pN` 이
   가리키는 쪽이 그 PDF 에 실제로 있고 그 내용인지 본다.

   ```bash
   python3 -c "
   import re
   from pathlib import Path
   from pypdf import PdfReader
   from scripts.lab import config, spec_parser
   spec = spec_parser.parse_spec(Path('<실험NN>/체크리스트/명세.md'))
   live = next(p for p in config.manual_candidates(spec.experiment) if Path(p).exists())
   pages = len(PdfReader(str(live)).pages)
   # source 에 복합 인용('manual:p10 (…) + manual:p4 (…)')과 범위 인용
   # ('manual:p13-p14')이 섞여 있다 — 단순 split(':p')[1] 은 두 형태 모두에서
   # 죽거나 쪽을 놓친다. manual: 로 시작하는 source 안의 pN 을 전부 뽑는다.
   # **`p(\\d+)` 단독으로는 안 된다** — 이 도메인은 `Rp`·`Rn` 소자 표기를
   # 실제로 쓴다. `manual:p9 (Rp2 측정 참조)` 를 그 정규식에 먹이면 `p2` 를
   # 쪽 번호로 잘못 줍는다. 앞이 `manual:` 이거나 범위 인용의 `-` 인 `pN`
   # 만 잡는다.
   cited = sorted({int(p) for t in spec.tables
                   if str(t.source).startswith('manual:')
                   for p in re.findall(r'(?:manual:|-)p(\d+)', str(t.source))})
   print('교안 쪽 수:', pages, '/ 인용된 쪽:', cited)
   for p in cited:
       if p > pages:
           print(f'✗ p{p} 는 이 교안에 없다')
   "
   ```

   **쪽 수를 넘는 인용은 error.** 범위 안이어도 내용까지는 코드가 못 본다 —
   그 쪽을 `pdftoppm -png -r 130` 으로 렌더해 vision 으로 읽고, 명세가 적은
   표가 실제로 그 쪽에 있는지 확인한다. 교안이 래스터 스캔이면 `pdftotext`
   가 아무것도 주지 않으므로 vision 이 유일한 길이다.

4. **보고서 섹션 대조.** **반드시 `.claude/보고서양식.md` 를 기준으로 한다.**
   목차를 스킬에 하드코딩하지 않는다 — 양식은 연도마다·학생마다 다르고
   이번 학기 것이 미확정이다 (R1).

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config, validate
   from scripts.lab.spec_parser import parse_spec
   root = config.find_project_root(Path('.'))
   fmt = config.load_report_format(root)
   spec = parse_spec('<실험NN>/체크리스트/명세.md')
   sections = fmt.pre if '<pre|result>' == 'pre' else fmt.result
   for f in validate.check_report_sections('<보고서 경로>', sections,
                                           item_count=len(spec.items)):
       print(f)
   for f in validate.check_report_references('<보고서 경로>', spec, root=root):
       print(f)
   for f in validate.check_body_style(Path('<보고서 경로>').read_text(encoding='utf-8')):
       print(f)
   for f in validate.check_notion_markdown('<보고서 경로>'):
       print(f)
   if '<pre|result>' == 'pre':
       for f in validate.check_report_tables('<보고서 경로>', spec):
           print(f)
   "
   ```

   `check_body_style` 은 본문 문체(백틱·em dash·"첫째"·조사/단위 띄어쓰기)를
   warn 으로 잡는다 — ③ §절대 규칙 21·④ §절대 규칙 8·18 의 기계 검사판이다.
   warn 이라도 라운드 문서에 그대로 적는다. `check_notion_markdown` 은
   ④ §실행 절차 12 가 도는 네 검사 중 넷째다 — 여기서 빠지면 ⑤ 가 ④ 보다 좁게
   재는 셈이 된다(2026-09-12 격리 1회차에서 에이전트가 지적).

   `check_report_tables` 는 **예비보고서에만** 부른다 — 예상 결과 표의 열 이름·열
   수·열 순서·셀을 명세 기록 대상 진리표와 맞댄다. ③ §절대 규칙 22 의 기계
   검사판이다. 2단계의 행 수 대조는 명세 안에서만 돌아서, 보고서가 열을 줄이거나
   이름을 바꿔도 모른다. 2026-09 실험01 예보가 `A B C L1 L2` 를 `A B C Y` 로 내고도
   `pre_review_round2` 를 통과해 조교 감점(-1)을 받았다. 결과보고서 표는 관측값이라
   셀이 명세와 다를 수 있으므로 부르지 않는다.

   `check_report_references` 는 참고문헌 절을 본다 — 실제로 쓴 IC 의 제조사
   데이터시트가 다 있는지, 개정·발행연도·URL 을 갖췄는지, 2차 미러
   (alldatasheet·네이버·블로그)가 섞이지 않았는지. ③ §절대 규칙 9 의 기계
   검사판이다. **과거 제출본(`from_the_past/`) 참고문헌은 거의 전부 여기서
   error 가 난다** — 그 형식을 본떠서는 안 되는 이유가 이것이다.

   `item_count=len(spec.items)` 를 항상 넘긴다 — `repeat: per-item` 섹션이
   항목 수만큼 정확히 반복됐는지는 이 인자 없이는 검사되지 않는다. ③·④ 가
   자기 절차 안에서 같은 인자를 넘기므로, 여기서 빠지면 같은 보고서를 두
   기준으로 재는 셈이 된다.

4b. **렌더된 HTML 검사.** `check_rendered_html`(표 셀에 남은 백틱·`**`)과
    `check_embedded_images`(경로가 안 풀려 깨진 그림)는 둘 다 `extract_text()`
    로는 안 보인다 — 실제로 표 셀 백틱 230개와 깨진 브레드보드 그림이 이
    검사 없이 제출된 적이 있다. **이 두 함수를 부르는 스킬은 이제 ⑤ 뿐이다**
    — ③·④ 는 보고서를 노션에 올리므로 HTML 을 아예 만들지 않고, HTML 을 내는
    나머지 스킬은 이 검사를 자기 절차에 갖고 있지 않다. 여기서 부르지 않으면
    아무도 안 부른다. 대상은 그 주차의 HTML **전부**다 —
    `<실험NN>/체크리스트/` 와 `<실험NN>/output/` 를 **둘 다** 본다.
    `output/` 의 HTML 은 옛 파이프라인의 잔재가 아니다:
    `explain-lab-preview` 가 실험프리뷰 HTML 을 거기 내고, ⑥ 은 PDF 변환이
    실패하면 표지 HTML 을 남긴다.

    ```bash
    python3 -c "
    from pathlib import Path
    from scripts.lab import validate
    week = Path('<실험NN>')
    for html in sorted(list((week / 'output').glob('*.html'))
                       + list((week / '체크리스트').glob('*.html'))):
        for f in validate.check_rendered_html(html) + validate.check_embedded_images(html):
            print(f)
    "
    ```

5. **코드가 못 보는 것을 사람이 본다.** 아래는 판정하지 말고 **질문으로** 남긴다.

   | 항목 | 왜 코드로 못 하나 |
   |---|---|
   | 고찰이 본인 경험인가 | 배운 점은 학생 것이다. 지어내면 안 된다 |
   | 교안 회로도와 netlist 위상이 맞는가 | PDF 벡터 판독이 필요하다 |
   | 인용한 쪽의 **내용**이 명세가 적은 표인가 | 3단계가 쪽 수 범위까지는 막는다. 내용 대조는 vision 이 필요하다 |
   | 표기가 R5·R6 을 지키는가 — 정의는 `docs/schema/lab-spec-v2.md` 「표기 (R5·R6)」 절(보수는 ASCII `'` 와 괄호 스코프, 오버바 승격은 부울식만·표 헤더/신호명/셀 값은 안 함) | 오버바 승격 범위는 문맥 판단이다 |
   | 섹션 제목이 양식의 이름과 **글자 그대로** 같은가 | 대조는 정확 일치다. `## 1. 실험 목적` 은 통과하지만(번호는 벗겨낸다) `## 1. 실험 목적 및 배경` 은 누락으로 잡힌다. 부분 문자열로 맞추면 `# 실험 결과 분석` 한 줄이 `실험 결과`·`결과 분석` 두 섹션을 동시에 만족시켜 버리므로 일부러 엄격하게 뒀다 |

6. **라운드 문서 작성.** `<실험NN>/output/<pre|result>_review_round<N>.md` 에 쓴다.

   ```markdown
   # <실험NN> <예비|결과>보고서 검토 — round<N>

   ## 자동 검사 (scripts/lab/validate.py)

   - ✗ error 3건 / ! warn 1건
   - (findings 를 그대로 나열)

   ## 사람이 확인할 것

   - (§실행 절차 5 의 항목 중 해당하는 것)

   ## 판정

   - [ ] 제출 가능
   - [x] 수정 필요 — error 가 남아 있다
   ```

7. **error 가 0 이 될 때까지 반복한다** (2·3·4·4b 단계 전부 합쳐서). warn 은
   남겨도 되지만 **왜 남기는지 한 줄** 적는다.

## 비-목표

- 보고서를 고쳐 쓰지 않는다. 지적만 한다 (수정은 ③·④ 의 일이다).
- 검사 규칙을 이 문서에 새로 적지 않는다. 규칙은 `validate.py` 에 있고
  거기에 테스트가 붙어 있다. 새 규칙이 필요하면 **테스트부터** 쓴다.
