import re
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

    def test_notion_parent_page_id_is_read(self):
        info = config.load_course_info(ROOT)
        self.assertIn("notion_parent_page_id", info)

    def test_notion_parent_page_id_defaults_when_the_key_is_absent(self):
        """미확정이면 지어내지 않는다. `ai_usage_log` 와 같은 규칙이다."""
        missing = Path(tempfile.mkdtemp())
        (missing / ".claude").mkdir()
        (missing / ".claude" / "과목정보.md").write_text(
            "---\ndepartment: 전자공학과\ncourse: 논리회로실험\n"
            "professor: 허용석 교수님\nclass_section: C082\n---\n",
            encoding="utf-8",
        )
        self.assertIsNone(config.load_course_info(missing)["notion_parent_page_id"])


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
        self.assertEqual(config.find_project_root(ROOT / "실험01" / "체크리스트"), ROOT)

    def test_raises_outside_project(self):
        with self.assertRaises(FileNotFoundError):
            config.find_project_root(Path("/"))


if __name__ == "__main__":
    unittest.main()


class MissingIdentityTest(unittest.TestCase):
    """조 편성 미확정 판정 — ⑥ 표지·③ 예보가 공유하는 게이트."""

    def test_모든_필드가_비면_전부_보고한다(self):
        self.assertEqual(
            config.missing_identity({}),
            ["team", "student_ids", "student_names"],
        )

    def test_None_과_빈_문자열을_모두_미확정으로_본다(self):
        # `~` 는 md 파서가 None 으로 준다. 빈 문자열도 표지에 찍히면 안 된다.
        info = {"team": None, "student_ids": "", "student_names": "홍길동"}
        self.assertEqual(config.missing_identity(info), ["team", "student_ids"])

    def test_다_채워지면_빈_리스트다(self):
        info = {"team": "3조", "student_ids": "202012345", "student_names": "홍길동"}
        self.assertEqual(config.missing_identity(info), [])

    def test_실제_과목정보로_돌아간다(self):
        root = config.find_project_root(Path(__file__))
        info = config.load_course_info(root)
        # 값 자체는 학기마다 바뀌므로 형태만 고정한다.
        self.assertIsInstance(config.missing_identity(info), list)


class SkillTemplateTest(unittest.TestCase):
    """실제 스킬 템플릿이 ⑤ 의 렌더 검사를 통과하는지.

    ① 프리뷰 템플릿의 CSS 주석에 백틱이 있어서 그 스킬이 낸 모든 HTML 이
    영구히 error 를 냈다. 백틱을 CSS 주석에 쓰는 건 자연스러운 저작이라
    (같은 자리에서 두 번 반복됐다) 템플릿을 제약하는 대신 검사를 정밀하게
    고쳤다. 이 테스트는 그 결과를 실제 템플릿으로 고정한다.
    """

    def test_치환된_템플릿이_렌더_검사를_통과한다(self):
        from scripts.lab import validate

        root = config.find_project_root(Path(__file__))
        templates = sorted((root / ".claude" / "skills").glob("*/template.html"))
        self.assertTrue(templates, "template.html 을 하나도 못 찾으면 이 테스트는 공허하게 통과한다")
        with tempfile.TemporaryDirectory() as tmp:
            for tmpl in templates:
                with self.subTest(template=tmpl.parent.name):
                    text = tmpl.read_text(encoding="utf-8")
                    for ph in re.findall(r"\{\{[A-Z_]+\}\}", text):
                        text = text.replace(ph, "샘플")
                    out = Path(tmp) / f"{tmpl.parent.name}.html"
                    out.write_text(text, encoding="utf-8")
                    self.assertEqual(validate.check_rendered_html(out), [])


class ExperimentDirTest(unittest.TestCase):
    """폴더 이름 규칙은 한 곳에서만 만든다 — 문자열로 흩뿌리면 반드시 어긋난다."""

    def test_두_자리로_0을_채운다(self):
        self.assertEqual(config.experiment_dir(1), "실험01")
        self.assertEqual(config.experiment_dir(9), "실험09")

    def test_열_번째는_그대로_두_자리다(self):
        self.assertEqual(config.experiment_dir(10), "실험10")

    def test_0을_채워야_사전순_정렬이_시간순과_맞는다(self):
        names = sorted(config.experiment_dir(n) for n in range(1, 11))
        self.assertEqual(names[0], "실험01")
        self.assertEqual(names[1], "실험02")
        self.assertEqual(names[-1], "실험10")

    def test_범위_밖_번호는_거절한다(self):
        # FPGA 는 실험 번호가 없다. 11 을 허용하면 저장소가 없는 번호를 발명한다.
        for bad in (0, 11, -1):
            with self.subTest(experiment=bad):
                with self.assertRaises(ValueError):
                    config.experiment_dir(bad)

    def test_bool은_정수가_아니다(self):
        # True 는 int 의 하위형이라 조용히 `실험01` 이 된다.
        with self.assertRaises(TypeError):
            config.experiment_dir(True)


class WeekMappingTest(unittest.TestCase):
    """주차 → 폴더 해석. 매핑이 1:1 이 아니라서 사람이 외우면 틀린다."""

    def test_회전_구간이_핵심이다(self):
        # 5·6·7주차가 실험 5·6·4 로 어긋난다. 여기가 틀리면 엉뚱한 교안을 연다.
        self.assertEqual(config.folder_for_week(5), "실험05")
        self.assertEqual(config.folder_for_week(6), "실험06")
        self.assertEqual(config.folder_for_week(7), "실험04")

    def test_평범한_구간(self):
        self.assertEqual(config.folder_for_week(2), "실험01")
        self.assertEqual(config.folder_for_week(12), "실험10")

    def test_FPGA_주차는_프로젝트_폴더다(self):
        for week in (13, 14, 15):
            with self.subTest(week=week):
                self.assertEqual(config.folder_for_week(week), "프로젝트")

    def test_중간고사_주차는_거절한다(self):
        with self.assertRaises(ValueError) as cm:
            config.folder_for_week(8)
        self.assertIn("중간고사", str(cm.exception))

    def test_범위_밖_주차는_거절한다(self):
        for bad in (1, 16, 0, -3):
            with self.subTest(week=bad):
                with self.assertRaises(ValueError):
                    config.folder_for_week(bad)

    def test_bool은_주차가_아니다(self):
        with self.assertRaises(TypeError):
            config.folder_for_week(True)

    def test_역방향도_회전을_지킨다(self):
        self.assertEqual(config.week_for_experiment(4), 7)
        self.assertEqual(config.week_for_experiment(5), 5)
        self.assertEqual(config.week_for_experiment(1), 2)
        self.assertEqual(config.week_for_experiment(10), 12)

    def test_왕복이_일치한다(self):
        for week, exp in config.WEEK_TO_EXPERIMENT.items():
            with self.subTest(week=week):
                self.assertEqual(config.week_for_experiment(exp), week)
                self.assertEqual(config.folder_for_week(week),
                                 config.experiment_dir(exp))

    def test_실험_열개가_빠짐없이_매핑된다(self):
        self.assertEqual(sorted(config.WEEK_TO_EXPERIMENT.values()),
                         list(range(1, config.EXPERIMENT_COUNT + 1)))

    # 위 테스트들은 회전 구간(5·6·7)과 양 끝(2, 12)만 리터럴로 고정한다.
    # 나머지 3·4·9·10·11주차는 어디에도 리터럴로 박혀 있지 않아서, 그 행들만
    # 뒤섞는 순열(예: 9→8, 10→9, 11→7)이 들어와도 위 테스트들은 전부 통과한다 —
    # `test_왕복이_일치한다` 는 WEEK_TO_EXPERIMENT 자신을 되읽어 검사하므로
    # 자기참조이고, `test_실험_열개가_빠짐없이_매핑된다` 는 값의 집합만 본다.
    # 그래서 열 행 전부를 매핑과 무관하게 여기 직접 적어 고정한다.
    WEEK_TO_EXPERIMENT_고정값 = {
        2: 1, 3: 2, 4: 3, 5: 5, 6: 6, 7: 4,
        9: 7, 10: 8, 11: 9, 12: 10,
    }

    def test_주차별_실험번호가_모두_리터럴로_고정된다(self):
        """열 행 전부를 매핑에서 되읽지 않고 직접 적은 값으로 고정한다.

        3·4·9·10·11주차는 이전 테스트 어디에도 리터럴로 박혀 있지 않아서,
        그 행들만 골라 뒤섞는 순열도 기존 테스트를 다 통과시킬 수 있었다.
        """
        for week, expected_experiment in self.WEEK_TO_EXPERIMENT_고정값.items():
            with self.subTest(week=week):
                self.assertEqual(
                    config.folder_for_week(week),
                    config.experiment_dir(expected_experiment),
                )

    def test_실험별_주차가_모두_리터럴로_고정된다(self):
        """`test_주차별_실험번호가_모두_리터럴로_고정된다` 의 역방향.

        한쪽 방향만 고정하면 그 방향에서만 쓰이는 순열은 잡히지만, 반대
        방향(`week_for_experiment`)이 따로 어긋나는 결함은 놓칠 수 있다.
        """
        for week, expected_experiment in self.WEEK_TO_EXPERIMENT_고정값.items():
            with self.subTest(experiment=expected_experiment):
                self.assertEqual(
                    config.week_for_experiment(expected_experiment),
                    week,
                )


class DocumentTitleTest(unittest.TestCase):
    """산출물 제목 형식. 네 곳이 제각각 만들다가 경로용 일괄 치환이 그중
    하나(프리뷰)를 조용히 덮어쓴 적이 있어서 한 함수로 모았다."""

    def test_형식은_실험번호_이름_종류다(self):
        self.assertEqual(
            config.document_title(1, "Basic Gates", "체크리스트"),
            "실험1 Basic Gates 체크리스트",
        )

    def test_제목에_주차가_들어가지_않는다(self):
        # 주차는 폴더를 찾을 때만 쓴다. 제출물 표지의 일이 아니다.
        for kind in config.DOCUMENT_KINDS:
            with self.subTest(kind=kind):
                self.assertNotIn("주차", config.document_title(1, "Basic Gates", kind))

    def test_폴더와_달리_0을_채우지_않는다(self):
        # 폴더는 정렬 때문에 `실험01`, 제목은 사람이 읽으므로 `실험1`.
        self.assertTrue(config.document_title(1, "x", "기록").startswith("실험1 "))
        self.assertTrue(config.document_title(10, "x", "기록").startswith("실험10 "))

    def test_모르는_종류는_거절한다(self):
        with self.assertRaises(ValueError):
            config.document_title(1, "Basic Gates", "표지")

    def test_빈_제목은_거절한다(self):
        for bad in ("", "   ", None):
            with self.subTest(title=bad):
                with self.assertRaises(ValueError):
                    config.document_title(1, bad, "기록")

    def test_실험번호_판정은_experiment_dir_와_같다(self):
        with self.assertRaises(ValueError):
            config.document_title(11, "x", "기록")
        with self.assertRaises(TypeError):
            config.document_title(True, "x", "기록")
