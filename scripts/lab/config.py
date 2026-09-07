"""`.claude/` 아래 설정 파일 로더.

양식을 스킬에 하드코딩하지 않기 위한 모듈이다 (R1). 양식이 연도마다·학생마다
다르고 이번 학기 것이 미확정이므로, 섹션 목록은 반드시 여기를 거쳐 읽는다.
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from . import md

COURSE_INFO = ".claude/과목정보.md"
REPORT_FORMAT = ".claude/보고서양식.md"

# 조 편성이 확정돼야 채워지는 신원 필드. 표지에 찍히는 값이라 비면 지어내지 않는다.
#
# `team` 은 2026-09-07 에 뺐다. 이 분반은 조 번호를 주지 않아 채울 값이 없는데,
# 게이트에 있는 동안에는 표지가 영원히 "미확정: team" 으로 멈췄다. 어느 템플릿도
# 조 번호를 인쇄하지 않으므로 제출물에 빈 칸이 생기지도 않는다. **여기 있는 이름은
# 전부 실제로 표지에 찍히는 값이어야 한다** — 안 찍히는 값을 게이트에 두면
# 채울 방법이 없는 필드가 산출물을 막는다.
IDENTITY_FIELDS = ("student_ids", "student_names")

# 실험은 1~10 뿐이다. FPGA(13~15주차)는 실험 번호가 없어 `프로젝트/` 로 간다.
EXPERIMENT_COUNT = 10

# 주차 산출물이 사는 **위치**. 실험 폴더는 저장소 루트가 아니라 이 아래에 있다
# (`보고서/실험01/...`). 이름 규칙(`실험NN`)과는 **다른 규칙**이라 상수를 따로
# 둔다 — 2026-09 에 폴더 여섯을 루트에서 여기로 옮겼을 때 이름 규칙만 한 곳에
# 모여 있고 위치는 어디에도 없어서, `config.py` 가 안 고쳐진 것을 아무도 못
# 봤다. 아홉 스킬 전부가 없는 경로를 열었다. 위치를 옮기는 결정이 또 오면
# **여기 한 줄만** 고친다. 문자열로 베끼지 않는다.
EXPERIMENT_BASE = "보고서"


def experiment_folder_name(experiment: int) -> str:
    """실험 번호 → 폴더 **이름**. 두 자리로 0 을 채운다. 위치는 붙이지 않는다.

    0 을 안 채우면 사전순 정렬이 `실험1, 실험10, 실험2, ...` 가 되어 시간
    순서와 어긋난다. 규칙을 여기 한 곳에만 두는 이유는, 이 저장소의 반복
    결함이 "같은 규약을 세 곳에 적용하고 네 번째를 잊는 것"이기 때문이다.

    경로가 필요하면 `experiment_dir` 을 쓴다. 이름만 필요한 곳은 실질적으로
    한 군데뿐이다 — `validate.check_folder_convention` 이 명세가 놓인 폴더의
    조부모 **이름** 과 견주는 자리다.
    """
    if isinstance(experiment, bool) or not isinstance(experiment, int):
        raise TypeError(f"실험 번호는 정수여야 합니다: {experiment!r}")
    if not 1 <= experiment <= EXPERIMENT_COUNT:
        raise ValueError(
            f"실험 번호는 1~{EXPERIMENT_COUNT} 입니다: {experiment}. "
            f"FPGA 프로젝트는 실험 번호가 없으므로 `{PROJECT_DIR}/` 를 씁니다."
        )
    return f"실험{experiment:02d}"


def experiment_dir(experiment: int) -> str:
    """실험 번호 → 저장소 루트 기준 **경로**(`보고서/실험01`).

    스킬이 폴더를 얻는 입구는 이것과 `manual_candidates` 둘뿐이고, 둘 다
    여기를 거치거나 `EXPERIMENT_BASE` 를 같은 방식으로 붙인다.
    """
    return f"{EXPERIMENT_BASE}/{experiment_folder_name(experiment)}"


# 루트에서 실험 폴더까지의 깊이. `보고서/실험01` 이면 2 다.
EXPERIMENT_DIR_DEPTH = len(Path(EXPERIMENT_BASE).parts) + 1


def root_relative_prefix(subfolder_depth: int = 1) -> str:
    """실험 폴더 아래 `subfolder_depth` 겹 안에서 저장소 루트까지의 `../` 사슬.

    `보고서/실험01/체크리스트/체크리스트.html` 이 `.claude/assets/` 의 그림을
    가리킬 때 쓴다. **직접 세지 않는다** — 기반 폴더가 한 겹 늘거나 줄면 이
    사슬도 같이 변해야 하는데, `../../` 를 문자열로 박아 두면 그 연결이 끊긴다.
    실제로 2026-09 이동에서 브레드보드 그림이 정확히 이 방식으로 끊겼다.
    깨져도 HTML 은 렌더되고 그림 자리만 비므로 눈으로는 놓치기 쉽다.
    """
    if isinstance(subfolder_depth, bool) or not isinstance(subfolder_depth, int):
        raise TypeError(f"깊이는 정수여야 합니다: {subfolder_depth!r}")
    if subfolder_depth < 0:
        raise ValueError(f"깊이는 0 이상이어야 합니다: {subfolder_depth}")
    return "../" * (EXPERIMENT_DIR_DEPTH + subfolder_depth)


# 과거 학기 교안 원본이 사는 곳. 이름이 `실험N.pdf` 로 정규화돼 있다.
MANUAL_ARCHIVE = "from_the_past/정리/강의노트"

# 이번 학기(2026-2) 교안이 배포되는 곳. 저장소 루트의 폴더 하나에 열 주차가
# 다 들어오고, **파일 이름에 제목이 붙는다** (`실험1. Basic Gates.pdf`).
# 번호만으로 이름을 만들 수 없어서 이 후보만 디스크를 훑는다.
MANUAL_DISTRIBUTION = "강의노트"


def _distributed_manual(experiment: int, root: Path) -> Optional[Path]:
    """배포 폴더에서 그 주차 교안을 찾는다. 없으면 `None`.

    **하위 폴더까지 훑는다.** 조교가 배포 폴더 안을 재편하면(2026-09-07 에
    실제로 파일 다섯이 `공지사항/` 으로 내려갔다) 비재귀 탐색은 조용히 실패해
    아카이브의 과거 학기 판으로 떨어진다. 아카이브에 늘 같은 번호 파일이
    있으므로 "교안을 못 찾았다"로 드러나지도 않는다.

    번호 뒤가 **숫자가 아니어야** 한다. `실험1` 로 앞자리만 맞추면
    `실험10`·`실험11`·`실험12` 를 집어삼킨다 — 이 과목은 실험이 10 개라
    한 자리와 두 자리가 실제로 섞인다.

    같은 번호가 여럿이면 경로순 첫 개를 쓴다. 얕은 것이 먼저 오도록
    (깊이, 경로) 로 정렬한다 — 최상위 배포본이 하위 사본을 이긴다.
    """
    folder = root / MANUAL_DISTRIBUTION
    if not folder.is_dir():
        return None
    pattern = re.compile(rf"^실험{experiment}(?!\d)")
    hits = sorted(
        (f for f in folder.rglob("*")
         if f.is_file() and f.suffix.lower() == ".pdf"
         and pattern.match(f.name)),
        key=lambda f: (len(f.relative_to(folder).parts), str(f)),
    )
    if not hits:
        return None
    return Path(MANUAL_DISTRIBUTION) / hits[0].relative_to(folder)


def manual_candidates(experiment, root=None) -> list:
    """실험 번호 → 교안 PDF 후보 경로. 우선순위 순서다.

    **폴더는 0 을 채우고 파일 이름은 안 채운다** — `실험04/강의노트/실험4.pdf`
    처럼 한 경로에 두 형식이 섞여 있다. 손으로 옮기면 두 자리 번호에서
    반드시 어긋난다. 그래서 이 규칙을 여기 한 곳에만 둔다.

    **아카이브 후보에는 `EXPERIMENT_BASE` 를 붙이지 않는다.** 과거 학기 원본
    아카이브는 `보고서/` 밖에 산다. 후보 목록 전체에 기반 경로를 일괄로
    붙이면 이쪽이 조용히 없는 경로가 되고, 스킬은 "교안을 못 찾았다"로
    넘어가 원인이 한참 뒤에 드러난다.

    **배포본이 주차 폴더 사본보다 먼저다.** 사본은 언제나 다른 데서 복사해
    온 것이라 배포본보다 새로울 수 없고, `init-lab-experiment` 가 만들던
    사본은 실제로 과거 학기 아카이브 사본이었다. 사본이 앞서면 그 낡은
    판본이 배포본을 조용히 가린다.

    2026-09 에 실험1 이 어긋난 것은 그보다 한 단계 앞이다 — 배포 폴더가
    후보 목록에 **아예 없어서** 아홉 스킬 전부가 아카이브의 2020-2 판을
    열었다. 두 판은 쪽수만 다른 게 아니라(13 쪽 vs 15 쪽) 실험 항목 구성이
    3 개 vs 5 개로 다르고, OR·NOR 의 IC 지정 유무도 다르다. 어느 쪽도
    "못 찾았다"로 드러나지 않는다 — 아카이브에 같은 번호의 파일이 늘 있기
    때문에 조용히 옛것을 연다. 그래서 배포본을 후보에 넣는 것과 사본보다
    앞세우는 것을 같이 한다.

    반환 길이가 고정이 아니다. 배포본은 실재할 때만 들어간다 — 후보를
    **번호로 집지 말고** `MANUAL_ARCHIVE`·`MANUAL_DISTRIBUTION` 로 가른다.
    """
    folder = experiment_dir(experiment)     # 번호 유효성·위치는 한 곳에서만 정한다
    name = f"실험{experiment}.pdf"          # 0 을 채우지 않는다
    distributed = _distributed_manual(experiment, Path(root) if root else Path("."))
    return [
        *([distributed] if distributed else []),
        Path(folder) / "강의노트" / name,
        Path(MANUAL_ARCHIVE) / name,
    ]


# 2026-2 실험 일정. 정본은 `강의노트/공지사항/2026-2_논리회로실험 운영계획
# (26.09.01).pdf` p1 이다.
#
# **실험 번호가 열쇠다.** 예전에는 주차가 열쇠였는데(`WEEK_TO_EXPERIMENT`),
# 그 모델로는 두 가지를 표현할 수 없었다 — 9/18 처럼 한 날에 실험이 둘인 경우
# (int→int 라 하나만 담긴다), 그리고 추석·중간고사처럼 실험이 없는 주(예외 표를
# 따로 들고 다녀야 했다). 실험을 열쇠로 두면 둘 다 사라진다. 같은 날짜를 두
# 실험이 가지면 그만이고, 실험이 없는 날은 그냥 이 표에 없다.
#
# **이 표를 스킬 문서에 베끼지 않는다.** 옛 주차표는 아홉 스킬에 문장으로
# 베껴져 있었고("실험4는 7주차다"), 운영계획이 바뀌자 열한 곳이 한꺼번에
# 거짓이 됐다.
EXPERIMENT_DATES = {
    1: date(2026, 9, 11),
    2: date(2026, 9, 18),
    3: date(2026, 9, 18),   # 실험2 와 같은 날. 8시 20분까지 둘 다 마쳐야 한다
    4: date(2026, 10, 2),
    5: date(2026, 10, 9),
    6: date(2026, 10, 16),
    7: date(2026, 10, 30),
    8: date(2026, 11, 6),
    9: date(2026, 11, 13),
    10: date(2026, 11, 20),
}

# FPGA 텀프로젝트 — 3주치가 한 프로젝트다. 실험 번호가 없어 `PROJECT_DIR` 로 간다.
PROJECT_DATES = (date(2026, 11, 27), date(2026, 12, 4), date(2026, 12, 11))

# FPGA 프로젝트도 주차 산출물이라 실험 폴더와 같은 기반 아래 둔다.
PROJECT_DIR = f"{EXPERIMENT_BASE}/프로젝트"


# 1주차 날짜. 운영계획 p1 의 첫 행이다(9/4 오리엔테이션).
# **표가 아니라 앵커 하나다.** 주차 → 날짜는 여기서 나오는 순수 산술이고,
# 날짜 → 실험은 EXPERIMENT_DATES 가 맡는다. 정본이 둘로 갈리지 않는다.
# 옛 WEEK_TO_EXPERIMENT 는 회전을 손으로 적어 둔 표라 운영계획이 바뀌자
# 다섯 곳이 한꺼번에 틀렸다 — 산술에는 그 실패 모드가 없다.
SEMESTER_WEEK1 = date(2026, 9, 4)
SEMESTER_WEEKS = 16


def _check_week(week) -> None:
    if isinstance(week, bool) or not isinstance(week, int):
        raise TypeError(f"주차는 정수여야 합니다: {week!r}")
    if not 1 <= week <= SEMESTER_WEEKS:
        raise ValueError(f"주차는 1~{SEMESTER_WEEKS} 입니다: {week}")


def week_date(week: int) -> date:
    """주차 → 그 주 수업 날짜."""
    _check_week(week)
    return SEMESTER_WEEK1 + timedelta(weeks=week - 1)


def is_project_week(week: int) -> bool:
    """주차 → FPGA 프로젝트(13~15주차) 주차인지.

    **`PROJECT_DATES` 에서 도출한다 — 주차 번호를 여기 새로 적지 않는다.**
    옛 `folder_for_week` 만 이 판정을 알았고, 주차 모델을 걷어내며 그 지식이
    통째로 사라졌다 — `experiments_in_week` 가 빈 리스트를 주는 두 가지
    이유(실험이 없는 주 / FPGA 주)를 스킬이 다시 가를 수 있게 이 함수가
    그 자리를 메운다. `week_date` 로 얻은 그 주 날짜가 `PROJECT_DATES` 에
    있는지만 본다 — 정본이 둘로 갈리지 않는다.
    """
    return week_date(week) in PROJECT_DATES


def experiments_in_week(week: int) -> list:
    """주차 → 그 주에 하는 실험 번호들. 실험이 없는 주면 빈 리스트.

    **리스트인 것이 요점이다.** 3주차(9/18)는 실험2·3 을 한 날에 하고,
    4주차(추석)·8주차(중간고사)·1주차(오리엔테이션)는 빈 리스트다.
    """
    _check_week(week)
    return experiments_on(week_date(week))


def experiment_date(experiment: int) -> date:
    """실험 번호 → 그 실험을 하는 날."""
    if isinstance(experiment, bool) or not isinstance(experiment, int):
        raise TypeError(f"실험 번호는 정수여야 합니다: {experiment!r}")
    if experiment not in EXPERIMENT_DATES:
        raise ValueError(
            f"실험 번호는 1~{EXPERIMENT_COUNT} 입니다: {experiment}"
        )
    return EXPERIMENT_DATES[experiment]


def experiments_on(when: date) -> list:
    """그 날 하는 실험 번호들. 실험이 없는 날이면 빈 리스트.

    **리스트인 것이 요점이다.** 9/18 은 실험2·3 을 한 날에 한다.
    """
    if not isinstance(when, date):
        raise TypeError(f"날짜여야 합니다: {when!r}")
    return sorted(e for e, d in EXPERIMENT_DATES.items() if d == when)


def next_experiments(today=None):
    """오늘 이후(당일 포함) 가장 가까운 실험일과 그 날의 실험들.

    학기가 끝났으면 `None`. 스킬이 "이번에 뭘 준비해야 하나"를 물을 때 쓴다.
    """
    if today is None:
        today = date.today()
    if not isinstance(today, date):
        raise TypeError(f"날짜여야 합니다: {today!r}")
    upcoming = sorted({d for d in EXPERIMENT_DATES.values() if d >= today})
    if not upcoming:
        return None
    return upcoming[0], experiments_on(upcoming[0])


# 산출물 제목의 유일한 형식. 예전에는 네 곳이 제각각 만들었고, 경로용 일괄
# 치환이 그중 하나(프리뷰)를 조용히 덮어쓴 적이 있다.
DOCUMENT_KINDS = ("체크리스트", "기록", "예비보고서", "결과보고서", "프리뷰")


def document_title(experiment: int, title: str, kind: str) -> str:
    """산출물 제목 — `실험1 Basic Gates 체크리스트` 형식.

    **주차를 넣지 않는다.** 주차는 이제 쓰지 않고, 사람이 읽는 제목에는
    실험 번호와 이름만 남긴다. 어느 주에 하는지는 강의계획서의 일이지
    제출물 표지의 일이 아니다.
    """
    if kind not in DOCUMENT_KINDS:
        raise ValueError(f"산출물 종류는 {list(DOCUMENT_KINDS)} 입니다: {kind!r}")
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"실험 제목이 비어 있습니다: {title!r}")
    experiment_folder_name(experiment)  # 번호 유효성은 한 곳에서만 판정한다
    return f"실험{experiment} {title.strip()} {kind}"


@dataclass
class Section:
    name: str
    repeat: Optional[str] = None   # None | "per-item"
    generate: bool = True


@dataclass
class ReportFormat:
    preset: str
    pre: list
    result: list


def find_project_root(start) -> Path:
    """`.claude/` 를 가진 가장 가까운 상위 디렉토리를 찾는다."""
    cur = Path(start).resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / ".claude").is_dir():
            return candidate
    raise FileNotFoundError(
        f"{start} 위쪽에서 `.claude/` 를 찾지 못했습니다. "
        "논회실 프로젝트 안에서 실행하세요."
    )


def load_course_info(root) -> dict:
    text = (Path(root) / COURSE_INFO).read_text(encoding="utf-8")
    info, _ = md.split_frontmatter(text)
    for required in ("department", "course", "professor", "class_section"):
        if not info.get(required):
            raise ValueError(f"과목정보.md 에 {required} 가 없습니다")
    info.setdefault("ai_usage_log", None)
    # 노션 업로드 대상 부모 페이지. 토큰은 여기 두지 않는다 — 이 파일은 git 에
    # 추적된다. 토큰은 환경변수 NOTION_TOKEN 에서만 읽는다 (scripts/lab/notion.py).
    info.setdefault("notion_parent_page_id", None)
    return info


def missing_identity(info) -> list:
    """`과목정보.md` 의 신원 필드 중 아직 `~` 인 것들을 이름 순서대로 돌려준다.

    표지를 내는 경로(⑥ `make-lab-report-cover`)와 표지 병합 여부를 정하는
    경로(③ `write-pre-report` 7단계)가 같은 판정을 쓰게 하려고 함수로 뺐다.
    산문 규칙으로만 두었을 때 ⑥ 이 그것을 건너뛰고 `None` 을 템플릿에 치환해
    `TypeError` 로 죽은 적이 있다.
    """
    return [k for k in IDENTITY_FIELDS if not info.get(k)]


def _section_body(body: str, name: str):
    """`# name` 헤딩부터 다음 `# ` 헤딩 직전까지를 잘라낸다.

    프리셋 절의 산문에 열 0 의 `# ` 를 쓰면 다음 프리셋 헤딩과 구별되지 않아
    블록이 일찍 잘린다. 보고서양식.md 안에서 `# ` 는 프리셋 헤딩 전용이다.
    """
    lines = body.split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.strip() == f"# {name}":
            start = i + 1
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].startswith("# "):
            end = j
            break
    return "\n".join(lines[start:end])


def _sections(raw) -> list:
    out = []
    for entry in raw or []:
        if not isinstance(entry, dict) or "name" not in entry:
            raise ValueError(f"섹션 항목에 name 이 없습니다: {entry!r}")
        out.append(Section(
            name=entry["name"],
            repeat=entry.get("repeat"),
            generate=entry.get("generate", True),
        ))
    return out


def load_report_format(root, preset=None) -> ReportFormat:
    text = (Path(root) / REPORT_FORMAT).read_text(encoding="utf-8")
    front, body = md.split_frontmatter(text)
    preset = preset or front.get("preset")
    if not preset:
        raise ValueError("보고서양식.md 프론트매터에 preset 이 없습니다")

    block = _section_body(body, preset)
    if block is None:
        raise ValueError(
            f"보고서양식.md 에 '# {preset}' 프리셋이 없습니다. "
            "사용 가능: 교집합, 배포양식형, 항목반복형"
        )

    # 프리셋 본문에서 `예비보고서:` / `결과보고서:` 블록만 뽑는다.
    keep, capture = [], False
    for line in block.split("\n"):
        if line.startswith(("예비보고서:", "결과보고서:")):
            capture = True
        elif line.strip() and not line.startswith((" ", "\t")):
            capture = False
        if capture:
            keep.append(line)

    data = md.parse_block("\n".join(keep)) if keep else {}
    fmt = ReportFormat(
        preset=preset,
        pre=_sections(data.get("예비보고서")),
        result=_sections(data.get("결과보고서")),
    )
    # 빈 섹션 목록은 정상적인 결과가 아니다. 이 파일은 조교 안내가 오면 학기 중에
    # 손으로 고칠 물건이라, 키 한 줄이 들여쓰기되는 정도의 실수가 실제로 일어난다.
    # 조용히 빈 목록을 돌려주면 이후 모든 보고서 스킬이 섹션 없는 보고서를
    # 오류 없이 만들어낸다. 시끄럽게 실패하는 편이 낫다.
    if not fmt.pre or not fmt.result:
        raise ValueError(
            f"보고서양식.md 의 '{preset}' 프리셋에서 섹션을 읽지 못했습니다 "
            f"(예비 {len(fmt.pre)}개 / 결과 {len(fmt.result)}개). "
            "`예비보고서:` 와 `결과보고서:` 가 각각 열 0 에서 시작하는지, "
            "그 아래 항목이 `  - {name: ...}` 형태인지 확인하세요."
        )
    return fmt
