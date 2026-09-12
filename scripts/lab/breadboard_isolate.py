"""격리 재생성용 — 렌더러에서 한 주차의 빌더 구간을 걷어낸다.

`isolate.build_isolated_tree` 는 파일 단위로 지운다. 결선도 검증은 파일 하나
(`render_breadboard.py`)의 **일부**가 답안이다 — 실험01 빌더 구간(`E1_SLOTS`·
`_e1_*`·`build_e1_*`·`E1_BOARDS`·`E1_FINALS`)은 지우고 렌더러 본체·`verify()`·
기준선 기능·실험02 빌더는 남겨야 한다. 파일을 통째로 지우면 시험할 도구가
없고, 통째로 두면 답안이 있다.

구간 경계는 렌더러 자신의 규약을 쓴다 — 주차 구간 앞뒤에
`# ----…` 줄이 있고 구간 머리가 `# 실험 N · …` 주석이다.

어느 **파일**을 지우는가(답안지 목록)는 여기 없다. 정본은
`docs/verify/breadboard-diagram.md` 다.
"""

import re
from pathlib import Path

RENDERER = ".claude/skills/breadboard-diagram/scripts/render_breadboard.py"
RULE = "# ----"            # 구간 경계 줄의 머리
E1_MARKER = "# 실험 1 ·"   # 실험01 구간 머리 주석의 머리


def strip_section(src: str, marker: str) -> str:
    """`marker` 로 시작하는 주석이 이끄는 구간을 걷어낸다.

    구간 = 그 주석 바로 앞의 경계 줄부터 다음 경계 줄 직전까지. 머리가 없거나
    둘 이상이거나 앞줄이 경계가 아니면 ValueError — 조용히 원본을 돌려주면
    답안이 든 트리로 시험을 돈다.
    """
    lines = src.splitlines(keepends=True)
    heads = [i for i, line in enumerate(lines) if line.startswith(marker)]
    if len(heads) != 1:
        raise ValueError(f"구간 머리 {marker!r} 가 {len(heads)}번 나온다 (1번이어야 한다)")
    i = heads[0]
    if i == 0 or not lines[i - 1].startswith(RULE):
        raise ValueError(f"{marker!r} 앞줄이 구간 경계({RULE}…)가 아니다")
    start = i - 1
    end = next((n for n in range(i + 1, len(lines)) if lines[n].startswith(RULE)),
               len(lines))
    return "".join(lines[:start] + lines[end:])


def strip_cli(src: str, prefix: str) -> str:
    """`main()` 의 `choices=[…]` 와 `dispatch = {…}` 에서 `prefix` 로 시작하는
    회로 ID 항목을 뺀다. 토큰을 뺀 뒤 공백만 남은 줄은 지운다."""
    p = re.escape(prefix)
    out = re.sub(rf'^[ \t]*"{p}\w*": \w+,[ \t]*\n', "", src, flags=re.M)
    out = re.sub(rf'"{p}\w*",[ \t]*', "", out)
    return "\n".join(line for line in out.split("\n") if line == "" or line.strip() != "")


def strip_e1(src: str) -> str:
    """실험01 답안 구간 + CLI 항목을 뺀 렌더러 소스."""
    return strip_cli(strip_section(src, E1_MARKER), "e1_")


def strip_e1_file(path) -> None:
    """격리 트리의 렌더러를 제자리에서 걷어낸다 — `build_isolated_tree(edit=)` 훅이 부른다."""
    p = Path(path)
    p.write_text(strip_e1(p.read_text(encoding="utf-8")), encoding="utf-8")
