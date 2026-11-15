"""복습노트 워크북 원고를 태블릿용 PDF 로 낸다 (A4 가로, 문항당 한 쪽).

    python -m scripts.lab.workbook_pdf 실험05 [--kind 기출문제|기출풀이|all] [--out DIR]

기본 출력은 `복습노트/<실험NN>/`이다. 인쇄용 HTML은 작업 폴더에서만 만든다. 변환 전 DOM 으로 쪽 맞춤이
끝났는지(`data-ready`)와 넘친 쪽이 없는지(`data-overflow`)를 확인하고, 변환 뒤에는
쪽 수·용지 크기를 payload 와 대조한다. 하나라도 어긋나면 실패다.

DOM 검사는 인쇄와 다른 Chrome 에서 돈다. 인쇄한 Chrome 이 맞춤까지 마쳤는지는 PDF 를 읽어서만
알 수 있으므로 변환 뒤에 내용도 본다 — 글자에 남은 원문 LaTeX(`$…\\`, KaTeX 가 안 돈 흔적)와
'답' 상자 상단을 넘어 내려간 그림(쪽 맞춤 전 상태가 찍힌 흔적). 2026-10-09 실험02 해설지가
둘 다였는데 쪽 수·크기 검사는 통과했다.
문제지는 문항당 정확히 한 쪽, 해설지는 풀이가 길면 두 쪽까지 이어지므로 문항 수 이상이면 된다.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf
from pypdf import PdfReader

from scripts.lab.html2pdf import DEFAULT_CHROME, PdfError, html_to_pdf, resolve_chrome
from scripts.lab.review_pack.manifest import DATA, VENDOR_DIR, load_manifest, workbook_pdf_names
from scripts.lab.review_pack.workbook_storage import pack_write_lock, replace_workbook_files
from scripts.lab.review_pack.workbook_render import (
    read_workbook_payload, render_workbook_html, workbook_source_path,
)

ROOT = Path(__file__).resolve().parents[2]
NOTES = ROOT / "복습노트"
KINDS = ("기출문제", "기출풀이")
BUDGET_MS = 15000
A4_LANDSCAPE_MM = (297, 210)
PT_PER_MM = 72 / 25.4


def dom_state(html_path, chrome=DEFAULT_CHROME, timeout=120):
    """스크립트가 끝난 뒤의 (data-ready, data-overflow). 확인할 수 없으면 (None, None).

    playwright 가 있으면 실제 Chrome 으로 기다린다. 없으면 `--dump-dom` 으로 대신한다.
    템플릿이 그림 decode() 를 기다리던 동안은 헤드리스에서 ready 를 못 찍었다(LOCAL_PATCHES 가 고침).
    """
    uri = Path(html_path).resolve().as_uri()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sync_playwright = None
    if sync_playwright:
        with sync_playwright() as driver:
            browser = driver.chromium.launch(channel="chrome")
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                page.goto(uri)
                page.wait_for_function("document.documentElement.dataset.ready", timeout=timeout * 1000)
                return (page.locator("html").get_attribute("data-ready"),
                        page.locator("body").get_attribute("data-overflow"))
            finally:
                browser.close()
    proc = subprocess.run(
        [resolve_chrome(chrome), "--headless=new", "--disable-gpu",
         f"--virtual-time-budget={BUDGET_MS}", "--dump-dom", uri],
        capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise PdfError(f"DOM 을 뜨지 못했습니다 (종료 코드 {proc.returncode}). {proc.stderr.strip()}")
    ready = re.search(r'<html[^>]*\bdata-ready="([^"]*)"', proc.stdout)
    overflow = re.search(r'<body[^>]*\bdata-overflow="([^"]*)"', proc.stdout)
    return (ready.group(1) if ready else None, overflow.group(1) if overflow else None)


def check_pdf(pdf_path, expected_pages, exact=True):
    """쪽 수와 용지 크기 문제 목록. 비어 있어야 성공이다."""
    reader = PdfReader(str(pdf_path))
    problems = []
    if len(reader.pages) != expected_pages if exact else len(reader.pages) < expected_pages:
        problems.append(f"쪽 수 {len(reader.pages)} / 문항 수 {expected_pages}")
    for i, page in enumerate(reader.pages, 1):
        w, h = float(page.mediabox.width) / PT_PER_MM, float(page.mediabox.height) / PT_PER_MM
        if abs(w - A4_LANDSCAPE_MM[0]) > 1 or abs(h - A4_LANDSCAPE_MM[1]) > 1:
            problems.append(f"{i}쪽 크기 {w:.0f}×{h:.0f}mm")
            break
    return problems


# `$` 와 `$` 사이에 명령(\\cmd)이나 첨자(_ ^)가 있으면 렌더되지 않은 식이다.
# 렌더된 KaTeX 도 MathML 주석으로 원문을 남기지만 구분자 `$` 는 없다.
RAW_LATEX = re.compile(r"\$[^$]*?(?:\\[A-Za-z]|[_^])[^$]*?\$")
ANSWER_LABEL = "답"
BACKGROUND_FRAC = 0.9     # 쪽 폭의 90% 이상인 그림은 점 격자 배경이다


def check_pdf_content(pdf_path):
    """인쇄 결과의 내용 문제 목록. 비어 있어야 성공이다."""
    problems = []
    with pymupdf.open(pdf_path) as doc:
        for i, page in enumerate(doc, 1):
            m = RAW_LATEX.search(page.get_text().replace("\n", " "))
            if m:
                problems.append(f"{i}쪽 원문 LaTeX {m.group(0)[:40]!r}")
            spans = (s for b in page.get_text("dict")["blocks"] if b["type"] == 0
                     for line in b["lines"] for s in line["spans"])
            tops = [s["bbox"][1] for s in spans if s["text"].strip() == ANSWER_LABEL]
            figs = [im["bbox"] for im in page.get_image_info()
                    if im["bbox"][2] - im["bbox"][0] < BACKGROUND_FRAC * page.rect.width]
            for top in tops:
                if any(f[1] < top < f[3] for f in figs):
                    problems.append(f"{i}쪽 그림 하단이 '답' 상자 상단보다 아래")
                    break
    return problems


def _temporary_html(note_dir, manifest, key, scratch):
    """Keep the legacy relative resource paths intact in the print workspace."""
    contents = scratch / 'pack'
    if not contents.exists():
        contents.mkdir()
        shutil.copytree(note_dir / DATA, contents / DATA)
        shutil.copytree(note_dir.parent / VENDOR_DIR, scratch / VENDOR_DIR)
    source = workbook_source_path(contents, manifest, key)
    pdf_name = workbook_pdf_names(manifest['experiment'])[key]
    path = contents / Path(pdf_name).with_suffix('.html')
    path.write_text(render_workbook_html(read_workbook_payload(source), contents / DATA / 'assets'),
                    encoding='utf-8')
    return path


def _render_pdf(src, out, kind):
    ready, overflow = dom_state(src)
    if ready == "error" or overflow or (ready is not None and ready != "true"):
        raise PdfError(f"{src.name}: 쪽 맞춤 미완료 (data-ready={ready!r}, 넘친 쪽={overflow!r})")
    if ready is None:
        print(f"주의: {src.name} 쪽 맞춤 완료를 확인하지 못했습니다(헤드리스 DOM). 인쇄 결과의 쪽 수·크기·내용만 검사합니다.")
    total = read_workbook_payload(src)["meta"]["total"]
    html_to_pdf(src, out, virtual_time_budget=BUDGET_MS)   # 쪽 맞춤 스크립트가 끝난 뒤 인쇄
    problems = check_pdf(out, total, exact=(kind == "기출문제")) + check_pdf_content(out)
    if problems:
        raise PdfError(f"{out.name}: " + "; ".join(problems))
    return out, total


def _export(note_dir, kinds, out_dir):
    note_dir, out_dir = Path(note_dir), Path(out_dir)
    with pack_write_lock(note_dir):
        return _export_locked(note_dir, kinds, out_dir)


def _export_locked(note_dir, kinds, out_dir):
    manifest_path = note_dir / DATA / 'manifest.json'
    manifest = load_manifest(manifest_path) if manifest_path.is_file() else {}
    pdf_mode = manifest.get('workbook_delivery') == 'pdf'
    outputs = {}
    files = {}
    with TemporaryDirectory(prefix='logic-workbook-print-') as scratch:
        scratch = Path(scratch)
        for kind in kinds:
            if pdf_mode:
                key = {'기출문제': 'question', '기출풀이': 'review'}[kind]
                src = _temporary_html(note_dir, manifest, key, scratch)
            else:
                src = note_dir / f'{note_dir.name}_{kind}.html'
                if not src.is_file():
                    raise PdfError(f'없는 파일: {src}')
            name = src.with_suffix('.pdf').name
            pdf, count = _render_pdf(src, scratch / name, kind)
            outputs[kind] = (out_dir / name, count)
            files[out_dir / name] = pdf
        if out_dir.resolve() == note_dir.resolve():
            replace_workbook_files(files, out_dir)
        else:
            with pack_write_lock(out_dir):
                replace_workbook_files(files, out_dir)
    return outputs


def export(note_dir, kind, out_dir):
    return _export(note_dir, (kind,), out_dir)[kind]


def export_pair(note_dir, out_dir):
    return _export(note_dir, KINDS, out_dir)


def main(argv=None):
    ap = argparse.ArgumentParser()
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument("exp", nargs="?", help="실험05 처럼")
    source.add_argument("--folder", type=Path, help="저작 중인 stage나 실험 폴더")
    ap.add_argument("--kind", default="all", choices=KINDS + ("all",))
    ap.add_argument("--out", type=Path, help="PDF 출력을 저장할 폴더")
    a = ap.parse_args(argv)
    note_dir = a.folder or NOTES / a.exp
    if not note_dir.is_dir():
        sys.exit(f"없는 폴더: {note_dir}")
    try:
        outputs = (export_pair(note_dir, a.out or note_dir) if a.kind == "all"
                   else {a.kind: export(note_dir, a.kind, a.out or note_dir)})
        for out, total in outputs.values():
            print(f"{out} ({out.stat().st_size // 1024} KB, {total}문항)")
    except (PdfError, OSError, ValueError) as exc:
        print(f"실패: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
