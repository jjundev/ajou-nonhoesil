"""고친 netlist 사본을 **실제 `보고서/` 밖**에 두고 읽게 하는 도우미.

검사·렌더는 그림·사이드카·`배치.py` 를 `netlist.path.parent` 에서 찾고, 인쇄 경로는
`../{폴더 이름}/` 으로 적는다. 그래서 사본은 `결선도` 라는 이름의 폴더에 원본 폴더의
파일이 다 보이게 놓여야 한다. 예전엔 원본 `결선도/` 에 `netlist_led_*.md` 를 잠깐 썼는데,
xdist 로 나란히 돌면 `보고서/` 의 `git status` 를 앞뒤로 재는 테스트
(`test_lab_schematic.TestMainWithSpec`)가 그 사본을 보고 불규칙하게 깨졌다(2026-10-14).
임시 폴더에 원본 파일을 심볼릭 링크로 늘어놓고 `netlist.md` 만 사본으로 바꿔 쓴다.
"""
import contextlib
import tempfile
from pathlib import Path


@contextlib.contextmanager
def netlist_copy(folder: Path, text: str):
    """`folder`(원본 `결선도/`)를 비춘 임시 `결선도/` 에 `text` 를 `netlist.md` 로 쓰고 그 경로를 준다."""
    with tempfile.TemporaryDirectory() as tmp:
        mirror = Path(tmp) / folder.name
        mirror.mkdir()
        for entry in folder.iterdir():
            if entry.name != "netlist.md":
                (mirror / entry.name).symlink_to(entry.resolve())
        path = mirror / "netlist.md"
        path.write_text(text, encoding="utf-8")
        yield path
