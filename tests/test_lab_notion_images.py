import base64
from pathlib import Path

import pytest

from scripts.lab import notion

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a234AAAAASUVORK5CYII=")


def make_source(tmp_path, text):
    (tmp_path / "한 글 (1).png").write_bytes(PNG)
    p = tmp_path / "report.md"
    p.write_text(text)
    return p


def plan(p):
    from scripts.lab.notion_images import plan_images
    return plan_images(p, operation_id="test-op")


def test_plan_relative_path_and_caption(tmp_path):
    p = make_source(tmp_path, "![결선도 (정상)](한 글 (1).png)\n")
    before = p.read_bytes()
    result = plan(p)
    assert result.images[0].path == (tmp_path / "한 글 (1).png").resolve()
    assert result.images[0].caption == "결선도 (정상)"
    assert result.images[0].line == 1
    assert p.read_bytes() == before
    assert result.images[0].marker in result.markdown


def test_duplicate_occurrences(tmp_path):
    result = plan(make_source(tmp_path, "![같음](한 글 (1).png)\n![같음](한 글 (1).png)"))
    assert len(result.images) == 2
    assert result.images[0].marker != result.images[1].marker


@pytest.mark.parametrize("fence", ["```", "~~~"])
def test_fenced_example_is_not_uploaded(tmp_path, fence):
    assert plan(make_source(tmp_path, f"{fence}md\n![fake](missing.png)\n{fence}\n")).images == ()


@pytest.mark.parametrize("text", [
    "| ![a](한 글 (1).png) |", "- ![a](한 글 (1).png)",
    "> ![a](한 글 (1).png)", "text ![a](한 글 (1).png)",
    '<img src="한 글 (1).png">', '![a](한 글 (1).png "title")',
    "![a](broken.png", "![a](missing.png)", "![a][ref]",
    "    ![a](한 글 (1).png)", "![a](http://example.com/x.png)",
    "![a](data:image/png;base64,AAA)", "![a](file:///tmp/a.png)",
])
def test_reject_unsupported_or_missing_image(tmp_path, text):
    with pytest.raises(notion.NotionError):
        plan(make_source(tmp_path, text))


@pytest.mark.parametrize("target", ["한%20글%20%281%29.png", r"한 글 \(1\).png"])
def test_encoded_escaped_paths(tmp_path, target):
    assert plan(make_source(tmp_path, f"![]({target})")).images[0].caption == ""


def test_external_https_unchanged(tmp_path):
    text = "![remote](https://example.com/a.png)"
    result = plan(make_source(tmp_path, text))
    assert not result.images
    assert result.markdown == text


def test_invalid_signature_and_large_file(tmp_path):
    p = make_source(tmp_path, "![](bad.png)")
    (tmp_path / "bad.png").write_bytes(b"not a png")
    with pytest.raises(notion.NotionError):
        plan(p)
    with (tmp_path / "bad.png").open("wb") as f:
        f.write(PNG)
        f.truncate(20 * 1024 * 1024 + 1)
    with pytest.raises(notion.NotionError):
        plan(p)


def test_frontmatter_and_no_source_mutation(tmp_path):
    p = make_source(tmp_path, "---\ntitle: report\n---\n\n![a](한 글 (1).png)")
    assert not plan(p).markdown.startswith("---")
