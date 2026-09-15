"""테스트가 주차 결선 파일(`보고서/실험NN/결선도/배치.py`)을 찾고 부르는 도우미.

주차 목록은 폴더가 정한다 — 실험 폴더에 `배치.py` 가 생기면 테스트도 따라 는다.
"""
import inspect
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
