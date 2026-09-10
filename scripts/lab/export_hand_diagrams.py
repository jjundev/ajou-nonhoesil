"""손그림 결선도 PDF 의 각 쪽을 개별 300 DPI PNG 로 추출하여 아카이빙한다.

`보고서/실험NN/결선도/손그림/` 에 기존 정본 결선도와 일대일 대응되는 국문 파일명으로
저장하여 보고서 마크다운 및 노션 동기화에서 손그림을 바로 임베드할 수 있게 한다.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Optional

from . import config
from . import hand_grid
from . import netlist_parser

# 브레드보드 템플릿 영역 기준 크롭 좌표 (가로: 행 화살표 포함, 세로: 상단 검은선/공백 및 하단 캡션 제외)
BOARD_CROP_TEMPLATE_X = (20, 565)
BOARD_CROP_TEMPLATE_Y = (30, 740)


def find_default_pdf(experiment: int) -> Path:
    """해당 실험의 가장 최신 손그림 PDF 를 찾는다.

    1. 최신 검토 라운드의 `hand.pdf`
    2. `output/실험NN_손그림결선도_최종통합본.pdf`
    """
    exp_dir = Path(config.experiment_dir(experiment))
    review_dir = exp_dir / "output" / "손그림검토"

    if review_dir.is_dir():
        rounds = []
        for d in review_dir.iterdir():
            if d.is_dir() and d.name.startswith("round"):
                try:
                    rnd_num = int(d.name[5:])
                    rounds.append((rnd_num, d))
                except ValueError:
                    continue
        rounds.sort(key=lambda x: x[0], reverse=True)
        for _, rnd_dir in rounds:
            pdf = rnd_dir / "hand.pdf"
            if pdf.is_file():
                return pdf

    unified_name = f"{config.experiment_folder_name(experiment)}_손그림결선도_최종통합본.pdf"
    unified_pdf = exp_dir / "output" / unified_name
    if unified_pdf.is_file():
        return unified_pdf

    raise FileNotFoundError(
        f"실험{experiment}의 손그림 PDF 를 찾을 수 없습니다. "
        f"PDF 경로를 직접 지정해 주세요: ({review_dir} 또는 {unified_pdf})"
    )


def resolve_circuit_filenames(
    experiment: int,
    page_count: int,
    round_dir: Optional[Path] = None,
) -> List[str]:
    """netlist.md 및 검토 전사를 참조하여 쪽별 아카이빙 파일명을 결정한다.

    파일명 규칙: {실험폴더명}_{소단원}_손그림_{회로명}.png
    (예: 실험01_1-1_손그림_3입력_AND.png, 실험01_3_손그림_복합논리회로.png)
    """
    try:
        folder_name = config.experiment_folder_name(experiment)
        netlist_path = Path(config.experiment_dir(experiment)) / "결선도" / "netlist.md"
    except ValueError:
        folder_name = f"실험{experiment:02d}"
        netlist_path = Path(f"보고서/{folder_name}/결선도/netlist.md")

    circuit_sections = []
    if netlist_path.is_file():
        try:
            nl = netlist_parser.parse_netlist(str(netlist_path))
            circuit_sections = [s for s in nl.sections if s.kind == "circuit"]
        except Exception:
            circuit_sections = []

    if not circuit_sections:
        return [f"{folder_name}_손그림_p{i+1}.png" for i in range(page_count)]

    # 회로 섹션별 메타데이터 추출
    circuit_info = []
    for idx, s in enumerate(circuit_sections):
        # 소단원 번호 추출 (E1.P1-1 -> 1-1, E1.P3 -> 3)
        m = re.search(r"(?:E\d+\.)?P?([\d-]+)", s.item or "")
        sub_item = m.group(1) if m else str(idx + 1)

        # 회로명 추출
        if s.diagram:
            diag_stem = Path(s.diagram).stem
            diag_clean = re.sub(r"_\d+단계.*$", "", diag_stem)
            if "결선도_" in diag_clean:
                name_part = diag_clean.split("결선도_", 1)[1]
            elif "결선도" in diag_clean:
                name_part = diag_clean.split("결선도", 1)[1].lstrip("_")
            else:
                name_part = diag_clean
        else:
            t = re.sub(r"^[A-Za-z0-9]+[ ·]*실험\s*[\d-]+[)]?\s*", "", s.title)
            name_part = re.sub(r"[^\w가-힣-]+", "_", t).strip("_")

        fname = f"{folder_name}_{sub_item}_손그림_{name_part}.png"
        circuit_info.append({
            "section": s,
            "sub_item": sub_item,
            "name_part": name_part,
            "filename": fname,
        })

    # 전사 파일이 있으면 페이지별 회로 매칭 시도 (페이지 셔플 대응)
    filenames: List[str] = []
    used_indices = set()

    trans_dir = round_dir / "전사" if round_dir else None
    has_transcripts = trans_dir and trans_dir.is_dir()

    for i in range(page_count):
        matched_filename = None
        if has_transcripts:
            tf = trans_dir / f"p{i+1}.json"
            if tf.is_file():
                try:
                    with open(tf, "r", encoding="utf-8") as f:
                        tdata = json.load(f)
                    ttitle = tdata.get("title", "")
                    tcircuit = tdata.get("circuit", "").lower()
                    for c_idx, ci in enumerate(circuit_info):
                        if c_idx in used_indices:
                            continue
                        if ci["sub_item"] in ttitle:
                            matched_filename = ci["filename"]
                            used_indices.add(c_idx)
                            break
                        if ci["name_part"] in ttitle or (ttitle and ttitle in ci["name_part"]):
                            matched_filename = ci["filename"]
                            used_indices.add(c_idx)
                            break
                        if "comb" in tcircuit and "복합" in ci["name_part"]:
                            matched_filename = ci["filename"]
                            used_indices.add(c_idx)
                            break
                except Exception:
                    pass

        if matched_filename:
            filenames.append(matched_filename)
        elif i < len(circuit_info):
            filenames.append(circuit_info[i]["filename"])
        else:
            filenames.append(f"{folder_name}_손그림_p{i+1}.png")

    return filenames


def export_hand_diagrams(
    experiment: int,
    pdf_path: Optional[str | Path] = None,
    out_dir: Optional[str | Path] = None,
    dpi: int = 300,
    crop_board: bool = True,
) -> List[Path]:
    """손그림 PDF 의 쪽들을 개별 고해상도 PNG 파일로 내보낸다.

    Args:
        experiment: 실험 번호 (예: 1)
        pdf_path: 대상 PDF 파일 경로 (None 이면 최신 파일 자동 탐색)
        out_dir: 출력 디렉토리 (None 이면 `보고서/실험NN/결선도/손그림`)
        dpi: 렌더링 해상도 (기본 300 DPI)
        crop_board: 브레드보드 및 상단 전원 잭 부분만 타이트하게 크롭할지 여부 (기본 True)

    Returns:
        생성된 PNG 파일의 Path 목록
    """
    round_dir: Optional[Path] = None
    if pdf_path is None:
        src_pdf = find_default_pdf(experiment)
        if src_pdf.parent.name.startswith("round"):
            round_dir = src_pdf.parent
    else:
        src_pdf = Path(pdf_path)
        if not src_pdf.is_file():
            raise FileNotFoundError(f"지정한 PDF 파일이 없습니다: {src_pdf}")
        if src_pdf.parent.name.startswith("round"):
            round_dir = src_pdf.parent

    if out_dir is None:
        target_dir = Path(config.experiment_dir(experiment)) / "결선도" / "손그림"
    else:
        target_dir = Path(out_dir)

    target_dir.mkdir(parents=True, exist_ok=True)

    import fitz

    doc = fitz.open(str(src_pdf))
    page_count = len(doc)
    doc.close()

    filenames = resolve_circuit_filenames(experiment, page_count, round_dir=round_dir)

    saved_paths: List[Path] = []
    for i in range(page_count):
        filename = filenames[i] if i < len(filenames) else f"{config.experiment_folder_name(experiment)}_손그림_p{i+1}.png"
        out_path = target_dir / filename
        im = hand_grid.render_page(str(src_pdf), i, dpi=dpi)

        if crop_board:
            # 브레드보드 판형 영역과 상단 잭 영역만 크롭하고 좌우 여백/필기 제목/하단 실체도 캡션을 제거한다.
            b = hand_grid.board_image(str(src_pdf), i)
            w_t, h_t = b.width, b.height
            bx0, by0, bx1, by1 = b.rect
            s = dpi / 72.0
            # 템플릿 좌표 기준: 가로 [20, 565] (행 라벨 화살표 포함, 우측 자필 제목 제외)
            # 세로 [30, 740] (상단 얇은 검은 줄 및 불필요한 공백 제거, 상단 전원 잭 및 배선 포함, 63행 아래 실체도 캡션 제외)
            px_x0 = max(0, int((bx0 + BOARD_CROP_TEMPLATE_X[0] / w_t * (bx1 - bx0)) * s))
            px_y0 = max(0, int((by0 + BOARD_CROP_TEMPLATE_Y[0] / h_t * (by1 - by0)) * s))
            px_x1 = min(im.width, int((bx0 + BOARD_CROP_TEMPLATE_X[1] / w_t * (bx1 - bx0)) * s))
            px_y1 = min(im.height, int((by0 + BOARD_CROP_TEMPLATE_Y[1] / h_t * (by1 - by0)) * s))
            im = im.crop((px_x0, px_y0, px_x1, px_y1))

        im.save(str(out_path), format="PNG")
        saved_paths.append(out_path)

    return saved_paths


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="손그림 결선도 PDF 를 개별 300 DPI PNG 로 추출하여 결선도/손그림/ 에 저장합니다."
    )
    parser.add_argument("experiment", type=int, help="실험 번호 (예: 1)")
    parser.add_argument("pdf", nargs="?", default=None, help="손그림 PDF 파일 경로 (생략 시 최신 검토본 사용)")
    parser.add_argument("--out", "-o", default=None, help="출력 디렉토리 (기본: 보고서/실험NN/결선도/손그림)")
    parser.add_argument("--dpi", type=int, default=300, help="해상도 DPI (기본: 300)")
    parser.add_argument("--full-page", action="store_true", help="브레드보드 크롭 없이 전체 페이지를 저장")

    args = parser.parse_args(argv)

    try:
        paths = export_hand_diagrams(
            experiment=args.experiment,
            pdf_path=args.pdf,
            out_dir=args.out,
            dpi=args.dpi,
            crop_board=not args.full_page,
        )
        print(f"[SUCCESS] {len(paths)}개의 손그림 PNG 생성 완료:")
        for p in paths:
            print(f"  - {p} ({p.stat().st_size // 1024} KB)")
        return 0
    except Exception as e:
        print(f"[ERROR] 손그림 추출 실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
