import unittest
import struct
import zlib
import tempfile
import os
import shutil
from scripts.split_hwp import (
    parse_hwp_paragraphs,
    rebuild_section0,
    write_hwp_ole,
    CFBFParser,
    extract_referenced_bins,
    rebuild_ole_directory_tree,
    split_hwp_file,
)

class TestHWPSplitter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_paragraph_serialization_roundtrip(self):
        # Paragraph 1
        p1 = [
            (66, 0, b"\x00" * 8),
            (67, 0, "Introduction".encode("utf-16le")),
            (68, 0, b"\x00" * 4),
        ]
        # Paragraph 2 with extended size (>4095 bytes)
        large_payload = b"A" * 5000
        p2 = [
            (66, 0, b"\x00" * 8),
            (67, 0, "Chapter 1".encode("utf-16le")),
            (69, 0, large_payload),
        ]

        raw_sec = rebuild_section0([p1, p2])
        parsed = parse_hwp_paragraphs(raw_sec)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0][1][2].decode("utf-16le"), "Introduction")
        self.assertEqual(parsed[1][1][2].decode("utf-16le"), "Chapter 1")
        self.assertEqual(parsed[1][2][2], large_payload)

    def test_extract_referenced_bins(self):
        tag85_data = bytearray(90)
        tag85_data[70] = 0x0A
        tag85_data[71] = 0x00
        para = [[(85, 0, bytes(tag85_data))]]
        bin_ids = extract_referenced_bins(para)
        self.assertIn(0x0A, bin_ids)

        # Non-picture records should not produce bin IDs
        other_para = [[(67, 0, "No bins here".encode("utf-16le"))]]
        self.assertEqual(extract_referenced_bins(other_para), set())

    def test_rebuild_ole_directory_tree(self):
        entries = [
            {"name": "Root Entry", "type": 5, "left": 0, "right": 0, "child": 0, "data": b""},
            {"name": "FileHeader", "type": 2, "left": 0, "right": 0, "child": 0, "data": b"Header"},
            {"name": "DocInfo", "type": 2, "left": 0, "right": 0, "child": 0, "data": b"DocInfo"},
            {"name": "BodyText", "type": 1, "left": 0, "right": 0, "child": 0, "data": b""},
            {"name": "Section0", "type": 2, "left": 0, "right": 0, "child": 0, "data": b"Sec0"},
            {"name": "BinData", "type": 1, "left": 0, "right": 0, "child": 0, "data": b""},
            {"name": "BIN0001.png", "type": 2, "left": 0, "right": 0, "child": 0, "data": b"Img1"},
            {"name": "BIN0002.jpg", "type": 2, "left": 0, "right": 0, "child": 0, "data": b"Img2"},
        ]
        rebuild_ole_directory_tree(entries)

        # Root Entry child should point to FileHeader (index 1)
        self.assertEqual(entries[0]["child"], 1)
        # Sibling linking for root children (FileHeader -> DocInfo -> BodyText -> BinData)
        self.assertEqual(entries[1]["right"], 2)
        self.assertEqual(entries[2]["right"], 3)
        self.assertEqual(entries[3]["right"], 5)

        # BodyText child should point to Section0 (index 4)
        self.assertEqual(entries[3]["child"], 4)

        # BinData child should point to BIN0001.png (index 6)
        self.assertEqual(entries[5]["child"], 6)
        self.assertEqual(entries[6]["right"], 7)

    def test_cfbf_reader_and_writer_integrity(self):
        fileheader_bytes = b"HWP Document File\x00" + b"\x00" * 238
        docinfo_comp = zlib.compress(b"Dummy DocInfo Content", level=9)[2:-4]
        sec0_comp = zlib.compress(
            rebuild_section0([[(66, 0, b"\x00" * 8), (67, 0, "Test Document".encode("utf-16le"))]]),
            level=9
        )[2:-4]
        bin_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 6000  # >4096 bytes to test multi-sector stream

        entries = [
            {"name": "Root Entry", "type": 5, "data": b""},
            {"name": "FileHeader", "type": 2, "data": fileheader_bytes},
            {"name": "DocInfo", "type": 2, "data": docinfo_comp},
            {"name": "BodyText", "type": 1, "data": b""},
            {"name": "Section0", "type": 2, "data": sec0_comp},
            {"name": "BinData", "type": 1, "data": b""},
            {"name": "BIN0001.png", "type": 2, "data": bin_data},
        ]

        out_ole = os.path.join(self.temp_dir, "test.hwp")
        write_hwp_ole(entries, out_ole)
        self.assertTrue(os.path.exists(out_ole))

        with CFBFParser(out_ole) as cfbf:
            fh_entry = next(e for e in cfbf.entries if e["name"] == "FileHeader")
            fh_data = cfbf.get_stream_data(fh_entry)
            self.assertTrue(fh_data.startswith(b"HWP Document File"))

            sec0_entry = next(e for e in cfbf.entries if e["name"] == "Section0")
            sec0_data = cfbf.get_stream_data(sec0_entry)
            decomp = zlib.decompress(sec0_data, -15)
            parsed_paras = parse_hwp_paragraphs(decomp)
            self.assertEqual(len(parsed_paras), 1)
            self.assertEqual(parsed_paras[0][1][2].decode("utf-16le"), "Test Document")

            bin_entry = next(e for e in cfbf.entries if e["name"] == "BIN0001.png")
            read_bin_data = cfbf.get_stream_data(bin_entry)
            self.assertEqual(len(read_bin_data), len(bin_data))
            self.assertEqual(read_bin_data[:8], b"\x89PNG\r\n\x1a\n")

    def test_split_hwp_file_with_bin_pruning(self):
        # Create a 5-part document with images
        def make_pic_record(bin_id):
            data = bytearray(90)
            data[70] = bin_id & 0xFF
            data[71] = (bin_id >> 8) & 0xFF
            return (85, 0, bytes(data))

        p0 = [(66, 0, b"\x00" * 8), (67, 0, "1. 서론".encode("utf-16le"))]
        p1 = [(66, 0, b"\x00" * 8), (67, 0, "4. 기능별 결과사진 (1. 더하기)".encode("utf-16le")), make_pic_record(1)]
        p2 = [(66, 0, b"\x00" * 8), (67, 0, "4. 나누기 동작".encode("utf-16le")), make_pic_record(2)]
        p3 = [(66, 0, b"\x00" * 8), (67, 0, "7. 0으로 나누었을 때".encode("utf-16le")), make_pic_record(3)]
        p4 = [(66, 0, b"\x00" * 8), (67, 0, "9. Reset 기능".encode("utf-16le")), make_pic_record(4)]

        raw_sec = rebuild_section0([p0, p1, p2, p3, p4])
        comp_sec = zlib.compress(raw_sec, level=9)[2:-4]

        entries = [
            {"name": "Root Entry", "type": 5, "data": b""},
            {"name": "FileHeader", "type": 2, "data": b"HWP Document File\x00" + b"\x00" * 238},
            {"name": "DocInfo", "type": 2, "data": b"DocInfo"},
            {"name": "BodyText", "type": 1, "data": b""},
            {"name": "Section0", "type": 2, "data": comp_sec},
            {"name": "BinData", "type": 1, "data": b""},
            {"name": "BIN0001.png", "type": 2, "data": b"PNG_DATA_1"},
            {"name": "BIN0002.png", "type": 2, "data": b"PNG_DATA_2"},
            {"name": "BIN0003.png", "type": 2, "data": b"PNG_DATA_3"},
            {"name": "BIN0004.png", "type": 2, "data": b"PNG_DATA_4"},
            {"name": "BIN0005.png", "type": 2, "data": b"PNG_DATA_5_UNUSED"},
        ]

        doc_path = os.path.join(self.temp_dir, "report.hwp")
        write_hwp_ole(entries, doc_path)

        out_parts = split_hwp_file(doc_path)
        self.assertEqual(len(out_parts), 5)

        # Verify Part 1 (p0 only, no images)
        with CFBFParser(out_parts[0]) as cfbf:
            bin_names = [e["name"] for e in cfbf.entries if e["name"].startswith("BIN")]
            self.assertEqual(bin_names, [])

        # Verify Part 2 (p1, BIN0001 only)
        with CFBFParser(out_parts[1]) as cfbf:
            bin_names = [e["name"] for e in cfbf.entries if e["name"].startswith("BIN")]
            self.assertEqual(bin_names, ["BIN0001.png"])

        # Verify Part 3 (p2, BIN0002 only)
        with CFBFParser(out_parts[2]) as cfbf:
            bin_names = [e["name"] for e in cfbf.entries if e["name"].startswith("BIN")]
            self.assertEqual(bin_names, ["BIN0002.png"])

        # Verify Part 4 (p3, BIN0003 only)
        with CFBFParser(out_parts[3]) as cfbf:
            bin_names = [e["name"] for e in cfbf.entries if e["name"].startswith("BIN")]
            self.assertEqual(bin_names, ["BIN0003.png"])

        # Verify Part 5 (p4, BIN0004 only)
        with CFBFParser(out_parts[4]) as cfbf:
            bin_names = [e["name"] for e in cfbf.entries if e["name"].startswith("BIN")]
            self.assertEqual(bin_names, ["BIN0004.png"])

        # Ensure BIN0005 was pruned from all parts
        for part in out_parts:
            with CFBFParser(part) as cfbf:
                bin_names = [e["name"] for e in cfbf.entries if e["name"].startswith("BIN")]
                self.assertNotIn("BIN0005.png", bin_names)

if __name__ == "__main__":
    unittest.main()
