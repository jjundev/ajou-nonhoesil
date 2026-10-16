"""Observable media behavior; all generated inputs/outputs live in TemporaryDirectory."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import unicodedata

from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "video_evidence.py"
spec = importlib.util.spec_from_file_location("video_evidence", SCRIPT)
ve = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ve)


class VideoEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(prefix="lab-video-tests-")
        cls.base = Path(cls.workspace.name)
        cls.clip = cls.base / "실험 원본 $`1`.mp4"
        cls.silent = cls.base / "silent.mp4"
        cls.rotated = cls.base / "rotated.mp4"
        cls.offset = cls.base / "offset.mp4"
        cls.vfr = cls.base / "vfr.mp4"
        ff = shutil.which("ffmpeg")
        if not ff:
            raise unittest.SkipTest("ffmpeg unavailable")

        def run(args):
            subprocess.run([ff, "-v", "error", "-n"] + args, check=True)

        run(["-f", "lavfi", "-i", "color=c=red:s=64x96:r=10:d=0.5",
             "-f", "lavfi", "-i", "color=c=blue:s=64x96:r=10:d=0.5",
             "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1",
             "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
             "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-c:a", "aac", str(cls.clip)])
        run(["-i", str(cls.clip), "-map", "0:v", "-c", "copy", str(cls.silent)])
        run(["-display_rotation:v:0", "90", "-i", str(cls.clip), "-c", "copy", str(cls.rotated)])
        run(["-i", str(cls.clip), "-c", "copy", "-output_ts_offset", "3", str(cls.offset)])
        run(["-f", "lavfi", "-i", "testsrc2=size=64x96:rate=30:duration=1",
             "-vf", "select='not(eq(mod(n,3),1))'", "-fps_mode", "vfr",
             "-c:v", "libx264", str(cls.vfr)])

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=self.base)
        self.root = Path(self.temp.name)
        self.experiment = self.root / "실험06"
        self.experiment.mkdir()
        self.delivery = self.root / "delivery"

    def tearDown(self):
        self.temp.cleanup()

    def inspect(self, videos=None, mode="photos", label="시험"):
        return ve.inspect_run(self.experiment, label, videos or [self.clip],
                              {}, mode, self.delivery)

    def select(self, manifest, at=0.7):
        m = ve.load(manifest)
        m["scenes"] = [{"id": "state", "source_id": "p1", "start_s": 0,
                        "end_s": 1, "item_id": None, "speech": [],
                        "observation": "색 상태", "unknowns": ["입력 미확인"]}]
        m["captures"] = [{"id": "photo1", "source_id": "p1", "at_s": at,
                          "scene_id": "state", "title": "상태", "observation": "파랑"}]
        return m

    def test_unicode_paths_resolve_actual_names(self):
        actual = self.root / unicodedata.normalize("NFD", "전사본.md")
        actual.write_text("내용")
        self.assertEqual(ve.actual_path(self.root / "전사본.md"), actual.resolve())

    def test_duplicate_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            self.inspect([self.clip, self.clip])

    def test_common_version_suffix_and_no_source_mutation(self):
        before = ve.sha256(self.clip)
        one = ve.load(self.inspect())
        two = ve.load(self.inspect())
        self.assertEqual(two["run_label"], one["run_label"] + "_v2")
        self.assertTrue(two["outputs"]["video"].endswith("_v2_편집본.mp4"))
        self.assertEqual(before, ve.sha256(self.clip))

    def test_invalid_ranges_and_interrupted_pair_validation(self):
        manifest = self.inspect([self.clip, self.silent])
        m = self.select(manifest, at=2)
        with self.assertRaises(ValueError):
            ve.validate_selection(m)
        m = self.select(manifest)
        m["scenes"].append(dict(m["scenes"][0], id="other", source_id="p2"))
        m["captures"].append(dict(m["captures"][0], id="photo2", source_id="p2", scene_id="other"))
        m["pairs"] = [{"id": "pair", "capture_ids": ["photo1", "photo2"],
                       "title": "비교", "continuity": "same_recording", "note": ""}]
        with self.assertRaises(ValueError):
            ve.validate_selection(m)
        m["pairs"][0]["continuity"] = "interrupted"
        ve.validate_selection(m)

    def test_photo_source_time_color_zip_and_manual_gate(self):
        manifest = self.inspect()
        m = self.select(manifest)
        ve.save(manifest, m)
        ve.build_run(manifest)
        m = ve.load(manifest)
        capture = m["captures"][0]
        with Image.open(capture["path"]) as image:
            pixel = image.convert("RGB").getpixel((32, 48))
        self.assertGreater(pixel[2], 220)
        self.assertLess(pixel[0], 25)
        self.assertAlmostEqual(capture["source_time_s"], 0.7, places=5)
        self.assertEqual(capture["frame_index"], 7)
        report = ve.verify_run(manifest)
        self.assertTrue(report["technical_pass"])
        self.assertFalse(report["complete"])
        m = ve.load(manifest)
        m["review"]["photos"] = "verified"
        ve.save(manifest, m)
        self.assertTrue(ve.verify_run(manifest)["complete"])
        original_png = ve.sha256(Path(capture["path"]))
        with self.assertRaises(FileExistsError):
            ve.build_run(manifest)
        self.assertEqual(original_png, ve.sha256(Path(capture["path"])))

    def test_rotated_source_photo_has_display_dimensions(self):
        manifest = self.inspect([self.rotated])
        ve.save(manifest, self.select(manifest))
        ve.build_run(manifest)
        m = ve.load(manifest)
        with Image.open(m["captures"][0]["path"]) as image:
            self.assertEqual(image.size, (96, 64))
        self.assertTrue(ve.verify_run(manifest)["technical_pass"])

    def test_nonzero_source_pts_uses_elapsed_time(self):
        manifest = self.inspect([self.offset])
        ve.save(manifest, self.select(manifest))
        ve.build_run(manifest)
        x = ve.load(manifest)["captures"][0]
        self.assertAlmostEqual(x["source_time_s"], 0.7, places=5)
        self.assertAlmostEqual(x["frame_pts_s"], 3.7, places=5)

    def test_vfr_uses_actual_frame_catalog(self):
        manifest = self.inspect([self.vfr])
        m = ve.load(manifest)
        frames = ve.catalog(m, "p1")
        gaps = {round(b["time_s"] - a["time_s"], 3) for a, b in zip(frames, frames[1:])}
        self.assertGreater(len(gaps), 1)
        self.assertEqual(ve.choose_fps({"avg_frame_rate": "30/1", "r_frame_rate": "120/1"}), "30")

    def test_input_change_prevents_build(self):
        source = self.root / "copy.mp4"
        shutil.copyfile(self.clip, source)
        manifest = self.inspect([source])
        ve.save(manifest, self.select(manifest))
        with source.open("ab") as f:
            f.write(b"changed")
        with self.assertRaises(ValueError):
            ve.build_run(manifest)

    def test_selected_frame_must_still_be_inside_scene(self):
        manifest = self.inspect()
        m = self.select(manifest, at=0.61)
        m["scenes"][0]["end_s"] = 0.65
        with self.assertRaises(ValueError):
            ve.validate_selection(m)

    def test_generated_photo_tampering_is_detected(self):
        manifest = self.inspect()
        ve.save(manifest, self.select(manifest))
        ve.build_run(manifest)
        m = ve.load(manifest)
        Image.new("RGB", (64, 96), "green").save(m["captures"][0]["path"])
        self.assertFalse(ve.verify_run(manifest)["technical_pass"])

    def test_preview_is_source_timed_and_does_not_overwrite(self):
        manifest = self.inspect()
        paths = ve.preview_run(manifest, "p1", start=0, end=1, step=0.2)
        self.assertTrue(paths)
        self.assertTrue(all(Path(p).is_file() for p in paths))
        with self.assertRaises(FileExistsError):
            ve.preview_run(manifest, "p1", start=0, end=1, step=0.2)

    def test_video_concat_with_silent_input_and_break_card(self):
        manifest = self.inspect([self.clip, self.silent], mode="both")
        m = self.select(manifest)
        m["cuts"] = [{"source_id": "p1", "start_s": 0.2, "end_s": 0.6,
                      "reason": "유효 구간"},
                     {"source_id": "p2", "start_s": 0, "end_s": 0.3,
                      "reason": "재촬영", "break_before": {"text": "재촬영", "duration_s": 0.2}}]
        m["review"] = {"photos": "verified", "boundaries": "verified", "audio": "unavailable"}
        ve.save(manifest, m)
        ve.build_run(manifest)
        report = ve.verify_run(manifest)
        self.assertTrue(report["complete"], report)
        self.assertAlmostEqual(report["video_duration_s"], 0.9, delta=0.11)
        out = ve.probe(Path(m["outputs"]["video"]))
        video = next(s for s in out["streams"] if s["codec_type"] == "video")
        self.assertEqual((video["width"], video["height"]), (64, 96))
        self.assertEqual(video["avg_frame_rate"], "10/1")
        m = ve.load(manifest)
        m["review"]["audio"] = "pending"
        ve.save(manifest, m)
        self.assertFalse(ve.verify_run(manifest)["complete"])


if __name__ == "__main__":
    unittest.main()
