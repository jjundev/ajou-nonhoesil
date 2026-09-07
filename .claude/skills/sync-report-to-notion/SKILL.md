---
name: sync-report-to-notion
description: 논리회로실험 예비·결과보고서 md 를 노션에 올리고, 사용자가 노션에서 고친 내용을 되읽어 하네스 개선 규칙으로 분류한다. 사용자가 "노션에 올려줘", "2주차 예보 노션에 올려", "다 고쳤어 읽어와", "노션에서 가져와" 등을 요청하거나 /sync-report-to-notion 을 호출할 때 사용한다. 제출용 PDF 는 사용자가 노션에서 직접 내보내고 ⑥ 이 만든 표지를 앞에 손으로 붙인다.
---

# sync-report-to-notion

## 절대 규칙

1. **페이지를 절대 덮어쓰지 않는다.** 업로드는 항상 새 페이지다. 사용자가
   노션에서 고쳤지만 아직 되읽지 않은 구간이 구조적으로 존재하고, 그 구간에
   덮어쓰면 수정이 경고 없이 사라진다.
2. **토큰을 저장소에 쓰지 않는다.** 환경변수 `NOTION_TOKEN` 에서만 읽는다.
   토큰 값을 로그·커밋·대화 어디에도 그대로 옮기지 않는다.
3. **사진을 자동으로 올리지 않는다.** 상대경로 이미지는 노션에서 깨지는 게
   정상이고, 사용자가 직접 끼워 넣는다. 몇 장을 어디에 넣어야 하는지만 알린다.
4. **분류를 지어내지 않는다.** diff 에 실제로 있는 변경만 표에 올린다.
   애매하면 "애매"로 표시하고 사용자에게 묻는다.
5. **예비·결과보고서만 다룬다.** 체크리스트·표지·프리뷰는 이 스킬의 대상이
   아니다 — 인쇄용 A4 레이아웃 자체가 산출물이라 노션이 재현하지 못한다.

## push — 노션에 올리기

0. **실험 번호를 폴더 이름으로 옮긴다.** 사용자는 "실험1 …" 또는 "다음 실험 …"
   으로 부르고, 아래 절차의 경로는 `<실험NN>/` 이다.

   ```bash
   python3 -c "
   from scripts.lab import config
   print(config.experiment_dir(<실험번호>))
   "
   ```

   **"다음 실험" 처럼 날짜로 물었으면** `config.next_experiments()` 로 찾는다.
   한 날에 실험이 둘일 수 있어 리스트가 온다(9/18 은 실험2·3 이다). `None` 이면
   학기가 끝난 것이다.

   **주차로 불렸으면**("2주차 예보 노션에 올려" 처럼) `config.experiments_in_week(<N>)`
   로 옮긴다. 빈 리스트인데 `config.is_project_week(<N>)` 가 참이면 FPGA
   프로젝트 주차(13~15주차)다. 실험 번호가 없어 `config.PROJECT_DIR` 로
   간다. 거짓이면 그 주엔 실험이 없다(1주차 오리엔테이션·4주차 추석·8주차
   중간고사) — 알리고 중단한다. 둘 이상이면(한 날에 실험이 둘인 주차가
   있다) 어느 쪽인지 되묻고 중단한다. 하나면 그 번호로 위
   `config.experiment_dir()` 을 부른다.

1. **올릴 파일을 정한다.** `<실험NN>/output/<실험NN>_예비보고서.md` 또는
   `..._결과보고서.md`. 없으면 ③ `write-pre-report` / ④ `write-result-report`
   를 먼저 돌리도록 안내하고 멈춘다.

2. **업로드 전 검사.** error 가 있으면 **올리지 않고** 보고한 뒤 사용자 판단을
   기다린다. info 는 그대로 사용자에게 전한다 — 노션에서 손으로 넣어야 할
   사진 목록이다.

   ```bash
   python3 -c "
   from scripts.lab import validate
   for f in validate.check_notion_markdown('<실험NN>/output/<파일명>.md'):
       print(f)
   "
   ```

3. **부모 페이지 id 를 읽는다.** `~` 면 `.claude/과목정보.md` 를 채우고 노션에서
   그 페이지에 integration 을 Connect 하도록 안내한 뒤 멈춘다.

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   info = config.load_course_info(config.find_project_root(Path('.')))
   print(info['notion_parent_page_id'])
   "
   ```

4. **올리고, 이력을 남기고, baseline 을 뜬다.** 세 가지가 한 덩어리다 —
   **baseline 없이 업로드만 하면 다음 pull 의 diff 가 왕복 노이즈로 뒤덮인다.**

   **페이지 제목은 `properties` 로 명시해 넘기고, 본문의 같은 제목 헤딩은 뺀다.**
   노션이 첫 `#` 헤딩을 제목으로 흡수해 주기는 하지만 그 흡수에는 조건이 붙는다
   — 제목 헤딩 바로 뒤에 목차 블록을 두었더니 흡수가 깨져 **제목이 빈 페이지**가
   만들어졌다(실제로 났다). 사이드바에 "Untitled" 로 뜨고 URL 에도 슬러그가 없어
   사람이 찾지 못한다. 명시로 넘기면 그 조건에 기대지 않아도 되고, 대신 본문
   첫 줄의 제목 헤딩을 빼야 제목이 두 번 보이지 않는다.

   ```bash
   python3 - <<'PY'
   from datetime import datetime
   from pathlib import Path
   from scripts.lab import config, notion
   from scripts.lab.spec_parser import parse_spec
   OUT, NAME, KIND = Path('<실험NN>/output'), '<파일명>.md', '<예비보고서|결과보고서>'
   root = config.find_project_root(Path('.'))
   info = config.load_course_info(root)
   token = notion.load_token()
   text = (OUT / NAME).read_text(encoding='utf-8')

   spec = parse_spec('<실험NN>/체크리스트/명세.md')
   title = config.document_title(spec.experiment, spec.title, KIND)
   page_title = f"{title} v{notion.next_version(OUT, KIND)}"
   body = text
   if body.startswith(f'# {title}\n'):
       body = body[len(f'# {title}\n'):].lstrip('\n')

   page = notion.push_markdown(body, info['notion_parent_page_id'], token,
                               title=page_title)
   rec = notion.append_record(OUT, KIND, page['page_id'], page['url'], NAME,
                              datetime.now().strftime('%Y-%m-%d %H:%M'))
   base = OUT / f"{NAME[:-3]}_notion_baseline_v{rec['version']}.md"
   base.write_text(notion.pull_markdown(page['page_id'], token), encoding='utf-8')
   print('제목', page_title)
   print('v', rec['version'], page['url'])
   print('baseline', base)
   PY
   ```

   올린 뒤 **페이지 제목이 비어 있지 않은지 확인한다.** URL 에 제목 슬러그가
   붙어 있으면(`.../p/1-Basic-Gates-...`) 제대로 들어간 것이고, 32자리 id 만
   있으면 제목이 비었다는 뜻이다.

   이 스크립트가 셋 중 어디서든 죽으면 그대로 다시 돌리지 않는다 — 복구 절차는 4b 를 본다.

   **제목 끝의 `v<N>` 은 업로드 전에 `next_version` 으로 구한다.** 사용자는
   노션 사이드바에서 PDF 를 내보내므로 거기서 판본을 구분할 수 있어야 한다.
   본문 첫 헤딩을 떼는 비교에는 버전 없는 `title` 을 그대로 쓴다 — 본문에는
   버전이 없다. 이미 올라간 v1~v6 의 제목은 소급하지 않는다.

4b. **4단계가 중간에 죽으면 그대로 다시 돌리지 않는다.** `push_markdown`·`append_record`·
    baseline pull 은 한 스크립트 안에 있을 뿐 서로 독립된 호출이라 에러 처리가 없다 —
    어디서 죽었느냐에 따라 남는 상태가 다르고, 복구 방법도 다르다.

    **A. `append_record` 까지는 성공하고 baseline pull 만 죽었을 때.** 노션에 페이지가
    있고 `notion.json` 에도 정상 레코드가 있다 — 없는 건 baseline 파일뿐이다. 이 상태에서
    4단계를 그냥 재실행하면 §절대 규칙 1 때문에 새 페이지가 또 생기고 버전이 한 번 더
    올라간다. 그러면 방금 만든 첫 버전은 baseline 없이 영영 고아로 남고, 9단계의 `diff -u`
    는 나중에 그 baseline 을 찾다가 file-not-found 로 죽는다. 복구는 재업로드가 아니라
    **재-pull** 이다 — pull 은 읽기 전용·멱등이므로 이미 기록된 `page_id` 로 baseline 만
    다시 뜨면 안전하다. **새 페이지를 만들지 않는다.**

    ```bash
    python3 - <<'PY'
    from pathlib import Path
    from scripts.lab import notion
    OUT = Path('<실험NN>/output')
    token = notion.load_token()
    for rec in notion.load_records(OUT):
        stem = rec['source'][:-3]  # '<파일명>.md' 에서 .md 를 뗀 접미사
        base = OUT / f"{stem}_notion_baseline_v{rec['version']}.md"
        if base.exists():
            continue
        print('복구:', base)
        base.write_text(notion.pull_markdown(rec['page_id'], token), encoding='utf-8')
    PY
    ```

    출력이 없으면 복구할 baseline 이 없었다는 뜻이다(4단계가 온전히 끝났거나 이미 복구된
    상태).

    **B. `push_markdown` 은 성공했는데 `append_record` 가 실패했을 때.** 이번엔 `page_id`
    가 디스크 어디에도 안 남는다 — `notion.json` 에 없으니 7단계("가장 최근 업로드를
    찾는다")로도 이 페이지를 찾을 수 없다. **스크립트로 복구할 수 없다** — 노션에 무엇이
    올라갔는지는 알지만 그것을 가리키는 레코드가 없으므로, 판단은 사용자 몫이다. 조용히
    다시 올리지 않는다 — 재업로드하면 같은 버전에 페이지가 두 개 남는데, 레코드가 없던
    첫 페이지를 사용자가 이미 봤는지조차 구분할 방법이 없어진다. 대신 있는 그대로
    보고한다: 레코드 없이 노션 페이지가 하나 생겼을 수 있다는 것을 알리고, 3단계와 같은
    방법으로 부모 페이지(`notion_parent_page_id`) id 를 다시 읽어 알려주어 그 아래에서
    사용자가 직접 찾아보게 한 뒤, 그 페이지를 노션에서 지울지 아니면 그대로 두고 새
    버전을 다시 올릴지 사용자에게 묻는다.

5. **왕복 손실을 확인한다.** 방금 뜬 baseline 과 올린 원본을 대조한다.

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import validate
   src = Path('<실험NN>/output/<파일명>.md').read_text(encoding='utf-8')
   got = Path('<실험NN>/output/<파일명 접미사>_notion_baseline_v<N>.md').read_text(encoding='utf-8')
   for f in validate.check_notion_roundtrip(src, got):
       print(f)
   "
   ```

   기대: 출력 없음. 절·표·인용이 줄었다고 나오면 **노션에 온전히 올라가지
   않은 것이다** — 사용자에게 보고하고, 그 페이지로 검토를 진행할지 다시 올릴지
   판단을 받는다.

6. **결과 안내.** 노션 URL, 버전 번호, 손으로 넣어야 할 사진 목록, 왕복 검사
   결과를 한 묶음으로. 그리고 **다 고치면 "읽어와"라고 말해 달라**고 알린다.

## pull — 노션에서 되읽고 분류하기

사용자가 "다 고쳤어, 읽어와" 라고 할 때 실행한다.

7. **가장 최근 업로드를 찾는다.**

   ```bash
   python3 -c "
   from scripts.lab import notion
   for r in notion.load_records('<실험NN>/output'):
       print(r['kind'], 'v%d' % r['version'], r['page_id'], r['uploaded_at'])
   "
   ```

8. **되읽어 저장한다.** baseline 을 덮어쓰지 않는다 — 파일 이름이 다르다.
   그림이 있으면 `pull_markdown` 이 S3 **서명 쿼리스트링을 뗀다** —
   자격증명이 저장소에 들어가지 않게, 그리고 되읽을 때마다 서명이 새로 생겨
   diff 가 노이즈로 덮이지 않게. 남은 URL 로는 그림을 못 받는다.
   되살리지 마라.

   ```bash
   python3 - <<'PY'
   from pathlib import Path
   from scripts.lab import notion
   OUT, PAGE, STEM, V = Path('<실험NN>/output'), '<page_id>', '<파일명 접미사>', <N>
   text = notion.pull_markdown(PAGE, notion.load_token())
   (OUT / f'{STEM}_notion_v{V}.md').write_text(text, encoding='utf-8')
   print('저장:', OUT / f'{STEM}_notion_v{V}.md', len(text), '자')
   PY
   ```

8b. **안 끼운 그림이 없는지 본다.**

    ```bash
    zsh -c 'PYTHONPATH=. python3 -c "
    from pathlib import Path
    from scripts.lab import validate
    p = Path(\"<실험NN>/output/<접미사>_notion_v<N>.md\")
    f = validate.check_pulled_images(p.read_text(encoding=\"utf-8\"))
    print(\"\n\".join(str(x) for x in f) or \"빈 그림 없음\")
    "'
    ```

    `✗` 가 나오면 **거기서 멈추고 사용자에게 알린다.** 상대경로 그림은
    노션에서 반드시 깨지므로 사용자가 손으로 끼워야 하는데, 안 끼운 채로 PDF
    를 내보내면 그 자리가 빈 채로 제출된다. 실험01 v7 에서 실제로 그럴
    뻔했고 기계는 조용했다. 사용자가 끼운 뒤 8단계부터 다시 돌린다.

9. **baseline 과 diff 를 뜬다.** **원본이 아니라 baseline 과 비교한다** — 노션
   변환기의 노이즈가 양쪽에 똑같이 들어가 상쇄되므로, 남는 차이가 순수하게
   사용자가 고친 것이다.

   ```bash
   diff -u '<실험NN>/output/<접미사>_notion_baseline_v<N>.md' \
           '<실험NN>/output/<접미사>_notion_v<N>.md'
   ```

10. **분류 표를 낸다.** diff 의 각 덩어리를 한 행으로.

    | # | 무엇이 바뀌었나 | 분류 | 반영 대상 |
    |---|---|---|---|

    - **기본값은 `체계적`** 이다. 사용자는 하네스를 고치려는 의도로 편집한다.
    - **애매하면 기본값으로 넘기지 않는다.** `애매` 로 표시하고 물어본다.
    - `일회성` 은 그 md 만 고친다. `체계적` 은 **어느 파일의 어느 절에** 박을지를
      반드시 함께 적는다 — 적을 수 없으면 그건 아직 체계적이 아니다.
    - **여러 실험에서 같은 수정이 나오면 논쟁 없이 체계적이다.** 라운드로 여러
      보고서를 한꺼번에 돌린 경우 이 대조를 먼저 한다.

11. **사용자 확인을 받는다.** 분류가 틀린 행만 사용자가 짚는다.

12. **로그를 남긴다.** `docs/notion-feedback/round<N>-<실험NN>-<종류>.md` 에
    §형식대로 쓴다. **반영하지 않기로 한 항목도 남긴다** — 나중에 과적합으로
    드러난 규칙을 되짚어 걷어내려면 어느 라운드의 무엇이 그 규칙을 만들었는지
    알아야 한다.

13. **하네스를 고친다.** `체계적` 로 확정된 항목만.

14. **재생성 대조.** 체계적 규칙을 하나라도 박았으면, 같은 입력으로 보고서를
    다시 만들어 사용자 수정본과 대조한다. **새 주차로 넘어가서 확인하지 않는다**
    — 내용이 달라 규칙이 먹힌 것인지 그냥 다른 내용이 나온 것인지 구분되지 않는다.
    일회성 수정만 있었던 라운드는 재생성하지 않는다.

## 제출

이 스킬은 **PDF 를 만들지 않는다.** 사용자가 노션에서 `⋯ → Export → PDF` 로
본문을 내려받고, ⑥ `make-lab-report-cover` 가 만든 표지 PDF 를 앞에 손으로
붙여 제출한다.

## 비-목표

- 사진을 API 로 첨부하지 않는다 (§절대 규칙 3).
- 노션 페이지를 지우거나 갈아엎지 않는다 (§절대 규칙 1).
- 체크리스트·표지·프리뷰를 올리지 않는다 (§절대 규칙 5).
- 부울식을 오버바로 승격하지 않는다 — 지금은 보수 `'` 그대로 올린다.
  `$\overline{A \cdot B}$` 렌더는 확인됐지만(`write-pre-report/SKILL.md:307`),
  승격 자체는 보류한다 — 실험6 `Q(t-1)'` 은 부울식이 아니라 상태 토큰이라
  승격하면 그 진리표가 깨진다.
