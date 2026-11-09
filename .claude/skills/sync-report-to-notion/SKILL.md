---
name: sync-report-to-notion
description: 논리회로실험 예비·결과보고서 md 를 노션에 올리고, 사용자가 노션에서 고친 내용을 되읽어 하네스 개선 규칙으로 분류한다. 사용자가 "노션에 올려줘", "2주차 예보 노션에 올려", "다 고쳤어 읽어와", "노션에서 가져와" 등을 요청하거나 /sync-report-to-notion 을 호출할 때 사용한다. 제출용 PDF 는 사용자가 노션에서 직접 내보내고 ⑥ 이 만든 표지를 앞에 손으로 붙인다.
---

# sync-report-to-notion

## 산출물 이름 (실험07부터)

파일 경로는 `scripts.lab.config.artifact_path(실험폴더, 종류, 확장자)`로 정한다.
실험07 이상은 `실험NN_실험_제목_산출물종류.확장자`이고, 실험01~06은 기존 이름 그대로다.
실험 제목은 명세의 `title`에서 읽는다. 문서 안의 제목·내부 그림 이름은 바꾸지 않는다.
이 문서의 `기록.md`·`체크리스트.pdf` 같은 짧은 이름은 종류를 뜻하는 별칭이며,
실제 생성·존재 확인·전사·검증·결과 링크에는 반드시 공통 함수가 반환한 경로를 쓴다.
종류는 `체크리스트`, `기록`, `예비보고서`, `결과보고서`, `예비보고서표지`,
`결과보고서표지`, `손그림모사`, `부품그리기`, `따라그리기`, `예상결과`다.
이름 변경 전 노션 이력이 있으면 레코드의 `history_source`에 이전 원본 파일명을 보존한다.
`source`는 현재 보고서명, baseline·되읽기 경로는 `notion.history_path`로 조회하며 기존 이력을 다시 만들지 않는다.
저장 위치·예외·이력 보존 규칙은 `docs/schema/lab-artifact-naming.md`를 따른다.

## 절대 규칙

1. **페이지를 절대 덮어쓰지 않는다.** 업로드는 항상 새 페이지다. 사용자가
   노션에서 고쳤지만 아직 되읽지 않은 구간이 구조적으로 존재하고, 그 구간에
   덮어쓰면 수정이 경고 없이 사라진다.
2. **토큰을 저장소에 쓰지 않는다.** 환경변수 `NOTION_TOKEN` 에서만 읽는다.
   토큰 값을 로그·커밋·대화 어디에도 그대로 옮기지 않는다.
3. **로컬 이미지를 자동 첨부하고 검증한다.** 본문 최상위 독립 줄의 PNG/JPEG를
   원래 위치에 삽입하고 alt 설명을 정확한 캡션으로 사용한다. 이미지 위치·순서·캡션·
   원본 내용과 본문 왕복 검사를 통과하기 전에는 baseline·완료 이력을 확정하지 않는다.
   원본 파일·기존 페이지는 보존한다. 표/목록/인용/인라인/HTML 이미지와 title 속성,
   누락 파일·20 MiB 초과 파일은 원격 쓰기 전에 거절한다. 외부 HTTPS 이미지는 유지한다.
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

1. **올릴 파일을 정한다.** `config.artifact_path('<실험NN>', '예비보고서', '.md')` 또는
   `..._결과보고서.md`. 없으면 ③ `write-pre-report` / ④ `write-result-report`
   를 먼저 돌리도록 안내하고 멈춘다.

2. **업로드 전 검사.** error 가 있으면 **올리지 않고** 보고한 뒤 사용자 판단을
   기다린다. info 는 자동 첨부할 이미지 목록이다. 상대경로는 md 파일의 폴더 기준이다.
   손그림 warn("`…_결선도_….png` 의 손그림이 있다")이 나오면 올리기 전에 md 의 그 줄을
   메시지가 준 `../결선도/손그림/…` 경로로 바꾼다 — 손그림이 제출하는 그림이다.

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

4. **검증된 업로드 CLI로 새 페이지를 만든다.** 이 명령만 push 진입점으로 사용한다.
   제목·버전은 과목정보와 명세에서 읽고, 본문의 같은 첫 제목을 제거한다.
   로컬 이미지마다 독립 표식을 만들고 파일 업로드 → 해당 위치 삽입 → 내용 검증 →
   표식 삭제 → 전체 위치·캡션·내용·본문 왕복 검사 → baseline·완료 이력 순서로 진행한다.

   ```bash
   python3 -m scripts.lab.notion_sync push --source '<실험NN>/output/<파일명>.md' --kind '<예비보고서|결과보고서>'
   ```

   실행 중 페이지 제목에는 `[sync:<작업ID>]`가 붙고, 완료하면 `<보고서 제목> v<N>`이 된다.
   진행 기록은 `<output>/.notion-sync/<작업ID>/journal.json`이다.
   토큰·원격 응답 전체·서명 URL은 저장하지 않는다. 같은 output/종류 동시 작업은 거절한다.

4b. **실패하면 오류에 출력된 journal로 재개한다. 새 push를 반복하지 않는다.**

   ```bash
   python3 -m scripts.lab.notion_sync resume --journal '<오류에 표시된 journal.json 절대경로>'
   ```

   재개는 작업 페이지·이미지를 원격 조회해, 응답이 유실된 쓰기를 먼저 대조한다.
   유일한 작업 페이지 또는 이미지 후보를 확인한 때만 이어서 처리한다.
   후보가 없거나 모호한 페이지 생성, 원본 보고서·이미지 변경, 원격 본문 변경은 중단하고
   상태와 journal 경로를 보고한다. 표식 아래 사용자 하위 문단이 생겼거나 서식이 달라져도
   삭제하지 않고 중단한다. 최초 본문 스냅샷 저장 전에 끊겼다면 전송한 표식 Markdown과
   되읽기를 보수적으로 대조한다. 빈 줄 차이 외의 변환을 확증할 수 없으면(예: 표가
   HTML로 바뀐 초기 재개) 자동 재개를 중단하고 사용자에게 원격 확인을 요청한다.
   잠금 파일이나 journal을 지워 우회하지 않는다.
   이미 첨부된 이미지를 다시 넣지 않고, baseline·완료 이력도 하나만 확정한다.
   이미지 없는 보고서도 같은 경로를 사용한다.

   **이전 방식의 업로드 이력만 있고 baseline이 없는 경우** 기존 `page_id`로
   `notion.pull_markdown`을 호출해 `notion.history_path`에 저장하는 읽기 전용 복구를 쓴다.
   이력이 없는 옛 페이지는 사용자에게 URL을 확인한다. 새 journal이 소유하지 않는
   기존 페이지를 수정하거나 새 push로 대체하지 않는다.

5. **완료 결과를 확인한다.** CLI가 `status: complete`와
   `position/caption/content/roundtrip passed`를 반환해야 한다.
   검증 실패 상태를 업로드 완료로 보고하지 않는다. baseline과 이력은 CLI가 관리하므로
   수동 `append_record`나 baseline 쓰기를 추가하지 않는다.

6. **결과 안내.** 노션 URL·버전·이미지 수·위치/캡션/내용 검증·본문 왕복 검사 결과를
   한 묶음으로 전달하고, 다 고치면 "읽어와"라고 말해 달라고 안내한다.

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
   OUT, PAGE = Path('<실험NN>/output'), '<page_id>'
   rec = next(r for r in notion.load_records(OUT) if r['page_id'] == PAGE)
   text = notion.pull_markdown(PAGE, notion.load_token())
   out = notion.history_path(OUT, rec, baseline=False)
   out.write_text(text, encoding='utf-8')
   print('저장:', out, len(text), '자')
   PY
   ```

8b. **빈 그림 링크가 없는지 본다.** 이전 방식으로 올린 페이지도 같은 검사를 유지한다.

    ```bash
    python3 - <<'PY'
    from pathlib import Path
    from scripts.lab import validate, notion
    OUT, PAGE = Path('<실험NN>/output'), '<page_id>'
    rec = next(r for r in notion.load_records(OUT) if r['page_id'] == PAGE)
    p = notion.history_path(OUT, rec, baseline=False)
    f = validate.check_pulled_images(p.read_text(encoding='utf-8'))
    print('\n'.join(str(x) for x in f) or '빈 그림 없음')
    PY
    ```

    `✗`가 나오면 멈추고 해당 이미지 누락을 알린다. 이전 페이지의 빈 링크도
    검출한다. 이후 사용자가 편집한 이미지의 위치·캡션은 baseline diff로 분류하며,
    업로드 시점 배치로 자동 복원하지 않는다.

9. **baseline 과 diff 를 뜬다.** **원본이 아니라 baseline 과 비교한다** — 노션
   변환기의 노이즈가 양쪽에 똑같이 들어가 상쇄되므로, 남는 차이가 순수하게
   사용자가 고친 것이다.

   ```bash
   python3 - <<'PY'
   from pathlib import Path
   import subprocess
   from scripts.lab import notion
   OUT, PAGE = Path('<실험NN>/output'), '<page_id>'
   rec = next(r for r in notion.load_records(OUT) if r['page_id'] == PAGE)
   subprocess.run(['diff', '-u', str(notion.history_path(OUT, rec)),
                   str(notion.history_path(OUT, rec, baseline=False))], check=False)
   PY
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
    일회성 수정만 있었던 라운드는 재생성하지 않는다. **결과보고서는
    `verify-write-result-report` 가 이 대조를 맡는다** — 답안 없는 격리 트리에서
    ④·⑤ 를 다시 돌리고 승인본과 여섯 갈래로 대조한다(2026-09-12 신설). 예비보고서는
    아직 손으로 한다.

## 제출

이 스킬은 **PDF 를 만들지 않는다.** 사용자가 노션에서 `⋯ → Export → PDF` 로
본문을 내려받고, ⑥ `make-lab-report-cover` 가 만든 표지 PDF 를 앞에 손으로
붙여 제출한다.

## 비-목표

- 이전 페이지의 이미지를 소급 보정하지 않는다. 이미지 크기·정렬·PDF 쪽 나눔은 자동화하지 않는다.
- 노션 페이지를 지우거나 갈아엎지 않는다 (§절대 규칙 1).
- 체크리스트·표지·프리뷰를 올리지 않는다 (§절대 규칙 5).
- 부울식을 오버바로 승격하지 않는다 — 지금은 보수 `'` 그대로 올린다.
  `$\overline{A \cdot B}$` 렌더는 확인됐지만(`write-pre-report/SKILL.md:307`),
  승격 자체는 보류한다 — 실험6 `Q(t-1)'` 은 부울식이 아니라 상태 토큰이라
  승격하면 그 진리표가 깨진다.
