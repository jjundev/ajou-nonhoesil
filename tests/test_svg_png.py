from scripts.lab.svg_png import svg_size


def test_svg_size_reads_viewbox():
    assert svg_size('<svg viewBox="0 0 1200 520" xmlns="http://www.w3.org/2000/svg"></svg>') == (1200, 520)


def _tiny_png(path):
    import struct, zlib
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    raw = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) \
        + chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff")) + chunk(b"IEND", b"")
    path.write_bytes(raw)


def test_png_text_stamp_roundtrip(tmp_path):
    from scripts.lab.svg_png import png_text, stamp_png_text
    p = tmp_path / "a.png"
    _tiny_png(p)
    assert png_text(p) == {}
    stamp_png_text(p, "svg-sha256", "abc")
    stamp_png_text(p, "svg-sha256", "def")      # 다시 찍으면 바뀐다
    assert png_text(p) == {"svg-sha256": "def"}
    assert p.read_bytes().endswith(b"IEND\xaeB`\x82")


def test_svg_size_ignores_marker_viewbox():
    # 루트 <svg> 에 viewBox 가 없으면 marker 의 viewBox 를 집지 않고 실패해야 한다
    import pytest
    with pytest.raises(ValueError):
        svg_size('<svg xmlns="http://www.w3.org/2000/svg"><marker viewBox="0 0 10 10"/></svg>')
