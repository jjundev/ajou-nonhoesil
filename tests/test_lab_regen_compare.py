"""재생성 결선도·명세를 승인본과 대조하는 도구의 계약.

격리 재생성의 판정을 사람 눈에 맡기면 매번 기준이 흔들린다. 2026-09-08 회차의
스크래치 스크립트는 `pin 3 → U1.pin4` 와 `pin 4 ← pin 3` 을 다른 것으로 봤다 —
같은 선을 어느 쪽 핀에 적었는가의 차이일 뿐인데 불일치로 찍었다. 그래서 여기는
**간선 집합**으로 비교한다. 살아 있는 실험01 결선도를 한 군데씩 변형해 검사기가
그 자리를 짚는지 본다. 합성 픽스처는 헤딩형 하나(`netlist_heading_chips.md`)만
쓴다 — 실험01 은 전부 불릿형이라 헤딩형 경로를 살아 있는 실물로는 못 밟는다.
"""

import re
import tempfile
import unittest
from pathlib import Path

from scripts.lab import config
from scripts.lab.regen_compare import compare_netlist_pins, pin_nets

ROOT = Path(__file__).resolve().parents[1]
E01 = ROOT / config.experiment_dir(1)
NETLIST = E01 / "결선도/netlist.md"
HEADING = ROOT / "tests/fixtures/netlist_heading_chips.md"


def _variant(replacements):
    """실험01 결선도를 한 군데 바꾼 임시 사본. `replacements` 는 (old, new) 쌍이고
    old 는 원문에 정확히 한 번 있어야 한다 — 두 번 있으면 무엇을 바꿨는지 모른다."""
    text = NETLIST.read_text(encoding="utf-8")
    for old, new in replacements:
        assert text.count(old) == 1, (old, text.count(old))
        text = text.replace(old, new)
    d = Path(tempfile.mkdtemp()) / "결선도"
    d.mkdir()
    p = d / "netlist.md"
    p.write_text(text, encoding="utf-8")
    return p


class PinNets(unittest.TestCase):
    def test_원본_자기대조는_차이_0건(self):
        self.assertEqual(compare_netlist_pins(NETLIST, NETLIST), [])

    def test_불릿형_C1_의_간선이_읽힌다(self):
        nets = pin_nets(NETLIST)
        c1 = nets["E1.P1-1"]
        self.assertIn(frozenset({("PIN", "74HC08", 1), ("IN", "A")}), c1)
        self.assertIn(frozenset({("PIN", "74HC08", 14), ("VCC",)}), c1)
        self.assertIn(frozenset({("PIN", "74HC08", 9), ("GND",)}), c1)      # 미사용 입력
        self.assertIn(frozenset({("PIN", "74HC08", 8), ("OPEN",)}), c1)     # 미사용 출력
        self.assertIn(frozenset({("PIN", "74HC08", 3), ("LED", "L1")}), c1)
        self.assertIn(frozenset({("PIN", "74HC08", 3), ("PIN", "74HC08", 4)}), c1)

    def test_다칩_회로는_U번호가_아니라_칩_종류로_맺는다(self):
        c3 = pin_nets(NETLIST)["E1.P2-1"]
        # 원문은 `U3.pin3 → U4.pin1` 이다. U 번호는 문서마다 달라도 되므로 키는 종류다.
        self.assertIn(frozenset({("PIN", "74HC08", 3), ("PIN", "74HC00", 1)}), c3)

    def test_팬아웃을_반대쪽_핀에만_적어도_같다(self):
        # C3 의 U3.pin3 → U4.pin1 선을 U3 쪽에서 지운다. U4 쪽 `pin 1 ← U3.pin3` 이
        # 같은 간선을 이미 말하므로 차이가 없어야 한다.
        v = _variant([("  - pin 3  → U4.pin1          (게이트1 출력 A·B)\n", "")])
        self.assertEqual(compare_netlist_pins(NETLIST, v), [])

    def test_핀_하나를_옮기면_양방향으로_짚는다(self):
        # C1 의 입력 C 를 pin 5 에서 pin 9 로 옮긴다. 원본에만 있는 간선(5←C)과
        # 재생성에만 있는 간선(9←C)이 **둘 다** 나와야 한다 — 충돌만 찾으면 누락은
        # 안 보인다(런북 §V1).
        v = _variant([("  - pin 5  ← 입력 C\n  - pin 6  → L2 애노드 (330Ω 직렬) → GND    ※ 최종 출력 L2 = A·B·C, T1 의 검증 대상",
                       "  - pin 9  ← 입력 C\n  - pin 6  → L2 애노드 (330Ω 직렬) → GND    ※ 최종 출력 L2 = A·B·C, T1 의 검증 대상")])
        out = compare_netlist_pins(NETLIST, v)
        self.assertTrue(any("E1.P1-1" in s and "원본에만" in s and "pin 5" in s for s in out), out)
        self.assertTrue(any("E1.P1-1" in s and "재생성에만" in s and "pin 9" in s for s in out), out)

    def test_헤딩형_표에서_핀을_읽는다(self):
        nets = pin_nets(HEADING)
        c1 = nets["E10.P1"]
        self.assertIn(frozenset({("PIN", "7490", 5), ("VCC",)}), c1)
        self.assertIn(frozenset({("PIN", "7490", 4), ("OPEN",)}), c1)      # `| 4, 13 | 개방 |`
        self.assertIn(frozenset({("PIN", "7404", 1), ("PIN", "7490", 12)}), c1)   # `| 1 ← | U1 pin 12 (QA) |`
        self.assertIn(frozenset({("PIN", "7404", 11), ("GND",)}), c1)     # `| 미사용 입력핀 11, 13 | GND |`

    def test_항목이_한쪽에만_있으면_그것도_차이다(self):
        v = _variant([("- item: E1.P3\n", "- item: E1.P9\n")])
        out = compare_netlist_pins(NETLIST, v)
        self.assertTrue(any("E1.P3" in s and "원본에만" in s for s in out), out)
        self.assertTrue(any("E1.P9" in s and "재생성에만" in s for s in out), out)


from scripts.lab.regen_compare import (classify_spec_diffs, judgment_markdown,
                                       shared_sentences)

SPEC = E01 / "체크리스트/명세.md"


def _spec_variant(replacements):
    """실험01 명세를 바꾼 임시 사본. **첫 출현만** 바꾼다 — `| 1 | 1 | 1 | 1  | 1  |`
    같은 행은 T1·T2 에 둘 다 있어서 전부 바꾸면 차이가 둘이 된다."""
    text = SPEC.read_text(encoding="utf-8")
    for old, new in replacements:
        assert text.count(old) >= 1, old
        text = text.replace(old, new, 1)
    d = Path(tempfile.mkdtemp()) / config.experiment_folder_name(1) / "체크리스트"
    d.mkdir(parents=True)
    p = d / "명세.md"
    p.write_text(text, encoding="utf-8")
    return p


class SharedSentences(unittest.TestCase):
    def test_자기_자신과는_전부_겹친다(self):
        out = shared_sentences([SPEC], [SPEC])
        self.assertTrue(out)
        self.assertTrue(all(len(s) >= 25 for s in out))

    def test_다른_글과는_안_겹친다(self):
        p = Path(tempfile.mkdtemp()) / "x.md"
        p.write_text("이 문장은 스물다섯 자를 넘기려고 일부러 길게 쓴 문장이다.\n", encoding="utf-8")
        self.assertEqual(shared_sentences([p], [SPEC]), [])


class ClassifySpecDiffs(unittest.TestCase):
    def test_다섯_키가_항상_있다(self):
        out = classify_spec_diffs([])
        self.assertEqual(set(out), {"id_shift", "encoding", "title", "cell", "other"})

    def test_인코딩만_바꾼_사본은_전부_encoding_으로_간다(self):
        # T1 을 0/1 → H/L 로 뒤집는다. 뜻은 같으니 cell 로 세면 안 된다.
        # `\b0\b`·`\b1\b` 는 헤더의 `L1`·`L2` 안 숫자를 건드리지 않는다 —
        # `L` 과 `1` 사이는 단어 경계가 아니다.
        text = SPEC.read_text(encoding="utf-8")
        start = text.index("## T1 ·")
        end = text.index("\n# ", start)
        block = text[start:end].replace("encoding: 0/1", "encoding: H/L")
        block = "\n".join(
            re.sub(r"\b1\b", "H", re.sub(r"\b0\b", "L", l)) if l.startswith("|") else l
            for l in block.splitlines())
        v = _spec_variant([(text[start:end], block)])
        from scripts.lab.specdiff import compare_specs
        got = classify_spec_diffs(compare_specs(SPEC, v))
        self.assertTrue(got["encoding"], got)
        self.assertEqual(got["cell"], [], got)
        self.assertEqual(got["title"], [], got)

    def test_셀_하나를_뒤집으면_cell_이다(self):
        v = _spec_variant([("| 1 | 1 | 1 | 1  | 1  |", "| 1 | 1 | 1 | 1  | 0  |")])
        from scripts.lab.specdiff import compare_specs
        got = classify_spec_diffs(compare_specs(SPEC, v))
        self.assertEqual(len(got["cell"]), 1, got)
        self.assertEqual(got["encoding"], [])

    def test_제목만_바꾸면_title_이다(self):
        v = _spec_variant([("## T1 · 3-input AND 진리표", "## T1 · 3-input AND gate 진리표")])
        from scripts.lab.specdiff import compare_specs
        got = classify_spec_diffs(compare_specs(SPEC, v))
        self.assertEqual(len(got["title"]), 1, got)
        self.assertEqual(got["cell"], [])


class Judgment(unittest.TestCase):
    def test_원본을_원본과_대조한_판정문(self):
        md = judgment_markdown(1, E01, corpus_dirs=[E01 / "output"])
        self.assertIn("compare_specs 차이 0건", md)
        self.assertIn("핀 간선 차이 0건", md)
        self.assertIn("check_netlist error 0건", md)
        self.assertIn("세션 메모리 주입 아래서 돌았다", md)
        self.assertIn("구조 검증이 통과했다는 것은 파서가 읽을 수 있다는 뜻이고", md)
