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
from scripts.lab.isolate import build_isolated_tree, leak_scan, leak_tokens

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
    (exp / "체크리스트/명세.md").write_text("정답\n", encoding="utf-8")
    (exp / "결선도/netlist.md").write_text("정답\n", encoding="utf-8")
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
