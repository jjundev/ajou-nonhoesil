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

0. **주차로 불렸으면 폴더를 코드로 옮긴다.** 매핑은 1:1 이 아니다(실험4 는 7주차).

   ```bash
   python3 -c "
   from scripts.lab import config
   print(config.folder_for_week(<N>))
   "
   ```

   사용자가 `실험N` 으로 불렀으면 `config.experiment_dir(<N>)` 을 쓴다.

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

   ```bash
   python3 - <<'PY'
   from datetime import datetime
   from pathlib import Path
   from scripts.lab import config, notion
   OUT, NAME, KIND = Path('<실험NN>/output'), '<파일명>.md', '<예비보고서|결과보고서>'
   root = config.find_project_root(Path('.'))
   info = config.load_course_info(root)
   token = notion.load_token()
   text = (OUT / NAME).read_text(encoding='utf-8')
   page = notion.push_markdown(text, info['notion_parent_page_id'], token)
   rec = notion.append_record(OUT, KIND, page['page_id'], page['url'], NAME,
                              datetime.now().strftime('%Y-%m-%d %H:%M'))
   base = OUT / f"{NAME[:-3]}_notion_baseline_v{rec['version']}.md"
   base.write_text(notion.pull_markdown(page['page_id'], token), encoding='utf-8')
   print('v', rec['version'], page['url'])
   print('baseline', base)
   PY
   ```

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
- 부울식을 오버바로 승격하지 않는다 — 지금은 보수 `'` 그대로 올린다. 프로브에서
  `$\overline{A \cdot B}$` 렌더가 확인되면 그때 승격 규칙을 연다.
