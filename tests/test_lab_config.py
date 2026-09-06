import re
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.lab import config

ROOT = Path(__file__).resolve().parents[1]


def archive_candidate(candidates: list) -> Path:
    """후보 목록에서 과거 학기 아카이브 후보를 집는다.

    **번호로 집지 않는다** — 배포본은 실재할 때만 들어가서 목록 길이가
    고정이 아니다. `[1]` 로 집으면 배포본이 있는 주차에서만 조용히 다른
    것을 집는다.
    """
    return next(c for c in candidates
                if str(c).startswith(config.MANUAL_ARCHIVE))


class TestManualCandidates(unittest.TestCase):
    """교안 PDF 경로. **폴더는 0 을 채우고 파일은 안 채운다.**"""

    def test_파일_이름은_0_을_채우지_않는다(self):
        # 폴더는 `실험04`, 파일은 `실험4.pdf`. 두 형식이 한 경로에 섞여
        # 있어서 손으로 옮기면 7주차(실험4)에서 반드시 어긋난다.
        got = config.manual_candidates(4)
        self.assertEqual(got[0], Path("보고서/실험04/강의노트/실험4.pdf"))
        self.assertEqual(got[1],
                         Path("from_the_past/정리/강의노트/실험4.pdf"))

    def test_아카이브_후보에는_실험_기반_경로가_붙지_않는다(self):
        """과거 학기 원본은 `보고서/` 밖에 산다. 기반 경로를 후보 전체에
        일괄로 붙이면 이쪽이 조용히 `보고서/from_the_past/...` 가 된다 —
        파일이 없으므로 스킬은 "교안을 못 찾았다"로 넘어가고, 원인은
        한참 뒤에나 드러난다."""
        got = archive_candidate(config.manual_candidates(1))
        self.assertFalse(str(got).startswith(config.EXPERIMENT_BASE))
        self.assertEqual(got, Path("from_the_past/정리/강의노트/실험1.pdf"))

    def test_주차_폴더_사본이_아카이브보다_먼저다(self):
        got = config.manual_candidates(10)
        self.assertLess(got.index(Path("보고서/실험10/강의노트/실험10.pdf")),
                        got.index(archive_candidate(got)))

    def test_범위_밖_번호는_거절한다(self):
        with self.assertRaises(ValueError):
            config.manual_candidates(11)

    def test_아카이브_후보가_열_개_다_실재한다(self):
        # 이 함수가 만드는 이름이 실물과 어긋나면 여기서 걸린다.
        for n in range(1, 11):
            with self.subTest(n=n):
                got = archive_candidate(config.manual_candidates(n))
                self.assertTrue((ROOT / got).exists())


class TestDistributedManual(unittest.TestCase):
    """이번 학기 배포 폴더(`강의노트/`). 이름에 제목이 붙어 번호만으로
    만들 수 없으므로 이 후보만 디스크를 훑는다."""

    def _배포폴더(self, *names) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / config.MANUAL_DISTRIBUTION).mkdir()
        for n in names:
            (root / config.MANUAL_DISTRIBUTION / n).touch()
        return root

    def test_배포본이_주차_폴더_사본보다_먼저다(self):
        """사본은 언제나 다른 데서 복사해 온 것이라 배포본보다 새로울 수
        없다. 사본을 먼저 두면 과거 학기 판본이 이번 학기 배포본을 조용히
        가린다 — 2026-09 실험1 에서 실제로 일어난 일이다."""
        root = self._배포폴더("실험1. Basic Gates.pdf")
        got = config.manual_candidates(1, root=root)
        self.assertEqual(got[0], Path("강의노트/실험1. Basic Gates.pdf"))
        self.assertEqual(got[1], Path("보고서/실험01/강의노트/실험1.pdf"))

    def test_한_자리_번호가_두_자리를_집어삼키지_않는다(self):
        """`실험1` 로 앞자리만 맞추면 `실험10` 이 걸린다. 이 과목은 실험이
        10 개라 한 자리와 두 자리가 실제로 섞인다."""
        root = self._배포폴더("실험10. Counter.pdf")
        self.assertEqual(config.manual_candidates(1, root=root),
                         config.manual_candidates(1, root=Path(tempfile.mkdtemp())))
        self.assertEqual(config.manual_candidates(10, root=root)[0],
                         Path("강의노트/실험10. Counter.pdf"))

    def test_배포_폴더가_없으면_후보가_둘이다(self):
        got = config.manual_candidates(1, root=Path(tempfile.mkdtemp()))
        self.assertEqual(len(got), 2)

    def test_PDF_가_아닌_파일은_후보가_아니다(self):
        # 배포 폴더에는 `자리배치도.png` 같은 것도 같이 들어온다.
        root = self._배포폴더("실험1 자리배치도.png")
        self.assertEqual(len(config.manual_candidates(1, root=root)), 2)


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
        """값까지 확인한다. 키 존재만 보면 프론트매터의 id 가 손으로 편집하다
        잘려도 통과한다 — 이 필드는 노션 업로드가 통째로 매달린 값이다."""
        info = config.load_course_info(ROOT)
        self.assertEqual(
            info["notion_parent_page_id"],
            "3cbb06d263bc80ecbbeec20761dc3f92",
        )

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

    def test_notion_parent_page_id_defaults_when_the_value_is_tilde(self):
        """ROOT 는 이제 실값이 있어 이 경로를 못 덮는다. 리포를 새로 클론해
        아직 자기 노션 페이지를 안 만든 사람은 키는 있고 값만 `~` 인 이 상태를
        보게 된다 — `test_ai_usage_log_defaults_to_none` 이 다른 필드에서
        지키는 것과 같은 경로다."""
        missing = Path(tempfile.mkdtemp())
        (missing / ".claude").mkdir()
        (missing / ".claude" / "과목정보.md").write_text(
            "---\ndepartment: 전자공학과\ncourse: 논리회로실험\n"
            "professor: 허용석 교수님\nclass_section: C082\n"
            "notion_parent_page_id: ~\n---\n",
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
        # 실험 폴더가 한 겹 더 깊어졌다 — 거슬러 올라가는 깊이가 늘어도
        # 같은 루트를 찾아야 한다.
        start = ROOT / config.experiment_dir(1) / "체크리스트"
        self.assertEqual(config.find_project_root(start), ROOT)

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


class ExperimentBaseTest(unittest.TestCase):
    """실험 폴더가 사는 **위치**. 이름 규칙(`실험NN`)과는 다른 규칙이다.

    2026-09 에 실험 폴더 여섯이 루트에서 `보고서/` 아래로 옮겨졌는데
    `config.py` 만 안 고쳐졌다 — 아홉 스킬 전부가 없는 경로를 열었다.
    그 이동이 눈에 안 띈 이유는 위치가 어디에도 상수로 없었기 때문이다
    (이름 규칙은 `experiment_dir` 이 이미 한 곳에 모아 두고 있었다).
    여기 테스트는 위치도 같은 대접을 받게 못 박는다.
    """

    def test_기반_폴더는_보고서다(self):
        self.assertEqual(config.EXPERIMENT_BASE, "보고서")

    def test_이름과_위치는_다른_함수다(self):
        # `experiment_folder_name` 은 이름만, `experiment_dir` 은 경로.
        # 검사기(validate.check_folder_convention)는 조부모 폴더의 *이름* 과
        # 견주므로 접두사가 붙지 않은 쪽이 따로 필요하다.
        self.assertEqual(config.experiment_folder_name(1), "실험01")
        self.assertEqual(config.experiment_dir(1), "보고서/실험01")

    def test_경로는_이름_앞에_기반을_붙인_것과_같다(self):
        # 두 함수가 따로 0 패딩을 하면 한쪽만 고쳐지는 자리가 또 생긴다.
        for n in range(1, config.EXPERIMENT_COUNT + 1):
            with self.subTest(experiment=n):
                self.assertEqual(
                    config.experiment_dir(n),
                    f"{config.EXPERIMENT_BASE}/{config.experiment_folder_name(n)}",
                )

    def test_기반이_두_입구_전부에_적용된다(self):
        """폴더를 얻는 입구는 이 둘뿐이다. 하나만 빠뜨리면 그 스킬만 조용히
        옛 경로를 연다. (예전에는 `folder_for_week` 를 더해 셋이었는데,
        주차 모델을 걷어내면서 둘이 됐다. FPGA 는 `PROJECT_DIR` 상수라
        바로 아래 `test_FPGA_프로젝트도_기반_아래다` 가 따로 본다.)"""
        base = config.EXPERIMENT_BASE
        self.assertTrue(config.experiment_dir(3).startswith(base + "/"))
        사본 = next(c for c in config.manual_candidates(3)
                   if str(c).startswith(base + "/"))
        self.assertEqual(사본, Path(f"{base}/실험03/강의노트/실험3.pdf"))

    def test_FPGA_프로젝트도_기반_아래다(self):
        # 실험 폴더만 옮기고 `프로젝트/` 를 루트에 두면 같은 성격의 산출물이
        # 두 곳으로 갈린다 — 13~15주차가 오면 그때 또 이 작업을 한다.
        self.assertEqual(config.PROJECT_DIR, "보고서/프로젝트")

    def test_실험_폴더_여섯이_기반_아래_실재한다(self):
        """상수가 실물과 어긋나면 여기서 걸린다. 아직 안 만든 실험은
        디스크에 없는 게 정상이라 있는 것만 본다."""
        live = sorted(p.name for p in (ROOT / config.EXPERIMENT_BASE).iterdir()
                      if p.is_dir() and p.name.startswith("실험"))
        self.assertEqual(
            live, ["실험01", "실험02", "실험03", "실험05", "실험06", "실험10"])
        for n in (1, 2, 3, 5, 6, 10):
            with self.subTest(experiment=n):
                self.assertTrue((ROOT / config.experiment_dir(n)).is_dir())

    def test_루트로_거슬러_올라가는_사슬이_기반_깊이를_따라간다(self):
        """②·③ 이 낸 문서가 `.claude/assets/` 그림을 가리킬 때 쓰는 `../`
        사슬. 문자열로 박아 두면 기반 폴더가 늘 때 조용히 끊긴다 — HTML 은
        그대로 렌더되고 그림 자리만 비어서 눈으로는 놓친다."""
        # `보고서/실험01/체크리스트/` 에서 루트까지는 세 겹이다.
        self.assertEqual(config.root_relative_prefix(), "../../../")
        self.assertEqual(config.root_relative_prefix(0), "../../")
        self.assertEqual(config.root_relative_prefix(2), "../../../../")

    def test_사슬이_실제로_루트에_닿는다(self):
        """`../` 개수를 리터럴로만 고정하면 두 리터럴이 함께 틀릴 수 있다.
        실물 경로로 되짚어 `.claude/assets/` 가 정말 열리는지 본다."""
        checklist_dir = ROOT / config.experiment_dir(1) / "체크리스트"
        asset = checklist_dir / (config.root_relative_prefix()
                                 + ".claude/assets/Breadboard.jpg")
        self.assertTrue(asset.resolve().is_file(), asset)
        self.assertEqual(asset.resolve(), (ROOT / ".claude/assets/Breadboard.jpg"))

    def test_깊이가_정수가_아니면_거절한다(self):
        for bad in (True, 1.5, "1"):
            with self.subTest(depth=bad):
                with self.assertRaises(TypeError):
                    config.root_relative_prefix(bad)
        with self.assertRaises(ValueError):
            config.root_relative_prefix(-1)

    def test_루트에는_실험_폴더가_남아_있지_않다(self):
        """이동이 절반만 끝난 상태를 잡는다 — 루트 사본과 `보고서/` 사본이
        동시에 있으면 코퍼스 glob 이 같은 명세를 두 번 세고, 사람은 옛
        사본을 고치고 스킬은 새 사본을 읽는다."""
        strays = sorted(p.name for p in ROOT.iterdir()
                        if p.is_dir() and p.name.startswith("실험"))
        self.assertEqual(strays, [], f"루트에 실험 폴더가 남아 있다: {strays}")


class ExperimentDirTest(unittest.TestCase):
    """폴더 이름 규칙은 한 곳에서만 만든다 — 문자열로 흩뿌리면 반드시 어긋난다."""

    def test_두_자리로_0을_채운다(self):
        self.assertEqual(config.experiment_folder_name(1), "실험01")
        self.assertEqual(config.experiment_folder_name(9), "실험09")
        self.assertEqual(config.experiment_dir(1), "보고서/실험01")
        self.assertEqual(config.experiment_dir(9), "보고서/실험09")

    def test_열_번째는_그대로_두_자리다(self):
        self.assertEqual(config.experiment_folder_name(10), "실험10")
        self.assertEqual(config.experiment_dir(10), "보고서/실험10")

    def test_0을_채워야_사전순_정렬이_시간순과_맞는다(self):
        names = sorted(config.experiment_dir(n) for n in range(1, 11))
        self.assertEqual(names[0], "보고서/실험01")
        self.assertEqual(names[1], "보고서/실험02")
        self.assertEqual(names[-1], "보고서/실험10")

    def test_범위_밖_번호는_거절한다(self):
        # FPGA 는 실험 번호가 없다. 11 을 허용하면 저장소가 없는 번호를 발명한다.
        for bad in (0, 11, -1):
            with self.subTest(experiment=bad):
                with self.assertRaises(ValueError):
                    config.experiment_dir(bad)
                with self.assertRaises(ValueError):
                    config.experiment_folder_name(bad)

    def test_bool은_정수가_아니다(self):
        # True 는 int 의 하위형이라 조용히 `실험01` 이 된다.
        with self.assertRaises(TypeError):
            config.experiment_dir(True)
        with self.assertRaises(TypeError):
            config.experiment_folder_name(True)


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


class TestExperimentDates(unittest.TestCase):
    def test_실험1은_9월11일이다(self):
        self.assertEqual(config.experiment_date(1), date(2026, 9, 11))

    def test_실험2와_실험3이_같은_날이다(self):
        # 주차를 열쇠로 쓰던 시절 int→int 로 표현할 수 없던 바로 그 자리다.
        self.assertEqual(config.experiment_date(2), date(2026, 9, 18))
        self.assertEqual(config.experiment_date(3), date(2026, 9, 18))

    def test_9월18일에_실험이_둘이다(self):
        self.assertEqual(config.experiments_on(date(2026, 9, 18)), [2, 3])

    def test_추석에는_실험이_없다(self):
        # 예전에는 NO_ARTIFACT_WEEKS 예외 표로 관리해야 했다. 이제 그냥 없다.
        self.assertEqual(config.experiments_on(date(2026, 9, 25)), [])

    def test_중간고사에는_실험이_없다(self):
        self.assertEqual(config.experiments_on(date(2026, 10, 23)), [])

    def test_회전_구간이_운영계획과_같다(self):
        # 옛 표는 5·6·7주차를 실험 5·6·4 로 알았다. 정본은 4·5·6 이다.
        self.assertEqual(config.experiment_date(4), date(2026, 10, 2))
        self.assertEqual(config.experiment_date(5), date(2026, 10, 9))
        self.assertEqual(config.experiment_date(6), date(2026, 10, 16))

    def test_열_실험이_모두_리터럴로_고정된다(self):
        expected = {
            1: date(2026, 9, 11), 2: date(2026, 9, 18), 3: date(2026, 9, 18),
            4: date(2026, 10, 2), 5: date(2026, 10, 9), 6: date(2026, 10, 16),
            7: date(2026, 10, 30), 8: date(2026, 11, 6), 9: date(2026, 11, 13),
            10: date(2026, 11, 20),
        }
        self.assertEqual(config.EXPERIMENT_DATES, expected)

    def test_없는_실험_번호는_거절한다(self):
        with self.assertRaises(ValueError):
            config.experiment_date(11)

    def test_bool은_실험_번호가_아니다(self):
        with self.assertRaises(TypeError):
            config.experiment_date(True)

    def test_다음_실험을_오늘_날짜로_찾는다(self):
        when, exps = config.next_experiments(date(2026, 9, 12))
        self.assertEqual(when, date(2026, 9, 18))
        self.assertEqual(exps, [2, 3])

    def test_실험_당일에는_그날을_준다(self):
        when, exps = config.next_experiments(date(2026, 9, 11))
        self.assertEqual((when, exps), (date(2026, 9, 11), [1]))

    def test_학기가_끝나면_None(self):
        self.assertIsNone(config.next_experiments(date(2026, 12, 31)))

    def test_주차_함수는_사라졌다(self):
        for gone in ("folder_for_week", "experiment_for_week",
                     "week_for_experiment", "WEEK_TO_EXPERIMENT",
                     "NO_ARTIFACT_WEEKS", "PROJECT_WEEKS"):
            self.assertFalse(hasattr(config, gone), f"{gone} 가 아직 있다")
