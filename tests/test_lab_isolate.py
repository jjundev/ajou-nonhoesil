"""격리 트리 계약. 답안지를 지운 뒤 `git init` 단일 커밋 위에 두어야
`git status` 로 삭제 목록이 새지 않는다(런북 2026-09-01 누출 (1)).

실제 저장소를 쓰지 않고 임시 git 저장소를 하나 만들어 돌린다 — 이 테스트가
본 저장소의 HEAD 에 의존하면 승인본이 바뀔 때마다 흔들린다.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.lab import config
from scripts.lab.isolate import (_DERIVED, build_isolated_tree, leak_scan, leak_sentences,
                                 leak_tokens)

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / config.experiment_dir(1) / "체크리스트/명세.md"


def _git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          cwd=cwd, check=True, capture_output=True, text=True).stdout


def _fake_repo():
    root = Path(tempfile.mkdtemp())
    (root / "docs/verify").mkdir(parents=True)
    (root / "docs/verify/answer.md").write_text("합격 조건\n", encoding="utf-8")
    exp = root / config.experiment_dir(1)
    (exp / "체크리스트").mkdir(parents=True)
    (exp / "결선도").mkdir()
    (exp / "output").mkdir()
    (exp / "실험사진/시트").mkdir(parents=True)
    (exp / "체크리스트/명세.md").write_text("정답\n", encoding="utf-8")
    (exp / "체크리스트/기록.md").write_text("기록\n", encoding="utf-8")
    (exp / "결선도/netlist.md").write_text("정답\n", encoding="utf-8")
    (exp / "output/실험01_예비보고서.md").write_text("예보 본문\n", encoding="utf-8")
    (exp / "output/실험01_결과보고서.md").write_text(
        "시험한 네 행은 모두 예상과 일치했다는 승인본 문장이다.\n", encoding="utf-8")
    (exp / "output/실험01_결과보고서_notion_baseline_v5.md").write_text("답\n", encoding="utf-8")
    (exp / "output/result_review_round1.md").write_text("리뷰\n", encoding="utf-8")
    (exp / "실험사진/시트/실험01_1-1_사진_3입력_AND.jpg").write_bytes(b"jpg")
    (root / "keep.md").write_text("남는 파일 E1.P1-1 언급\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "seed")
    return root


class BuildIsolatedTree(unittest.TestCase):
    def setUp(self):
        self.root = _fake_repo()
        self.dest = Path(tempfile.mkdtemp()) / "iso"
        build_isolated_tree(self.root, self.dest, 1, ["docs/verify"])

    def test_답안지는_없고_나머지는_있다(self):
        self.assertFalse((self.dest / "docs/verify").exists())
        self.assertTrue((self.dest / "keep.md").exists())

    def test_실험_폴더는_비어_있되_남아_있다(self):
        exp = self.dest / config.experiment_dir(1)
        self.assertTrue((exp / "체크리스트").is_dir())
        self.assertTrue((exp / "결선도").is_dir())
        self.assertTrue((exp / "output").is_dir())
        self.assertFalse((exp / "체크리스트/명세.md").exists())
        self.assertFalse((exp / "결선도/netlist.md").exists())

    def test_독립_저장소이고_커밋은_하나이며_status_는_비어_있다(self):
        self.assertTrue((self.dest / ".git").is_dir())
        self.assertEqual(_git(self.dest, "rev-list", "--count", "HEAD").strip(), "1")
        self.assertEqual(_git(self.dest, "status", "--porcelain"), "")

    def test_원본_저장소는_건드리지_않는다(self):
        self.assertTrue((self.root / "docs/verify/answer.md").exists())
        self.assertEqual(_git(self.root, "status", "--porcelain"), "")

    def test_답안지_키가_dest_밖이면_예외를_던지고_아무것도_안_지운다(self):
        # `dest / key` 는 key 가 절대경로처럼 보이면 dest 를 버리고 key 그대로가
        # 된다 — 답안지 키에 앞 `/` 가 붙으면 임의 절대경로를 rmtree/unlink 할
        # 뻔했다. 여기서는 실제로 아무것도 지우지 않고 예외만 확인한다.
        root = _fake_repo()
        dest = Path(tempfile.mkdtemp()) / "iso"
        with self.assertRaises(ValueError):
            build_isolated_tree(root, dest, 1, ["/etc"])
        # 격리 밖(원본 저장소)은 전혀 건드리지 않았다.
        self.assertTrue((root / "docs/verify/answer.md").exists())
        self.assertTrue((root / "keep.md").exists())


class LeakScan(unittest.TestCase):
    def test_승인본에서_토큰을_뽑는다(self):
        toks = leak_tokens(SPEC)
        self.assertIn("E1.P1-1", toks)
        self.assertIn("실험 1-1) 3-input AND gate", toks)
        self.assertTrue(any(t.startswith("X = A + (A'·B)'") for t in toks), toks)

    def test_트리에서_토큰을_찾고_git_은_건너뛴다(self):
        root = _fake_repo()
        hits = leak_scan(root, ["E1.P1-1"])
        self.assertEqual(len(hits), 1, hits)
        self.assertTrue(hits[0].startswith("keep.md:1:"), hits[0])

    def test_derived가_여러_줄로_이어져도_토큰을_뽑는다(self):
        # spec_parser._attrs() 는 들여쓴(2칸 이상) 줄을 앞 값에 이어 붙인다
        # (spec_parser.py:70-80). `derived (...)` 가 이 규칙으로 두 줄에 걸쳐
        # 적혀도 leak_tokens 가 여전히 토큰을 뽑아야 한다 — 이어붙이기
        # 회귀 테스트다. _attrs() 가 줄바꿈을 공백으로 눌러 붙이므로
        # `_DERIVED` 가 re.S 없이도 이 입력에서는 통과한다 — re.S 자체를
        # 재는 것은 아래 test_DERIVED_정규식은_줄바꿈을_건너_잡는다다.
        original = "- source: derived (X = A + (A'·B)' ; Y = A + B ; Z = (A'·B)')"
        wrapped = (
            "- source: derived (X = A + (A'·B)' ; Y = A + B ;\n"
            "  Z = (A'·B)')"
        )
        text = SPEC.read_text(encoding="utf-8")
        self.assertIn(original, text, "명세의 T5 source 줄 형식이 바뀌었다 — 테스트를 갱신하라")
        wrapped_text = text.replace(original, wrapped)

        tmp_dir = Path(tempfile.mkdtemp())
        tmp_spec = tmp_dir / "명세.md"
        tmp_spec.write_text(wrapped_text, encoding="utf-8")

        toks = leak_tokens(tmp_spec)
        self.assertTrue(any(t.startswith("Y = A + B") for t in toks), toks)

    def test_DERIVED_정규식은_줄바꿈을_건너_잡는다(self):
        # 위 테스트는 spec_parser._attrs() 가 줄바꿈을 공백으로 눌러 붙이기
        # 때문에 re.S 유무와 무관하게 통과한다 — re.S 가 실제로 관측되는
        # 유일한 자리는 정규식 자체다. `.` 이 줄바꿈을 건너야 `search` 가
        # 매치한다: re.S 없이 `.*` 는 `\n` 을 소비하지 않는다.
        self.assertIsNotNone(_DERIVED.search("derived (A ;\nB)"))


class ResultReportMode(unittest.TestCase):
    """결과보고서 검증용 격리 — output 만 비우고 예비보고서 md 를 되살린다.

    명세·기록·결선도·사진 시트는 ④ 의 **입력**이라 남아야 한다. 답안은
    output/ 의 결과보고서 계열과 리뷰 문서뿐이다.
    """

    def setUp(self):
        self.root = _fake_repo()
        self.dest = Path(tempfile.mkdtemp()) / "iso"
        exp = config.experiment_dir(1)
        build_isolated_tree(self.root, self.dest, 1, ["docs/verify"],
                            clear_subdirs=("output",),
                            keep=[f"{exp}/output/실험01_예비보고서.md"])
        self.exp = self.dest / exp

    def test_입력물은_남는다(self):
        self.assertTrue((self.exp / "체크리스트/명세.md").exists())
        self.assertTrue((self.exp / "체크리스트/기록.md").exists())
        self.assertTrue((self.exp / "결선도/netlist.md").exists())
        self.assertTrue((self.exp / "실험사진/시트/실험01_1-1_사진_3입력_AND.jpg").exists())

    def test_output_은_예비보고서만_남는다(self):
        self.assertEqual(sorted(p.name for p in (self.exp / "output").iterdir()),
                         ["실험01_예비보고서.md"])
        self.assertEqual((self.exp / "output/실험01_예비보고서.md").read_text(encoding="utf-8"),
                         "예보 본문\n")

    def test_status_는_비어_있다(self):
        self.assertEqual(_git(self.dest, "status", "--porcelain"), "")

    def test_글롭_키를_편다(self):
        dest = Path(tempfile.mkdtemp()) / "iso"
        exp = config.experiment_dir(1)
        build_isolated_tree(self.root, dest, 1, [f"{exp}/output/*결과보고서*"], clear_subdirs=())
        names = sorted(p.name for p in (dest / exp / "output").iterdir())
        self.assertEqual(names, ["result_review_round1.md", "실험01_예비보고서.md"])

    def test_없는_keep_경로는_예외다(self):
        dest = Path(tempfile.mkdtemp()) / "iso"
        with self.assertRaises(KeyError):
            build_isolated_tree(self.root, dest, 1, [], clear_subdirs=("output",),
                                keep=["없는/파일.md"])

    def test_절대경로_글롭_키는_ValueError_이고_아무것도_안_지운다(self):
        # Windows 드라이브 경로(`C:/...`)는 `/` 로 시작하지 않아 문자열 검사만으로는
        # 새고, `Path.glob` 은 그것을 NotImplementedError 로 튕긴다 — 계약은 ValueError 다.
        root = _fake_repo()
        dest = Path(tempfile.mkdtemp()) / "iso"
        drive = Path(tempfile.gettempdir()).anchor or "/"
        for key in (f"{drive}Windows/*.md", "/etc/*.conf", "../*.md"):
            with self.subTest(key):
                with self.assertRaises(ValueError):
                    build_isolated_tree(root, dest, 1, [key], clear_subdirs=())
        self.assertTrue((root / "keep.md").exists())

    def test_같은_dest_에_두_번_만들어도_된다(self):
        # 지난 회차 트리의 `.git/objects/` 는 Windows 에서 읽기 전용이라 그냥
        # rmtree 하면 PermissionError 다(2026-09-12 2회차) — 두 번째 호출이 통과해야 한다.
        dest = Path(tempfile.mkdtemp()) / "iso"
        build_isolated_tree(self.root, dest, 1, [])
        build_isolated_tree(self.root, dest, 1, [])
        self.assertEqual(_git(dest, "rev-list", "--count", "HEAD").strip(), "1")

    def test_기본_인자는_세_폴더를_비운다(self):
        dest = Path(tempfile.mkdtemp()) / "iso"
        build_isolated_tree(self.root, dest, 1, [])
        exp = dest / config.experiment_dir(1)
        self.assertFalse((exp / "체크리스트/기록.md").exists())
        self.assertEqual(list((exp / "output").iterdir()), [])


class LeakSentences(unittest.TestCase):
    def test_승인본_문장이_남은_파일을_짚는다(self):
        root = _fake_repo()
        approved = root / config.experiment_dir(1) / "output/실험01_결과보고서.md"
        tree = Path(tempfile.mkdtemp())
        (tree / "a.md").write_text("서론. 시험한 네 행은 모두 예상과 일치했다는 승인본 문장이다. 끝.\n",
                                   encoding="utf-8")
        (tree / "b.md").write_text("이 문장은 스물다섯 자를 넘기려고 일부러 길게 쓴 문장이다.\n",
                                   encoding="utf-8")
        hits = leak_sentences(approved, tree)
        self.assertEqual(len(hits), 1, hits)
        self.assertTrue(hits[0].startswith("a.md: "), hits[0])

    def test_git_폴더와_다른_확장자는_건너뛴다(self):
        root = _fake_repo()
        approved = root / config.experiment_dir(1) / "output/실험01_결과보고서.md"
        tree = Path(tempfile.mkdtemp())
        (tree / ".git").mkdir()
        (tree / ".git/x.md").write_text(approved.read_text(encoding="utf-8"), encoding="utf-8")
        (tree / "x.jpg").write_text(approved.read_text(encoding="utf-8"), encoding="utf-8")
        self.assertEqual(leak_sentences(approved, tree), [])
