"""v2 배치기 — 주차 `배치.py` 의 칩 행·LED 행·브리지 행을 고르고 같은 폴더에 `배치탐색.md` 를 쓴다.

설계: `docs/plans/2026-10-05-v2-배치기-설계.md`. 고른 layout 은 사람이 `배치.py` 의 `LAYOUT` 과 netlist
`kind: layout` 표에 옮겨 적는다 — 테스트(`PlaceEnforced`)가 지문·layout 을 맞댄다. 한 판 실측에
약 1분, 기본 9판(기준 + 앞 8개)이라 10분 남짓 걸린다.

    python -m scripts.lab.place_search 보고서/실험05/결선도/배치.py [--top 8]
"""
import argparse
import importlib.util
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py'


def load(path):
    spec = importlib.util.spec_from_file_location('render_breadboard', ENGINE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, mod.load_board_file(Path(path), Path(path).parent.name)


def run(mod, board, path, top):
    """`place_plan` → `<path 의 폴더>/배치탐색.md`. 결과 dict 를 돌려준다."""
    path = Path(path)
    result = mod.place_plan(board, top=top)
    (path.parent / mod.PLACE_REPORT).write_text(mod.place_report(result, path.as_posix()), encoding='utf-8')
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('board', help='주차 배치.py 경로')
    ap.add_argument('--top', type=int, default=None, help='라운드마다 실측할 근사 순위 앞 개수')
    a = ap.parse_args(argv)
    t = time.perf_counter()
    mod, board = load(a.board)
    result = run(mod, board, a.board, a.top or mod.PLACE_TOP)
    chosen = next(r for r in result['rows'] if r['status'] == '✔ 고름')
    print(f"고름: 순위 {chosen['rank']} · 길이 {chosen['length']:.1f}칸 · 밀도 {chosen['density']:.1f}칸 "
          f"({time.perf_counter() - t:.0f}초)")
    print('LAYOUT =', json.dumps(result['layout'], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
