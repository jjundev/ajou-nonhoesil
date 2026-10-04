"""v2 배선기 λ 스윕 — 실험04 v2 시험판 MUX·DMUX 를 λ 마다 그려 길이·꺾임·밀도를 잰다.

설계: `docs/plans/2026-10-04-v2-배선기-밀도-설계.md` #11 — 두 회로 모두 길이 ≤ λ=0 × 1.15 인 λ 중
밀도 합이 가장 작은 것(동률이면 작은 λ). 고른 값은 사람이 엔진 `DENSITY_WEIGHT` 에 옮겨 적는다.

    python -m scripts.lab.route_sweep [--out tmp/route_sweep]
"""
import argparse
import importlib.util
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / '.claude/skills/breadboard-diagram/scripts/render_breadboard.py'
TRIAL = ROOT / 'tests/fixtures/board_v2_e4/배치.py'
WEIGHTS = (0.0, 0.5, 1.0, 2.0, 4.0, 8.0)
LENGTH_SLACK = 1.15


def load():
    spec = importlib.util.spec_from_file_location('render_breadboard', ENGINE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, mod.load_board_file(TRIAL, 'board_v2_e4')


def measure(mod, build, out_png, weight):
    """한 회로·한 λ. 막히면(경로 없음) {'weight', 'blocked': 첫 줄}."""
    t = time.perf_counter()
    try:
        bb = build(str(out_png), density_weight=weight)
    except AssertionError as e:
        return {'weight': weight, 'blocked': str(e).splitlines()[0]}
    m = mod.wire_metrics(bb)
    m.update(weight=weight, seconds=round(time.perf_counter() - t, 1))
    return m


def pick(rows, slack=LENGTH_SLACK):
    """rows = {'mux': [...], 'dmux': [...]}, 두 목록 같은 λ 순서, 첫 행은 λ=0 기준."""
    mux, dmux = rows['mux'], rows['dmux']
    if mux[0]['weight'] != 0 or dmux[0]['weight'] != 0 or 'blocked' in mux[0] or 'blocked' in dmux[0]:
        raise ValueError('첫 행은 막히지 않은 λ=0 기준이어야 한다')
    best_d, best_w = mux[0]['density'] + dmux[0]['density'], 0.0
    for a, b in zip(mux[1:], dmux[1:]):
        if 'blocked' in a or 'blocked' in b:
            continue
        if a['length'] > mux[0]['length'] * slack or b['length'] > dmux[0]['length'] * slack:
            continue
        d = a['density'] + b['density']
        if d < best_d:
            best_d, best_w = d, a['weight']
    return best_w


def _cell(r):
    if 'blocked' in r:
        return f"막힘: {r['blocked']} | | "
    return f"{r['length']:.0f} | {r['bends']} | {r['density']:.1f}"


def table(rows, chosen):
    lines = ['| λ | MUX 길이 | MUX 꺾임 | MUX 밀도 | DMUX 길이 | DMUX 꺾임 | DMUX 밀도 | 초 |',
             '|---|---|---|---|---|---|---|---|']
    for a, b in zip(rows['mux'], rows['dmux']):
        mark = ' ✔' if a['weight'] == chosen else ''
        secs = a.get('seconds', 0) + b.get('seconds', 0)
        lines.append(f"| {a['weight']:g}{mark} | {_cell(a)} | {_cell(b)} | {secs:.0f} |")
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', default=str(ROOT / 'tmp/route_sweep'))
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    mod, board = load()
    rows = {'mux': [], 'dmux': []}
    for w in WEIGHTS:
        rows['mux'].append(measure(mod, board.build_trial_mux, out / f'mux_l{w:g}.png', w))
        rows['dmux'].append(measure(mod, board.build_trial_dmux, out / f'dmux_l{w:g}.png', w))
        print(w, rows['mux'][-1], rows['dmux'][-1], flush=True)
    chosen = pick(rows)
    text = f'# v2 배선기 λ 스윕\n\n길이·밀도 단위는 칸. 고른 λ = {chosen:g}\n\n{table(rows, chosen)}\n'
    (out / 'sweep.md').write_text(text, encoding='utf-8')
    print(text)
    return chosen


if __name__ == '__main__':
    main()
