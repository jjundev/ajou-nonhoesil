"""추적 환경 변수가 있으면 `tests/_trace.py` 를 불러 기록기를 건다.

`PYTHONPATH=<저장소>/tests/_trace_site:…` 로 자식 파이썬도 이 파일을 먼저 실어, 테스트가 띄운
파이썬 자식이 읽는 파일까지 적는다. `_trace.py` 는 **파일 경로로** 불러 `sys.path` 를 건드리지
않는다 — 자식의 import 환경을 바꾸면 추적이 결과를 바꾼다.
"""

import os

if os.environ.get('AFFECTED_TRACE_DIR'):
    try:
        import importlib.util

        _path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '_trace.py')
        _spec = importlib.util.spec_from_file_location('_affected_trace_site', _path)
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        _mod.install()
    except Exception:
        pass   # 추적 실패가 자식 프로그램을 깨면 안 된다
