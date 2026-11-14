"""Build the 자구알 concept-check template from a staged 논회실 pack."""
from html import escape
import re

import _paths
import interaction
import render
from content import ContentError, load_data, quiz_name
from scripts.lab.review_pack.manifest import VENDOR_URL

SLOT = re.compile(r"\{\{([A-Z_]+)\}\}")


def load_source(src):
    return load_data(src)


def render_page(src):
    source = load_source(src)
    pack = source["pack"]
    objectives = {o["id"]: o for o in source["objectives"]}
    items = source["items"]
    cards = "".join(render.card_html(item, objectives[item["objective"]], n, pack.note.name)
                    for n, item in enumerate(items, 1))
    title = escape(f"실험 {pack.experiment:02d} 확인문제 — {pack.manifest['title'].split(' — ')[0]}")
    template = _paths.read_asset("review-template.html")
    values = dict(
        ASSET_ROOT=VENDOR_URL,
        PAGE_TITLE=title,
        DESCRIPTION=title,
        TITLE=title,
        TOC='<a href="#check">확인</a>',
        NOTE_HREF=escape(pack.note.name),
        INTRO=f"이번 실험에서 새로 배운 개념을 {len(items)}문항으로 확인해요.",
        PARTS=f'<section id="check"><h2>확인문제</h2>{cards}</section>',
        FOOTER="<p>AI가 실험 교안과 실험설명을 바탕으로 만든 문항이에요.</p>",
        SCRIPTS="",
        RANGE=f"실험{pack.experiment:02d}-확인",
    )
    page = SLOT.sub(lambda m: values[m[1]], template)
    replacements = {
        '<strong class="brand">복습문제</strong>': '<strong class="brand">확인문제</strong>',
        '>정리노트</a>': '>실험설명</a>',
        f'{VENDOR_URL}/katex/contrib/auto-render.min.js': f'{VENDOR_URL}/katex/auto-render.min.js',
    }
    for original, replacement in replacements.items():
        if page.count(original) != 1:
            raise ContentError(f"템플릿의 변환 지점이 하나여야 해요: {original}")
        page = page.replace(original, replacement)
    name = quiz_name(pack.experiment)
    return pack.folder / name, interaction.install(page, name.removesuffix(".html"))


def build(src):
    out, page = render_page(src)
    out.write_bytes(page.encode("utf-8"))
    return out
