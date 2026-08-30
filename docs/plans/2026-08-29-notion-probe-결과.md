# 노션 API 프로브 결과 (2026-08-29)

계획서 `2026-08-29-notion-report-loop.md` Task 1 의 산출물. 실측값이며,
`scripts/lab/notion.py` 와 `scripts/lab/validate.py` 의 상수·분기가 이 문서를 근거로 한다.

부모 페이지: `3cbb06d263bc80ecbbeec20761dc3f92` (`.claude/과목정보.md` 의 `notion_parent_page_id`)
API 버전: `2026-03-11` · integration 종류: **internal**

## 결론 요약

| 항목 | 결과 |
|---|---|
| `POST /v1/pages` 의 `markdown` 파라미터 | **작동한다.** md→블록 JSON 변환기가 필요 없다 |
| 응답의 page id 키 / URL 키 | `id` / `url` (`public_url` 도 함께 온다) |
| 첫 `#` 헤딩 | **페이지 제목으로 흡수되고 본문에서 사라진다** |
| `GET /v1/pages/{id}/markdown` | **internal integration 에서 열린다.** 자동 되읽기 가능 |
| 되읽기 응답에서 마크다운이 담긴 키 | `markdown` |
| 되읽기 응답의 다른 키 | `id`, `object`, `request_id`, `truncated`, `unknown_block_ids` |

## 왕복에서 보존되는 것

- `##` 이하 헤딩 — 텍스트 그대로
- `> 인용` — `>` 형태 그대로 (이 보고서들의 `> 출처:` 근거 표기가 살아남는다)
- 산문 텍스트

## 왕복에서 **변형되는** 것

### 1. 파이프 표 → HTML `<table>` (이것이 가장 중요하다)

올린 것:

    | A | B | C |
    |---|---|---|
    | 0 | 0 | 0 |

되읽은 것:

    <table header-row="true">
    <tr>
    <td>A</td>
    <td>B</td>
    <td>C</td>
    </tr>
    <tr>
    <td>0</td>
    ...
    </table>

**`md.parse_tables()` 는 파이프 표만 인식하므로 되읽은 문서에서 표를 0개로 센다.**
`validate.markdown_shape` 가 이 형태를 함께 세지 않으면 `check_notion_roundtrip` 이
매 업로드마다 "표가 N개에서 0개로 줄었다"를 띄워, 진짜 손실을 가리는 잡음이 된다.

`header-row="true"` 일 때 첫 `<tr>` 은 헤더다 — `MdTable.rows` 는 헤더를 빼고 세므로
행 수를 맞추려면 여기서도 빼야 한다.

### 2. 인라인 수식에 백틱이 붙는다

올린 `$\overline{A \cdot B}$` → 되읽으면 ``$`\overline{A \cdot B}`$``.
질문 8에서 미룬 "보수 `'` → LaTeX 오버바 승격" 을 나중에 열 때, 왕복 후 형태가
입력과 다르다는 점을 baseline 이 흡수한다(원본이 아니라 baseline 과 비교하는 이유).

### 3. 빈 줄이 사라진다

블록 사이의 빈 줄이 제거된다. 문단 경계가 줄바꿈 하나로 바뀐다 — 예상했던 잡음이며,
구조 불변량만 보는 설계가 이걸 무시한다.

## 후속 조치로 닫힌 항목

- **오버바 렌더 여부** — 확인됨. 인라인 수식 `$\overline{A \cdot B}$` 는 노션
  화면에서 실제 오버바로 렌더된다(`write-pre-report/SKILL.md:307` 에서 실측
  확인). 다만 보수 `'` → 오버바 승격 자체는 아직 열지 않고 보류한다 — 실험6
  `Q(t-1)'` 은 부울식이 아니라 상태 토큰이라, 승격하면 그 진리표가 깨진다.
- **`truncated` / `unknown_block_ids` 가 언제 참이 되는지** — 언제 참이 되는지의
  실측은 여전히 없다. 대신 `pull_markdown` (`scripts/lab/notion.py`) 이
  `truncated: true` 를 받으면 baseline 을 저장하지 않고 `NotionError` 를 던지도록
  바뀌었다 — `check_notion_roundtrip` 은 baseline 대비 손실만 보므로, 잘린
  baseline 이 한 번이라도 조용히 저장되면 이후의 진짜 손실이 영영 안 보이게 된다.
  언제 참이 되는지 몰라도 상관없다: 참이 되는 순간 조용히 넘어가지 않고 그 자리에서
  드러나므로, 실험01 예비보고서(19.5KB) 파일럿에서 걸리더라도 baseline 이 잘린 채
  굳는 대신 즉시 실패로 알 수 있다.
- **상대경로 이미지가 노션에서 어떤 블록이 되는지** — 실측했다: 깨진 이미지도
  텍스트도 아니라 **경로 자체가 통째로 비워진다.**
  `![브레드보드 작도 캔버스](../../.claude/assets/Breadboard.jpg)` 를 올리고
  되읽으면 `![브레드보드 작도 캔버스]()` 로 돌아온다(`실험01/output/실험01_예비보고서.md`
  291행 ↔ `실험01/output/실험01_예비보고서_notion_baseline_v6.md` 791행 대조 —
  경로가 사라졌을 뿐 문자열로 남지도 않는다). 저장소 내부 경로가 노션 페이지
  어디에도 눈에 보이는 형태로 남지 않으므로, 보고서 md 는 상대경로 이미지를
  학생이 노션에서 손으로 교체할 자리 표시로 그대로 실어도 안전하다.
