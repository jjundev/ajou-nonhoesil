"""Chrome 헤드리스 PDF 변환 (macOS).

**성공 판정 규칙이 이 모듈의 존재 이유다.** Chrome 은 macOS 에서 정상 동작 중에도
stderr 로 `task_policy_set TASK_CATEGORY_POLICY: (os/kern) invalid argument` 를
뱉는다. 종료 코드나 stderr 로 판정하면 멀쩡한 변환을 실패로 읽는다.
**PDF 파일이 실제로 생겼는지로만 판정한다.**
"""

import subprocess
from pathlib import Path

DEFAULT_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


class PdfError(RuntimeError):
    pass


def html_to_pdf(html_path, pdf_path, chrome=DEFAULT_CHROME, timeout=120) -> Path:
    html_path, pdf_path = Path(html_path).resolve(), Path(pdf_path).resolve()
    if not html_path.exists():
        raise PdfError(f"입력 HTML 이 없습니다: {html_path}")
    if not Path(chrome).exists():
        raise PdfError(
            f"Chrome 을 찾을 수 없습니다: {chrome}\n"
            "`.claude/과목정보.md` 의 chrome 경로를 확인하세요."
        )

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    before = pdf_path.stat().st_mtime if pdf_path.exists() else None

    proc = subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf_path}", html_path.as_uri()],
        capture_output=True, text=True, timeout=timeout,
    )

    if not pdf_path.exists() or (before is not None and pdf_path.stat().st_mtime == before):
        raise PdfError(
            f"PDF 가 생성되지 않았습니다 (종료 코드 {proc.returncode}).\n"
            f"stderr:\n{proc.stderr.strip()}"
        )
    return pdf_path
