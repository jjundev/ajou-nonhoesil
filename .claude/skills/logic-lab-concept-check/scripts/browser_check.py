#!/usr/bin/env python3
"""확인문제 HTML 을 Playwright 로 실제 조작해 보는 발행 게이트.

CLI: browser_check.py <확인문제 html> --src <자료_확인문제 폴더> --out <json> [--shots <dir>]

- 브라우저를 오프라인으로 설정하고 file://로 열어 공유 글꼴·KaTeX를 확인한다.
- 1280×900·375×812 × light·dark 4회. 매 회 콘솔 error·.katex-error·가로 넘침을 본다.
- 우측 패널: 채점 전에 현재 문항의 힌트를 열고, 풀이가 가려져 있는지 본다.
- 객관식: 오답 클릭 → 상태 문구·보기별 설명 → 다시 풀기 → 정답 클릭.
- 값 입력(short): 허용답의 소문자·공백 변형을 넣고 '답 확인' → 맞음 상태('자동 일치').
- 마지막 문항 제출 뒤 복기 창이 한 번 열리고 미응답 수를 보여 준다.
- 새로고침하면 선택·입력이 비어야 한다(저장소 null).
- 실패는 멈추지 않고 모아 JSON 에 남기며 하나라도 있으면 exit 1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
import sys

import _paths
import build

VIEWPORTS = [(1280, 900), (375, 812)]
THEMES = ["light", "dark"]
ACTION_TIMEOUT = 3000
NAV_TIMEOUT = 20000
SETTLE_MS = 600  # 화면 전환 애니메이션이 끝난 뒤 찍는다
SHORT_CORRECT = "자동 일치"  # review-interaction.js 가 short 정답일 때 .review-status 에 쓰는 글


def route_external(blocked: set[str]):
    """파일과 인라인 자원만 허용하고 외부 요청은 기록한다."""
    def handle(route):
        url = route.request.url
        if url.startswith(("file:", "data:", "blob:")):
            return route.continue_()
        blocked.add(url)
        return route.abort()
    return handle


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def short_variant(answer: dict) -> str:
    """정답과 대소문자·공백이 다른 허용답(소문자, 공백 있는 것 우선). 없으면 canonical.lower()."""
    canonical = answer["canonical"]
    pool = answer["accepted"]
    cands = [v.lower() for v in pool if v.lower() != canonical]
    spaced = [v for v in cands if " " in v]
    return (spaced or cands or [canonical.lower()])[0]


class Run:
    """뷰포트 × 테마 한 번. 예외 대신 실패를 모은다."""

    def __init__(self, page, label: str):
        self.page, self.label = page, label
        self.failures: list[str] = []
        self.errors: list[str] = []
        self.blocked: set[str] = set()
        page.on("pageerror", lambda e: self.errors.append(f"페이지 오류: {e}"))
        page.on("console", lambda m: self.errors.append(f"콘솔 error: {m.text}") if m.type == "error" else None)
        page.on("requestfailed", lambda r: self.errors.append(f"로컬 자원 요청 실패: {r.url}")
                if r.url.startswith("file:") else None)
        page.context.route("**/*", route_external(self.blocked))

    def expect(self, ok: bool, what: str) -> bool:
        if not ok:
            self.failures.append(f"{self.label}: {what}")
        return ok

    def step(self, what: str, fn):
        try:
            return fn()
        except Exception as e:  # Playwright TimeoutError 등: 기록하고 계속
            self.failures.append(f"{self.label}: {what}: {type(e).__name__}: {str(e).splitlines()[0]}")
            return None

    def go(self, card: str):
        self.page.evaluate("(id) => { location.hash = id; }", card)
        self.page.locator(f"#{card}").wait_for(state="visible")

    def page_checks(self, where: str):
        page = self.page
        self.expect(page.locator(".katex-error").count() == 0, f"{where}: 수식 렌더 오류(.katex-error)")
        self.expect(page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), f"{where}: 가로 넘침")


def check_hint(run: Run, item: dict, shot: Path | None):
    page, cid = run.page, item["id"]
    text = item.get("hint")
    aid = page.locator(f"#panel-right .aid[data-card-id='{cid}']")
    hint = aid.locator("details.hint")
    if not run.expect(hint.count() == int(bool(text)), f"{cid}: 우측 패널의 힌트 개수가 원본과 다름") or not text:
        return False

    run.go(cid)
    toggle = page.locator("#toggle-right")
    was_closed = toggle.get_attribute("aria-expanded") == "false"
    if was_closed:
        toggle.click()
    try:
        summary = hint.get_by_text("힌트 보기", exact=True)
        body = hint.locator("p")
        solution = aid.locator("details.solution")
        run.expect(hint.get_attribute("open") is not None, f"{cid}: 첫 방문에 힌트가 접혀 있음")
        shown = body.text_content() or ""
        run.expect(body.is_visible() and bool(shown.strip()), f"{cid}: 펼친 힌트 내용이 보이지 않음")
        # KaTeX가 수식을 그리면 텍스트 노드는 원본의 $…$ 문자열과 달라진다.
        if body.locator(".katex").count() == 0:
            run.expect(shown == text, f"{cid}: 펼친 힌트가 원본과 다름")
        run.expect(not solution.is_visible(), f"{cid}: 채점 전 풀이가 보임")
        run.page_checks(f"{cid} 힌트")
        if shot is not None:
            page.screenshot(path=str(shot), animations="disabled")
        summary.click()
        run.expect(hint.get_attribute("open") is None and not body.is_visible(), f"{cid}: 힌트가 접히지 않음")
    finally:
        if was_closed:
            close = page.locator("#panel-right [data-panel-close]")
            (close if close.is_visible() else toggle).click()
    return True


def check_mcq(run: Run, item: dict):
    page, cid = run.page, item["id"]
    run.go(cid)
    buttons = page.locator(f"#{cid} .review-choice")
    ids = [o["id"] for o in item["options"]]
    run.expect(buttons.count() == len(ids), f"{cid}: 보기 버튼 {buttons.count()}개 ≠ {len(ids)}")
    right = ids.index(item["answer"])
    wrong = (right + 1) % len(ids)
    buttons.nth(wrong).click()
    run.expect(buttons.nth(wrong).get_attribute("data-selected") == "true", f"{cid}: 오답 선택 표시 없음")
    status = (page.locator(f"#{cid} .review-status").text_content() or "").strip()
    run.expect(bool(status), f"{cid}: 오답 후 채점 상태 문구 없음")
    run.expect(page.locator(f"#{cid} .review-diagnostic:visible").count() >= 1, f"{cid}: 오답 후 진단 설명이 보이지 않음")
    page.locator(f"#{cid} .review-reset").click()
    run.expect(page.locator(f"#{cid} .review-choice[data-selected='true']").count() == 0, f"{cid}: 다시 풀기 뒤 선택 남음")
    buttons.nth(right).click()
    run.expect(buttons.nth(right).get_attribute("data-result") == "correct", f"{cid}: 정답 클릭 후 정답 표시 없음")
    return True


def check_short(run: Run, item: dict):
    page, cid = run.page, item["id"]
    run.go(cid)
    value = short_variant(item["answer"])
    page.locator(f"#{cid} .short-input input[type=text]").fill(value)
    page.locator(f"#{cid} .check-answer").click()
    status = (page.locator(f"#{cid} .review-status").text_content() or "").strip()
    run.expect(status == SHORT_CORRECT, f"{cid}: 허용답 '{value}' 입력 뒤 상태가 '{status}' (기대 '{SHORT_CORRECT}')")
    # 템플릿이 풀이(details)를 오른쪽 패널 .aid 로 옮긴다. 375 폭에서는 패널이 접혀 있어 open 만 본다.
    opened = page.locator(f".aid[data-card-id='{cid}'] details.solution[open]:not([hidden])").count()
    run.expect(opened == 1, f"{cid}: 답 확인 뒤 풀이가 열리지 않음")
    return True


def check_note_link(run: Run, item: dict):
    """채점 뒤 오른쪽 패널 풀이 끝에 그 목표의 실험설명 토픽 링크(같은 창)가 있어야 한다."""
    cid = item["id"]
    link = run.page.locator(f".aid[data-card-id='{cid}'] details.solution:not([hidden]) .note-link a")
    run.expect(link.count() == 1, f"{cid}: 채점 뒤 풀이에 실험설명 링크가 {link.count()}개 (기대 1)")
    if link.count() == 1:
        href = link.get_attribute("href") or ""
        run.expect(href.endswith("#" + item["topic_id"]), f"{cid}: 실험설명 링크 '{href}' 가 #{item['topic_id']} 로 가지 않음")
        run.expect(link.get_attribute("target") is None, f"{cid}: 실험설명 링크가 같은 창에서 열리지 않음(target 있음)")
    return True


def check_note_navigation(run: Run, item: dict):
    cid = item["id"]
    run.go(cid)
    fn = check_short if item["format"] == "short" else check_mcq
    fn(run, item)
    toggle = run.page.locator("#toggle-right")
    if toggle.get_attribute("aria-expanded") == "false":
        toggle.click()
    link = run.page.locator(f".aid[data-card-id='{cid}'] details.solution:not([hidden]) .note-link a")
    href = link.get_attribute("href")
    link.click()
    destination = urlsplit(run.page.url)
    run.expect(unquote(destination.path).endswith("/" + href.partition("#")[0]),
               "실험설명 파일로 이동하지 않음")
    run.expect(destination.fragment == item["topic_id"], "실험설명 토픽으로 이동하지 않음")
    run.page.locator(f"article[id='{item['topic_id']}']").wait_for(state="visible")
    run.page_checks("실험설명 이동 뒤")


def check_review_dialog(run: Run, item: dict, total: int, shot: Path | None):
    page, cid = run.page, item["id"]
    run.go(cid)
    opener = page.get_by_role("button", name="복기 열기", exact=True)
    dialog = page.get_by_role("dialog", name="복기할 준비가 됐어요")
    run.expect(not page.get_by_role("button", name="복기 프롬프트 복사").is_visible(),
               "마지막 문항 채점 전에 복사 버튼이 보임")
    run.expect(not opener.is_visible() and not dialog.is_visible(), "채점 전에 복기 기능이 열림")

    def answer():
        if item["format"] == "short":
            field = page.locator(f"#{cid} .short-input input[type=text]")
            field.fill(short_variant(item["answer"]))
            field.press("Enter")
        else:
            page.locator(f"#{cid} .review-choice").first.click()

    answer()
    if not run.expect(dialog.is_visible(), "마지막 문항을 제출해도 복기 창이 열리지 않음"):
        return
    if total > 1:
        run.expect(dialog.get_by_text(f"미응답 {total - 1}문항", exact=True).is_visible(),
                   "복기 창의 미응답 문항 수가 다름")
    if shot is not None:
        page.screenshot(path=str(shot), animations="disabled")
    page.keyboard.press("Escape")
    run.expect(not dialog.is_visible() and opener.is_visible(), "복기 창을 닫은 뒤 다시 열기 버튼이 보이지 않음")
    page.locator(f"#{cid} .review-reset").click()
    answer()
    run.expect(not dialog.is_visible(), "마지막 문항을 다시 제출하자 복기 창이 자동으로 다시 열림")
    opener.click()
    run.expect(dialog.is_visible(), "복기 열기 버튼으로 복기 창이 열리지 않음")
    page.evaluate("""() => {
        Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {
            writeText: async text => { window.testCopiedPrompt = text; }
        }});
    }""")
    dialog.get_by_role("button", name="복기 프롬프트 복사").click()
    message = "복사했어요. AI 채팅에 붙여 넣으세요"
    toast = page.locator('.review-feedback[data-result="copied"]')
    toast.get_by_text(message, exact=True).wait_for()
    run.expect(not dialog.is_visible(), "복사 성공 후 복기 창이 닫히지 않음")
    run.expect(page.evaluate("window.testCopiedPrompt.includes('미응답 ' + " + str(total - 1) + ")"),
               "복사된 프롬프트의 미응답 문항 수가 다름")
    page.evaluate("""() => {
        navigator.clipboard.writeText = async () => { throw new Error('clipboard denied'); };
        document.execCommand = () => false;
    }""")
    opener.click()
    dialog.get_by_role("button", name="복기 프롬프트 복사").click()
    area = dialog.get_by_role("textbox", name="복기 프롬프트")
    area.wait_for()
    run.expect(area.input_value() == page.evaluate("window.testCopiedPrompt"), "직접 복사할 프롬프트가 다름")
    page.evaluate("""() => {
        delete navigator.clipboard;
        delete document.execCommand;
        delete window.testCopiedPrompt;
    }""")
    dialog.get_by_role("button", name="닫기", exact=True).click()
    page.locator(f"#{cid} .review-reset").click()


def check_run(run: Run, url: str, items: list[dict], shots: Path | None, tag: str) -> dict:
    page = run.page
    page.goto(url, wait_until="load")
    run.expect(page.evaluate("""async () => (await document.fonts.load('400 16px Pretendard', '한글'))
                    .some(font => font.family === 'Pretendard' && font.status === 'loaded')"""), "Pretendard 로드 실패")
    run.expect(page.evaluate("typeof renderMathInElement === 'function'"), "KaTeX 자동 렌더 로드 실패")
    run.page_checks("시작 화면")
    review_shot = shots / f"{tag}-review.png" if shots is not None else None
    run.step("복기 창", lambda: check_review_dialog(run, items[-1], len(items), review_shot))
    checked = 0
    hints_checked = 0
    for n, item in enumerate(items):
        if n == 0 and shots is not None:
            page.locator(".review-feedback").wait_for(state="hidden", timeout=5000)
        hint_shot = shots / f"{tag}-{item['id']}-hint.png" if n == 0 and shots is not None else None
        if run.step(f"{item['id']}: 힌트", lambda: check_hint(run, item, hint_shot)):
            hints_checked += 1
        fn = check_short if item["format"] == "short" else check_mcq
        if run.step(f"{item['id']}: 조작", lambda fn=fn, item=item: fn(run, item)):
            checked += 1
        run.step(f"{item['id']}: 실험설명 링크", lambda item=item: check_note_link(run, item))
        if n == 0 and shots is not None:
            shot = shots / f"{tag}-{item['id']}.png"
            run.step("스크린샷 첫 문항", lambda: (
                page.locator(".review-feedback").wait_for(state="hidden"), page.screenshot(path=str(shot))))
        run.page_checks(item["id"])
    opener = page.get_by_role("button", name="복기 열기", exact=True)
    if run.expect(opener.is_visible(), "복기 열기 버튼 없음"):
        def check_full_review():
            opener.click()
            dialog = page.get_by_role("dialog", name="복기할 준비가 됐어요")
            run.expect(dialog.is_visible(), "모든 문항을 제출한 뒤 복기 창을 열 수 없음")
            run.expect(dialog.get_by_text("미응답", exact=False).count() == 0,
                       "모든 문항을 제출했지만 미응답이 표시됨")
            dialog.get_by_role("button", name="닫기", exact=True).click()
        run.step("전체 제출 뒤 복기 창", check_full_review)
    if shots is not None:
        shot = shots / f"{tag}-last.png"
        run.step("스크린샷 마지막 화면", lambda: (page.wait_for_timeout(SETTLE_MS), page.screenshot(path=str(shot))))
    if page.locator("#solved-btn").is_visible():  # 푼 문제 표시를 눌러 둬도 새로고침하면 사라져야 한다
        run.step("푼 문제로 표시", lambda: page.locator("#solved-btn").click())
    first_hint = next((item["id"] for item in items if item.get("hint")), None)
    if first_hint is not None:
        run.step("힌트 문항 다시 방문", lambda: run.go(first_hint))
        active_aid = page.locator(f".aid[data-card-id='{first_hint}']:not([hidden])")
        run.expect(active_aid.locator("details.hint:not([open])").count() == 1, "다시 방문한 문항의 힌트가 펼쳐져 있음")
    run.step("새로고침", lambda: page.reload(wait_until="load"))
    progress = (page.locator("#progress-n").text_content() or "").strip()
    run.expect(progress == "0", f"새로고침 뒤 푼 문제 수가 {progress} (기대 0)")
    run.expect(page.locator(".review-choice[data-selected='true']").count() == 0, "새로고침 뒤 선택 남음")
    run.expect(page.locator("details.hint[open]").count() == sum(bool(item.get("hint")) for item in items),
               "새로고침 뒤 접힌 힌트가 있음")
    values = run.step("새로고침 뒤 입력값 읽기", lambda: page.locator(".short-input input[type=text]").evaluate_all(
        "els => els.map(e => e.value)")) or []
    run.expect(all(v == "" for v in values), f"새로고침 뒤 입력값 남음: {values}")
    saved = run.step("새로고침 뒤 진행 기록 읽기", lambda: page.evaluate(
        "Object.keys(localStorage).filter(k => k.startsWith('od-review-solved:'))")) or []
    run.expect(saved == [], f"진행 기록이 localStorage 에 남음: {saved}")
    run.step("실험설명 실제 이동", lambda: check_note_navigation(run, items[0]))
    return {"items_checked": checked, "items": len(items), "hints_checked": hints_checked}


def check(html: Path, out: Path, shots: Path | None, *, src: Path, serve_root: Path | None = None,
          viewports=VIEWPORTS, themes=THEMES) -> dict:
    from playwright.sync_api import sync_playwright
    html = Path(html).resolve()
    root = Path(serve_root if serve_root is not None else _paths.REPO).resolve()
    if not html.is_relative_to(root):
        raise ValueError(f"HTML 이 서버 루트 밖에 있습니다: {html} (루트 {root})")
    source = build.load_source(src)
    topics = {o["id"]: o["topic_id"] for o in source["objectives"]}
    items = [dict(it, topic_id=topics[it["objective"]]) for it in source["items"]]
    report = {"html": html.relative_to(root).as_posix(), "sha256": sha256(html), "viewports": [f"{w}x{h}" for w, h in viewports],
              "themes": list(themes), "runs": [], "failures": []}
    if shots is not None:
        shots = Path(shots)
        shots.mkdir(parents=True, exist_ok=True)
    report["transport"] = "file://, offline=True"
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for width, height in viewports:
                for theme in themes:
                    with browser.new_context(viewport={"width": width, "height": height},
                                             offline=True, color_scheme=theme) as ctx:
                        page = ctx.new_page()
                        page.set_default_timeout(ACTION_TIMEOUT)
                        page.set_default_navigation_timeout(NAV_TIMEOUT)
                        run = Run(page, f"{width}x{height} {theme}")
                        detail = run.step("검사", lambda: check_run(run, html.as_uri(), items, shots,
                                                                  f"{width}x{height}-{theme}")) or {}
                        run.failures += [f"{run.label}: {e}" for e in run.errors]
                        run.expect(not run.blocked, "외부 자원 요청: " + ", ".join(sorted(run.blocked)))
                        report["runs"].append({"label": run.label, "detail": detail, "failures": run.failures,
                                               "external_blocked": sorted(run.blocked)})
                        report["failures"] += run.failures
        finally:
            browser.close()
    report["status"] = "fail" if report["failures"] else "pass"
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="확인문제 브라우저 조작 검사")
    parser.add_argument("html", type=Path)
    parser.add_argument("--src", type=Path, required=True, help="자료_확인문제 폴더")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--shots", type=Path)
    parser.add_argument("--serve-root", type=Path, help="검증할 임시 실행 폴더")
    args = parser.parse_args(argv)
    try:
        report = check(args.html, args.out, args.shots, src=args.src, serve_root=args.serve_root)
    except (OSError, ValueError) as e:
        print(f"browser: {e}", file=sys.stderr)
        return 1
    print(f"browser: {report['status']} · 실행 {len(report['runs'])}회 · 실패 {len(report['failures'])}건 → {args.out}")
    for line in report["failures"][:20]:
        print("  " + line)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
