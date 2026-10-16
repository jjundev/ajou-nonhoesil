"""Canonical layouts must also survive a future source RUN build."""
from pathlib import Path
import ast
import subprocess
import sys

def test_experiment06_generator_carries_layout_metadata(tmp_path):
    # Exercise the generator's real explanation-writing block without unrelated PDF/figure imports.
    path=Path('docs/learning-pack-source/실험06/build_run.py')
    tree=ast.parse(path.read_text())
    start=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.For) and ast.unparse(n.target)=='(pid, html)' and 'E.items()' in ast.unparse(n.iter))
    end=next(i for i,n in enumerate(tree.body[start+1:],start+1) if isinstance(n,ast.Assign))
    block=ast.Module(body=tree.body[start:end],type_ignores=[])
    run=tmp_path/'run';(run/'problem-explanations').mkdir(parents=True)
    exec(compile(block,str(path),'exec'),dict(RUN=run,E={'sample':'<p>same</p>'},Path=Path,__file__=str(path.resolve())))
    assert (run/'problem-explanations/table-layout.json').read_bytes()==path.with_name('problem-explanations').joinpath('table-layout.json').read_bytes()

def test_experiment06_canonical_fragments_match_generator():
    # A separate process isolates its local `h`, `sections`, `problems` module names.
    result=subprocess.run([sys.executable,'-c',"from pathlib import Path; from explanations import E; root=Path('docs/learning-pack-source/실험06/problem-explanations'); assert all((root/(pid+'.html')).read_text()==value for pid,value in E.items())"],env=__import__('os').environ|{'PYTHONPATH':'docs/learning-pack-source/실험06'},capture_output=True,text=True)
    assert result.returncode==0,result.stderr
