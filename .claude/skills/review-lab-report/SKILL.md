---
name: review-lab-report
description: 논리회로실험 명세·결선도·예비보고서·결과보고서를 검증하고 라운드별 리뷰 문서를 남긴다. 사용자가 "2주차 예비보고서 검토", "명세 검증해줘", "보고서 리뷰", "결과보고서 확인해줘" 등을 요청하거나 /review-lab-report 를 호출할 때 사용한다. 진리표 부울식 역검산, 행 수 대조, 예비보고서 표 머리 대조, source·encoding 누락, netlist 의 VCC/GND/미사용핀 누락, 그리고 `.claude/보고서양식.md` 기준 섹션 대조를 수행한다. 본업은 보고서의 사실 문장(수치·핀·IC·신호 이름·행·파일 경로)을 교안·데이터시트·명세·기록과 하나씩 맞대는 내용 대조다.
---

# review-lab-report

## 산출물 이름 (실험07부터)

파일 경로는 `scripts.lab.config.artifact_path(실험폴더, 종류, 확장자)`로 정한다.
실험07 이상은 `실험NN_실험_제목_산출물종류.확장자`이고, 실험01~06은 기존 이름 그대로다.
실험 제목은 명세의 `title`에서 읽는다. 문서 안의 제목·내부 그림 이름은 바꾸지 않는다.
이 문서의 `기록.md`·`체크리스트.pdf` 같은 짧은 이름은 종류를 뜻하는 별칭이며,
실제 생성·존재 확인·전사·검증·결과 링크에는 반드시 공통 함수가 반환한 경로를 쓴다.
종류는 `체크리스트`, `기록`, `예비보고서`, `결과보고서`, `예비보고서표지`,
`결과보고서표지`, `손그림모사`, `부품그리기`, `따라그리기`, `예상결과`다.
저장 위치·예외·이력 보존 규칙은 `docs/schema/lab-artifact-naming.md`를 따른다.

보고서를 쓴 세션과 떨어진 눈으로 **사실 문장을 근거와 맞대고**, 결과를 라운드 문서로 남긴다.

자동 검사(`scripts/lab/validate.py`)는 ③·④ 가 자기 절차에서 이미 같은 인자로 돌린다.
그래서 실험01~03 라운드 21개 중 자동 검사가 error 를 낸 것은 하나뿐이었고,
"수정 필요" 판정 네 건(실험02 예보 r1, 실험03 예보 r2·결보 r1·r3)은 전부 사실
문장을 근거와 다시 맞대서 나왔다. 자동 규칙은 `validate.py` 에, 내용 판단은
**근거 인용**으로 남긴다 — 근거 파일과 줄·쪽을 못 대는 지적은 지적이 아니다.

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

2. **자동 검사 — 명세·판본·결선도.** 한 블록으로 돌린다. 보고서가 기대는 명세가
   깨졌거나 과거 학기 판본이면 나머지는 전부 무의미하다 — 명세가 통째로 옛
   판본이어도 역검산·행 수 대조는 명세 안에서만 닫혀 있어 **전부 통과한다.**

   ```bash
   python3 -c "
   import re
   from pathlib import Path
   from pypdf import PdfReader
   from scripts.lab.netlist_parser import parse_netlist
   from scripts.lab.spec_parser import parse_spec, SpecError
   from scripts.lab import config, validate
   spec_path = Path('<실험NN>/체크리스트/명세.md')
   netlist = Path('<실험NN>/결선도/netlist.md')
   try:
       spec = parse_spec(spec_path)
   except SpecError as e:
       print('SPEC-ERROR:', e); raise SystemExit(1)
   live = next((p for p in config.manual_candidates(spec.experiment)
                if Path(p).exists()), None)
   same = live and Path(live).as_posix() == Path(spec.source_manual).as_posix()
   print('판본:', '일치' if same else f'✗ 불일치 (명세 {spec.source_manual} / 지금 {live})')
   if same:
       pages = len(PdfReader(str(live)).pages)
       cited = sorted({int(p) for t in spec.tables
                       if str(t.source).startswith('manual:')
                       for p in re.findall(r'(?:manual:|-)p(\d+)', str(t.source))})
       print('교안 쪽 수:', pages, '/ 인용된 쪽:', cited)
       for p in cited:
           if p > pages:
               print(f'✗ p{p} 는 이 교안에 없다')
   findings = (validate.check_folder_convention(spec_path, spec)
               + validate.check_item_scope(spec)
               + validate.validate_spec(spec)
               + validate.check_manual_names(spec, validate.extract_manual_pages(spec.source_manual))
               + validate.check_netlist(str(netlist), spec)
               + validate.check_netlist_circuits(parse_netlist(netlist), spec))
   for f in findings:
       print(f)
   "
   ```

   - `SpecError`·판본 불일치·쪽 수를 넘는 인용·`check_manual_names` error 는
     **그 라운드를 멈춘다.** 명세를 고치지 말고 `draft-lab-spec` 으로 다시
     저작하라고 안내한다(판본이 다르면 항목 구성부터 다르다 — 실험1 은 아카이브가
     13쪽·3항목, 배포본이 15쪽·5항목이다).
   - 판본 경로는 `as_posix()` 로 맞춰 비교한다. Windows 의 `manual_candidates` 는
     `\` 구분자를 돌려줘 문자열 비교가 같은 파일도 불일치로 냈다(2026-09-12).
   - 인용 쪽 정규식은 앞이 `manual:` 이거나 범위의 `-` 인 `pN` 만 잡는다.
     `p(\d+)` 단독은 `Rp2` 같은 소자 표기를 쪽 번호로 줍는다.
   - 인용 쪽의 **내용**을 vision 으로 대조하는 일은 `draft-lab-spec` 이 저작 때
     한다. 여기서 다시 하지 않는다.
   - 폴더 규약 finding 은 "폴더 이름과 명세의 `experiment` 중 하나가 틀렸다"는 뜻이다.

3. **자동 검사 — 보고서와 HTML.** 섹션 기준은 반드시 `.claude/보고서양식.md` 다
   (목차를 스킬에 하드코딩하지 않는다 — R1).

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config, validate
   from scripts.lab.spec_parser import parse_spec
   root = config.find_project_root(Path('.'))
   fmt = config.load_report_format(root)
   spec = parse_spec('<실험NN>/체크리스트/명세.md')
   rep = '<보고서 경로>'
   text = Path(rep).read_text(encoding='utf-8')
   sections = fmt.pre if '<pre|result>' == 'pre' else fmt.result
   findings = (validate.check_report_sections(rep, sections, item_count=len(spec.items))
               + validate.check_report_references(rep, spec, root=root)
               + validate.check_body_style(text)
               + validate.check_result_photo_diagrams(text)
               + validate.check_notion_markdown(rep)
               + validate.check_report_tables(rep, spec, cells='<pre|result>' == 'pre'))
   week = Path('<실험NN>')
   for html in sorted(list((week / 'output').glob('*.html'))
                      + list((week / '체크리스트').glob('*.html'))):
       findings += validate.check_rendered_html(html) + validate.check_embedded_images(html)
   for f in findings:
       print(f)
   "
   ```

   ③·④ 와 **같은 인자**로 잰다 — 좁게 재면 같은 보고서를 두 기준으로 재는 셈이다.
   `item_count` 가 빠지면 `repeat: per-item` 반복 횟수가 검사되지 않고,
   `cells` 는 예보만 진리표 셀까지 본다(결과 칸은 관측값이라 명세와 다를 수 있다).
   `check_result_photo_diagrams` 는 예보에 빈 목록을 돌려주므로 두 종류에 같은
   블록을 돌려도 된다. 각 검사가 무엇을 보는지는 `validate.py` docstring 에 있다.
   HTML 두 검사(`check_rendered_html`·`check_embedded_images`)는 ③·④ 가 부르지
   않는다 — `output/` 과 `체크리스트/` 의 HTML 은 여기서 안 부르면 아무도 안 본다.

4. **근거 묶음을 모은다.** 내용 대조가 맞댈 파일 목록이다. 실재하는 것만 적는다.

   | 보고서 | 근거 |
   |---|---|
   | 예비 | `<실험NN>/체크리스트/명세.md`, `<실험NN>/결선도/netlist.md`, 2단계가 찾은 교안 PDF 와 인용 쪽, `from_the_past/정리/소자_데이터시트_및_미디어/1_데이터시트_및_핀아웃/`, `<실험NN>/결선도/` 의 그림 |
   | 결과 | 위 명세·netlist·교안, `config.artifact_path('<실험NN>', '기록', '.md')`, `<실험NN>/실험사진/`(시트 포함), `config.artifact_path('<실험NN>', '예비보고서', '.md')`, `<실험NN>/실험중있었던일.md`(있으면) |

   데이터시트 PDF 가 로컬에 없으면 참고문헌의 URL 을 근거로 적지 않는다 — 그 문장은
   `근거 없음` 으로 두고 사람이 확인할 것에 올린다.

5. **내용 대조 — 맥락 없는 서브에이전트에 맡긴다.** Agent 도구로
   general-purpose 에이전트를 하나 띄운다. 보고서 경로와 4단계의 근거 경로만
   넘기고 **작성 맥락은 넘기지 않는다** — ④ 직후 같은 세션에서 부르면
   보고서를 읽을 때 '쓴 것' 이 아니라 '의도한 것' 을 본다(`draft-lab-spec` 의
   fresh 검토와 같은 이유). 근거 파일은 넘긴다: 잡아야 할 것이 근거와의 불일치다.
   프롬프트는 아래 그대로 쓴다.

   ```text
   아래 보고서를 근거 파일과 대조하라. 아무 파일도 고치지 마라.

   보고서: <보고서 경로>
   근거: <4단계 목록>

   1. 사실 문장을 뽑는다 — 수치·핀 번호·IC 이름·신호 이름·진리표 행·전압·시간·
      파일 경로가 든 문장과 표 셀. 이론 설명은 교안·데이터시트의 수치나 규격을
      말할 때만 대상이다.
   2. 문장마다 근거를 찾아 판정한다.
      ✓ 근거와 같다 / ✗ 근거와 다르다 / 근거 없음 (어느 근거에도 없다)
   3. 보고서 안에서 서로 모순되는 두 문장을 찾는다(✗ 로 적고 두 줄을 다 적는다).
   4. 보고서가 가리키는 그림·링크 경로가 디스크에 실재하는지 본다(없으면 ✗).
   5. 표로 돌려준다: 줄 | 주장(한 줄 요약) | 근거(파일:쪽 또는 파일:줄) | 판정.
      ✓ 는 개수만 세고 행은 ✗ 와 근거 없음만 적는다.
   ```

6. **✗ 를 메인에서 다시 연다.** 서브에이전트의 ✗·근거 없음을 하나씩 근거
   파일에서 직접 확인한다. 오탐이면 ✓ 로 내리고 이유를 한 줄 적는다(라운드
   문서에 남긴다 — 같은 오탐이 다음 라운드에 되살아나지 않게). 남은 ✗ 가
   이 라운드의 **내용 ✗** 다.

7. **코드도 근거 대조도 못 보는 것을 사람이 본다.** 아래는 판정하지 말고
   **질문으로** 남긴다.

   | 항목 | 왜 못 하나 |
   |---|---|
   | 고찰이 본인 경험인가 | 배운 점은 학생 것이다. 지어내면 안 된다 |
   | 교안 회로도와 netlist 위상이 맞는가 | PDF 벡터 판독이 필요하다 |
   | 표기가 R5·R6 을 지키는가 — 정의는 `docs/schema/lab-spec-v2.md` 「표기 (R5·R6)」 절(보수는 ASCII `'` 와 괄호 스코프, 오버바 승격은 부울식만·표 헤더/신호명/셀 값은 안 함) | 오버바 승격 범위는 문맥 판단이다 |
   | 섹션 제목이 양식의 이름과 **글자 그대로** 같은가 | 대조는 정확 일치다. `## 1. 실험 목적` 은 통과하지만(번호는 벗겨낸다) `## 1. 실험 목적 및 배경` 은 누락으로 잡힌다. 부분 문자열로 맞추면 `# 실험 결과 분석` 한 줄이 `실험 결과`·`결과 분석` 두 섹션을 동시에 만족시켜 버리므로 일부러 엄격하게 뒀다 |
   | 6단계에 남은 `근거 없음` | 근거가 로컬에 없거나(데이터시트) 사용자 기억에만 있다 |

8. **라운드 문서 작성.** `<실험NN>/output/<pre|result>_review_round<N>.md` 에 쓴다.

   ```markdown
   # <실험NN> <예비|결과>보고서 검토 — round<N>

   ## 자동 검사 (scripts/lab/validate.py)

   - ✗ error 0건 / ! warn 1건 / ℹ info 2건
   - (findings 를 그대로 나열)

   ## 내용 대조

   - ✓ 41건 / ✗ 1건 / 근거 없음 2건 / 오탐으로 내린 것 1건
   | 줄 | 주장 | 근거 | 판정 |
   |---|---|---|---|
   | 90 | 갈리는 행은 3행이다 | 기록.md:22 — 3·5행 | ✗ |

   ## 사람이 확인할 것

   - (7단계의 항목 중 해당하는 것)

   ## 판정

   - [ ] 제출 가능
   - [x] 수정 필요 — 내용 ✗ 1건(90행)
   ```

   **"제출 가능"은 자동 error 0 이고 내용 ✗ 0 일 때만** 체크한다. warn 과
   근거 없음은 남겨도 되지만 **왜 남기는지 한 줄** 적는다.

9. **자동 error 0·내용 ✗ 0 이 될 때까지 반복한다.** 다음 라운드는 2단계부터
   다시 돈다 — 고친 문장이 다른 검사가 보는 자리를 바꿨을 수 있다.

## 비-목표

- 보고서를 고쳐 쓰지 않는다. 지적만 한다 (수정은 ③·④ 의 일이다).
- 기계 검사 규칙을 이 문서에 새로 적지 않는다. 규칙은 `validate.py` 에 있고
  거기에 테스트가 붙어 있다. 내용 대조에서 같은 종류의 ✗ 가 되풀이되면 그때
  **테스트부터** 써서 `validate.py` 로 올린다.
