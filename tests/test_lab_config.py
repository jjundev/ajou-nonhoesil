import tempfile
import unittest
from pathlib import Path

from scripts.lab import config

ROOT = Path(__file__).resolve().parents[1]


class TestCourseInfo(unittest.TestCase):
    def test_reads_required_fields(self):
        info = config.load_course_info(ROOT)
        self.assertEqual(info["course"], "논리회로실험")
        self.assertEqual(info["professor"], "허용석 교수님")
        self.assertEqual(info["class_section"], "C082")
        self.assertIn("chrome", info)

    def test_ai_usage_log_defaults_to_none(self):
        """표기 의무가 미확인이므로 자리만 비워둔다. 값이 없으면 로깅하지 않는다."""
        self.assertIsNone(config.load_course_info(ROOT)["ai_usage_log"])

    def test_ai_usage_log_defaults_when_the_key_is_absent(self):
        missing = Path(tempfile.mkdtemp())
        (missing / ".claude").mkdir()
        (missing / ".claude" / "과목정보.md").write_text(
            "---\ndepartment: 전자공학과\ncourse: 논리회로실험\n"
            "professor: 허용석 교수님\nclass_section: C082\n---\n",
            encoding="utf-8",
        )
        self.assertIsNone(config.load_course_info(missing)["ai_usage_log"])


class TestReportFormat(unittest.TestCase):
    def test_default_preset_is_intersection(self):
        fmt = config.load_report_format(ROOT)
        self.assertEqual(fmt.preset, "교집합")

    def test_intersection_pre_report_sections(self):
        fmt = config.load_report_format(ROOT)
        self.assertEqual(
            [s.name for s in fmt.pre],
            ["실험 목적", "실험 이론", "실험 부품",
             "실험 과정 및 예상 결과", "회로 결선도", "출처 및 참고문헌"],
        )

    def test_intersection_result_report_covers_grading_rubric(self):
        """평가기준.txt(권위 2순위)가 요구하는 결보 섹션이 전부 있어야 한다."""
        fmt = config.load_report_format(ROOT)
        names = [s.name for s in fmt.result]
        for required in ["실험 결과", "예비 비교", "결과 분석", "고찰", "추가 공부"]:
            self.assertIn(required, names)

    def test_optional_sections_are_not_generated(self):
        fmt = config.load_report_format(ROOT)
        optional = [s for s in fmt.result if s.name == "추가 공부"]
        self.assertEqual(len(optional), 1)
        self.assertFalse(optional[0].generate)

    def test_repeat_per_item_flag_survives(self):
        """항목반복형은 결보 29편 중 14편의 실제 구조다 (R2)."""
        fmt = config.load_report_format(ROOT, preset="항목반복형")
        repeated = [s.name for s in fmt.result if s.repeat == "per-item"]
        self.assertIn("고찰", repeated)
        self.assertIn("결선도", repeated)
        self.assertNotIn("전체적인 고찰", repeated)

    def test_distributed_form_preset(self):
        """예비보고서 양식.pdf 의 목차 (권위 1순위, 2017~2019 실증)."""
        fmt = config.load_report_format(ROOT, preset="배포양식형")
        self.assertEqual(
            [s.name for s in fmt.pre],
            ["실험목적", "실험이론", "실험부품",
             "실험과정 및 예상결과", "출처 및 참고문헌"],
        )

    def test_unknown_preset_raises(self):
        with self.assertRaises(ValueError):
            config.load_report_format(ROOT, preset="없는프리셋")

    def test_empty_section_list_raises_instead_of_returning_nothing(self):
        """이 파일은 학기 중에 손으로 고친다. 키 한 줄이 들여쓰기되는 실수가
        조용한 빈 보고서로 이어지면 안 된다."""
        broken = Path(tempfile.mkdtemp())
        (broken / ".claude").mkdir()
        (broken / ".claude" / "보고서양식.md").write_text(
            "---\nschema: report-format/v1\npreset: 교집합\n---\n\n"
            "# 교집합\n\n"
            "  예비보고서:\n"          # 실수로 들여쓰기됐다
            "    - {name: 실험 목적}\n"
            "결과보고서:\n"
            "  - {name: 실험 결과}\n",
            encoding="utf-8",
        )
        with self.assertRaises(ValueError) as ctx:
            config.load_report_format(broken)
        self.assertIn("섹션을 읽지 못했습니다", str(ctx.exception))


class TestProjectRoot(unittest.TestCase):
    def test_walks_up_to_dotclaude(self):
        self.assertEqual(config.find_project_root(ROOT / "2주차" / "체크리스트"), ROOT)

    def test_raises_outside_project(self):
        with self.assertRaises(FileNotFoundError):
            config.find_project_root(Path("/"))


if __name__ == "__main__":
    unittest.main()
