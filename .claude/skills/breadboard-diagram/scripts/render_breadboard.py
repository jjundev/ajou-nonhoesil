import os
import re
import sys
import glob
import json
import types
import hashlib
import argparse
import tempfile
import copy
import bisect
import itertools
import math
from dataclasses import dataclass
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

# 저장소 루트. 이 파일은 `<루트>/.claude/skills/breadboard-diagram/scripts/`
# 에 있다. **cwd 로 찾지 않는다** — 예전 후보 목록이 상대 경로여서 저장소
# 루트 밖에서 부르면 조용히 못 찾았고, 그 자리를 메우려고 남의 계정에서는
# 그냥 죽는 절대 경로가 하드코딩돼 있었다.
REPO_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))

# 엔진 몸통은 `engine/` 의 조각들이다 — 아래 순서로 **이 모듈의 이름공간에서** 실행한다.
# 패키지로 나누지 않은 까닭: 엔진을 부를 때마다 독립된 사본이어야 한다(`tests/test_breadboard_boards.py`
# `test_주차_파일은_불러온_엔진의_클래스를_쓴다`). 모듈 전역을 바꿔 끼우는 시험(`other._font = …`,
# `mod._routes = …`)과 사본마다 따로인 캐시(`_ORDERED`·`_PLACE_PATHS`)가 그 위에 선다.
# 설계: `docs/plans/2026-10-05-결선도-엔진-나누기-설계.md`.
#   base.py      템플릿·글꼴·배율·색·판형(`BoardSpec`)
#   checks.py    `_RuleChecks` — R5~R14·넷 모형·`verify()`
#   renderer.py  `BreadboardRenderer` — 그리기·번호 원 자리·도장·`export()`
#   helpers.py   주차 빌더 도우미 — `_tag`·`_input_jumper`
#   router.py    칩 모델 표(`DIP_PINS`)·배선기(`route_plan`)
#   placer.py    배치기(`place_*`)
# 이 파일에는 주차 결선 파일 로더·`build_all`·CLI 가 남는다.
_PARTS = ('base.py', 'checks.py', 'renderer.py', 'helpers.py', 'router.py', 'placer.py')
_ENGINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'engine')
for _part in _PARTS:
    _path = os.path.join(_ENGINE_DIR, _part)
    with open(_path, encoding='utf-8') as _f:
        exec(compile(_f.read(), _path, 'exec'), globals())
del _part, _path, _f


# ---------------------------------------------------------------------------
# 주차 결선 파일 — `보고서/실험NN/결선도/배치.py`
#
# 엔진은 주차를 모른다. 주차마다 결선(칩 자리·배선 순서·단계)은 그 실험 폴더의
# `배치.py` 에 있고, 엔진은 그 파일의 `BOARDS`(기준선 사슬)·`FINALS`(완성본)를
# 뽑기만 한다. 설계: `docs/plans/2026-09-15-결선도-엔진-주차분리-설계.md`.

BOARD_FILE = '배치.py'

# 도장 — PNG 텍스트 청크. 그림이 **무엇을** 싣는가의 해시(`BreadboardRenderer.content()`).
# 글꼴·줄바꿈은 들지 않는다 — 기계가 달라도 선과 문구가 같으면 도장이 같다.
# `tests/test_breadboard_boards.py` 가 커밋된 PNG 의 도장을 지금 코드와 맞댄다.
STAMP_KEY = 'breadboard-stamp'
# PNG 옆 JSON 의 스키마. 체크리스트(`scripts/lab/render.py`)가 같은 문자열을 따로 들고
# 대조한다 — 그쪽은 이 모듈을 import 하지 않는다
SIDECAR_SCHEMA = 'breadboard-sidecar/v1'


def _jsonable(o):
    """`json.dumps` 가 모르는 값 — 집합은 정렬해 목록으로, 나머지는 문자열로."""
    return sorted(o, key=repr) if isinstance(o, (set, frozenset)) else str(o)


def read_stamp(path):
    """PNG 에 찍힌 도장. 없으면 None. `text` 는 PNG 전용 속성이라 다른 형식이면 없다."""
    with Image.open(path) as im:
        return getattr(im, 'text', {}).get(STAMP_KEY)


def _config():
    """`scripts.lab.config` — 실험 폴더 경로 규칙의 정본. 엔진은 스킬 폴더에 있어
    import 경로에 저장소 루트가 없을 수 있다."""
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    from scripts.lab import config
    return config


def board_path(experiment):
    """실험 번호 → 그 주차 결선 파일의 절대 경로. 있는지는 보지 않는다."""
    return os.path.join(REPO_ROOT, _config().experiment_dir(experiment), '결선도', BOARD_FILE)


def board_numbers(root=None):
    """결선 파일이 있는 실험 번호, 오름차순. 폴더 이름을 `experiment_folder_name` 으로
    되돌려 같을 때만 센다 — 이름 규칙은 config 한 곳에 있다."""
    cfg = _config()
    out = []
    for p in glob.glob(os.path.join(root or REPO_ROOT, cfg.EXPERIMENT_BASE, '*', '결선도', BOARD_FILE)):
        name = os.path.basename(os.path.dirname(os.path.dirname(p)))
        m = re.search(r'(\d+)$', name)
        try:
            if m and cfg.experiment_folder_name(int(m.group(1))) == name:
                out.append(int(m.group(1)))
        except ValueError:
            continue
    return sorted(out)


def load_board_file(path, name=None):
    """주차 결선 파일 하나를 모듈로 불러온다.

    그 파일의 `from render_breadboard import …` 는 **이 엔진**을 가리킨다. 테스트와
    대조기는 엔진을 `importlib` 로 여러 번 로드하고 `sys.modules` 에 올리지 않는다 —
    불러오는 동안만 이 엔진의 전역 이름을 담은 모듈을 그 자리에 끼웠다가 되돌린다.
    그래서 주차 파일의 `BreadboardRenderer` 는 이 엔진의 클래스와 같은 객체다.
    불러오는 동안 바이트코드를 쓰지 않는다 — 보고서 폴더에 `__pycache__` 가 생긴다.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(name or 'board', os.path.abspath(path))
    mod = importlib.util.module_from_spec(spec)
    view = types.ModuleType('render_breadboard')
    view.__dict__.update(globals())
    saved, saved_flag = sys.modules.get('render_breadboard'), sys.dont_write_bytecode
    sys.modules['render_breadboard'] = view
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = saved_flag
        if saved is None:
            sys.modules.pop('render_breadboard', None)
        else:
            sys.modules['render_breadboard'] = saved
    board = getattr(mod, 'BOARD', DEFAULT_BOARD)
    if board not in BOARD_VERSIONS:
        raise ValueError(f'{path}: BOARD 는 {BOARD_VERSIONS} 중 하나다: {board!r}')
    return mod


def load_board(experiment):
    path = board_path(experiment)
    mod = load_board_file(path, f'board_e{experiment}')
    require_board(mod, experiment, path)
    return mod


def require_board(board, experiment, label):
    """주차 `배치.py` 는 `BOARD` 를 꼭 적는다. 빠뜨리면 렌더러 기본값(`DEFAULT_BOARD`)으로 그려져
    v1 주차(`config.BOARD_V2_FROM` 앞)가 아무도 모른 채 v2 그림으로 나가고, v2 주차도 기본값이
    바뀌는 날 같은 일을 겪는다. 실험 번호가 정하는 판형과 달라도 적어 두면 연다."""
    want = _config().default_board(experiment)
    if not hasattr(board, 'BOARD'):
        raise ValueError(f"{label}: 실험{experiment} 부터 판형은 {want} 다 — 머리에 BOARD = '{want}' 를 "
                         "두고 빌더마다 BreadboardRenderer(..., board=BOARD) 로 넘긴다")


def board_version(board):
    """주차 결선 모듈의 판형 — 모듈 상수 `BOARD`, 없으면 렌더러 기본값(`DEFAULT_BOARD`)."""
    return getattr(board, 'BOARD', DEFAULT_BOARD)


def check_board(board, bb, label):
    """빌더가 그린 판형이 주차 `BOARD` 와 같은가. 빌더가 `board=BOARD` 를 빠뜨리면 v2 주차가 v1
    그림으로 **조용히** 나간다 — `build_all` 과 손그림 참조(`hand_compare.reference_diagram`)가
    부른다."""
    want = board_version(board)
    if bb.board != want:
        raise ValueError(f"{label}: 주차 BOARD 는 '{want}' 인데 렌더러는 '{bb.board}' 판형이다 — "
                         "빌더가 BreadboardRenderer(..., board=BOARD) 로 넘겨야 한다")


def fresh_board(fn):
    """`rebuild: true` 회로(netlist)의 첫 보드 빌더를 만든다 — 기준선을 버리고 부른다.

    앞 회로의 신호선을 전부 뽑고 새로 짓는 경계라, 앞 보드를 기준선으로 이으면 그
    배선이 전부 '걷는다' 로 잡혀 단계 보드가 선을 걷게 된다(`test_단계_보드는_아무것도_
    걷지_않는다`). 전부 뽑으므로 걷기 보드도 없다 — 체크리스트 배너가 지시한다.
    돌려주는 클로저는 표준 빌더 시그니처라 `BOARDS` 에 그대로 들어간다(2026-09-27, 실험04).
    """
    def build(output_path, template_path=None, stage=None, baseline=None):
        return fn(output_path, template_path, stage=stage, baseline=None)
    build.__name__ = f'fresh_{getattr(fn, "__name__", "board")}'
    return build


def stage_budget(board):
    """주차 `board` 의 단계 예산 — 기본은 `STAGE_WIRE_BUDGET`(셋).

    주차 파일이 `STAGE_WIRE_BUDGET` 을 두면 그 값을 쓴다. 칩 구조상 셋으로는 관측
    노드 하나를 세울 수 없는 주차의 예외다 — 실험04 는 4입력 NAND 라 입력 넷과
    관측선 하나가 한꺼번에 있어야 한다(2026-09-27 결정, 예산 = 게이트 입력 수 + 1).
    **이유(`STAGE_WIRE_BUDGET_REASON`)가 없으면 거절한다** — 숫자만 올리면 예산이
    조용히 풀리고, 무엇 때문에 풀었는지 다음 주차가 알 수 없다.
    """
    value = getattr(board, 'STAGE_WIRE_BUDGET', None)
    if value is None:
        return STAGE_WIRE_BUDGET
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f'주차 STAGE_WIRE_BUDGET 은 양의 정수여야 한다: {value!r}')
    if not str(getattr(board, 'STAGE_WIRE_BUDGET_REASON', '') or '').strip():
        raise ValueError('주차 STAGE_WIRE_BUDGET 예외에는 STAGE_WIRE_BUDGET_REASON 이 있어야 한다 '
                         '— 왜 셋으로 관측 노드 하나를 세울 수 없는지 적는다')
    return value


def removal_board(prev, nxt, title, subtitle):
    """걷기 보드 빌더를 만든다. `prev`·`nxt` 는 `(빌더, stage)`.

    앞 회로(`prev`)를 전부 회색으로 그리고, 다음 회로(`nxt`)에 없는 배선만 빨간 점선 +
    걷기 번호로 그린다. 새 선은 없다. **선을 뽑는 자리마다 한 장** — 회로 경계뿐
    아니라 같은 회로 안의 인접 단계에서 임시 프로브 급전선을 뽑을 때도 같다.

    돌려주는 클로저는 표준 빌더 시그니처라 `BOARDS` 에 그대로 들어간다. `__module__` 이
    엔진이라 주차 파일의 `build_*` 열거(`tests/_boards.py`)에 안 잡힌다 — 걷기 보드는
    `steps` 가 비어 가독성 검사(`steps > 0`)의 대상이 아니다. 주차 파일에 `build_` 로
    시작하는 래퍼를 두지 않는다.

    `baseline` 을 안 넘기면 앞 보드를 임시 렌더해 스스로 만든다 — 단계 래퍼
    (`_eN_board`)가 그렇게 부른다. 사슬(`build_all`)은 앞 보드의 snapshot 을 넘긴다.

    클로저는 `stage` 를 **거절한다** — 앞뒤 회로의 단계는 `prev`·`nxt` 로 이미 정해져
    있어서, 호출 쪽이 또 주면 조용히 무시돼 엉뚱한 단계의 걷기 그림이 나간다.
    """
    prev_fn, prev_stage = prev
    nxt_fn, nxt_stage = nxt

    def build(output_path, template_path=None, stage=None, baseline=None):
        assert stage is None, ('걷기 보드는 stage 를 받지 않는다 — '
                               'prev/nxt 의 stage 는 removal_board() 인자로 준다')
        with tempfile.TemporaryDirectory() as d:
            base = baseline or prev_fn(os.path.join(d, 'prev.png'), template_path,
                                       stage=prev_stage).snapshot()
            nb = nxt_fn(os.path.join(d, 'next.png'), template_path,
                        stage=nxt_stage, baseline=base)
            wires = {r['key']: r['n'] for r in nb.removals()}
            here = {(ch['anode'], ch['cathode'], ch['res_top'], ch['res_bottom'])
                    for ch in nb.led_chains}
            chains = {k: tag for k, tag in base['chains'].items() if k not in here}
        if not wires:
            raise ValueError(f'{title}: 걷을 배선이 없다 — 걷기 보드가 필요 없는 경계다')
        spec = {'wires': wires, 'title': title, 'subtitle': subtitle}
        if chains:
            # 사슬째 뽑는 경계(실험04 8걷기) — 없으면 키를 안 둬 옛 걷기 보드 도장이 그대로다
            spec['chains'] = chains
        ghost = dict(base, ghost=spec)
        return prev_fn(output_path, template_path, stage=prev_stage, baseline=ghost)

    build.__name__ = f'removal_{nxt_fn.__name__}'
    return build


def build_all(board, output_dir, template_path=None):
    """주차 결선 파일 `board` 의 결선도를 전부 뽑는다 — 절차 사슬 `BOARDS` 는 앞 보드를
    기준선으로 이어 그리고(회색·걷기 표), 완성본 `FINALS` 는 기준선 없이 그린다.
    `{파일명: 도장}` 을 돌려준다(사슬 순서, 그다음 완성본)."""
    os.makedirs(output_dir, exist_ok=True)
    made, base = {}, None
    for filename, fn, stage in board.BOARDS:
        bb = fn(os.path.join(output_dir, filename), template_path, stage=stage, baseline=base)
        if bb is None:
            raise TypeError(
                f"{filename}: 빌더 {fn.__name__} 가 렌더러를 돌려주지 않는다 — "
                "빌더 끝에 `return bb` 가 있어야 한다")
        check_board(board, bb, filename)
        base = bb.snapshot()
        made[filename] = bb.stamp()
    for filename, fn in board.FINALS:
        bb = fn(os.path.join(output_dir, filename), template_path)
        if bb is None:
            raise TypeError(
                f"{filename}: 빌더 {fn.__name__} 가 렌더러를 돌려주지 않는다 — "
                "빌더 끝에 `return bb` 가 있어야 한다")
        check_board(board, bb, filename)
        made[filename] = bb.stamp()
    return made


def main():
    parser = argparse.ArgumentParser(description="Breadboard Diagram Generator")
    parser.add_argument("--experiment", type=int, required=True,
                        help="실험 번호 — 보고서/실험NN/결선도/배치.py 의 결선도를 전부 뽑는다")
    parser.add_argument("--output", default=None,
                        help="출력 폴더 (기본: 그 배치.py 가 있는 결선도 폴더)")
    parser.add_argument("--template", default=None, help="양식 이미지 경로 (기본: 주차 BOARD 의 양식 — v1 Breadboard.jpg, v2 breadboard_v2/Breadboard_v2.png)")
    args = parser.parse_args()
    try:
        path = board_path(args.experiment)
    except ValueError as e:
        parser.error(str(e))
    if not os.path.exists(path):
        parser.error(f"주차 결선 파일이 없다: {path}")
    out = args.output or os.path.dirname(path)
    made = build_all(load_board(args.experiment), out, args.template)
    print(f"[SUCCESS] {_config().experiment_folder_name(args.experiment)} "
          f"결선도 {len(made)}장 생성: {out}")


if __name__ == "__main__":
    main()
