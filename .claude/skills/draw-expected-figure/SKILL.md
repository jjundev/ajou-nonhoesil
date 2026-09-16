---
name: draw-expected-figure
description: 논리회로실험 예비보고서의 "실험 과정 및 예상 결과" 에 넣을 예상 개형 그림을 만든다. 명세에 capture 표가 없으면 한 줄로 알리고 바로 끝낸다. 있으면 요소마다 근거를 대고 그림 HTML·아티팩트·3배 PNG 를 만든 뒤 명세 figure 필드와 예비보고서 그림 자리를 채운다. 사용자가 "예상 결과 그림 만들어줘", "예상 개형 그려줘", "5주차 예상 결과 시각화", "/draw-expected-figure" 등을 요청할 때 사용한다.
---

# draw-expected-figure

## 절대 규칙

1. **명세에 `capture` 표가 없으면 그리지 않는다.** `truth-table`·`stepped` 표는
   셀 표가 곧 예상 결과라 그림은 같은 행을 두 번 보여 줄 뿐이다. 판정은
   `figure.capture_tables` 로만 하고, "글로 설명하기 어려운가" 를 따로 따지지
   않는다. 끝낼 때는 `figure.gate_message` 의 한 줄을 사용자에게 그대로 남긴다 —
   말없이 끝나면 실패와 판정이 구분되지 않는다.
2. **측정 화면처럼 그리지 않는다.** 흰 바탕 모식도다. 오실로스코프의 검은 바탕,
   형광 트레이스, 화면 테두리를 흉내내지 않는다. 결과보고서에서 실측 사진과
   나란히 놓일 때 둘이 섞이면 안 된다.
3. **그림 속 소수값은 예비보고서 md 에 같은 글자로 있는 값만 쓴다.** 보간·환산한
   값, 본문과 자릿수가 다른 값(본문 `1.5` 를 그림 `1.50` 으로)은 쓰지 않는다.
   §실행 절차 5 의 숫자 검사가 기계로 본다. 눈금 라벨만 `tick` 으로 빠진다.
4. **본문에 없는 주장을 그림에만 넣지 않는다.** 맞는 말이어도 넣지 않는다.
   조건이 바뀌면 값이 어느 쪽으로 움직인다는 식의 추론, 본문이 말하지 않은 항등식이
   여기 든다. 그림에 넣고 싶으면 먼저 예비보고서 본문에 있어야 한다.
5. **패널 구성은 강의노트의 해당 그림을 따른다.** 강의노트가 파형과 특성 곡선을
   짝지어 그리면 그림도 그 짝으로 그린다. 강의노트에 그 항목의 그림이 없으면 명세
   `expected` 가 말하는 축 하나로만 그린다.
6. **흑백으로 인쇄해도 구분되게 한다.** 색만으로 가르는 요소를 두지 않는다 — 선
   굵기, 실선·점선, 채움, 글자 라벨을 함께 쓴다.
7. **이미지 안에 각주·그림 제목·그림 번호를 넣지 않는다.** 캡션은 이미지 밖 한 줄
   글자이고 "그림 N." 을 붙이지 않는다. 사용자가 이미지 하단 각주를 지워 달라고
   했고(2026-09-16), 보고서의 결선도 그림도 번호 없이 alt 만 쓴다.
8. **그림 영역은 테마와 무관하게 흰 종이로 고정한다.** 노션의 흰 페이지에 들어간다.
   템플릿의 `.paper` 와 `svgWrap` 이 이미 그렇게 한다 — 바꾸지 않는다.
9. **노션에 올린 예비보고서 md 는 고치지 않는다.** 노션 페이지는 덮어쓰지 않으므로
   올린 뒤에 md 를 고치면 둘이 갈라진다. `figure.is_uploaded` 가 참이면 넣을 자리와
   캡션을 알리기만 한다.
10. **과거 제출본을 읽지 않는다.** `from_the_past/` 의 보고서는 알려진 오염이 있다.
    재료는 명세, 예비보고서 md, 그 주 강의노트뿐이다.

## 실행 절차

0. **실험 번호를 폴더로 옮기고 입력을 확인한다.**

   ```bash
   python3 -c "
   from scripts.lab import config
   print(config.experiment_dir(<실험번호>))
   "
   ```

   `<실험NN>/체크리스트/명세.md` 와 `<실험NN>/output/<실험NN>_예비보고서.md` 가
   둘 다 있어야 한다. 예비보고서가 없으면 `write-pre-report` 를 먼저 돌리라고
   알리고 멈춘다 — 그림 속 숫자를 맞댈 본문이 없다.

1. **판정한다** (§절대 규칙 1).

   ```bash
   python3 -c "
   from scripts.lab import config, figure
   from scripts.lab.spec_parser import parse_spec
   exp = config.experiment_dir(<실험번호>)
   spec = parse_spec(exp + '/체크리스트/명세.md')
   pairs = figure.capture_tables(spec)
   if not pairs:
       print(figure.gate_message(spec))
   for item, table in pairs:
       print(item.id, table.id, item.title, '→', figure.figure_png_name(exp, item))
   "
   ```

   `capture 표가 없어` 로 시작하는 줄이 나오면 그 줄을 사용자에게 그대로 전하고
   **여기서 끝낸다.** 파일을 하나도 만들지 않는다.

2. **재료를 읽는다.**
   - 명세의 그 표 `expected` 산문.
   - 예비보고서 md 의 `# 실험 과정 및 예상 결과` 안 `## <항목 제목>` 소절 전체와,
     그 소절이 기대는 `# 실험 이론` 문단·표.
   - 강의노트(명세 frontmatter `source_manual`)에서 그 항목의 쪽(`items[].pages`)과
     이론 쪽의 그림. 회로도·그림은 래스터라 텍스트 추출이 비므로 렌더해서 본다:

     ```bash
     pdftoppm -r 110 -png '<source_manual>' '<스크래치>/manual'
     ```

   §절대 규칙 10 대로 과거 제출본은 열지 않는다.

3. **요소 ↔ 근거 표를 먼저 쓴다.** 그림에 그릴 요소(패널·축·곡선·문턱선·화살표·
   라벨·범위 표시)마다 한 행이다. 근거는 예비보고서 문장(짧게 인용), 명세 `expected`,
   강의노트 그림 쪽 중 하나 이상이다. **근거 칸을 채울 수 없는 행은 지우고 그
   요소는 그리지 않는다**(§절대 규칙 4). 패널 구성 행의 근거는 강의노트 그림 쪽이거나
   명세 `expected` 다(§절대 규칙 5). 근거가 둘 이상으로 갈려 구성이 달라지는 경우에만
   사용자에게 묻는다.

4. **그림 HTML 을 쓴다.** `.claude/skills/draw-expected-figure/template.html` 을
   `<실험NN>/output/<실험NN>_예상결과.html` 로 복사하고 `실험NN` 을 바꾼다. 3단계
   표를 `table.evidence` 의 `tbody` 에 옮기고, `FIGURES` 에 1단계가 출력한 순서대로
   그림을 하나씩 넣는다 — `title` 은 항목 제목, `file` 은 1단계의 PNG 이름,
   `caption` 은 번호 없는 한 줄(§절대 규칙 7). 눈금 라벨은 `text(…, { tick: true })`
   로 쓴다. 가로는 1000 이고 글자는 16 이상으로 둔다(A4 본문 폭에서 약 8pt).
   이미 파일이 있으면 맨 위 주석의 `artifact:` 줄을 지우지 않는다.

5. **숫자 검사를 돌린다** (§절대 규칙 3).

   ```bash
   python3 -m scripts.lab.figure_export <실험번호> --check-only
   ```

   error 가 나오면 3단계로 돌아가 그 값을 본문 글자대로 고치거나 요소를 뺀다.
   `숫자 검사 통과` 가 나올 때까지 반복하고, **몇 번 만에 통과했는지 기억해 둔다**
   (11단계에서 보고한다).

6. **PNG 를 뽑는다.**

   ```bash
   python3 -m scripts.lab.figure_export <실험번호>
   ```

   `<실험NN>/output/` 에 1단계의 이름으로 PNG 가 생긴다. 가로 3000px 이다.

7. **한 번 본다.** PNG 를 한 장씩 열어 글자 겹침·잘림·범례 가림만 고치고 6단계를
   다시 돈다. 두 번째로 보지 않는다.

8. **아티팩트로 게시한다.** `artifact-design` 스킬을 읽은 뒤 Artifact 도구로
   `<실험NN>/output/<실험NN>_예상결과.html` 을 게시한다. 맨 위 주석 `artifact:` 줄에
   URL 이 있으면 그 URL 을 `url` 로 넘겨 같은 주소를 갱신하고, `(게시 전)` 이면 새로
   게시한 뒤 그 줄에 URL 을 적는다.

9. **명세 `figure` 를 적는다.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config, figure
   from scripts.lab.spec_parser import parse_spec
   exp = config.experiment_dir(<실험번호>)
   path = Path(exp) / '체크리스트/명세.md'
   text = path.read_text(encoding='utf-8')
   for item, table in figure.capture_tables(parse_spec(path)):
       text = figure.set_spec_figure(text, table.id,
                                     figure.spec_figure_path(figure.figure_png_name(exp, item)))
   path.write_text(text, encoding='utf-8')
   for item, table in figure.capture_tables(parse_spec(path)):
       print(table.id, table.figure, (path.parent / table.figure).exists())
   "
   ```

   표마다 경로 뒤가 `True` 여야 한다. 체크리스트 인쇄본은 이 필드로 그림을 싣는다 —
   다시 뽑는 것은 `prep-lab-checklist` 의 몫이라 10단계에서 안내만 한다.

10. **예비보고서에 자리를 넣거나 안내한다** (§절대 규칙 9).

    ```bash
    python3 -c "
    from pathlib import Path
    from scripts.lab import config, figure, validate
    from scripts.lab.spec_parser import parse_spec
    exp = Path(config.experiment_dir(<실험번호>))
    md = exp / 'output' / (exp.name + '_예비보고서.md')
    if figure.is_uploaded(md.parent, md.name):
        print('올린 보고서 — md 를 고치지 않는다')
    else:
        CAPTIONS = {<표 id>: '<4단계의 그 그림 caption>'}
        text = md.read_text(encoding='utf-8')
        for item, table in figure.capture_tables(parse_spec(exp / '체크리스트/명세.md')):
            text = figure.insert_placeholder(text, item.title,
                                             figure.figure_png_name(exp, item), CAPTIONS[table.id])
        md.write_text(text, encoding='utf-8')
        for f in (validate.check_notion_markdown(md) + validate.check_body_style(text)
                  + validate.check_report_wrapping(text)):
            print(f)
    "
    ```

    `CAPTIONS` 의 키는 `'T1'` 처럼 따옴표 친 표 id 다. 자리를 넣었으면 error·warn 이
    0 이어야 하고, info 로 "노션에서 직접 넣어야 할 그림" 이 늘어난 것은 정상이다.
    올린 보고서면 표마다 "`## <항목 제목>` 소절 마지막 문단 뒤에 그림, 그 아래 캡션
    한 줄" 을 캡션 글자와 함께 사용자에게 알린다.

11. **보고한다.** 다섯 가지를 낸다.
    - 3단계 요소 ↔ 근거 표
    - PNG 경로와 픽셀 크기, 5단계 숫자 검사가 몇 번 만에 통과했는지
    - 아티팩트 URL
    - 9단계 `figure` 줄과 10단계 결과(자리를 넣었는지, 안내했는지)
    - 다음 할 일: `prep-lab-checklist` 로 체크리스트를 다시 뽑는다. 자리를 넣었으면
      `sync-report-to-notion` 으로 올린 뒤 노션에서 그림을 끼우고, 올린 보고서였으면
      노션에서 바로 끼운다.

## 비-목표

- 결과보고서에 그림을 넣는 것. 실측 사진과의 비교는 `write-result-report` 의 몫이다.
- `stepped` 표를 그래프로 바꾸는 것.
- 체크리스트를 다시 뽑는 것(`prep-lab-checklist`)과 노션에 올리는 것
  (`sync-report-to-notion`).
- 그림 종류별(파형·전달 특성·타이밍) 세부 규칙. 사례가 생기면 절대 규칙에 더한다.
