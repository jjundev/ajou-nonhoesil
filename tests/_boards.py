"""테스트가 주차 결선 파일(`보고서/실험NN/결선도/배치.py`)을 찾고 부르는 도우미.

주차 목록은 폴더가 정한다 — 실험 폴더에 `배치.py` 가 생기면 테스트도 따라 는다.
"""
import ast
import inspect
import re
from pathlib import Path

from scripts.lab import config

ROOT = Path(__file__).resolve().parents[1]


def board_files():
    """주차 결선 파일 경로, 이름순. 소스를 ast 로 읽는 테스트용 — 엔진을 불러오지 않는다."""
    return sorted((ROOT / config.EXPERIMENT_BASE).glob("실험*/결선도/배치.py"))


def all_builders(mod):
    """엔진 `mod` 로 불러온 모든 주차의 `build_*` 함수. 같은 엔진으로 불러야 테스트가
    `mod.BreadboardRenderer` 에 건 스파이가 빌더에도 걸린다."""
    out = {}
    for n in mod.board_numbers():
        board = mod.load_board(n)
        for name, fn in vars(board).items():
            if (name.startswith("build_") and inspect.isfunction(fn)
                    and fn.__module__ == board.__name__):
                out[name] = fn
    return out


def builder_names():
    """주차 파일의 `build_*` 이름, 이름순 — ast 로 읽어 엔진 없이 수집 시점에 쓴다.
    `all_builders()` 와 같은 집합인지는 `test_breadboard_nets` 가 본다."""
    return sorted(n.name for p in board_files()
                  for n in ast.parse(p.read_text(encoding="utf-8")).body
                  if isinstance(n, ast.FunctionDef) and n.name.startswith("build_"))


def experiment_numbers():
    """결선 파일이 있는 실험 번호, 오름차순 — 폴더 이름에서 읽는다."""
    return [int(re.search(r"(\d+)$", p.parent.parent.name).group(1)) for p in board_files()]


def _spawn(base, ns, suffixes, attr):
    """`base` 를 `suffixes` 마다 하나씩 복제해 `ns` 에 넣고 `base` 는 모듈에서 뺀다 —
    남겨 두면 unittest 가 값 없는 원본까지 돌린다(`__test__` 는 pytest 만 읽는다).

    복제 클래스의 `render_group` 이 `tests/conftest.py` 에서 `xdist_group` 이 된다.
    """
    del ns[base.__name__]
    for s, value in suffixes:
        name = f"{base.__name__}_{s}"
        group = value if attr == "builder_name" else name
        ns[name] = type(name, (base,), {attr: value, "render_group": group,
                                        "__module__": ns["__name__"]})


def per_builder(base, ns):
    """회로마다 클래스 하나. 그룹 이름이 빌더 이름이라 파일이 달라도 같은 회로를
    보는 테스트는 한 워커에 모이고, 렌더 캐시(`tests/_renders.py`)를 한 번만 채운다."""
    _spawn(base, ns, [(n, n) for n in builder_names()], "builder_name")


def per_experiment(base, ns):
    """실험마다 클래스 하나 — 캐시를 안 쓰는 일괄 렌더 테스트를 실험별로 흩는다."""
    _spawn(base, ns, [(f"e{n:02d}", n) for n in experiment_numbers()], "experiment")


_ONCE = {}


def load_once(loader):
    """`loader()` 가 돌려준 엔진과 그 `all_builders()` 를 로더마다 한 번만 만든다 —
    회로별 클래스 마흔두 개가 `setUpClass` 에서 엔진을 저마다 다시 실행하지 않게."""
    if loader not in _ONCE:
        mod = loader()
        _ONCE[loader] = (mod, all_builders(mod))
    return _ONCE[loader]
