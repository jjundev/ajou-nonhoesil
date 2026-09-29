"""xdist 를 `--dist loadgroup` 으로 돌릴 때 그룹을 정한다(`pytest.ini`).

- `tests/_boards.py` 의 `per_builder`·`per_experiment` 가 만든 클래스는 자기
  `render_group` 으로 묶는다 — 같은 회로를 보는 테스트가 한 워커에 모여 렌더 캐시를
  한 번만 채운다.
- `xdist_per_test = True` 인 클래스는 테스트마다 따로 흩는다 — `setUp` 이 매번 새로
  만들어 나눠 쓰는 것이 없고, 한 클래스가 한 워커를 1분 넘게 잡던 자리다.
- 나머지는 파일::클래스 단위로 묶는다. 마크 없는 테스트를 loadgroup 은 낱개로 흩는데,
  그러면 `setUpClass` 준비를 테스트마다 다시 한다.
"""
import pytest


@pytest.hookimpl(tryfirst=True)   # xdist 가 마크를 읽어 nodeid 에 `@그룹` 을 붙이기 전에
def pytest_collection_modifyitems(items):
    for item in items:
        if item.get_closest_marker("xdist_group"):
            continue
        cls = item.cls
        if getattr(cls, "xdist_per_test", False):
            group = item.nodeid
        else:
            group = getattr(cls, "render_group", None) or f"{item.path.name}::{cls.__name__ if cls else ''}"
        item.add_marker(pytest.mark.xdist_group(group))
