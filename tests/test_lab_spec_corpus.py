"""살아 있는 명세 전부가 파서와 검사를 통과하는지 훑는다.

이름으로 찍어 보는 테스트(`test_lab_spec_parser.py` 는 실험01·06·10)는
**새로 만든 명세를 보지 않는다.** 실험02·05 는 여태 어떤 테스트도 안 봤다.
glob 으로 훑으면 다음에 만드는 명세가 자동으로 그물에 든다 —
`draft-lab-spec` 이 조용히 깨진 명세를 남길 수 있는 경로를 막는다.

여기 있는 테스트는 **구조만** 본다. 실험02 는 이 검사들을 전부 통과한 채로
물리 오류 두 개를 갖고 있었다. 통과는 "파서가 읽을 수 있다"는 뜻이지
"내용이 맞다"는 뜻이 아니다.
"""

import unittest
from pathlib import Path

from scripts.lab import validate
from scripts.lab.spec_parser import parse_spec

ROOT = Path(__file__).resolve().parents[1]

# `2^n` 행 수 warn 을 정상으로 허용하는 자리. **사유를 반드시 적는다.**
# 사유 없이 늘리면 이 목록이 경고를 삼키는 쓰레기통이 된다.
ROW_COUNT_WARN_ALLOWLIST = {
    ("실험05", "T4"):
        "one-hot 입력 — 입력 하나당 한 행이면 족하다 (교안 p7 원문)",
    ("실험05", "T5"):
        "one-hot 입력. `D0` 가 어느 출력식에도 안 나와 입력 수가 7 로 세진다",
}


def live_specs():
    return sorted(ROOT.glob("실험*/체크리스트/명세.md"))


class LiveSpecCorpus(unittest.TestCase):
    def test_코퍼스가_비어_있지_않다(self):
        # glob 이 0건이면 아래 테스트가 전부 조용히 통과한다.
        self.assertGreaterEqual(len(live_specs()), 5, "명세를 하나도 못 찾았다")

    def test_전부_파싱된다(self):
        for path in live_specs():
            with self.subTest(path.parent.parent.name):
                parse_spec(path)

    def test_명세에_error_가_없다(self):
        for path in live_specs():
            with self.subTest(path.parent.parent.name):
                spec = parse_spec(path)
                errors = [f for f in
                          validate.check_folder_convention(path, spec)
                          + validate.validate_spec(spec)
                          if f.level == "error"]
                self.assertEqual(errors, [],
                                 "\n".join(str(f) for f in errors))

    def test_결선도가_짝으로_있고_error_가_없다(self):
        for path in live_specs():
            with self.subTest(path.parent.parent.name):
                spec = parse_spec(path)
                netlist = path.parent.parent / "결선도" / "netlist.md"
                errors = [f for f in validate.check_netlist(netlist, spec)
                          if f.level == "error"]
                self.assertEqual(errors, [],
                                 "\n".join(str(f) for f in errors))

    def test_warn_은_사유와_함께_허용목록에만_있다(self):
        for path in live_specs():
            folder = path.parent.parent.name
            spec = parse_spec(path)
            for f in validate.validate_spec(spec):
                if f.level != "warn":
                    continue
                table_id = f.where.rsplit(":", 1)[-1]
                with self.subTest(f"{folder}/{table_id}"):
                    self.assertIn(
                        (folder, table_id), ROW_COUNT_WARN_ALLOWLIST,
                        f"허용목록에 사유와 함께 올리거나 표를 고친다: {f}")

    def test_허용목록에_죽은_줄이_없다(self):
        # 표를 고쳐 warn 이 사라져도 목록 줄은 남는다 — 그러면 다음 사람이
        # 그 표를 "허용된 예외" 로 읽는다.
        live = set()
        for path in live_specs():
            folder = path.parent.parent.name
            spec = parse_spec(path)
            live |= {(folder, f.where.rsplit(":", 1)[-1])
                     for f in validate.validate_spec(spec)
                     if f.level == "warn"}
        self.assertEqual(set(ROW_COUNT_WARN_ALLOWLIST) - live, set(),
                         "warn 이 사라진 줄이 허용목록에 남아 있다")
