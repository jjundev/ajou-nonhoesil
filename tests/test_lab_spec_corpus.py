"""살아 있는 명세 전부가 파서와 검사를 통과하는지 훑는다.

이름으로 찍어 보는 테스트는 **새로 만든 명세를 보지 않는다.** glob 으로
훑으면 다음에 만드는 명세가 자동으로 그물에 든다 — `draft-lab-spec` 이
조용히 깨진 명세를 남길 수 있는 경로를 막는다.

2026-09-10 에 실험02~10 을 2026-2 교안 기준으로 다시 쓰려고 지웠다. 이 파일의
검사는 그때 번호를 박은 목록을 전부 버리고 실물 glob 으로 옮겼다 — 실험이
하나씩 돌아올 때마다 목록을 고치지 않아도 자동으로 그물에 들게 하려는 것이고,
동시에 재작성 중인 빈 자리 때문에 빨간불이 뜨지 않게 하려는 것이다.

여기 있는 테스트는 **구조만** 본다. 실험02 는 이 검사들을 전부 통과한 채로
물리 오류 두 개를 갖고 있었다. 통과는 "파서가 읽을 수 있다"는 뜻이지
"내용이 맞다"는 뜻이 아니다.
"""

import unittest
from pathlib import Path

from scripts.lab import config, validate
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
    # glob 도 기반 폴더를 거친다. 여기에 `실험*` 만 적어 두면 이동 뒤 0건이
    # 되고, `test_코퍼스가_비어_있지_않다` 하나만 빨개진 채 나머지 네 검사가
    # 조용히 통과한다 — 그물이 있다는 착각이 그물이 없는 것보다 나쁘다.
    return sorted((ROOT / config.EXPERIMENT_BASE).glob("실험*/체크리스트/명세.md"))


class LiveSpecCorpus(unittest.TestCase):
    def test_코퍼스가_비어_있지_않다(self):
        # glob 이 0건이면 아래 테스트가 전부 조용히 통과한다. 여기서 막는 건
        # **0건**이지 코퍼스가 줄어드는 것이 아니다 — 2026-09-10 에 실험02~10
        # 을 교안 기준으로 다시 쓰려고 지웠고, 그동안 살아 있는 명세는
        # 실험01 하나다. 명세를 새로 놓으면 glob 이 알아서 다시 문다.
        self.assertGreaterEqual(len(live_specs()), 1, "명세를 하나도 못 찾았다")

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

    def test_진리표_열_이름이_강의노트에_있다(self):
        """이름 검사는 전부 명세 기준이라 명세가 강의노트와 어긋나면 하류가 다 통과한다
        (2026-09-14 실험03 `Bo`). 강의노트 PDF 쪽 텍스트와 직접 맞댄다."""
        for path in live_specs():
            with self.subTest(path.parent.parent.name):
                spec = parse_spec(path)
                pages = validate.extract_manual_pages(ROOT / spec.source_manual)
                errors = [f for f in validate.check_manual_names(spec, pages)
                          if f.level == "error"]
                self.assertEqual(errors, [], "\n".join(str(f) for f in errors))

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
        folders = set()
        for path in live_specs():
            folder = path.parent.parent.name
            folders.add(folder)
            spec = parse_spec(path)
            live |= {(folder, f.where.rsplit(":", 1)[-1])
                     for f in validate.validate_spec(spec)
                     if f.level == "warn"}
        # 재작성 대기 중인 실험의 줄은 재운다. 지워 버리면 그 실험을 다시 쓸
        # 때 사유(교안 원문 근거)가 함께 사라져 warn 을 새로 조사하게 된다.
        # 폴더가 돌아왔는데도 warn 이 없으면 그때 죽은 줄로 잡힌다.
        dead = {k for k in ROW_COUNT_WARN_ALLOWLIST if k[0] in folders} - live
        self.assertEqual(dead, set(),
                         "warn 이 사라진 줄이 허용목록에 남아 있다")


class 인쇄본_코퍼스(unittest.TestCase):
    """커밋된 여섯 주차 인쇄본이 저장소 자체 검사를 통과하는가.

    실험02 인쇄본이 `**` 10개를 담은 채 커밋된 적이 있다 — `_stepped_html` 이
    `_plain` 을 안 씌웠고, `prep-lab-checklist` 절차가 `check_rendered_html` 을
    안 돌려서 아무도 못 봤다. 산출물을 커밋하는 저장소라 산출물도 검사한다.
    """

    def test_인쇄본에_마크다운_표기가_남지_않는다(self):
        # 명세가 살아 있으면 그 주차 인쇄본도 있어야 한다. 번호를 박지 않고
        # 명세에서 끌어오면, 재작성으로 실험이 빠졌다 돌아오는 동안 이 검사가
        # "인쇄본이 없다" 로 빨개지지 않으면서도 **명세만 있고 인쇄본을 안 낸**
        # 진짜 누락은 그대로 잡는다.
        specs = live_specs()
        self.assertTrue(specs, "명세를 하나도 못 찾았다")
        for spec_path in specs:
            folder = spec_path.parent.parent
            path = folder / "체크리스트/체크리스트.html"
            with self.subTest(folder.name):
                self.assertTrue(path.exists(), f"{path} 가 없다")
                errors = [f for f in validate.check_rendered_html(path)
                          if f.level == "error"]
                self.assertEqual(
                    [str(f) for f in errors], [],
                    f"{folder.name} 인쇄본이 자체 검사에서 error 를 낸다")
