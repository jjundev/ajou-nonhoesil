---
name: make-lab-report-cover
description: 논리회로실험 보고서 표지를 한글 IEEE 윤리 강령과 함께 A4 한 장으로 생성한다. 사용자가 "2주차 예비보고서 표지", "결과보고서 표지 만들어줘", "보고서 표지" 등을 요청하거나 /make-lab-report-cover 를 호출할 때 사용한다. 제목만 받으면 학부·과목·교수·분반·학번·성명을 `.claude/과목정보.md` 에서 읽어 HTML 과 PDF 한 쌍을 만든다. 조 번호(4조)도 같은 파일에서 읽어 표지에 찍는다.
---

# make-lab-report-cover

보고서 첫 장에 들어가는 **표지 한 장**을 만든다. 한 장 안에 제목·과목 헤더,
한글 IEEE 윤리 강령 10개 항목, 서약문과 조·학번·성명 표가 다 들어간다.

**조 번호는 2026-09-12 부터 찍는다** (우리는 4조). 푸터 표의 분반과 학번
사이 「조」 칸이 `{{TEAM}}` 이고, 값은 `과목정보.md` 의 `team` 이다. 인쇄되는
값이 되었으므로 `team` 은 1b 게이트(`IDENTITY_FIELDS`)에도 다시 들어갔다.

조는 2026-09-13 에 5조에서 4조로 재편성됐다 — `과목정보.md` 의 `team` 값만
고치면 되고, 이 파일 자체는 값을 담지 않으므로 고칠 곳이 없다. 아래 예시의
"4조"는 현재 값을 보여주려는 것일 뿐, 스킬에 박힌 값이 아니다.

**한 장·한국어는 사용자가 2026-09-07 에 내린 결정이다.** 그 전에는 영문 IEEE
원문 1쪽 + 표지 1쪽의 2장 구성이었고 (2016-2 이후 코퍼스의 지배적 관행이
그 2장이다), 그보다 더 전에는 한글 강령이 표지 안에 있었다 — `c5d53f9` 가
영문 쪽과 중복이라 지운 그 블록을 되살린 것이 지금 템플릿이다. 쪽수나 언어를
다시 바꾸려면 사용자에게 묻는다. 임의로 영문 쪽을 되돌리지 않는다.

## 값의 출처

**스킬에 조 번호·학번·성명·교수명을 적지 않는다.** 전부 `.claude/과목정보.md` 에서 읽는다.
"4조" 도 템플릿에 박지 않는다 — `team` 을 읽어 `{{TEAM}}` 에 넣는다.

```bash
python3 -c "
from pathlib import Path
from scripts.lab import config
root = config.find_project_root(Path('.'))
info = config.load_course_info(root)
print(info)
"
```

`team` / `student_ids` / `student_names` 가 `~` 이면 (조 편성 전) **한 줄로 되묻고**,
사용자가 알려주면 이번 실행에만 쓰되 **`과목정보.md` 에 적어둘지 물어본다.**

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

   **주차로 불렸으면**("3주차 표지" 처럼) 아래로 옮긴다. 한 날에 실험이
   둘일 수 있어 리스트가 온다.

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

1. **제목 추출.** 사용자는 "실험1 예비보고서 표지" 처럼 부르고, **표지에 찍는 제목은 실험 기준이다** — `config.document_title(<실험번호>, <명세의 title>, '예비보고서')` 로 만든다 (`실험1 Basic Gates 예비보고서`). 무엇을 만들 표지인지 (예비보고서/결과보고서) 못 찾으면 되묻고 중단.

1b. **조 편성 확인 — 미확정이면 값을 지어내지 말고 멈춘다.** 위 「값의 출처」의
    규칙을 여기서 **실행 가능한 게이트로** 다시 둔다. 산문으로만 적혀 있던
    탓에, 절차를 1→2→3→4→5 로 따라가면 5단계에서
    `TypeError: replace() argument 2 must be str, not None` 로 죽었다.
    (③ `write-pre-report` 는 7단계에서 같은 판정을 이미 한다 — 이 스킬을
    단독 호출했을 때 그 보호가 없는 것이 문제였다.)

    ```bash
    python3 -c "
    from pathlib import Path
    from scripts.lab import config
    info = config.load_course_info(config.find_project_root(Path('.')))
    print('미확정:', config.missing_identity(info) or '없음')
    "
    ```

    - **`미확정: 없음` 이면** 그대로 진행한다.
    - **하나라도 비어 있으면** 표지를 만들지 않는다. 어떤 값이 없는지와
      `.claude/과목정보.md` 의 해당 줄을 한 줄로 알리고, 사용자가 값을 주면
      이번 실행에만 쓰되 그 파일에 적어둘지 물어본다. **`None`·빈 문자열·
      임의의 학번을 템플릿에 넣지 않는다** — 표지는 제출물의 첫 장이다.

2. **출력 폴더 결정.** 0단계에서 확인한 `<실험NN>/` 가 있으면 그 아래 `output/`.
   폴더가 없으면 **거절하고** `init-lab-experiment` 를 안내한다.

3. **충돌 확인.** `<폴더>/<제목> 표지.pdf` 가 이미 있으면 덮어쓸지 한 줄로 확인.

4. **제출일.** 사용자가 명시하지 않으면 오늘 날짜. **형식도 `과목정보.md` 에서 읽는다.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   print(config.load_course_info(config.find_project_root(Path('.')))['date_format'])
   " | xargs -I{} date +{}
   ```

5. **템플릿 치환.** 스킬 폴더의 `template.html` 을 읽고 플레이스홀더 9개를 모두 바꾼다:
   `{{TITLE}}`, `{{COURSE}}`, `{{CLASS_SECTION}}`, `{{DEPARTMENT}}`,
   `{{SUBMIT_DATE}}`, `{{PROFESSOR}}`, `{{TEAM}}`, `{{STUDENT_IDS}}`, `{{STUDENT_NAMES}}`

   `{{TEAM}}` 은 `team` 값(`4조`)을 **그대로** 넣는다 — 값에 이미 "조" 가
   붙어 있으니 덧붙이지 않는다. `scripts/lab/merge_report.py` 도 같은 템플릿을
   자체 치환표로 채우므로, 플레이스홀더를 늘리면 그쪽 표도 같이 늘린다.

6. **HTML 저장 → PDF 변환.**

   ```bash
   python3 -c "
   from pathlib import Path
   from scripts.lab import config
   from scripts.lab.html2pdf import DEFAULT_CHROME, html_to_pdf
   info = config.load_course_info(config.find_project_root(Path('.')))
   html_to_pdf('<폴더>/<제목> 표지.html', '<폴더>/<제목> 표지.pdf',
               chrome=info.get('chrome') or DEFAULT_CHROME)
   "
   ```

   **`chrome=` 를 반드시 넘긴다.** 안 넘기면 `과목정보.md` 의 `chrome` 필드가
   선언만 되고 아무 효과가 없어, 크롬 위치를 바꿔도 반영되지 않는다.

   `chrome` 은 macOS·Windows 경로 **목록**이다. `html_to_pdf` 가 그중 이
   머신에 실재하는 첫 경로를 고르므로 기기를 바꿔도 아무것도 고치지 않는다.
   "Chrome 을 찾을 수 없습니다" 가 나오면 시도한 경로가 에러에 다 찍힌다 —
   그 기기의 실제 경로를 목록에 한 줄 추가한다.

   실패하면 에러를 그대로 보여주고 **HTML 은 남긴다.**

7. **A4 실측.** 이 템플릿은 `@page { size: A4; margin: 0; }` + 하드코딩된
   `210mm × 297mm` `.page` 박스를 쓴다 — 여백을 CSS 가 아니라 콘텐츠
   패딩으로 흉내 내는, 이 저장소에서 가장 취약한 페이지 설정이다. 아래를
   돌려 **쪽수가 1이고** 그 한 쪽이 210×297mm 인지 확인한다. 강령 10개 항목이
   한 장을 채우는 구성이라 폰트·여백을 조금만 키워도 2쪽으로 터진다 — 쪽수를
   같이 보는 이유다. 어긋나면 CSS 를 고치고 다시 낸다.

   ```bash
   python3 -c "
   from pypdf import PdfReader
   pages = PdfReader('<폴더>/<제목> 표지.pdf').pages
   print('쪽수:', len(pages))
   for p in pages:
       print(round(float(p.mediabox.width)/72*25.4,1),
             round(float(p.mediabox.height)/72*25.4,1))
   "
   ```

8. **AI 활용 로그.** `과목정보.md` 의 `ai_usage_log` 가 `~` 가 아니면 그 경로에
   한 줄 추가한다. `~` 면 아무것도 하지 않는다.

9. **결과 안내.** HTML·PDF 두 파일의 마크다운 링크를 한 줄로 출력.

## 자연어 오버라이드

"교수님 김철수로", "분반 D012-1", "제출일 2026.09.20" 처럼 같이 말하면
해당 필드만 바꾼다. 별도 옵션 문법은 없다. 명시되지 않은 필드는 `과목정보.md` 값을 쓴다.

## 비-목표

- 예비/결과 표지를 다른 템플릿으로 나누지 않는다 (제목 문자열만 다르다).
- 윤리 강령을 표지에서 떼어 별도 쪽으로 만들지 않는다 (한 장 구성이다).
- 과목 정보를 스킬 안에 영속 저장하지 않는다 (`과목정보.md` 가 단일 소스다).
