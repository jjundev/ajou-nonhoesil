"""주차 빌더를 **한 프로세스에서 한 번만** 그려 두고 테스트끼리 나눠 쓴다.

2026-09-29 실측: `test_breadboard_physical`·`readability`·`nets` 의 "모든 회로" 테스트
열두 개가 저마다 82장을 처음부터 그리고 PNG 로 저장했다가 버렸다 — 한 개에 약 15초,
합쳐 스위트의 절반이다. 보는 항목만 다르고 그리는 일은 같으니 결과를 한 번 잡아 둔다.

돌려주는 렌더러는 **여러 테스트가 같이 보는 객체**다. 값을 바꿔 보려는 테스트는
`copy.copy(bb)` 에 새 값을 붙인다 — 원본의 속성을 바꾸면 뒤 테스트가 오염된다.
"""
import inspect
import os
import tempfile

BOARD_L, BOARD_R = 149, 877

_CACHE = {}


def render(mod, fn):
    """`fn` 을 엔진 `mod` 로 임시 파일에 그리고 `(렌더러, 보드 위 배지 수)` 를 돌려준다.

    export() 안에서 verify() 가 돌므로 결선 규칙도 이때 한 번 검사된다. 배지는 내보낸
    그림 한 장 것만 센다 — 단계 그림은 기준선을 얻으려고 앞 보드를 한 번 더 그리는데,
    그 배지까지 합치면 한 장에 5개인 그림이 10개로 잡힌다.
    """
    key = (inspect.getsourcefile(fn), fn.__name__)
    if key not in _CACHE:
        _CACHE[key] = _render(mod, fn)
    return _CACHE[key]


def _render(mod, fn):
    counted = {}
    captured = {}
    cls = mod.BreadboardRenderer
    orig_badge, orig_export = cls.draw_badge, cls.export

    def spy_badge(self_, x, y, text, *a, **k):
        if BOARD_L < x < BOARD_R:
            counted[self_] = counted.get(self_, 0) + 1
        return orig_badge(self_, x, y, text, *a, **k)

    def spy_export(self_, *a, **k):
        captured['bb'] = self_
        return orig_export(self_, *a, **k)

    cls.draw_badge, cls.export = spy_badge, spy_export
    try:
        with tempfile.TemporaryDirectory() as d:
            fn(os.path.join(d, 'x.png'))
    finally:
        cls.draw_badge, cls.export = orig_badge, orig_export
    bb = captured['bb']
    return bb, counted.get(bb, 0)
