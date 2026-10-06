"""Re-render a published pack's workbook HTML/MD from its own payloads (no run folder needed)."""
from pathlib import Path
from .manifest import load_manifest, output_names
from .workbook_checks import check_workbook_pack
from .workbook_md import write_workbook_md
from .workbook_render import read_workbook_payload, render_workbook_html
from .work_table import mark_payload

RETIRED_STEP_PREFIX='원문 대조'  # 해설지에서 없앤 단계. 이미 없으면 아무것도 하지 않는다.

def rerender_workbook(folder):
    """Rewrite both workbook sheets in place. Returns check errors (empty = OK)."""
    folder=Path(folder)
    manifest=load_manifest(folder/'manifest.json')
    names=output_names(manifest['experiment'],review_presentation_version=2)
    for key in ('question','review'):
        path=folder/names[key+'_html']
        data=read_workbook_payload(path)
        mark_payload(data)          # 채울 표는 풀이 칸으로. 이미 달려 있으면 아무것도 하지 않는다
        for p in data['problems']:
            if 'solution' in p:
                p['solution']['steps']=[s for s in p['solution']['steps'] if not s['label'].startswith(RETIRED_STEP_PREFIX)]
        path.write_text(render_workbook_html(data,folder/'assets'),encoding='utf-8')
        write_workbook_md(data,manifest,folder/names[key+'_md'])
    return check_workbook_pack(folder,manifest)
