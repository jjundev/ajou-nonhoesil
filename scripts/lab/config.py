"""`.claude/` 아래 설정 파일 로더.

양식을 스킬에 하드코딩하지 않기 위한 모듈이다 (R1). 양식이 연도마다·학생마다
다르고 이번 학기 것이 미확정이므로, 섹션 목록은 반드시 여기를 거쳐 읽는다.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import md

COURSE_INFO = ".claude/과목정보.md"
REPORT_FORMAT = ".claude/보고서양식.md"

# 조 편성이 확정돼야 채워지는 신원 필드. 표지에 찍히는 값이라 비면 지어내지 않는다.
IDENTITY_FIELDS = ("team", "student_ids", "student_names")

# 실험은 1~10 뿐이다. FPGA(13~15주차)는 실험 번호가 없어 `프로젝트/` 로 간다.
EXPERIMENT_COUNT = 10


def experiment_dir(experiment: int) -> str:
    """실험 번호 → 폴더 이름. 두 자리로 0 을 채운다.

    0 을 안 채우면 사전순 정렬이 `실험1, 실험10, 실험2, ...` 가 되어 시간
    순서와 어긋난다. 규칙을 여기 한 곳에만 두는 이유는, 이 저장소의 반복
    결함이 "같은 규약을 세 곳에 적용하고 네 번째를 잊는 것"이기 때문이다.
    """
    if isinstance(experiment, bool) or not isinstance(experiment, int):
        raise TypeError(f"실험 번호는 정수여야 합니다: {experiment!r}")
    if not 1 <= experiment <= EXPERIMENT_COUNT:
        raise ValueError(
            f"실험 번호는 1~{EXPERIMENT_COUNT} 입니다: {experiment}. "
            "FPGA 프로젝트는 실험 번호가 없으므로 `프로젝트/` 를 씁니다."
        )
    return f"실험{experiment:02d}"


# 과거 학기 교안 원본이 사는 곳. 2026-2 교안이 배포되면 각 주차 폴더의
# `강의노트/` 로 들어오고 그쪽이 우선한다.
MANUAL_ARCHIVE = "from_the_past/정리/강의노트"


def manual_candidates(experiment) -> list:
    """실험 번호 → 교안 PDF 후보 경로. 우선순위 순서다.

    **폴더는 0 을 채우고 파일 이름은 안 채운다** — `실험04/강의노트/실험4.pdf`
    처럼 한 경로에 두 형식이 섞여 있다. 손으로 옮기면 7주차(실험4)에서
    반드시 어긋난다. 그래서 이 규칙을 여기 한 곳에만 둔다.
    """
    folder = experiment_dir(experiment)     # 번호 유효성은 한 곳에서만 판정한다
    name = f"실험{experiment}.pdf"          # 0 을 채우지 않는다
    return [Path(folder) / "강의노트" / name, Path(MANUAL_ARCHIVE) / name]


# 주차 → 실험 매핑. **1:1 이 아니다** — 5·6·7주차가 실험 5·6·4 로 어긋난다.
# 이 표를 스킬 문서에 베껴 두면 한 곳만 고쳐지고 나머지가 틀어진다.
WEEK_TO_EXPERIMENT = {2: 1, 3: 2, 4: 3, 5: 5, 6: 6, 7: 4,
                      9: 7, 10: 8, 11: 9, 12: 10}
PROJECT_WEEKS = (13, 14, 15)   # FPGA 텀프로젝트 — 3주치가 한 프로젝트다
PROJECT_DIR = "프로젝트"
NO_ARTIFACT_WEEKS = {8: "중간고사"}


def folder_for_week(week: int) -> str:
    """주차 → 그 주 산출물이 들어갈 폴더 이름.

    사용자는 "2주차 체크리스트" 처럼 **주차로 부른다.** 스킬 절차의 경로는
    `실험NN/` 이므로 그 사이를 옮기는 곳이 필요한데, 표를 스킬마다 베껴 두면
    한 곳만 고쳐진다 — 이 저장소가 반복해 온 결함이다.
    """
    if isinstance(week, bool) or not isinstance(week, int):
        raise TypeError(f"주차는 정수여야 합니다: {week!r}")
    if week in NO_ARTIFACT_WEEKS:
        raise ValueError(
            f"{week}주차는 {NO_ARTIFACT_WEEKS[week]}라 실험 산출물이 없습니다. "
            "폴더를 만들지 않습니다."
        )
    if week in PROJECT_WEEKS:
        return PROJECT_DIR
    if week not in WEEK_TO_EXPERIMENT:
        raise ValueError(
            f"{week}주차에 해당하는 실험이 없습니다. "
            f"실험 주차는 {sorted(WEEK_TO_EXPERIMENT)}, "
            f"FPGA 는 {list(PROJECT_WEEKS)} 입니다."
        )
    return experiment_dir(WEEK_TO_EXPERIMENT[week])


def experiment_for_week(week: int) -> int:
    """주차 → 그 주 실험 번호(정수).

    `folder_for_week` 는 경로용 폴더 이름을 문자열로 주는데, 교안 파일
    이름(`manual_candidates`)은 정수 실험 번호를 요구한다. 폴더 이름에서
    번호를 되파싱하면(`실험10` → `10`) `실험NN` 규약이 스킬 문서로 새어
    나온다 — 그 규약은 `experiment_dir` 한 곳에만 있어야 한다. 그래서
    스킬 절차가 폴더 이름과 실험 번호를 **둘 다** 코드로 구하도록 이
    함수를 둔다. `프로젝트`(13~15주차)는 실험 번호가 없으므로 거절한다.
    """
    if isinstance(week, bool) or not isinstance(week, int):
        raise TypeError(f"주차는 정수여야 합니다: {week!r}")
    if week in NO_ARTIFACT_WEEKS:
        raise ValueError(
            f"{week}주차는 {NO_ARTIFACT_WEEKS[week]}라 실험 산출물이 없습니다. "
            "폴더를 만들지 않습니다."
        )
    if week in PROJECT_WEEKS:
        raise ValueError(
            f"{week}주차는 FPGA 프로젝트라 실험 번호가 없습니다. "
            f"`{PROJECT_DIR}` 폴더를 씁니다."
        )
    if week not in WEEK_TO_EXPERIMENT:
        raise ValueError(
            f"{week}주차에 해당하는 실험이 없습니다. "
            f"실험 주차는 {sorted(WEEK_TO_EXPERIMENT)}, "
            f"FPGA 는 {list(PROJECT_WEEKS)} 입니다."
        )
    return WEEK_TO_EXPERIMENT[week]


# 산출물 제목의 유일한 형식. 예전에는 네 곳이 제각각 만들었고, 경로용 일괄
# 치환이 그중 하나(프리뷰)를 조용히 덮어쓴 적이 있다.
DOCUMENT_KINDS = ("체크리스트", "기록", "예비보고서", "결과보고서", "프리뷰")


def document_title(experiment: int, title: str, kind: str) -> str:
    """산출물 제목 — `실험1 Basic Gates 체크리스트` 형식.

    **주차를 넣지 않는다.** 주차는 폴더를 찾을 때만 쓰고(`folder_for_week`),
    사람이 읽는 제목에는 실험 번호와 이름만 남긴다. 어느 주에 하는지는
    강의계획서의 일이지 제출물 표지의 일이 아니다.
    """
    if kind not in DOCUMENT_KINDS:
        raise ValueError(f"산출물 종류는 {list(DOCUMENT_KINDS)} 입니다: {kind!r}")
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"실험 제목이 비어 있습니다: {title!r}")
    experiment_dir(experiment)          # 번호 유효성은 한 곳에서만 판정한다
    return f"실험{experiment} {title.strip()} {kind}"


def week_for_experiment(experiment: int) -> int:
    """실험 번호 → 그 실험을 하는 주차. `folder_for_week` 의 역방향.

    스킬이 "실험5 는 5주차입니다" 처럼 되짚어 알릴 때 쓴다.
    """
    if isinstance(experiment, bool) or not isinstance(experiment, int):
        raise TypeError(f"실험 번호는 정수여야 합니다: {experiment!r}")
    for week, exp in WEEK_TO_EXPERIMENT.items():
        if exp == experiment:
            return week
    raise ValueError(
        f"실험 번호는 1~{EXPERIMENT_COUNT} 입니다: {experiment}"
    )


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
