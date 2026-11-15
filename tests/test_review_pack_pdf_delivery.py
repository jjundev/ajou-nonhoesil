import json
from pathlib import Path

import pytest

from scripts.lab.review_pack.checks import check_pack
from scripts.lab.review_pack.manifest import DATA, load_manifest, output_names
from scripts.lab.review_pack.workbook_render import read_workbook_payload


def test_published_workbooks_own_json_and_pdf_without_html():
    for experiment in range(1, 10):
        folder = Path('복습노트') / f'실험{experiment:02d}'
        manifest = load_manifest(folder / DATA / 'manifest.json')
        names = output_names(experiment, review_presentation_version=2)
        assert manifest['workbook_delivery'] == 'pdf'
        for key, mode in [('question', 'problems'), ('review', 'answers')]:
            assert not (folder / names[key + '_html']).exists()
            relative = f'{DATA}/workbook-{mode}.json'
            assert relative in manifest['generated_files']
            data = read_workbook_payload(folder / relative)
            assert [item['id'] for item in data['problems']] == [
                item['id'] for item in manifest['problems'] if item['status'] == 'included'
            ]
            pdf = Path(names[key + '_html']).with_suffix('.pdf').name
            assert pdf in manifest['generated_files']
            assert (folder / pdf).is_file()
        assert check_pack(folder) == []


@pytest.mark.parametrize('experiment', [4, 10])
def test_build_publication_and_explanation_output_are_pdf_only(tmp_path, monkeypatch, experiment):
    import shutil
    from scripts.lab import workbook_pdf
    from scripts.lab.review_pack.__main__ import main
    from scripts.lab.review_pack.explanation_stage import prepare_explanation_stage
    from scripts.lab.review_pack.publish import publish
    from scripts.lab.review_pack.sources import file_sha256
    from tests._explanation_recall_fixture import setup_v2

    manifest, run, _ = setup_v2(tmp_path)
    manifest['experiment'] = experiment
    assets = tmp_path / '.claude/skills/logic-lab-review-pack/assets'
    shutil.copytree(Path('.claude/skills/logic-lab-review-pack/assets'), assets)
    for source in manifest['sources']:
        path = tmp_path / source['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'source')
        source['sha256'] = file_sha256(path)
    manifest['checks'].update(source_visual='pass', content='self_review', browser='pass')
    manifest['explanation_checks'].update(source_visual='pass', content='self_review', browser='pass')
    (run / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False))

    printed = []
    def fake_print(source, output, kind):
        assert source.suffix == '.html'
        assert not source.is_relative_to(tmp_path)
        data = read_workbook_payload(source)
        printed.append(data['meta']['mode'])
        output.write_bytes(kind.encode())
        return output, data['meta']['total']

    monkeypatch.setattr(workbook_pdf, '_render_pdf', fake_print)
    stage = tmp_path / 'stage'
    assert main(['build', '--root', str(tmp_path), '--run', str(run), '--stage', str(stage)]) == 0
    assert printed == ['problems', 'answers']
    destination = tmp_path / '복습노트' / f'실험{experiment:02d}'
    publish(stage, destination, tmp_path)
    assert not list(destination.glob('*_기출*.html'))
    assert len(list(destination.glob('*_기출*.pdf'))) == 2

    explain = tmp_path / 'explain-stage'
    prepare_explanation_stage(destination, destination / DATA / 'problem-explanations', explain)
    assert not list(explain.glob('*_기출*.html'))
    for path in destination.glob('*_기출*.pdf'):
        assert (explain / path.name).read_bytes() == path.read_bytes()
    for folder in (destination, explain):
        files = load_manifest(folder / DATA / 'manifest.json')['generated_files']
        panel_files = {f'{DATA}/assets/explanation-panel.{ext}' for ext in ('css', 'js')}
        assert (panel_files & set(files)) == (panel_files if experiment == 10 else set())
        if experiment == 10:
            html = (folder / '실험10_문제설명.html').read_text(encoding='utf-8')
            assert 'data-question-label="문제지 PDF"' in html


def test_failed_answer_keeps_existing_pdf_pair(tmp_path, monkeypatch):
    import pytest
    from scripts.lab import workbook_pdf

    folder = Path('복습노트/실험07')
    output = tmp_path / 'output'
    output.mkdir()
    before = {pdf.name: pdf.name.encode() for pdf in folder.glob('*_기출*.pdf')}
    assert len(before) == 2
    for name, content in before.items():
        (output / name).write_bytes(content)

    def fail_answer(source, destination, kind):
        if kind == '기출풀이':
            raise workbook_pdf.PdfError('answer print failed')
        destination.write_bytes(b'new question')
        return destination, 22

    monkeypatch.setattr(workbook_pdf, '_render_pdf', fail_answer)
    with pytest.raises(workbook_pdf.PdfError, match='answer print failed'):
        workbook_pdf.export_pair(folder, output)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before


def test_export_and_pack_publication_share_a_lock(tmp_path):
    import pytest
    from scripts.lab import workbook_pdf
    from scripts.lab.review_pack.workbook_storage import pack_write_lock

    with pack_write_lock(tmp_path), pytest.raises(ValueError, match='갱신 중'):
        workbook_pdf.export_pair(tmp_path, tmp_path)
