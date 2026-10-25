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


def para(id, text, parent="PAGE"):
    return {"id": id, "type": "paragraph", "parent": {"page_id": parent},
            "paragraph": {"rich_text": [{"plain_text": text}]}}


def img(id, caption="", parent="PAGE"):
    return {"id": id, "type": "image", "parent": {"page_id": parent},
            "image": {"caption": [{"plain_text": caption}]}}


def placement_fixture(tmp_path):
    from scripts.lab import notion_images as ni
    result = plan(make_source(tmp_path, "![](한 글 (1).png)\n\n본문\n\n![](한 글 (1).png)\n![](한 글 (1).png)\n\n끝\n\n![](한 글 (1).png)"))
    tree = [para("m0", result.images[0].marker), para("body", "본문"),
            para("m1", result.images[1].marker), para("m2", result.images[2].marker),
            para("end", "끝"), para("m3", result.images[3].marker)]
    placements = ni.locate_markers(result, tree)
    from dataclasses import replace
    placements = [replace(p, block_id=f"i{i}") for i, p in enumerate(placements)]
    return result, placements


def test_same_caption_adjacent_first_last_images(tmp_path):
    from scripts.lab import notion_images as ni
    result, positions = placement_fixture(tmp_path)
    remote = [img("i0"), para("body", "본문"), img("i1"), img("i2"), para("end", "끝"), img("i3")]
    assert ni.verify_placements(result, positions, remote) == []
    remote[2], remote[3] = remote[3], remote[2]
    assert any(f.level == "error" for f in ni.verify_placements(result, positions, remote))


def test_image_in_wrong_section_fails_with_correct_count(tmp_path):
    from scripts.lab import notion_images as ni
    result, positions = placement_fixture(tmp_path)
    remote = [para("body", "본문"), img("i0"), img("i1"), img("i2"), para("end", "끝"), img("i3")]
    assert ni.verify_placements(result, positions, remote)


def test_caption_rich_text_join_exact(tmp_path):
    from scripts.lab import notion_images as ni
    from dataclasses import replace
    result, positions = placement_fixture(tmp_path)
    result = replace(result, images=(replace(result.images[0], caption="한글"), *result.images[1:]))
    remote = [img("i0", "한글"), para("body", "본문"), img("i1"), img("i2"), para("end", "끝"), img("i3")]
    remote[0]["image"]["caption"] = [{"text": {"content": "한"}}, {"plain_text": "글"}]
    assert not ni.verify_placements(result, positions, remote)
    remote[0]["image"]["caption"].append({"plain_text": " "})
    assert ni.verify_placements(result, positions, remote)


@pytest.mark.parametrize("mode", ["missing", "duplicate", "merged", "nested"])
def test_marker_missing_duplicate_or_merged_fails(tmp_path, mode):
    from scripts.lab import notion_images as ni
    result = plan(make_source(tmp_path, "![](한 글 (1).png)"))
    marker = result.images[0].marker
    tree = {"missing": [], "duplicate": [para("m1", marker), para("m2", marker)],
            "merged": [para("m", marker + " more")],
            "nested": [{"id": "x", "type": "toggle", "_children": [para("m", marker)]}]}[mode]
    with pytest.raises(notion.NotionError):
        ni.locate_markers(result, tree)


def test_external_image_not_counted_as_local(tmp_path):
    from scripts.lab import notion_images as ni
    from dataclasses import replace
    result = plan(make_source(tmp_path, "![](한 글 (1).png)"))
    positions = ni.locate_markers(result, [img("external"), para("m", result.images[0].marker)])
    positions = [replace(positions[0], block_id="local")]
    assert not ni.verify_placements(result, positions, [img("external"), img("local")])
    assert ni.verify_placements(result, positions, [img("external")])


def test_download_no_auth_header_and_reencoding(tmp_path, monkeypatch):
    from scripts.lab import notion_images as ni
    from PIL import Image
    import io
    local = tmp_path / "x.png"
    Image.new("RGB", (3, 2), "red").save(local)
    remote = io.BytesIO()
    Image.new("RGB", (3, 2), "red").save(remote, format="PNG", compress_level=0)
    class Response(io.BytesIO):
        pass
    def download(req, timeout):
        assert not req.has_header("Authorization")
        return Response(remote.getvalue())
    monkeypatch.setattr("urllib.request.urlopen", download)
    result = ni.verify_image_content(local, "https://files.example/a?X-Amz-Signature=secret")
    assert result["ok"] and result["comparison"] == "pixels"
    assert "secret" not in str(result)
    remote.seek(0)
    remote.truncate()
    Image.new("RGB", (3, 2), "blue").save(remote, format="PNG")
    assert not ni.verify_image_content(local, "https://files.example/a")["ok"]


def test_missing_pillow_does_not_pass(tmp_path, monkeypatch):
    from scripts.lab import notion_images as ni
    import builtins
    import io
    p = make_source(tmp_path, "")
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: io.BytesIO(b"different"))
    real_import = builtins.__import__
    def without_pillow(name, *a, **k):
        if name == "PIL":
            raise ImportError("Pillow unavailable")
        return real_import(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", without_pillow)
    assert not ni.verify_image_content(tmp_path / "한 글 (1).png", "https://files.example/x")["ok"]
