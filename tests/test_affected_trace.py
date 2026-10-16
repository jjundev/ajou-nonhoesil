"""추적기(`tests/_trace.py`) 검사 — 테스트가 읽은 파일·훑은 디렉터리·띄운 자식을 적는다.

끝단 시험은 임시 프로젝트에서 pytest 를 따로 띄워 `<pid>.json` 을 모아 본다.
"""

import json
import os
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

from tests._trace import Recorder, install, is_read, rel

REPO = Path(__file__).resolve().parents[1]
# 가짜 저장소 루트 — POSIX 는 `/r`, 윈도는 `C:\r`(3.13 부터 `/r` 은 윈도에서 절대 경로가 아니다).
R = os.path.abspath(os.sep + 'r')


def _p(*parts: str) -> str:
    return os.path.join(R, *parts)


def test_pyc_는_원본_py_로_적는다():
    assert rel(_p('scripts', 'lab', '__pycache__', 'md.cpython-314.pyc'), R) == 'scripts/lab/md.py'


def test_저장소_밖과_건너뛸_곳은_버린다():
    assert rel(os.path.abspath(os.sep + 'elsewhere') + os.sep + 'x.md', R) is None
    assert rel(_p('.git', 'HEAD'), R) is None
    assert rel(_p('tmp', 'a.md'), R) is None
    assert rel(_p('scripts', '__pycache__'), R) is None


def test_NFD_를_NFC_로():
    nfd = unicodedata.normalize('NFD', _p('보고서', '실험05', '명세.md'))
    assert rel(nfd, R) == unicodedata.normalize('NFC', '보고서/실험05/명세.md')


def test_읽기만_센다():
    assert is_read('r', 0) and is_read('rb', 0)
    assert not is_read('w', 0) and not is_read('r+', 0) and not is_read('ab', 0)
    assert is_read(None, os.O_RDONLY) and not is_read(None, os.O_WRONLY | os.O_CREAT)


def _trace_run(tmp_path, body: str, *, extra_env=None, extra_files=None) -> dict:
    """임시 프로젝트에서 `body` 를 pytest 로 돌리고 `<pid>.json` 들을 합쳐 돌려준다."""
    proj = tmp_path / 'proj'
    (proj / 'sub').mkdir(parents=True)
    (proj / 'data.txt').write_text('d', encoding='utf-8')
    (proj / 'sub' / 'a.txt').write_text('a', encoding='utf-8')
    (proj / 'child.txt').write_text('c', encoding='utf-8')
    for name, text in (extra_files or {}).items():
        (proj / name).parent.mkdir(parents=True, exist_ok=True)
        (proj / name).write_text(text, encoding='utf-8')
    (proj / 'test_x.py').write_text(body, encoding='utf-8')
    out = tmp_path / 'out'
    out.mkdir()
    env = {**os.environ, 'AFFECTED_TRACE_DIR': str(out), 'AFFECTED_ROOT': str(proj),
           'PYTHONPATH': f'{REPO}/tests/_trace_site{os.pathsep}{REPO}', **(extra_env or {})}
    if os.name == 'nt':
        # UCRT의 spawnve는 부모 환경에 숨은 드라이브 경로가 전혀 없으면 충돌한다
        # (cpython#137934). cmd.exe가 보통 넣는 항목을 테스트 부모에만 보충한다.
        # 아래 body가 spawnve에 넘기는 빈 환경/추적 환경과 네이티브 호출은 그대로다.
        drive = os.path.splitdrive(str(proj))[0]
        if len(drive) == 2 and drive[1] == ':':
            env.setdefault(f'={drive}', str(proj))
    done = subprocess.run(
        [sys.executable, '-m', 'pytest', '-n0', '-p', 'tests._trace', '-p', 'no:cacheprovider',
         '-q', 'test_x.py'],
        cwd=proj, env=env, capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
    merged = {'files': set(), 'dirs': set(), 'spawned': [], 'opaque': False, 'count': 0}
    for jf in sorted(out.glob('*.json')):
        one = json.loads(jf.read_text(encoding='utf-8'))
        merged['files'] |= set(one['files'])
        merged['dirs'] |= set(one['dirs'])
        merged['spawned'] += one['spawned']
        merged['opaque'] = merged['opaque'] or one['opaque']
        merged['count'] += 1
    merged['files'] = sorted(merged['files'])
    merged['dirs'] = sorted(merged['dirs'])
    return merged


def test_읽은_파일_훑은_디렉터리_파이썬_자식을_적는다(tmp_path):
    got = _trace_run(tmp_path, '''
import subprocess, sys
from pathlib import Path
def test_x():
    Path('data.txt').read_text()
    list(Path('sub').glob('*.txt'))
    subprocess.run([sys.executable, '-c', "open('child.txt').read()"], check=True)
''')
    assert {'data.txt', 'child.txt', 'test_x.py'} <= set(got['files'])
    assert 'sub' in got['dirs']
    assert got['opaque'] is False


def test_chdir_뒤_상대경로도_저장소_경로로_적는다(tmp_path):
    got = _trace_run(tmp_path, '''
import os
def test_x():
    os.chdir('sub'); open('a.txt').read()
''')
    assert 'sub/a.txt' in got['files']


def test_추적_변수_없이_띄운_파이썬_자식은_opaque(tmp_path):
    got = _trace_run(tmp_path, '''
import subprocess, sys
def test_x():
    subprocess.run([sys.executable, '-c', 'pass'], env={}, check=True)
''')
    assert got['opaque'] is True


@pytest.mark.skipif(os.name != 'posix', reason='`cat` 은 POSIX 에만 있다')
def test_비파이썬_자식은_opaque_이고_인자_경로를_적는다(tmp_path):
    got = _trace_run(tmp_path, '''
import subprocess
def test_x():
    subprocess.run(['cat', 'data.txt'], check=True, capture_output=True)
''')
    assert got['opaque'] is True and 'data.txt' in got['files']


def test_환경을_무시하는_파이썬_플래그를_준_자식은_opaque(tmp_path):
    # -I 는 PYTHONPATH 를 무시해 sitecustomize 가 안 실린다 — env 를 안 건드려도 추적이 끊긴다.
    got = _trace_run(tmp_path, '''
import subprocess, sys
def test_x():
    subprocess.run([sys.executable, '-I', '-c', 'pass'], check=True)
''')
    assert got['opaque'] is True


def test_자식에게_추적_변수를_넘기면_opaque_아님(tmp_path):
    got = _trace_run(tmp_path, '''
import os, subprocess, sys
def test_x():
    subprocess.run([sys.executable, '-c', 'pass'], env=dict(os.environ), check=True)
''')
    assert got['opaque'] is False


def test_추적_변수가_없으면_설치하지_않는다(monkeypatch):
    monkeypatch.delenv('AFFECTED_TRACE_DIR', raising=False)
    assert install() is None


def test_install_을_두_번_불러도_기록기와_JSON_은_하나(tmp_path):
    # 추적되는 pytest 에서는 sitecustomize(파일 경로 적재)와 -p tests._trace 가 둘 다 install() 한다.
    out = tmp_path / 'out'
    out.mkdir()
    code = (
        'import sys, importlib.util\n'
        f"sys.path.insert(0, {str(REPO)!r})\n"
        'import tests._trace as a\n'
        f"spec = importlib.util.spec_from_file_location('other_trace', {str(REPO / 'tests/_trace.py')!r})\n"
        'b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)\n'
        'r1, r2, r3 = a.install(), b.install(), a.install()\n'
        'assert r1 is not None and r1 is r2 is r3\n'
    )
    env = {**os.environ, 'AFFECTED_TRACE_DIR': str(out), 'AFFECTED_ROOT': str(tmp_path)}
    env.pop('PYTHONPATH', None)
    done = subprocess.run([sys.executable, '-c', code], cwd=tmp_path, env=env,
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
    assert len(list(out.glob('*.json'))) == 1


def test_훅은_엉뚱한_인자에도_예외를_내지_않는다():
    rec = Recorder(R)
    rec.hook('open', (None, None, None))
    rec.hook('open', (12, 'r', 0))
    rec.hook('os.listdir', (object(),))
    rec.hook('subprocess.Popen', (None, None, None, None))
    rec.hook('os.exec', ())
    rec.hook('os.posix_spawn', (None,))
    rec.hook('os.spawn', (0,))
    rec.hook('open', (_p('ok.txt'), 'r', 0))
    assert rec.files == {'ok.txt'}


def test_윈도_형_문자열_인자도_토큰으로_쪼개_파이썬_자식으로_본다():
    # 윈도의 CPython 은 감사 이벤트 전에 args 를 list2cmdline 문자열로 바꾼다.
    rec = Recorder('/r')
    rec.hook('subprocess.Popen', (None, 'C:\\py\\python.exe -c "print(1)"', None, None))
    assert rec.spawned == {('C:\\py\\python.exe', '-c', 'print(1)')}
    assert rec.opaque is False
    rec.hook('subprocess.Popen', ('C:\\py\\python.exe', 'C:\\py\\python.exe -c pass', None, None))
    assert rec.opaque is False
    rec.hook('subprocess.Popen', (None, 'cat.exe data.txt', None, None))
    assert rec.opaque is True and ('cat.exe', 'data.txt') in rec.spawned


def test_가져오기_기계가_훑은_디렉터리는_적지_않는다(tmp_path):
    got = _trace_run(tmp_path, '''
from pathlib import Path
import pkg.mod
def test_x():
    assert pkg.mod.V == 1
    list(Path('sub').glob('*.txt'))
''', extra_files={'pkg/__init__.py': '', 'pkg/mod.py': 'V = 1\n'})
    assert 'pkg/mod.py' in got['files']
    assert 'pkg' not in got['dirs']
    assert 'sub' in got['dirs']


def test_추적_변수는_있어도_site_경로가_없으면_자식은_opaque(tmp_path):
    got = _trace_run(tmp_path, '''
import os, subprocess, sys
def test_x():
    env = dict(os.environ); env['PYTHONPATH'] = ''
    subprocess.run([sys.executable, '-c', 'pass'], env=env, check=True)
''')
    assert got['opaque'] is True


def test_값을_받는_플래그_뒤의_I_도_본다():
    for argv in (['python', '-W', 'ignore', '-I', '-c', 'pass'], ['python', '-Wignore', '-I', '-c', 'pass'],
                 ['python', '-X', 'utf8', '-c', 'pass']):
        rec = Recorder('/r')
        rec.hook('subprocess.Popen', (argv[0], argv, None, None))
        assert rec.opaque is ('-I' in argv), argv


def test_종료_중_다른_스레드가_기록을_바꿔도_JSON_을_쓴다(tmp_path):
    import threading
    rec = Recorder('/r')
    stop = threading.Event()

    def churn():
        i = 0
        while not stop.is_set():
            rec.hook('open', (f'/r/f{i}.txt', 'r', 0))
            i += 1
    t = threading.Thread(target=churn)
    t.start()
    try:
        for _ in range(20):
            rec.finish(str(tmp_path))
            rec._done = False   # 다음 반복에서도 훅이 돌게(시험용)
    finally:
        stop.set()
        t.join()
    assert list(tmp_path.glob('*.json'))


def test_file_URI_인자는_경로로_풀어_적는다(tmp_path):
    # Chrome 에는 `Path.as_uri()` 를 넘긴다(html2pdf·figure_export) — 쿼리가 붙거나 한글·공백이 % 로 와도 같은 파일이다.
    page = tmp_path / '복습 노트' / 'a.html'
    page.parent.mkdir()
    page.write_text('x', encoding='utf-8')
    rec = Recorder(str(tmp_path))
    rec.hook('subprocess.Popen', ('chrome', ['chrome', '--headless', f'{page.as_uri()}?fig=1'], None, None))
    assert rec.files == {'복습 노트/a.html'} and rec.opaque is True


def test_os_spawn_으로_추적_변수_없이_띄운_자식은_opaque(tmp_path):
    # POSIX 의 os.spawnve 는 fork 한 자식이 exec 한다 — 그 자식이 exec 직전에 남긴 기록에 opaque 가 실린다.
    got = _trace_run(tmp_path, '''
import os, sys
def test_x():
    assert os.spawnve(os.P_WAIT, sys.executable, [sys.executable, '-c', 'pass'], {}) == 0
''')
    assert got['opaque'] is True


def test_os_spawn_으로_추적_변수를_넘긴_파이썬_자식은_opaque_아님(tmp_path):
    got = _trace_run(tmp_path, '''
import os, sys
def test_x():
    code = "open('child.txt').read()"
    assert os.spawnve(os.P_WAIT, sys.executable, [sys.executable, '-c', code], dict(os.environ)) == 0
''')
    assert got['opaque'] is False and 'child.txt' in got['files']
    assert got['count'] >= 2   # 실제 네이티브 자식도 sitecustomize로 기록을 남겼다.


@pytest.mark.skipif(not hasattr(os, 'posix_spawn'), reason='os.posix_spawn 이 없는 플랫폼')
def test_os_posix_spawn_으로_추적_변수_없이_띄운_자식은_opaque(tmp_path):
    got = _trace_run(tmp_path, '''
import os, sys
def test_x():
    pid = os.posix_spawn(sys.executable, [sys.executable, '-c', 'pass'], {})
    assert os.waitstatus_to_exitcode(os.waitpid(pid, 0)[1]) == 0
''')
    assert got['opaque'] is True


def test_subprocess_가_속으로_쓰는_posix_spawn_은_다시_판정하지_않는다(tmp_path):
    # close_fds=False 면 subprocess 가 os.posix_spawn 을 쓴다(macOS) — 추적이 이어지는 자식이 opaque 로 바뀌면 안 된다.
    got = _trace_run(tmp_path, '''
import os, subprocess, sys
def test_x():
    subprocess.run([sys.executable, '-c', "open('child.txt').read()"], close_fds=False, check=True)
''')
    assert got['opaque'] is False and 'child.txt' in got['files']


def test_Popen_이_다룬_자식의_posix_spawn_은_한_번만_판정한다():
    # subprocess 의 속 os.posix_spawn 은 Popen 과 argv 가 같다 — 그 env 가 달라 보여도 다시 판정하지 않는다.
    argv = ['python', '-c', 'pass']
    rec = Recorder(R)
    rec.hook('subprocess.Popen', ('python', argv, None, None))
    rec.hook('os.posix_spawn', ('/usr/bin/python', argv, {}))
    assert rec.opaque is False
    rec.hook('os.posix_spawn', ('/usr/bin/python', argv, {}))   # 짝이 없는 두 번째는 따로 띄운 자식이다
    assert rec.opaque is True
