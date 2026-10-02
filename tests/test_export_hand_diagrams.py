import tempfile
import unittest
from pathlib import Path
from PIL import Image

from scripts.lab import export_hand_diagrams as ehd


class TestExportHandDiagrams(unittest.TestCase):
    def setUp(self):
        self.pdf_path = Path("보고서/실험01/output/손그림검토/round8/hand.pdf")
        self.assertTrue(self.pdf_path.exists(), "round8 hand.pdf 가 존재해야 합니다.")

    def test_find_default_pdf(self):
        found = ehd.find_default_pdf(1)
        self.assertTrue(found.is_file())
        self.assertEqual(found.name, "hand.pdf")

    def test_export_hand_diagrams_default_no_crop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_paths = ehd.export_hand_diagrams(
                experiment=1,
                pdf_path=self.pdf_path,
                out_dir=tmpdir,
                dpi=150,  # fast test
            )
            self.assertEqual(len(out_paths), 5)
            expected_names = [
                "실험01_1-1_손그림_3입력_AND.png",
                "실험01_1-2_손그림_3입력_OR.png",
                "실험01_2-1_손그림_3입력_NAND.png",
                "실험01_2-2_손그림_3입력_NOR.png",
                "실험01_3_손그림_복합논리회로.png",
            ]
            for p, expected in zip(out_paths, expected_names):
                self.assertEqual(p.name, expected)
                self.assertTrue(p.is_file())
                # Default is no crop: full landscape page (width > height)
                with Image.open(p) as img:
                    self.assertEqual(img.format, "PNG")
                    self.assertGreater(img.width, img.height)

    def test_export_hand_diagrams_cropped_requires_visual_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(ValueError, "crop-plan"):
                ehd.export_hand_diagrams(1, self.pdf_path, tmpdir, crop_board=True)

    def test_resolve_circuit_filenames_from_netlist(self):
        filenames = ehd.resolve_circuit_filenames(1, 5)
        expected = [
            "실험01_1-1_손그림_3입력_AND.png",
            "실험01_1-2_손그림_3입력_OR.png",
            "실험01_2-1_손그림_3입력_NAND.png",
            "실험01_2-2_손그림_3입력_NOR.png",
            "실험01_3_손그림_복합논리회로.png",
        ]
        self.assertEqual(filenames, expected)

    def test_resolve_circuit_filenames_fallback(self):
        filenames = ehd.resolve_circuit_filenames(99, 2)
        self.assertEqual(filenames, ["실험99_손그림_p1.png", "실험99_손그림_p2.png"])

    def test_resolve_circuit_filenames_with_transcripts(self):
        round_dir = Path("보고서/실험01/output/손그림검토/round8")
        if round_dir.is_dir():
            filenames = ehd.resolve_circuit_filenames(1, 5, round_dir=round_dir)
            expected = [
                "실험01_1-1_손그림_3입력_AND.png",
                "실험01_1-2_손그림_3입력_OR.png",
                "실험01_2-1_손그림_3입력_NAND.png",
                "실험01_2-2_손그림_3입력_NOR.png",
                "실험01_3_손그림_복합논리회로.png",
            ]
            self.assertEqual(filenames, expected)

    def test_resolve_circuit_filenames_shuffled_pdf(self):
        import fitz
        # Create temporary shuffled PDF: [2, 4, 0, 3, 1]
        # Page 0 (new) -> 2 (2-1 NAND)
        # Page 1 (new) -> 4 (3 복합)
        # Page 2 (new) -> 0 (1-1 AND)
        # Page 3 (new) -> 3 (2-2 NOR)
        # Page 4 (new) -> 1 (1-2 OR)
        with tempfile.TemporaryDirectory() as tmpdir:
            shuffled_path = Path(tmpdir) / "shuffled.pdf"
            src_doc = fitz.open(str(self.pdf_path))
            shuffled_doc = fitz.open()
            for idx in [2, 4, 0, 3, 1]:
                shuffled_doc.insert_pdf(src_doc, from_page=idx, to_page=idx)
            shuffled_doc.save(str(shuffled_path))
            shuffled_doc.close()
            src_doc.close()

            filenames = ehd.resolve_circuit_filenames(1, 5, pdf_path=shuffled_path)
            expected = [
                "실험01_2-1_손그림_3입력_NAND.png",
                "실험01_3_손그림_복합논리회로.png",
                "실험01_1-1_손그림_3입력_AND.png",
                "실험01_2-2_손그림_3입력_NOR.png",
                "실험01_1-2_손그림_3입력_OR.png",
            ]
            self.assertEqual(filenames, expected)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            exit_code = ehd.main(["1", str(self.pdf_path), "--out", tmpdir, "--dpi", "100"])
            self.assertEqual(exit_code, 0)
            files = list(Path(tmpdir).glob("*.png"))
            self.assertEqual(len(files), 5)
            # Default CLI should not crop
            with Image.open(files[0]) as img:
                self.assertGreater(img.width, img.height)

    def test_parse_pages_arg(self):
        self.assertEqual(ehd.parse_pages_arg("1,2"), [0, 1])
        self.assertEqual(ehd.parse_pages_arg("3-4"), [2, 3])
        self.assertEqual(ehd.parse_pages_arg("1, 3, 5"), [0, 2, 4])

    def test_export_hand_diagrams_pages_subset(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_paths = ehd.export_hand_diagrams(
                experiment=1,
                pdf_path=self.pdf_path,
                out_dir=tmpdir,
                dpi=100,
                pages=[0, 1],
            )
            self.assertEqual(len(out_paths), 2)
            self.assertEqual(out_paths[0].name, "실험01_1-1_손그림_3입력_AND.png")
            self.assertEqual(out_paths[1].name, "실험01_1-2_손그림_3입력_OR.png")


if __name__ == "__main__":
    unittest.main()

