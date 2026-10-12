"""손그림 모사 시험판 — 완성본 결선도 한 장을 배선만 마커로 그은 것처럼 흔들어 그린다.

주차 결선 파일(`배치.py`)의 `FINALS` 에서 이름이 같은 빌더를 `hand=<시드>` 로 부른다. 시드는
출력 파일 이름에서 나오므로 다시 뽑아도 같은 그림이다. 사이드카·도장은 없다.

    .venv/bin/python -m scripts.lab.hand_sim --experiment 4 --final 실험04_1-1_결선도_4x1MUX.png
"""
import argparse
import hashlib
from pathlib import Path

from scripts.lab.hand_grid import REPO_ROOT, load_renderer


def hand_seed(filename):
    return int.from_bytes(hashlib.sha256(filename.encode('utf-8')).digest()[:8], 'big')


def main(argv=None):
    parser = argparse.ArgumentParser(description='완성본 결선도 한 장을 손그림 모사로 뽑는다')
    parser.add_argument('--experiment', type=int, required=True)
    parser.add_argument('--final', required=True, help='배치.py FINALS 의 완성본 PNG 이름')
    parser.add_argument('--out', default=str(REPO_ROOT / 'tmp/hand-sim'))
    args = parser.parse_args(argv)

    finals = dict(load_renderer().load_board(args.experiment).FINALS)
    if args.final not in finals:
        raise SystemExit(f'FINALS 에 없는 완성본: {args.final} — 가능한 이름: {", ".join(finals)}')
    out = Path(args.out) / args.final.replace('결선도', '손그림모사')
    finals[args.final](str(out), hand=hand_seed(out.name))
    return out


if __name__ == '__main__':
    main()
