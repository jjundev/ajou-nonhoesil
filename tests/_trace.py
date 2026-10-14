"""테스트가 읽은 파일을 감사 훅(`sys.addaudithook`)으로 적는 추적기 — 표준 라이브러리만 쓴다.

변경 기반 테스트 라우터가 테스트 파일마다 따로 띄운 프로세스에서 쓴다(`tests/test_*.py` 하나당
`python -m pytest -n0 -p tests._trace`, 환경 변수 `AFFECTED_TRACE_DIR`·`AFFECTED_ROOT`,
`PYTHONPATH=<저장소>/tests/_trace_site:<저장소>`). 프로세스마다 `<AFFECTED_TRACE_DIR>/<pid>.json`
하나를 남기고, 라우터가 그것들을 합친다::

    {"files": [...], "dirs": [...], "spawned": [[...]], "opaque": bool}   # 모두 정렬

- files   읽기로 연 파일(저장소 상대 NFC posix 경로) + `sys.modules` 의 소스 파일
- dirs    `os.scandir`·`os.listdir` 로 훑은 디렉터리(저장소 루트 자신은 뺀다)
- spawned `subprocess.Popen` 으로 띄운 자식의 argv
- opaque  추적이 끊긴 자식을 띄웠다 — 이 테스트가 무엇을 읽는지 다 알 수 없다

추적이 켜진 자식 파이썬은 `tests/_trace_site/sitecustomize.py` 가 이 파일을 불러 같은 기록을 남긴다.
"""

import atexit
import functools
import json
import os
import shlex
import sys
import threading
import unicodedata

ENV_DIR = 'AFFECTED_TRACE_DIR'
ENV_ROOT = 'AFFECTED_ROOT'
SKIP_PREFIXES = ('.git/', '.venv/', '.pytest_cache/', 'tmp/', '.claude/worktrees/')

# 한 프로세스에 기록기는 하나다. sitecustomize 는 이 파일을 파일 경로로 불러(= 다른 모듈 객체)
# install() 하고, `-p tests._trace` 의 pytest_configure 도 install() 한다 — 모듈 전역이 아니라
# `sys` 에 걸어야 두 사본이 같은 기록기를 본다.
_SLOT = '_affected_trace_recorder'

_HANDLED = frozenset({'open', 'os.scandir', 'os.listdir', 'os.system', 'subprocess.Popen'})
# 이 파이썬 플래그는 PYTHONPATH·사이트를 무시해 sitecustomize 가 안 실린다.
_UNTRACED_FLAGS = 'IES'
_STOP_FLAGS = 'cm'       # 뒤따르는 것이 코드·모듈 — 여기서 플래그 읽기를 멈춘다
_VALUE_FLAGS = 'WXQ'     # 값을 받는 플래그 — 값(붙었으면 같은 덩어리, 아니면 다음 인자)만 건너뛴다
_SITE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_trace_site')


@functools.lru_cache(maxsize=None)
def _roots(root: str) -> tuple:
    """`root` 의 표기들(그대로·실경로) — macOS `/var` ↔ `/private/var` 처럼 같은 곳의 두 이름."""
    norm = (lambda p: unicodedata.normalize('NFC', os.path.normpath(p)))
    forms = [norm(root)]
    real = norm(os.path.realpath(root))
    if real not in forms:
        forms.append(real)
    return tuple(forms)


def rel(path, root: str, cwd: str | None = None) -> str | None:
    """`path` 의 저장소 상대 NFC posix 경로. 저장소 밖·건너뛸 곳·`__pycache__` 면 `None`.

    상대 경로는 `cwd`(없으면 지금 작업 디렉터리)로 푼다. 저장소 루트 자신은 `''`.
    `…/__pycache__/m.cpython-314.pyc` 는 원본 `…/m.py` 로 돌린다.
    """
    p = os.fsdecode(os.fspath(path))
    if not os.path.isabs(p):
        p = os.path.join(cwd if cwd is not None else os.getcwd(), p)
    p = unicodedata.normalize('NFC', os.path.normpath(p))
    for base in _roots(root):
        if p == base:
            return ''
        prefix = base.rstrip(os.sep) + os.sep
        if p.startswith(prefix):
            out = p[len(prefix):].replace(os.sep, '/')
            break
    else:
        return None
    parts = out.split('/')
    if '__pycache__' in parts:
        # pyc 만 원본으로 돌린다. 그 밖의 `__pycache__` 안(디렉터리 자신 포함)은 버린다.
        if len(parts) < 2 or parts[-2] != '__pycache__' or not parts[-1].endswith('.pyc'):
            return None
        parts = parts[:-2] + [parts[-1].split('.')[0] + '.py']
        out = '/'.join(parts)
    if (out + '/').startswith(SKIP_PREFIXES):
        return None
    return out


def is_read(mode, flags) -> bool:
    """`open` 이벤트가 읽기 전용인가. `mode` 가 문자열이면 그것으로, `None` 이면 `os.open` 플래그로."""
    if isinstance(mode, str):
        return not any(c in mode for c in 'wax+')
    return (flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT)) == 0


def _is_pathlike(x) -> bool:
    return isinstance(x, (str, bytes, os.PathLike))


def _split_args(args) -> list:
    """Popen 감사 이벤트의 args 를 argv 목록으로. 윈도의 CPython 은 `list2cmdline` 문자열을 준다."""
    if isinstance(args, (str, bytes)):
        text = os.fsdecode(args)
        try:
            tokens = shlex.split(text, posix=False)   # 역슬래시 경로를 보존한다
        except ValueError:
            tokens = text.split()
        return [t[1:-1] if len(t) >= 2 and t[0] == t[-1] and t[0] in '"\'' else t for t in tokens]
    return [os.fsdecode(a) for a in args]


def _env_has(env, name: str):
    """Popen `env`(str 또는 bytes 키)의 `name` 값. 없으면 `None`."""
    for k, v in env.items():
        if os.fsdecode(k) == name:
            return os.fsdecode(v)
    return None


def _site_on_path(pythonpath: str | None) -> bool:
    entries = [e for e in (pythonpath or '').split(os.pathsep) if e]
    targets = {os.path.normcase(os.path.normpath(_SITE_DIR)),
               os.path.normcase(os.path.realpath(_SITE_DIR))}
    return any(os.path.normcase(os.path.normpath(e)) in targets for e in entries)


def _traces_child(argv: list, executable, env) -> bool:
    """이 Popen 이 추적이 이어지는 파이썬 자식인가."""
    name = os.fsdecode(executable) if executable else (argv[0] if argv else '')
    base = name.replace('\\', '/').rsplit('/', 1)[-1].lower()   # 윈도 경로도 이름만 뽑는다
    if not (base.startswith('python') or name == sys.executable):
        return False
    if env is not None:
        # 자식이 sitecustomize 를 실으려면 추적 변수와 `_trace_site` 경로가 둘 다 있어야 한다.
        if _env_has(env, ENV_DIR) is None or not _site_on_path(_env_has(env, 'PYTHONPATH')):
            return False
    i = 1
    while i < len(argv):
        arg = argv[i]
        if not arg.startswith('-') or arg.startswith('--'):
            break
        skip = 1
        for j, c in enumerate(arg[1:], 1):
            if c in _UNTRACED_FLAGS:
                return False
            if c in _STOP_FLAGS:
                return True
            if c in _VALUE_FLAGS:
                skip = 2 if j == len(arg) - 1 else 1
                break
        i += skip
    return True


class Recorder:
    """감사 이벤트를 받아 읽은 파일·훑은 디렉터리·띄운 자식을 모은다."""

    def __init__(self, root: str):
        self.root = root
        self.files: set[str] = set()
        self.dirs: set[str] = set()
        self.spawned: set[tuple] = set()
        self.opaque = False
        self._done = False
        self._busy = threading.local()   # 훅이 하는 파일 일로 다시 훅이 불리지 않게

    def hook(self, event: str, args: tuple) -> None:
        # 감사 훅이 예외를 내면 추적되는 프로그램이 깨진다 — 무엇이 와도 삼킨다.
        if event not in _HANDLED or self._done or getattr(self._busy, 'on', False):
            return
        self._busy.on = True
        try:
            if event == 'open':
                self._open(*args[:3])
            elif event in ('os.scandir', 'os.listdir'):
                # 가져오기 기계(FileFinder 가 패키지 디렉터리를 listdir)가 낸 것은 테스트가 훑은 게 아니다.
                if not sys._getframe(1).f_code.co_filename.startswith('<frozen importlib'):
                    self._listing(args[0] if args else None)
            elif event == 'subprocess.Popen':
                try:
                    self._popen(*args[:4])
                except Exception:
                    self.opaque = True   # 무엇을 띄웠는지 못 읽으면 보수적으로
            elif event == 'os.system':
                self.opaque = True
        except Exception:
            pass
        finally:
            self._busy.on = False

    def _open(self, path, mode, flags) -> None:
        if not _is_pathlike(path) or not is_read(mode, flags):
            return
        r = rel(path, self.root, os.getcwd())
        if r:
            self.files.add(r)

    def _listing(self, path) -> None:
        if path is None:
            path = os.getcwd()
        if not _is_pathlike(path):
            return
        r = rel(path, self.root, os.getcwd())
        if r:
            self.dirs.add(r)

    def _popen(self, executable, args, cwd, env) -> None:
        argv = _split_args(args)
        self.spawned.add(tuple(argv))
        if not _traces_child(argv, executable, env):
            self.opaque = True
        here = os.getcwd()
        base = os.path.join(here, os.fsdecode(cwd)) if cwd is not None else here
        for arg in argv:
            r = rel(arg, self.root, base)
            if not r:
                continue
            full = os.path.join(base, arg)
            if os.path.isfile(full):
                self.files.add(r)
            elif os.path.isdir(full):
                self.dirs.add(r)

    def _snapshot(self, items: set) -> list:
        """다른 스레드가 훅에서 집합을 바꾸는 중에도 복사한다(`RuntimeError` 면 다시). 끝내 못 하면 opaque."""
        for _ in range(100):
            try:
                return list(items)
            except RuntimeError:
                continue
        self.opaque = True
        return []

    def finish(self, out_dir: str) -> None:
        """`<out_dir>/<pid>.json` 을 쓴다. 쓰는 동안 훅이 자기 일을 적지 않게 먼저 멈춘다."""
        self._done = True
        files = set(self._snapshot(self.files))
        for mod in list(sys.modules.values()):
            f = getattr(mod, '__file__', None)
            if isinstance(f, str):
                try:
                    r = rel(f, self.root)
                except Exception:
                    continue
                if r:
                    files.add(r)
        data = {'files': sorted(files), 'dirs': sorted(self._snapshot(self.dirs)),
                'spawned': sorted(list(a) for a in self._snapshot(self.spawned)), 'opaque': self.opaque}
        os.makedirs(out_dir, exist_ok=True)
        final = os.path.join(out_dir, f'{os.getpid()}.json')
        tmp = final + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False)
        os.replace(tmp, final)


def install() -> 'Recorder | None':
    """`AFFECTED_TRACE_DIR` 이 있으면 이 프로세스에 기록기를 건다(한 번만). 없으면 `None`."""
    out_dir = os.environ.get(ENV_DIR)
    if not out_dir:
        return None
    existing = getattr(sys, _SLOT, None)
    if existing is not None:
        return existing
    root = os.environ.get(ENV_ROOT) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rec = Recorder(root)
    setattr(sys, _SLOT, rec)
    sys.addaudithook(rec.hook)
    atexit.register(rec.finish, out_dir)
    return rec


def pytest_configure(config) -> None:
    """`-p tests._trace` 로만 실린다."""
    install()
