import json
import tempfile
from pathlib import Path
from tests.test_breadboard_boards import _load


def test_e7_preparation_split_preserves_original_connections():
    mod = _load()
    board = mod.load_board(7)
    entries = next(iter(board.ASSEMBLY_BOARDS.values()))
    assert len(entries) == 12
    expected = json.loads((Path(__file__).parent / 'fixtures/e7_preparation_original.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory() as tmp:
        base = None
        groups = []
        for name, fn in entries:
            bb = fn(str(Path(tmp) / name), baseline=base)
            bb.verify()
            groups.append([{k: step[k if k != 'from' else 'frm'] for k in ('kind', 'from', 'to', 'desc')} for step in bb.steps])
            base = bb.snapshot()
        assert [len(g) for g in groups[1:10]] == [4] * 9
        for idx in range(3):
            assert sum(groups[1 + idx * 3:4 + idx * 3], []) == expected[idx]
        assert groups[10:] == expected[3:]
