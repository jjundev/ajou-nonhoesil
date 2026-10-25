"""Local image planning and verification. Never rewrites the report or its history."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from . import md, notion


@dataclass(frozen=True)
class ImageOccurrence:
    index: int
    line: int
    path: Path
    caption: str
    sha256: str
    content_type: str
    marker: str


@dataclass(frozen=True)
class ImagePlan:
    operation_id: str
    source: Path
    source_sha256: str
    markdown: str
    images: tuple[ImageOccurrence, ...]


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def image_type(path):
    path = Path(path)
    if path.stat().st_size > 20 * 1024 * 1024:
        raise notion.NotionError(f"20 MiB 초과 이미지: {path.name}")
    with path.open("rb") as f:
        signature = f.read(12)
    if path.suffix.lower() == ".png" and signature.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if path.suffix.lower() in (".jpg", ".jpeg") and signature.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    raise notion.NotionError(f"PNG/JPEG 확장자와 실제 파일 형식이 일치하지 않습니다: {path.name}")


def _balanced(text, start, opening, closing):
    depth, out, pos = 1, [], start
    while pos < len(text):
        c = text[pos]
        if c == "\\" and pos + 1 < len(text):
            # Preserve literal slashes unless escaping Markdown punctuation.
            nxt = text[pos + 1]
            out.append(nxt if nxt in r"\()[]!" else "\\" + nxt)
            pos += 2
            continue
        if c == opening:
            depth += 1
        elif c == closing:
            depth -= 1
            if not depth:
                return "".join(out), pos + 1
        out.append(c)
        pos += 1
    raise notion.NotionError("이미지 Markdown 괄호가 닫히지 않았습니다")


def plan_images(source: Path, *, operation_id: str, body: str | None = None) -> ImagePlan:
    source = Path(source).resolve()
    raw = source.read_bytes()
    if body is None:
        _, body = md.split_frontmatter(raw.decode("utf-8"))
    if not re.fullmatch(r"[A-Za-z0-9-]+", operation_id):
        raise notion.NotionError("잘못된 작업 ID")
    images, lines = [], []
    fence = None
    for line_no, line in enumerate(body.splitlines(keepends=True), 1):
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            lines.append(line)
            if re.fullmatch(r" {0,3}" + re.escape(fence[0]) + "{" + str(fence[1]) + r",}\s*", line):
                fence = None
            continue
        if opening:
            fence = (opening[1][0], len(opening[1]))
            lines.append(line)
            continue
        if re.search(r"<img\b", line, re.I):
            raise notion.NotionError(f"{source.name}:{line_no}: HTML 이미지는 지원하지 않습니다")
        if "![" not in line:
            lines.append(line)
            continue
        # Only standalone, unindented images are supported, including HTTPS images.
        if not line.startswith("!["):
            raise notion.NotionError(f"{source.name}:{line_no}: 최상위 독립 이미지 줄만 지원합니다")
        caption, pos = _balanced(line, 2, "[", "]")
        if line[pos:pos + 1] != "(":
            raise notion.NotionError(f"{source.name}:{line_no}: inline 이미지 문법만 지원합니다")
        target, end = _balanced(line, pos + 1, "(", ")")
        if line[end:].strip() or not target or re.search(r'["<>\n\r]', target):
            raise notion.NotionError(f"{source.name}:{line_no}: 이미지 title/복합 문법은 지원하지 않습니다")
        target = target.strip()
        parts = urlsplit(target)
        if parts.scheme == "https" and parts.netloc:
            lines.append(line)
            continue
        if parts.scheme or parts.netloc or parts.query or parts.fragment:
            raise notion.NotionError(f"{source.name}:{line_no}: 로컬 경로 또는 HTTPS 이미지가 필요합니다")
        path = (source.parent / unquote(target)).resolve()
        if not path.is_file():
            raise notion.NotionError(f"{source.name}:{line_no}: 이미지 파일이 없습니다: {path.name}")
        content_type = image_type(path)
        marker = f"NOTIONIMAGE-{operation_id}-{len(images):04d}"
        if marker in body:
            raise notion.NotionError("원본에 작업 표식이 이미 존재합니다")
        images.append(ImageOccurrence(len(images), line_no, path, caption,
                                      file_hash(path), content_type, marker))
        lines.append("\n" + marker + "\n\n")
    return ImagePlan(operation_id, source, hashlib.sha256(raw).hexdigest(),
                     "".join(lines), tuple(images))
