"""scripts/lab/merge_report.py

논리회로실험 보고서 본문 PDF와 표지 PDF를 무손실 병합하여 최종 제출용 PDF를 생성한다.
표지가 없거나 날짜가 달라졌으면 make-lab-report-cover 파이프라인으로 자동 생성한다.
산출물은 언더스코어 표준 파일명 (`실험N_<제목>_<종류>.pdf`)으로 저장된다.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import re
import sys

import pypdf

from scripts.lab import config
from scripts.lab.html2pdf import DEFAULT_CHROME, html_to_pdf
from scripts.lab.spec_parser import parse_spec


import unicodedata

def output_filename(experiment_num: int, title: str, kind: str) -> str:
    """언더스코어 표준 파일명을 생성한다 (예: '실험1_Basic_Gates_예비보고서.pdf')."""
    clean_title = re.sub(r"\s+", "_", title.strip())
    clean_title = unicodedata.normalize("NFC", clean_title)
    kind_norm = unicodedata.normalize("NFC", kind)
    return f"실험{experiment_num}_{clean_title}_{kind_norm}.pdf"


def find_body_pdf(exp_dir: Path, kind: str | None = None) -> Path:
    """실험 폴더 또는 output 폴더에서 본문 보고서 PDF를 자동 탐색한다.

    표지, 체크리스트, 결선도/통합본 및 이미 생성된 최종 병합본을 제외한다.
    """
    exp_dir = Path(exp_dir).resolve()
    candidates: list[Path] = []
    kind_norm = unicodedata.normalize("NFC", kind) if kind else None

    # 검색 대상 경로: exp_dir 최상위 및 output/
    search_dirs = [exp_dir]
    if (exp_dir / "output").is_dir():
        search_dirs.append(exp_dir / "output")

    excluded_keywords = ["표지", "체크리스트", "손그림", "결선도", "통합본"]

    for sdir in search_dirs:
        for p in sdir.glob("*.pdf"):
            fname = unicodedata.normalize("NFC", p.name)
            # 제외 키워드 필터링
            if any(kw in fname for kw in excluded_keywords):
                continue
            # 이미 병합된 표준 출력 파일(실험N_*_*.pdf 형태 중 UUID가 없는 것) 건너뛰기
            if re.match(r"^실험\d+_.+_(예비|결과)보고서\.pdf$", fname):
                continue
            # kind 조건 필터링
            if kind_norm and kind_norm not in fname:
                continue
            candidates.append(p)

    if not candidates:
        kind_str = f" ({kind})" if kind else ""
        raise FileNotFoundError(f"본문 PDF{kind_str}를 찾을 수 없습니다: {exp_dir}")

    if len(candidates) > 1:
        # 노션 UUID 형식 (32자리 hex + _)이 붙은 파일이 유일하게 존재하면 우선 선택
        uuid_candidates = [
            c for c in candidates if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_", c.name)
        ]
        if len(uuid_candidates) == 1:
            return uuid_candidates[0]

        cand_names = "\n".join(f"- {c.name}" for c in candidates)
        raise RuntimeError(f"복수의 본문 PDF 후보가 발견되었습니다. 파일을 직접 지정해주세요:\n{cand_names}")

    return candidates[0]


def _find_cover_template(root: Path) -> Path:
    """표지 HTML 템플릿 경로를 찾는다."""
    candidates = [
        root / ".agents/skills/make-lab-report-cover/template.html",
        root / ".claude/skills/make-lab-report-cover/template.html",
    ]
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError("표지 템플릿 template.html을 찾을 수 없습니다.")


def generate_cover_pdf(
    exp_dir: Path,
    spec,
    kind: str,
    submit_date: str | None = None,
    chrome: str | None = None,
) -> Path:
    """make-lab-report-cover 템플릿을 사용하여 A4 1장 표지 PDF를 생성한다."""
    exp_dir = Path(exp_dir).resolve()
    root = config.find_project_root(exp_dir)
    info = config.load_course_info(root)

    # 1b 조 편성 미확정 게이트
    missing = config.missing_identity(info)
    if missing:
        raise RuntimeError(f"과목 정보에 미확정 항목이 있습니다: {missing}")

    title = config.document_title(spec.experiment, spec.title, kind)
    date_str = submit_date or datetime.now().strftime(info.get("date_format", "%Y.%m.%d"))

    template_path = _find_cover_template(root)
    html_content = template_path.read_text(encoding="utf-8")

    replacements = {
        "{{TITLE}}": title,
        "{{COURSE}}": info.get("course", "논리회로실험"),
        "{{CLASS_SECTION}}": info.get("class_section", ""),
        "{{DEPARTMENT}}": info.get("department", "전자공학과"),
        "{{SUBMIT_DATE}}": date_str,
        "{{PROFESSOR}}": info.get("professor", ""),
        "{{STUDENT_IDS}}": str(info.get("student_ids", "")),
        "{{STUDENT_NAMES}}": str(info.get("student_names", "")),
    }
    for placeholder, val in replacements.items():
        html_content = html_content.replace(placeholder, val)

    out_dir = exp_dir / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"{title} 표지.html"
    pdf_path = out_dir / f"{title} 표지.pdf"

    html_path.write_text(html_content, encoding="utf-8")
    chrome_bin = chrome or info.get("chrome") or DEFAULT_CHROME
    html_to_pdf(html_path, pdf_path, chrome=chrome_bin)

    # 쪽수 및 A4 검증
    reader = pypdf.PdfReader(str(pdf_path))
    if len(reader.pages) != 1:
        raise RuntimeError(f"생성된 표지가 1쪽이 아닙니다: {len(reader.pages)}쪽")

    return pdf_path


def ensure_cover_pdf(
    exp_dir: Path,
    spec,
    kind: str,
    submit_date: str | None = None,
    chrome: str | None = None,
) -> Path:
    """표지 PDF의 존재 여부를 확인하고, 없으면 생성하여 반환한다."""
    exp_dir = Path(exp_dir).resolve()
    title = config.document_title(spec.experiment, spec.title, kind)
    cover_pdf = exp_dir / "output" / f"{title} 표지.pdf"

    if cover_pdf.is_file():
        if submit_date:
            reader = pypdf.PdfReader(str(cover_pdf))
            text = reader.pages[0].extract_text() or ""
            if submit_date not in text:
                # 제출일이 달라졌으면 재생성
                return generate_cover_pdf(exp_dir, spec, kind, submit_date=submit_date, chrome=chrome)
        return cover_pdf

    return generate_cover_pdf(exp_dir, spec, kind, submit_date=submit_date, chrome=chrome)


def merge_report_pdf(cover_path: Path, body_path: Path, output_path: Path) -> Path:
    """표지(1쪽)와 본문(N쪽)을 무손실 병합한다."""
    cover_path = Path(cover_path).resolve()
    body_path = Path(body_path).resolve()
    output_path = Path(output_path).resolve()

    if not cover_path.is_file():
        raise FileNotFoundError(f"표지 PDF가 없습니다: {cover_path}")
    if not body_path.is_file():
        raise FileNotFoundError(f"본문 PDF가 없습니다: {body_path}")

    cover_reader = pypdf.PdfReader(str(cover_path))
    body_reader = pypdf.PdfReader(str(body_path))
    expected_pages = len(cover_reader.pages) + len(body_reader.pages)

    writer = pypdf.PdfWriter()
    writer.append(str(cover_path))
    writer.append(str(body_path))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)

    verify_merged_pdf(output_path, expected_pages=expected_pages)
    return output_path


def verify_merged_pdf(pdf_path: Path, expected_pages: int | None = None) -> dict:
    """병합된 최종 PDF의 쪽수 및 규격을 실측 검증한다."""
    pdf_path = Path(pdf_path).resolve()
    reader = pypdf.PdfReader(str(pdf_path))
    total_pages = len(reader.pages)

    if expected_pages is not None and total_pages != expected_pages:
        raise ValueError(f"쪽수가 일치하지 않습니다: 기대 {expected_pages}쪽, 실제 {total_pages}쪽")

    # 1쪽 A4 치수 확인
    p1 = reader.pages[0]
    w_mm = float(p1.mediabox.width) / 72 * 25.4
    h_mm = float(p1.mediabox.height) / 72 * 25.4
    if not (205.0 <= w_mm <= 215.0 and 290.0 <= h_mm <= 302.0):
        raise ValueError(f"1쪽 표지가 A4 규격(210x297mm)을 벗어납니다: {w_mm:.1f} x {h_mm:.1f} mm")

    return {
        "pages": total_pages,
        "valid": True,
        "page1_size_mm": (round(w_mm, 1), round(h_mm, 1)),
    }


def merge_lab_report(
    exp_target: int | str | Path,
    kind: str = "예비보고서",
    body_path: Path | str | None = None,
    submit_date: str | None = None,
    chrome: str | None = None,
) -> Path:
    """실험 번호 또는 디렉토리를 받아 표지를 보장하고 본문과 병합한다."""
    root = config.find_project_root(Path("."))
    if isinstance(exp_target, int):
        exp_dir = root / config.experiment_dir(exp_target)
    elif isinstance(exp_target, str) and exp_target.isdigit():
        exp_dir = root / config.experiment_dir(int(exp_target))
    elif isinstance(exp_target, (str, Path)):
        exp_dir = Path(exp_target).resolve()
    else:
        raise ValueError(f"유효하지 않은 실험 대상입니다: {exp_target}")

    spec_path = exp_dir / "체크리스트/명세.md"
    if not spec_path.is_file():
        raise FileNotFoundError(f"명세 파일이 없습니다: {spec_path}")

    spec = parse_spec(spec_path)
    body_pdf = Path(body_path).resolve() if body_path else find_body_pdf(exp_dir, kind=kind)
    cover_pdf = ensure_cover_pdf(exp_dir, spec, kind, submit_date=submit_date, chrome=chrome)

    fname = output_filename(spec.experiment, spec.title, kind)
    out_path = exp_dir / fname

    return merge_report_pdf(cover_pdf, body_pdf, out_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="보고서 본문 PDF와 표지 PDF를 병합하여 최종본을 생성합니다.")
    parser.add_argument("--exp", type=int, help="실험 번호 (예: 1)")
    parser.add_argument("--dir", type=str, help="실험 폴더 경로 (예: 보고서/실험01)")
    parser.add_argument("--body", type=str, help="본문 PDF 파일 경로 (미지정 시 자동 탐색)")
    parser.add_argument("--kind", choices=["예비보고서", "결과보고서"], default="예비보고서", help="보고서 종류 (기본값: 예비보고서)")
    parser.add_argument("--date", type=str, help="제출일 (YYYY.MM.DD, 미지정 시 오늘 날짜)")
    parser.add_argument("--chrome", type=str, help="Chrome 바이너리 경로")
    args = parser.parse_args(argv)

    target = args.exp if args.exp is not None else args.dir
    if target is None:
        parser.error("--exp 또는 --dir 중 하나를 지정해야 합니다.")

    try:
        out = merge_lab_report(
            target,
            kind=args.kind,
            body_path=args.body,
            submit_date=args.date,
            chrome=args.chrome,
        )
        print(f"성공적으로 병합되었습니다: {out}")
        return 0
    except Exception as e:
        print(f"오류 발생: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
