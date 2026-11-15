"""Re-render a pack's workbook from its own payloads (no run folder needed)."""
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from .manifest import load_manifest, output_names, workbook_pdf_names, DATA, VENDOR_DIR
from .workbook_checks import check_workbook_pack
from .workbook_md import write_workbook_md
from .workbook_render import (
    read_workbook_payload, render_workbook_html, workbook_source_path, write_workbook_payload,
)
from .work_table import mark_payload
from .workbook_storage import pack_write_lock, replace_workbook_files

RETIRED_STEP_PREFIX = '원문 대조'


def _update_workbook(folder, manifest):
    names = output_names(manifest['experiment'], review_presentation_version=2)
    updated = []
    for key in ('question', 'review'):
        path = workbook_source_path(folder, manifest, key)
        data = read_workbook_payload(path)
        mark_payload(data)
        for problem in data['problems']:
            if 'solution' in problem:
                solution = problem['solution']
                solution['steps'] = [step for step in solution['steps']
                                     if not step['label'].startswith(RETIRED_STEP_PREFIX)]
        if path.suffix == '.json':
            write_workbook_payload(path, data)
        else:
            path.write_text(render_workbook_html(data, folder / DATA / 'assets'), encoding='utf-8')
        updated.extend((path, write_workbook_md(data, manifest, folder / DATA / names[key + '_md'])))
    return updated


def rerender_workbook(folder):
    """Update both workbook sheets together after their checks pass."""
    folder = Path(folder)
    with pack_write_lock(folder):
        return _rerender_locked(folder)


def _rerender_locked(folder):
    manifest = load_manifest(folder / DATA / 'manifest.json')
    if manifest.get('workbook_delivery') != 'pdf':
        _update_workbook(folder, manifest)
        return check_workbook_pack(folder, manifest)

    from scripts.lab.workbook_pdf import export_pair
    with TemporaryDirectory(prefix='logic-workbook-rerender-') as scratch:
        stage = Path(scratch) / folder.name
        shutil.copytree(folder, stage)
        shutil.copytree(folder.parent / VENDOR_DIR, stage.parent / VENDOR_DIR)
        updated = _update_workbook(stage, manifest)
        errors = check_workbook_pack(stage, manifest)
        if errors:
            return errors
        export_pair(stage, stage)
        updated.extend(stage / name for name in workbook_pdf_names(manifest['experiment']).values())
        replace_workbook_files({folder / p.relative_to(stage): p for p in updated}, folder)
    return []
