"""Compare published explanation documents with their canonical teaching fragments."""
from pathlib import Path
from collections import Counter
from tempfile import TemporaryDirectory
from urllib.parse import unquote,urlsplit
from .manifest import output_names,DATA,resolve_shared_vendor
from .explanation_render import write_explanations
from .html2md import Parser,check_md
from .navigation import check_navigation
from .workbook_render import read_workbook_payload
from .explanation_content import within

def check_explanations(folder: Path, manifest: dict) -> list[str]:
    if manifest.get('problem_explanation_version') not in (1,2):return []
    folder=Path(folder);errors=[]
    names=output_names(manifest['experiment'],review_presentation_version=2,problem_explanation_version=manifest['problem_explanation_version'])
    try:
        from .workbook_checks import check_workbook_pack
        errors.extend(check_workbook_pack(folder,manifest))
        question=read_workbook_payload(folder/names['question_html'])
        with TemporaryDirectory(prefix='explanation-check-') as scratch:
            paths=write_explanations(manifest,question,folder/DATA,Path(scratch),folder/DATA/'assets')
            for key,path in paths.items():
                if (folder/path.relative_to(scratch)).read_bytes()!=path.read_bytes():errors.append(key+': explanation differs from authored content')
        source=folder/names['explanation_html'];parser=Parser();parser.feed(source.read_text(encoding='utf-8'))
        ids=[n.attrs['id'] for n in parser.root.walk() if n.attrs.get('id')]
        errors.extend('duplicate ID: '+ident for ident,count in Counter(ids).items() if count>1)
        errors.extend(check_navigation(parser.root,names['explanation_html']))
        errors.extend(check_md(source,folder/DATA/names['explanation_md']))
        for n in parser.root.walk():
            attr='src' if n.tag in {'img','script'} else 'href' if n.tag in {'a','link'} else None
            value=n.attrs.get(attr,'') if attr else ''
            if not value:continue
            parts=urlsplit(unquote(value))
            if parts.scheme or parts.netloc:errors.append('Remote explanation resource: '+value);continue
            vendor_dest=resolve_shared_vendor(folder,parts.path) if n.tag in {'link','script'} else None
            if vendor_dest is not None:
                if not vendor_dest.is_file():errors.append('Missing explanation resource: '+value)
                continue
            dest=within(folder,parts.path) if parts.path else source
            if not dest.is_file():errors.append('Missing explanation resource: '+value);continue
            if parts.fragment and dest.suffix=='.html':
                if dest.name in (names['question_html'],names['review_html']):
                    ids={p['id'] for p in read_workbook_payload(dest)['problems']}
                else:
                    tree=Parser();tree.feed(dest.read_text(encoding='utf-8'))
                    ids={x.attrs.get('id') for x in tree.root.walk()}
                if parts.fragment not in ids:errors.append('Missing explanation anchor: '+value)
    except (OSError,ValueError,KeyError,TypeError) as exc:errors.append('Explanation inspection: '+str(exc))
    return errors
