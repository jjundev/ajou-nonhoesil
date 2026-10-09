"""Chrome 헤드리스 PDF 변환 (macOS·Windows).

**성공 판정 규칙이 이 모듈의 존재 이유다.** Chrome 은 macOS 에서 정상 동작 중에도
stderr 로 `task_policy_set TASK_CATEGORY_POLICY: (os/kern) invalid argument` 를
뱉는다. 종료 코드나 stderr 로 판정하면 멀쩡한 변환을 실패로 읽는다.
**PDF 파일이 실제로 생겼는지로만 판정한다.**

Chrome 위치는 **후보 목록**으로 받는다. 같은 저장소를 macOS 와 Windows 에서
번갈아 쓰는데, 경로가 하나뿐이던 동안에는 기기를 바꿀 때마다 `과목정보.md` 를
고치지 않으면 모든 PDF 변환이 "Chrome 을 찾을 수 없습니다" 로 멈췄다.
"""

import subprocess
from pathlib import Path

DEFAULT_CHROME = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
)


class PdfError(RuntimeError):
    pass


def resolve_chrome(chrome=DEFAULT_CHROME) -> str:
    """후보 중 이 머신에 실재하는 첫 경로를 돌려준다.

    `chrome` 은 경로 하나(str)여도, `과목정보.md` 의 목록이어도 된다. 없는 경로는
    다른 기기의 것이므로 조용히 건너뛴다 — 하나도 없을 때만 실패한다.
    """
    if chrome is None:
        chrome = DEFAULT_CHROME
    candidates = [chrome] if isinstance(chrome, (str, Path)) else list(chrome)
    for c in candidates:
        if c and Path(c).exists():
            return str(c)
    tried = "\n".join(f"  - {c}" for c in candidates)
    raise PdfError(
        f"Chrome 을 찾을 수 없습니다. 시도한 경로:\n{tried}\n"
        "`.claude/과목정보.md` 의 chrome 목록에 이 머신의 경로를 추가하세요."
    )


def html_to_pdf(html_path, pdf_path, chrome=DEFAULT_CHROME, timeout=120,
                virtual_time_budget=None) -> Path:
    """`virtual_time_budget`(ms)를 주면 Chrome 이 그만큼의 가상 시간이 흐를 때까지 인쇄를
    미룬다. 비동기 스크립트로 쪽을 맞추는 페이지는 이것 없이는 맞춤 전 상태가 찍힌다."""
    html_path, pdf_path = Path(html_path).resolve(), Path(pdf_path).resolve()
    if not html_path.exists():
        raise PdfError(f"입력 HTML 이 없습니다: {html_path}")
    chrome = resolve_chrome(chrome)

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    before = pdf_path.stat().st_mtime if pdf_path.exists() else None

    budget = [f"--virtual-time-budget={virtual_time_budget}"] if virtual_time_budget else []
    proc = subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer", *budget,
         f"--print-to-pdf={pdf_path}", html_path.as_uri()],
        capture_output=True, text=True, timeout=timeout,
    )

    if not pdf_path.exists() or (before is not None and pdf_path.stat().st_mtime == before):
        raise PdfError(
            f"PDF 가 생성되지 않았습니다 (종료 코드 {proc.returncode}).\n"
            f"stderr:\n{proc.stderr.strip()}"
        )
    return pdf_path
