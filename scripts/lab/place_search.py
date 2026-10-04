"""v2 배치기 — 주차 `배치.py` 의 칩 행·LED 행·브리지 행을 고르고 같은 폴더에 `배치탐색.md` 를 쓴다.

설계: `docs/plans/2026-10-05-v2-배치기-설계.md`. 고른 layout 은 사람이 `배치.py` 의 `LAYOUT` 과 netlist
`kind: layout` 표에 옮겨 적는다 — 테스트(`PlaceEnforced`)가 지문·layout 을 맞댄다. 한 판 실측에
약 1분이라 라운드마다 실측·verify 를 프로세스 `--jobs` 개(기본 min(top, 코어 수))에 나눠 돌린다.
프로세스마다 엔진과 주차 파일을 따로 불러온다 — 주차 빌더(`PlaceCircuit.fixed`)는 피클로 못 넘긴다.

    python -m scripts.lab.place_search 보고서/실험05/결선도/배치.py [--top 8] [--jobs 8]
"""
import argparse
import importlib.util
import json
import os
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py'


def load(path):
    spec = importlib.util.spec_from_file_location('render_breadboard', ENGINE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, mod.load_board_file(Path(path), Path(path).parent.name)


_W = {}


def _init(path):
    """작업 프로세스 하나 — 엔진·주차 파일을 불러 둔다."""
    _W['mod'], _W['board'] = load(path)


def worker_measure(lay):
    return _W['mod']._place_measure(list(_W['board'].PLACE), lay)


def worker_verify(lay):
    return _W['mod'].place_verify(_W['board'], lay, tempfile.mkdtemp())


def run(mod, board, path, top, jobs=1):
    """`place_plan` → `<path 의 폴더>/배치탐색.md`. 결과 dict 를 돌려준다. `jobs` > 1 이면 프로세스 풀."""
    path = Path(path)
    if jobs > 1:
        with ProcessPoolExecutor(jobs, initializer=_init, initargs=(str(path),)) as pool:
            result = mod.place_plan(board, top=top, measure=worker_measure, verify=worker_verify,
                                    mapper=lambda fn, items: list(pool.map(fn, items)), chunk=jobs)
    else:
        result = mod.place_plan(board, top=top)
    (path.parent / mod.PLACE_REPORT).write_text(mod.place_report(result, path.as_posix()), encoding='utf-8')
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('board', help='주차 배치.py 경로')
    ap.add_argument('--top', type=int, default=None, help='라운드마다 실측할 근사 순위 앞 개수')
    ap.add_argument('--jobs', type=int, default=None, help='작업 프로세스 수 (기본 min(top, 코어 수), 1 = 차례대로)')
    a = ap.parse_args(argv)
    t = time.perf_counter()
    mod, board = load(a.board)
    top = a.top or mod.PLACE_TOP
    result = run(mod, board, a.board, top, a.jobs or min(top, os.cpu_count() or 1))
    chosen = next(r for r in result['rows'] if r['status'] == '✔ 고름')
    print(f"고름: 순위 {chosen['rank']} · 길이 {chosen['length']:.1f}칸 · 밀도 {chosen['density']:.1f}칸 "
          f"({time.perf_counter() - t:.0f}초)")
    print('LAYOUT =', json.dumps(result['layout'], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
