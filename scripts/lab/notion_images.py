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


def _only_external_images(line):
    for match in re.finditer(r"!\[", line):
        _, pos = _balanced(line, match.end(), "[", "]")
        if line[pos:pos + 1] != "(":
            return False
        target, _ = _balanced(line, pos + 1, "(", ")")
        parts = urlsplit(target)
        if parts.scheme != "https" or not parts.netloc:
            return False
    return True


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
        if _only_external_images(line):
            lines.append(line)
            continue
        # Local uploads require a standalone, unindented image.
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


@dataclass(frozen=True)
class ImagePlacement:
    index: int
    marker_id: str
    parent_id: str
    before_id: str | None
    after_id: str | None
    block_id: str | None = None


def plain_text(parts):
    return "".join(p.get("plain_text", p.get("text", {}).get("content", "")) for p in parts)


def block_text(block):
    return plain_text(block.get(block["type"], {}).get("rich_text", []))


def walk(tree):
    for block in tree:
        yield block
        yield from walk(block.get("_children", []))


def locate_markers(plan: ImagePlan, tree: list[dict]) -> list[ImagePlacement]:
    markers = {image.marker for image in plan.images}
    positions = []
    for image in plan.images:
        found = [b for b in walk(tree) if image.marker in block_text(b)]
        if (len(found) != 1 or found[0]["type"] != "paragraph"
                or block_text(found[0]) != image.marker or found[0] not in tree):
            raise notion.NotionError(f"이미지 {image.index}: 고유한 최상위 독립 표식이 없습니다")
        block = found[0]
        i = tree.index(block)
        left = next((b["id"] for b in reversed(tree[:i]) if block_text(b) not in markers), None)
        right = next((b["id"] for b in tree[i + 1:] if block_text(b) not in markers), None)
        parent = block.get("parent", {})
        parent_id = parent.get("page_id", parent.get("block_id", ""))
        positions.append(ImagePlacement(image.index, block["id"], parent_id, left, right))
    return positions


def verify_placements(plan, placements, tree, *, markers_allowed=False):
    from .validate import Finding
    errors = []
    def error(message):
        errors.append(Finding("error", plan.source.name, message))
    if len(placements) != len(plan.images):
        error("이미지 등장 수와 위치 기록 수가 다릅니다")
        return errors
    all_blocks = list(walk(tree))
    ids = [b["id"] for b in tree]
    marker_ids = {p.marker_id for p in placements}
    marker_texts = {im.marker for im in plan.images}
    if not markers_allowed and any(b["id"] in marker_ids or block_text(b) in marker_texts for b in all_blocks):
        error("표식이 본문에 남아 있습니다")
    groups = {}
    for image, p in zip(plan.images, placements):
        found = [b for b in all_blocks if b["id"] == p.block_id]
        if len(found) != 1 or found[0]["type"] != "image":
            error(f"이미지 {image.index}: 누락/중복/타입 오류")
            continue
        b = found[0]
        parent = b.get("parent", {})
        if parent.get("page_id", parent.get("block_id", "")) != p.parent_id or b not in tree:
            error(f"이미지 {image.index}: 부모 위치 불일치")
        if plain_text(b["image"].get("caption", [])) != image.caption:
            error(f"이미지 {image.index}: 캡션 불일치")
        groups.setdefault((p.before_id, p.after_id), []).append(p.block_id)
    for (before, after), expected in groups.items():
        if (before is not None and before not in ids) or (after is not None and after not in ids):
            error("이미지 본문 경계가 사라졌습니다")
            continue
        start = ids.index(before) + 1 if before else 0
        end = ids.index(after) if after else len(ids)
        actual = ids[start:end]
        if markers_allowed:
            actual = [id for id in actual if id not in marker_ids]
        if start > end or actual != expected:
            error("이미지의 정확한 본문 경계/순서가 다릅니다")
    return errors


def verify_image_content(local_path, url):
    import io
    import urllib.request
    from urllib.parse import urlsplit
    if urlsplit(url).scheme != "https":
        raise notion.NotionError("이미지 다운로드는 HTTPS만 지원합니다")
    try:
        req = urllib.request.Request(url, headers={"Accept": "image/*"})
        with urllib.request.urlopen(req, timeout=120) as response:
            remote = response.read(40 * 1024 * 1024 + 1)
        if len(remote) > 40 * 1024 * 1024:
            raise ValueError("remote image too large")
    except Exception:
        # Do not include an exception message: many HTTP clients echo the signed URL.
        raise notion.NotionError("원격 이미지 다운로드 실패; 새 URL 재조회가 필요합니다") from None
    local = Path(local_path).read_bytes()
    source_hash, remote_hash = hashlib.sha256(local).hexdigest(), hashlib.sha256(remote).hexdigest()
    result = {"ok": source_hash == remote_hash, "comparison": "sha256",
              "source_sha256": source_hash, "remote_sha256": remote_hash}
    if not result["ok"]:
        result["comparison"] = "pixels"
        try:
            from PIL import Image, ImageOps
            with Image.open(io.BytesIO(local)) as a, Image.open(io.BytesIO(remote)) as b:
                left = ImageOps.exif_transpose(a).convert("RGBA")
                right = ImageOps.exif_transpose(b).convert("RGBA")
                result["ok"] = left.size == right.size and left.tobytes() == right.tobytes()
        except (ImportError, OSError, ValueError):
            result["ok"] = False
    return result
