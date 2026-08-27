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
            {"id": 0, "name": "Root Entry", "type": 5, "left": 0, "right": 0, "child": 0, "data": b""},
            {"id": 1, "name": "FileHeader", "type": 2, "left": 0, "right": 0, "child": 0, "parent_name": "Root Entry", "data": b"Header"},
            {"id": 2, "name": "DocInfo", "type": 2, "left": 0, "right": 0, "child": 0, "parent_name": "Root Entry", "data": b"DocInfo"},
            {"id": 3, "name": "BodyText", "type": 1, "left": 0, "right": 0, "child": 0, "parent_name": "Root Entry", "data": b""},
            {"id": 4, "name": "Section0", "type": 2, "left": 0, "right": 0, "child": 0, "parent_name": "BodyText", "data": b"Sec0"},
            {"id": 5, "name": "BinData", "type": 1, "left": 0, "right": 0, "child": 0, "parent_name": "Root Entry", "data": b""},
            {"id": 6, "name": "BIN0001.png", "type": 2, "left": 0, "right": 0, "child": 0, "parent_name": "BinData", "data": b"Img1"},
            {"id": 7, "name": "BIN0002.jpg", "type": 2, "left": 0, "right": 0, "child": 0, "parent_name": "BinData", "data": b"Img2"},
        ]
        rebuild_ole_directory_tree(entries)

        # Root Entry child should be a valid index in the tree
        self.assertNotEqual(entries[0]["child"], 0xFFFFFFFF)
        self.assertNotEqual(entries[3]["child"], 0xFFFFFFFF)
        self.assertNotEqual(entries[5]["child"], 0xFFFFFFFF)

    def test_cfbf_reader_and_writer_integrity(self):
        fileheader_bytes = b"HWP Document File\x00" + b"\x00" * 238
        docinfo_comp = zlib.compress(b"Dummy DocInfo Content", level=9)[2:-4]
        sec0_comp = zlib.compress(
            rebuild_section0([[(66, 0, b"\x00" * 8), (67, 0, "Test Document".encode("utf-16le"))]]),
            level=9
        )[2:-4]
        bin_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 6000  # >4096 bytes to test multi-sector stream

        entries = [
            {"id": 0, "name": "Root Entry", "type": 5, "data": b""},
            {"id": 1, "name": "FileHeader", "type": 2, "parent_name": "Root Entry", "data": fileheader_bytes},
            {"id": 2, "name": "DocInfo", "type": 2, "parent_name": "Root Entry", "data": docinfo_comp},
            {"id": 3, "name": "BodyText", "type": 1, "parent_name": "Root Entry", "data": b""},
            {"id": 4, "name": "Section0", "type": 2, "parent_name": "BodyText", "data": sec0_comp},
            {"id": 5, "name": "BinData", "type": 1, "parent_name": "Root Entry", "data": b""},
            {"id": 6, "name": "BIN0001.png", "type": 2, "parent_name": "BinData", "data": bin_data},
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
            {"id": 0, "name": "Root Entry", "type": 5, "data": b""},
            {"id": 1, "name": "FileHeader", "type": 2, "parent_name": "Root Entry", "data": b"HWP Document File\x00" + b"\x00" * 238},
            {"id": 2, "name": "DocInfo", "type": 2, "parent_name": "Root Entry", "data": b"DocInfo"},
            {"id": 3, "name": "BodyText", "type": 1, "parent_name": "Root Entry", "data": b""},
            {"id": 4, "name": "Section0", "type": 2, "parent_name": "BodyText", "data": comp_sec},
            {"id": 5, "name": "BinData", "type": 1, "parent_name": "Root Entry", "data": b""},
            {"id": 6, "name": "BIN0001.png", "type": 2, "parent_name": "BinData", "data": b"PNG_DATA_1_ORIGINAL_LARGE"},
            {"id": 7, "name": "BIN0002.png", "type": 2, "parent_name": "BinData", "data": b"PNG_DATA_2_ORIGINAL_LARGE"},
            {"id": 8, "name": "BIN0003.png", "type": 2, "parent_name": "BinData", "data": b"PNG_DATA_3_ORIGINAL_LARGE"},
            {"id": 9, "name": "BIN0004.png", "type": 2, "parent_name": "BinData", "data": b"PNG_DATA_4_ORIGINAL_LARGE"},
            {"id": 10, "name": "BIN0005.png", "type": 2, "parent_name": "BinData", "data": b"PNG_DATA_5_UNUSED_LARGE"},
        ]

        doc_path = os.path.join(self.temp_dir, "report.hwp")
        write_hwp_ole(entries, doc_path)

        out_parts = split_hwp_file(doc_path, max_part_mb=0.000001)
        self.assertEqual(len(out_parts), 5)

        # In Part 1, BIN0001 retains original data, others have minimal dummy placeholders
        with CFBFParser(out_parts[0]) as cfbf:
            b1 = next(e for e in cfbf.entries if e["name"] == "BIN0001.png")
            self.assertEqual(cfbf.get_stream_data(b1), b"PNG_DATA_1_ORIGINAL_LARGE")
            b2 = next(e for e in cfbf.entries if e["name"] == "BIN0002.png")
            self.assertTrue(len(cfbf.get_stream_data(b2)) < 5000)

        # Verify Part 4 (BIN0004 retains original data)
        with CFBFParser(out_parts[3]) as cfbf:
            b4 = next(e for e in cfbf.entries if e["name"] == "BIN0004.png")
            self.assertEqual(cfbf.get_stream_data(b4), b"PNG_DATA_4_ORIGINAL_LARGE")

        # Ensure BIN0005 has dummy placeholder size in all parts
        for part in out_parts:
            with CFBFParser(part) as cfbf:
                b5 = next(e for e in cfbf.entries if e["name"] == "BIN0005.png")
                self.assertTrue(len(cfbf.get_stream_data(b5)) < 5000)

if __name__ == "__main__":
    unittest.main()
