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
    return info


def _section_body(body: str, name: str):
    """`# name` 헤딩부터 다음 `# ` 헤딩 직전까지를 잘라낸다."""
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
    return ReportFormat(
        preset=preset,
        pre=_sections(data.get("예비보고서")),
        result=_sections(data.get("결과보고서")),
    )
