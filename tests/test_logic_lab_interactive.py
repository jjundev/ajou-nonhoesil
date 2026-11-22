from pathlib import Path
import shutil
import subprocess

import pytest

from scripts.lab import standalone_note

ROOT = Path(__file__).resolve().parents[1]


def test_74hc76_transition_against_t3():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js is needed to test the browser model')
    subprocess.run([node, '--input-type=module', '-e', """
        import assert from 'node:assert/strict';
        import {transition} from './.claude/skills/logic-lab-interactive/assets/74hc76.mjs';
        const change = (state, pin, value) => transition(state, {pin, value});
        const base = {CLK: 0, J: 1, K: 1, PR: 1, CLR: 1, Q: 0};
        assert.equal(change(base, 'CLK', 0).rule, 'low');
        assert.equal(change(base, 'CLK', 1).rule, 'rising');
        assert.equal(change({...base, CLK: 1}, 'CLK', 1).rule, 'high');
        assert.equal(change(base, 'K', 0).next.Q, 0);
        // T3, ordered by JK = 00, 01, 10, 11, for both previous states.
        for (const [q, outputs] of [[0, [0, 0, 1, 1]], [1, [1, 0, 1, 0]]]) {
          for (const [index, expected] of outputs.entries()) {
            const state = {...base, CLK: 1, J: index >> 1, K: index & 1, Q: q};
            const result = change(state, 'CLK', 0);
            assert.equal(result.next.Q, expected);
            assert.equal(result.rule, ['jk00', 'jk01', 'jk10', 'jk11'][index]);
            assert.equal(state.Q, q);
            assert.equal(state.CLK, 1);
          }
        }
        const set = change(base, 'PR', 0);
        assert.equal(set.next.Q, 1);
        assert.equal(set.rule, 'pr');
        const conflicting = change({...set.next, CLK: 1, J: 0, K: 1}, 'CLK', 0);
        assert.equal(conflicting.next.Q, 1);
        assert.equal(conflicting.rule, 'pr');
        assert.equal(change(set.next, 'PR', 1).next.Q, 1);
        const cleared = change({...base, Q: 1}, 'CLR', 0);
        assert.equal(cleared.next.Q, 0);
        assert.equal(cleared.rule, 'clr');
        assert.equal(change(cleared.next, 'CLR', 1).next.Q, 0);
        const invalid = change(set.next, 'CLR', 0);
        assert.equal(invalid.accepted, false);
        assert.deepEqual(invalid.next, set.next);
        assert.equal(change(base, 'Q', 1).accepted, false);
    """], cwd=ROOT, check=True)


def only_legacy_registration(interactive, monkeypatch):
    # The fixture manifest has only the original lesson's topic.
    def legacy_only(directory, manifest):
        author = directory / f"{manifest['experiment']:02d}.json"
        yield author, interactive.Attachment(interactive.load_lesson(author, manifest), None)

    monkeypatch.setattr(interactive, 'registered_lessons', legacy_only)


def test_lab_attachment_and_standalone_note(tmp_path, monkeypatch):
    from scripts.lab import interactive

    only_legacy_registration(interactive, monkeypatch)
    folder = tmp_path / '실험06'
    folder.mkdir()
    note = folder / '실험06_실험설명.html'
    note.write_text('<article class="topic" id="t-74hc76"><h3>JK</h3><p>본문</p></article>',
                    encoding='utf-8')
    manifest = {'experiment': 6, 'topics': [{'id': 't-74hc76'}]}
    interactive.attach(ROOT, folder, manifest)
    first = note.read_bytes()
    interactive.attach(ROOT, folder, manifest)
    assert note.read_bytes() == first
    assert first.count(b'data-interactive-lab=') == 1
    path = folder / '실험06_인터랙티브_74HC76.html'
    html = path.read_text(encoding='utf-8')
    assert '실험06_실험설명.html#t-74hc76' in html
    assert '<script src=' not in html
    single_note = standalone_note.build(folder, '실험설명')
    assert standalone_note.leftovers(single_note) == []
    assert '<span' in single_note
    assert '본문' in single_note


@pytest.mark.parametrize('width,theme', [(1440, 'light'), (1440, 'dark'), (375, 'light'), (375, 'dark')])
def test_lab_runs_offline_with_keyboard(tmp_path, width, theme, monkeypatch):
    from scripts.lab import interactive

    only_legacy_registration(interactive, monkeypatch)
    playwright = pytest.importorskip('playwright.sync_api')
    note = tmp_path / '실험06_실험설명.html'
    note.write_text('<article class="topic" id="t-74hc76"><h3>JK</h3></article>', encoding='utf-8')
    path, = interactive.attach(ROOT, tmp_path, {'experiment': 6, 'topics': [{'id': 't-74hc76'}]})
    with playwright.sync_playwright() as runner:
        if not Path(runner.chromium.executable_path).exists():
            pytest.skip('Playwright Chromium is needed for the offline interaction check')
        with runner.chromium.launch() as browser:
            mobile = width == 375
            page = browser.new_page(
                viewport={'width': width, 'height': 812 if mobile else 900},
                color_scheme=theme, offline=True, has_touch=mobile,
            )
            errors = []
            external = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: external.append(request.url) if request.url.startswith(('http:', 'https:')) else None)
            page.goto(note.as_uri())
            page.get_by_role('link', name='74HC76 핀과 파형 실험 열기').press('Enter')
            assert page.url == path.as_uri()
            expect = playwright.expect
            wave = page.locator('#traces svg')
            waveform = page.locator('#traces')
            fixed = page.locator('#fixed-inputs')
            popup = page.locator('#trace-popup')
            hovered = popup.and_(page.locator('[aria-hidden="true"]'))
            details = popup.and_(page.locator(':not([aria-hidden])'))
            event = page.locator('#event')
            circuit = page.locator('#circuit svg')
            t3 = page.locator('#truth-table [aria-current="true"]')
            shell = page.locator('#ec2-lab-root')
            left = page.get_by_role('button', name='조작 패널', exact=True)
            right = page.get_by_role('button', name='설명 패널', exact=True)
            card = page.locator('#prediction')
            hint = card.locator('#prediction-next')

            def open_left():
                if mobile:
                    left.press('Enter')
                    expect(shell).to_have_attribute('data-drawer', 'left')
                    expect(page.get_by_role('button', name='조작 닫기')).to_be_focused()
                    page.keyboard.press('Shift+Tab')
                    expect(page.get_by_role('button', name='이 단계 처음부터')).to_be_focused()
                    page.keyboard.press('Tab')
                    expect(page.get_by_role('button', name='조작 닫기')).to_be_focused()

            def close_left():
                if mobile:
                    page.keyboard.press('Escape')
                    expect(left).to_be_focused()

            def select_task(name):
                open_left()
                page.get_by_role('button', name=name).click()
                if mobile:
                    expect(shell).to_have_attribute('data-drawer', 'none')

            def trace(pin, index):
                return wave.locator(f'[data-trace-pin="{pin}"][data-trace-index="{index}"]')

            def trace_color(pin):
                return wave.locator(f'[data-signal="{pin}"] .signal').evaluate('line => getComputedStyle(line).stroke')

            def inspect(pin, index):
                target = trace(pin, index)
                if mobile:
                    target.tap()
                else:
                    target.click()
                expect(details).to_be_visible()

            expect(shell).to_be_visible()
            expect(page.locator(('#stage' if mobile else '#panel-right') + ' #prediction')).to_be_visible()
            expect(hint).to_be_hidden()
            expect(circuit.locator('[data-pin]')).to_have_count(16)
            assert page.evaluate("document.fonts.ready.then(() => document.fonts.check('16px Pretendard'))")
            expect(wave).to_have_attribute('aria-label', 'CLK 0 / Q 0')
            colors = {pin: trace_color(pin) for pin in ('CLK', 'Q')}
            assert colors['CLK'] != colors['Q']
            expect(page.locator('#panel-right .diagnosis, #truth-note')).to_have_count(0)
            expect(fixed).to_have_text('고정 입력 PR=1 · CLR=1 · J=1 · K=1')
            expect(t3).to_have_count(0)

            clr_probe = page.get_by_role('button', name='3번 CLR 프로브')
            expect(clr_probe).to_have_count(0)
            fixed_pin = circuit.locator('[data-pin="3"] [data-value]')
            if mobile:
                fixed_pin.tap()
            else:
                fixed_pin.click()
            expect(trace('CLR', 0)).to_have_count(0)
            expect(fixed).to_contain_text('CLR=1')

            probe = page.get_by_role('button', name='15번 Q 프로브')
            probe.press('Space')
            expect(wave).to_have_attribute('aria-label', 'CLK 0')
            probe.press('Enter')
            expect(probe).to_have_attribute('aria-pressed', 'true')
            expect(circuit.locator('[data-net="Q"]')).to_have_class('is-probed')
            assert probe.bounding_box()['height'] >= 44
            edge_answer = page.get_by_role('radio', name='1 → 0')
            edge_answer.check()
            expect(hint).to_contain_text('CLK 0 유지')
            if not mobile:
                right.click()
                expect(page.locator('#stage #prediction')).to_be_visible()
                expect(edge_answer).to_be_checked()
                expect(wave).to_have_attribute('aria-label', 'CLK 0 / Q 0')
                right.click()
                expect(page.locator('#panel-right #prediction')).to_be_visible()
            for name, q in [('CLK 0 유지', 0), ('CLK 올리기 ↑', 0), ('CLK 내리기 ↓', 1)]:
                expect(hint).to_contain_text(name)
                page.get_by_role('button', name=name, exact=True).press('Enter')
                expect(event).to_contain_text(f'현재 Q={q}')
            expect(hint).to_be_hidden()
            expect(wave).to_have_attribute('aria-label', 'CLK 0, 0, 1, 0 / Q 0, 0, 0, 1')
            expect(t3).to_have_attribute('data-rule', 'jk11')
            expect(circuit.locator('[data-led="Q"]')).to_have_attribute('data-level', '1')
            expect(page.locator('#feedback')).to_contain_text('맞았어요')
            expect(page.locator('#advance')).to_be_hidden()
            expect(waveform).to_be_focused()
            if mobile:
                right.press('Enter')
                expect(shell).to_have_attribute('data-drawer', 'right')
                expect(t3).to_be_visible()
                page.keyboard.press('Escape')
                expect(right).to_be_focused()
            if not mobile:
                trace('Q', 2).hover()
                page.evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                expect(hovered).to_contain_text('상승 엣지')
                expect(hovered).to_have_css('border-left-color', colors['Q'])
                expect(hovered).to_contain_text('조작 2 · CLK 올리기 ↑')
                expect(page.locator('#position')).to_have_text('3 / 3')
                expect(t3).to_have_attribute('data-rule', 'jk11')
                expect(circuit.locator('[data-led="Q"]')).to_have_attribute('data-level', '1')
                page.keyboard.press('Escape')
                expect(hovered).to_be_hidden()
            inspect('Q', 2)
            expect(popup).to_have_css('position', 'absolute')
            expect(page.locator('.plot-wrap > .trace-card')).to_have_count(0)
            expect(details.locator('[data-trace-value]')).to_have_css('color', colors['Q'])
            expect(details).to_contain_text('15번 핀 Q = 0')
            expect(details).to_contain_text('조작 2 · CLK 올리기 ↑')
            expect(details).to_contain_text('상승 엣지')
            expect(details).not_to_contain_text('T3')
            expect(event).to_contain_text('현재 Q=0')
            expect(t3).to_have_count(0)
            expect(circuit.locator('[data-led="Q"]')).to_have_attribute('data-level', '0')
            expect(circuit.locator('[data-pin="15"] [data-value]')).to_have_text('0')
            waveform.press('ArrowRight')
            expect(details).to_contain_text('Q 0 → 1')
            expect(details).to_contain_text('T3 · 반전')
            expect(t3).to_have_attribute('data-rule', 'jk11')
            waveform.press('ArrowUp')
            waveform.press('Enter')
            expect(details).to_contain_text('1번 핀 CLK 1 → 0')
            expect(details).not_to_contain_text('T3')
            waveform.press('Escape')
            expect(details).to_be_hidden()
            waveform.press('Enter')
            page.get_by_role('button', name='파형 설명 닫기').press('Enter')
            expect(popup).to_be_hidden()
            expect(waveform).to_be_focused()
            waveform.press('ArrowLeft')
            open_left()
            page.get_by_role('button', name='K 입력, 현재 1', exact=True).press('Space')
            close_left()
            expect(page.get_by_role('button', name='다음 조작', exact=True)).to_be_disabled()
            expect(wave).to_have_attribute('aria-label', 'CLK 0, 0, 1, 1 / Q 0, 0, 0, 0 / K 1, 1, 1, 0')
            expect(fixed).not_to_contain_text('K=')
            k_probe = page.get_by_role('button', name='16번 K 프로브')
            k_probe.press('Enter')
            expect(trace('K', 3)).to_have_count(0)
            expect(fixed).not_to_contain_text('K=')
            k_probe.press('Enter')
            waveform.press('ArrowLeft')
            expect(trace('K', 3)).to_be_visible()
            page.get_by_role('button', name='CLK 내리기 ↓', exact=True).press('Enter')
            expect(wave).to_have_attribute('aria-label', 'CLK 0, 0, 1, 0 / Q 0, 0, 0, 1')
            expect(k_probe).to_have_count(0)
            expect(fixed).to_contain_text('K=1')

            open_left()
            page.get_by_role('button', name='PR 입력, 현재 1', exact=True).press('Space')
            close_left()
            expect(trace('PR', 4)).to_be_visible()
            waveform.press('ArrowLeft')
            open_left()
            page.get_by_role('button', name='CLK 입력, 현재 0', exact=True).press('Space')
            close_left()
            expect(trace('PR', 4)).to_have_count(0)
            expect(fixed).to_contain_text('PR=1')

            select_task('클럭 없이 Q 바꾸기')
            expect(wave).to_have_attribute('aria-label', 'CLK 0 / Q 1 / CLR 1')
            assert {pin: trace_color(pin) for pin in colors} == colors
            clr_color = trace_color('CLR')
            assert clr_color not in colors.values()
            inspect('CLR', 0)
            expect(details).to_have_css('border-left-color', clr_color)
            expect(fixed).not_to_contain_text('CLK')
            expect(page.get_by_role('button', name='1번 CLK 프로브')).to_have_count(0)
            page.get_by_role('radio', name='CLR을 0으로 내릴 때').check()
            expect(hint).to_contain_text('CLR 내리기 ↓')
            page.get_by_role('button', name='CLR 내리기 ↓').click()
            expect(hint).to_contain_text('CLR 올리기 ↑')
            expect(clr_probe).to_have_attribute('aria-pressed', 'true')
            expect(event).to_contain_text('CLR=0')
            expect(event).to_contain_text('현재 Q=0')
            expect(t3).to_have_attribute('data-rule', 'clr')
            open_left()
            page.get_by_role('button', name='PR 입력, 현재 1').click()
            expect(page.locator('#input-error')).to_contain_text('이 실험의 범위 밖')
            close_left()
            expect(event).to_contain_text('이 실험의 범위 밖')
            expect(page.locator('#position')).to_have_text('1 / 1')
            page.get_by_role('button', name='CLR 올리기 ↑').click()
            expect(page.locator('#input-error')).to_be_hidden()
            expect(wave).to_have_attribute('aria-label', 'CLK 0, 0, 0 / Q 1, 0, 0 / CLR 1, 0, 1')
            expect(t3).to_have_attribute('data-rule', 'low')
            inspect('Q', 2)
            expect(details).to_contain_text('CLR이 1로 올라가')
            expect(details).to_contain_text('T3 · 이전 Q 유지')
            inspect('Q', 1)
            expect(details).to_contain_text('T3 · 리셋')
            expect(circuit.locator('[data-pin="3"] [data-value]')).to_have_text('0')
            expect(t3).to_have_attribute('data-rule', 'clr')

            select_task('하강 엣지 찾기')
            open_left()
            page.get_by_role('button', name='CLR 입력, 현재 1').click()
            close_left()
            page.get_by_role('button', name='CLK 올리기 ↑', exact=True).click()
            expect(circuit.locator('[data-pin="1"] [data-value]')).to_have_text('1')
            expect(t3).to_have_attribute('data-rule', 'clr')
            page.get_by_role('button', name='CLK 내리기 ↓', exact=True).click()
            expect(wave).to_have_attribute('aria-label', 'CLK 0, 0, 1, 0 / Q 0, 0, 0, 0 / CLR 1, 0, 0, 0')
            expect(t3).to_have_attribute('data-rule', 'clr')
            expect(page.get_by_role('button', name='CLK 올리기 ↑', exact=True)).to_be_enabled()

            select_task('새 파형에서 예측하기')
            expect(page.locator('#advance')).to_be_hidden()
            expect(wave).to_have_attribute('aria-label', 'CLK 0, 1, 0 / Q 0, 나머지는 예측 후 공개')
            inspect('Q', 0)
            expect(details).to_contain_text('시작 상태')
            inspect('Q', 2)
            expect(details).to_contain_text('예측 후 공개')
            expect(details).not_to_contain_text('T3')
            expect(details).not_to_contain_text('0 → 1')
            if not mobile:
                waveform.press('Escape')
                trace('Q', 1).hover()
                expect(hovered).to_contain_text('예측 후 공개')
                expect(hovered).not_to_contain_text('상승 엣지')
            expect(circuit.locator('[data-led="Q"]')).to_have_attribute('data-level', 'unknown')
            expect(circuit.locator('[data-pin="15"] [data-value]')).to_have_text('?')
            expect(t3).to_have_count(0)
            reveal = page.get_by_role('button', name='파형 펼쳐서 확인')
            expect(reveal).to_be_disabled()
            page.get_by_role('radio', name='② 하강 엣지').check()
            reveal.press('Enter')
            expect(wave).to_have_attribute('aria-label', 'CLK 0, 1, 0 / Q 0, 0, 1')
            signal_paths = wave.locator('path.signal')
            revealed = signal_paths.evaluate_all("paths => paths.map(path => path.getAttribute('d'))")
            expect(t3).to_have_attribute('data-rule', 'jk10')
            inspect('Q', 2)
            expect(details).to_contain_text('T3 · 세트')
            expect(page.locator('#feedback')).to_contain_text('맞았어요')
            open_left()
            page.get_by_role('button', name='이 단계 처음부터').press('Enter')
            close_left()
            expect(wave).to_have_attribute('aria-label', 'CLK 0, 1, 0 / Q 0, 나머지는 예측 후 공개')
            skip = page.get_by_role('button', name='예측 없이 파형 보기')
            skip.tap() if mobile else skip.click()
            expect(card).to_be_hidden()
            expect(waveform).to_be_focused()
            expect(waveform).to_be_in_viewport()
            expect(page.locator('#position')).to_have_text('2 / 2')
            expect(wave).to_have_attribute('aria-label', 'CLK 0, 1, 0 / Q 0, 0, 1')
            assert signal_paths.evaluate_all("paths => paths.map(path => path.getAttribute('d'))") == revealed
            expect(circuit.locator('[data-led="Q"]')).to_have_attribute('data-level', '1')
            expect(t3).to_have_attribute('data-rule', 'jk10')
            expect(page.locator('#advance')).to_be_hidden()
            open_left()
            expect(page.get_by_role('button', name='CLK 입력')).to_be_enabled()
            close_left()
            if width == 375:
                select_task('하강 엣지 찾기')
                open_left()
                for _ in range(10):
                    page.get_by_role('button', name='CLK 입력').click()
                close_left()
                scrollbox = page.locator('#traces')
                assert scrollbox.evaluate('(element) => element.scrollLeft') > 0
                for _ in range(10):
                    page.get_by_role('button', name='이전 조작', exact=True).press('Enter')
                assert scrollbox.evaluate('(element) => element.scrollLeft') == 0
            assert page.evaluate('document.documentElement.scrollWidth') == width
            page.get_by_role('link', name='실험설명으로').press('Enter')
            assert page.url == note.as_uri() + '#t-74hc76'
            assert errors == []
            assert external == []


def test_checked_attachment_rejects_missing_or_stale_receipt(tmp_path):
    from scripts.lab import interactive

    repo = tmp_path / 'repo'
    skill = repo / interactive.SKILL
    shutil.copytree(ROOT / interactive.SKILL, skill, ignore=shutil.ignore_patterns('06'))
    font_folder = interactive.FONT_VENDOR / 'pretendard'
    shutil.copytree(ROOT / font_folder, repo / font_folder)
    author = skill / 'lessons/06.json'
    for source in interactive.read_json(author)['sources']:
        path = repo / source['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / source['path'], path)
    receipt = skill / 'lessons/06.verification.json'
    receipt.unlink(missing_ok=True)
    folder = tmp_path / 'pack'
    folder.mkdir()
    note = folder / '실험06_실험설명.html'
    note.write_text('<article class="topic" id="t-74hc76"><h3>JK</h3></article>', encoding='utf-8')
    manifest = {'experiment': 6, 'topics': [{'id': 't-74hc76'}]}
    with pytest.raises(ValueError, match='74hc76: .*검증 기록'):
        interactive.attach(repo, folder, manifest, reviewed_only=True)
    path, = interactive.attach(repo, folder, manifest)
    assert interactive.check_attachment(folder, manifest)
    evidence = folder / '.pack/자료_인터랙티브/74hc76/verification.json'
    interactive.write_json(receipt, {
        'basis': interactive.read_json(evidence),
        'checks': {name: {'status': 'pass'} for name in interactive.REQUIRED_CHECKS},
    })
    interactive.attach(repo, folder, manifest, reviewed_only=True)
    assert interactive.check_attachment(folder, manifest, root=repo) == []
    path.write_text('updated', encoding='utf-8')
    assert '현재 파일과 일치' in interactive.check_attachment(folder, manifest)[0]
    shutil.rmtree(evidence.parent)
    assert '검증 기록' in interactive.check_attachment(folder, manifest)[0]


def test_multiple_registered_lessons_rebuild_and_publish_gate(tmp_path):
    import shutil

    from scripts.lab import interactive

    repo = tmp_path / 'repo'
    skill = repo / interactive.SKILL
    shutil.copytree(ROOT / interactive.SKILL, skill, ignore=shutil.ignore_patterns('06'))
    shutil.copytree(ROOT / interactive.FONT_VENDOR, repo / interactive.FONT_VENDOR)
    lessons = skill / 'lessons'
    legacy = interactive.read_json(lessons / '06.json')
    for source in legacy['sources']:
        destination = repo / source['path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / source['path'], destination)

    authors = lessons / '06'
    authors.mkdir()
    for lesson_id in ('edge-practice', 'reset-practice'):
        interactive.write_json(authors / f'{lesson_id}.json', {**legacy, 'title': lesson_id})

    folder = tmp_path / 'pack'
    folder.mkdir()
    note = folder / '실험06_실험설명.html'
    note.write_text('<article class="topic" id="t-74hc76"><p>본문</p></article>', encoding='utf-8')
    manifest = {'experiment': 6, 'topics': [{'id': 't-74hc76'}]}
    evidence_dir = folder / '.pack/자료_인터랙티브'
    paths = interactive.attach(repo, folder, manifest)
    assert {path.name for path in paths} == {
        '실험06_인터랙티브_74HC76.html',
        '실험06_인터랙티브_edge-practice.html',
        '실험06_인터랙티브_reset-practice.html',
    }
    assert interactive.digest(folder / '실험06_인터랙티브_74HC76.html') == (
        interactive.read_json(lessons / '06.verification.json')['basis']['html_sha256']
    )
    first_note = note.read_bytes()
    assert first_note.count(b'data-interactive-lab=') == 3
    for lesson_id in ('edge-practice', 'reset-practice'):
        assert f'data-interactive-lab="{lesson_id}"'.encode() in first_note
        with pytest.raises(ValueError, match=lesson_id):
            interactive.attach(repo, folder, manifest, reviewed_only=True)
        assert note.read_bytes() == first_note
        interactive.write_json(authors / f'{lesson_id}.verification.json', {
            'basis': interactive.read_json(evidence_dir / lesson_id / 'verification.json'),
            'checks': {name: {'status': 'pass'} for name in interactive.REQUIRED_CHECKS},
        })
    interactive.attach(repo, folder, manifest, reviewed_only=True)
    assert note.read_bytes() == first_note
    assert interactive.check_attachment(folder, manifest, root=repo) == []

    (authors / 'edge-practice.json').unlink()
    assert '등록 원고' in interactive.check_attachment(folder, manifest, root=repo)[0]
    interactive.attach(repo, folder, manifest, reviewed_only=True)
    assert not (folder / '실험06_인터랙티브_edge-practice.html').exists()
    assert not (evidence_dir / 'edge-practice').exists()
    assert b'edge-practice' not in note.read_bytes()
    assert interactive.check_attachment(folder, manifest, root=repo) == []


def test_d_latch_prediction_moves_without_resetting_the_experiment(tmp_path):
    from scripts.lab import interactive

    playwright = pytest.importorskip('playwright.sync_api')
    assets = ROOT / interactive.SKILL / 'assets'
    lesson = interactive.read_json(ROOT / interactive.SKILL / 'lessons/06/d-latch.json')
    path = tmp_path / 'd-latch.html'
    path.write_text(interactive.render(lesson, assets, '실험06_실험설명.html', ROOT / interactive.FONT_VENDOR),
                    encoding='utf-8')
    with playwright.sync_playwright() as runner:
        if not Path(runner.chromium.executable_path).exists():
            pytest.skip('Playwright Chromium is needed for the offline interaction check')
        with runner.chromium.launch() as browser:
            page = browser.new_page(viewport={'width': 1024, 'height': 900}, offline=True)
            page.set_default_timeout(3000)
            page.goto(path.as_uri())
            expect = playwright.expect
            card = page.locator('#prediction')
            center = page.locator('#stage #prediction')
            sidebar = page.locator('#panel-right #prediction')
            right = page.get_by_role('button', name='설명 패널', exact=True)
            wave = page.locator('#traces')

            expect(sidebar).to_be_visible()
            advance = page.locator('#advance')
            hint = page.locator('#prediction-next')
            expect(hint).to_be_hidden()
            first_answer = page.get_by_role('radio', name='0 → 1 → 0')
            first_answer.focus()
            first_answer.press('Space')
            expect(first_answer).to_be_focused()
            expect(hint).to_contain_text('D를 1로 올리기')
            advance.press('Enter')
            expect(advance).to_have_text('D를 0으로 내리기')
            expect(hint).to_contain_text('D를 0으로 내리기')
            advance.press('Enter')
            expect(advance).to_be_hidden()
            expect(hint).to_be_hidden()
            expect(wave).to_be_focused()
            expect(page.locator('#position')).to_have_text('2 / 2')
            page.locator('#previous').press('Enter')
            expect(advance).to_have_text('D를 0으로 내리기')
            expect(hint).to_contain_text('D를 0으로 내리기')
            page.get_by_role('button', name='E=0에서 Q 유지하기', exact=True).click()
            page.get_by_role('radio', name='1', exact=True).check()
            expect(hint).to_contain_text('E를 0으로 내리기')
            advance.press('Enter')
            expect(hint).to_contain_text('D를 0으로 내리기')
            halfway = wave.inner_html()
            card.get_by_role('button', name='예측 건너뛰기', exact=True).click()
            expect(card).to_be_hidden()
            expect(page.locator('#position')).to_have_text('1 / 1')
            assert wave.inner_html() == halfway
            advance.press('Enter')
            expect(page.locator('#position')).to_have_text('2 / 2')
            page.get_by_role('button', name='E를 다시 열기 전에 예측하기', exact=True).click()
            answer = page.get_by_role('radio', name='② E를 1로 올릴 때')
            answer.check()
            masked = wave.inner_html()

            right.click()
            expect(center).to_be_visible()
            expect(answer).to_be_checked()
            assert wave.inner_html() == masked
            right.click()
            expect(sidebar).to_be_visible()
            answer.focus()
            page.set_viewport_size({'width': 1023, 'height': 900})
            expect(center).to_be_visible()
            expect(answer).to_be_focused()
            page.set_viewport_size({'width': 1024, 'height': 900})
            expect(sidebar).to_be_visible()
            expect(answer).to_be_focused()
            expect(answer).to_be_checked()

            card.get_by_role('button', name='파형 펼쳐서 확인', exact=True).click()
            expect(wave).to_be_focused()
            expect(page.locator('#feedback')).to_contain_text('맞았어요')
            expect(page.locator('[data-led="Q"]')).to_have_attribute('data-level', '0')
            revealed = wave.inner_html()
            assert revealed != masked
            right.click()
            expect(center).to_be_visible()
            expect(page.locator('#feedback')).to_contain_text('맞았어요')
            assert wave.inner_html() == revealed
            right.click()
            expect(sidebar).to_be_visible()
            expect(card).to_have_count(1)

            page.get_by_role('button', name='E를 다시 열기 전에 예측하기', exact=True).click()
            expect(page.locator('#submit')).to_be_disabled()
            card.get_by_role('button', name='예측 없이 파형 보기', exact=True).click()
            expect(card).to_be_hidden()
            expect(wave).to_be_focused()
            expect(page.locator('#position')).to_have_text('2 / 2')
            expect(page.locator('[data-led="Q"]')).to_have_attribute('data-level', '0')
            assert wave.inner_html() == revealed
            page.locator('#previous').press('Enter')
            expect(page.locator('[data-led="Q"]')).to_have_attribute('data-level', '1')


def test_d_latch_transition_matches_every_handout_row():
    subprocess.run(['node', '--input-type=module', '-e', '''
        import assert from 'node:assert/strict';
        import {transition} from './.claude/skills/logic-lab-interactive/assets/d-latch.mjs';

        for (const E of [0, 1]) {
          for (const D of [0, 1]) {
            for (const Q of [0, 1]) {
              for (const pin of ['D', 'E']) {
                for (const value of [0, 1]) {
                  const previous = {E, D, Q};
                  const result = transition(previous, {pin, value});
                  const nextE = pin === 'E' ? value : E;
                  const nextD = pin === 'D' ? value : D;
                  assert.equal(result.accepted, true);
                  assert.deepEqual(result.next, {E: nextE, D: nextD, Q: nextE ? nextD : Q});
                  assert.equal(result.rule, nextE ? (nextD ? 'set' : 'reset') : 'hold');
                  assert.deepEqual(previous, {E, D, Q});
                }
              }
            }
          }
        }
        assert.equal(transition({E: 0, D: 0, Q: 0}, {pin: 'Q', value: 1}).accepted, false);
    '''], cwd=ROOT, check=True)
