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


def test_lab_attachment_and_standalone_note(tmp_path):
    from scripts.lab import interactive

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
def test_lab_runs_offline_with_keyboard(tmp_path, width, theme):
    from scripts.lab import interactive

    playwright = pytest.importorskip('playwright.sync_api')
    note = tmp_path / '실험06_실험설명.html'
    note.write_text('<article class="topic" id="t-74hc76"><h3>JK</h3></article>', encoding='utf-8')
    path = interactive.attach(ROOT, tmp_path, {'experiment': 6, 'topics': [{'id': 't-74hc76'}]})
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
            hovered = page.locator('#trace-hover')
            details = page.locator('#trace-detail')
            event = page.locator('#event')
            circuit = page.locator('#circuit svg')
            t3 = page.locator('#truth-table [aria-current="true"]')
            shell = page.locator('#ec2-lab-root')
            left = page.get_by_role('button', name='조작 패널', exact=True)
            right = page.get_by_role('button', name='설명 패널', exact=True)

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
            page.get_by_role('radio', name='1 → 0').check()
            for name, q in [('CLK 0 유지', 0), ('CLK 올리기 ↑', 0), ('CLK 내리기 ↓', 1)]:
                page.get_by_role('button', name=name, exact=True).press('Enter')
                expect(event).to_contain_text(f'현재 Q={q}')
            expect(wave).to_have_attribute('aria-label', 'CLK 0, 0, 1, 0 / Q 0, 0, 0, 1')
            expect(t3).to_have_attribute('data-rule', 'jk11')
            expect(circuit.locator('[data-led="Q"]')).to_have_attribute('data-level', '1')
            expect(page.locator('#feedback')).to_contain_text('맞았어요')
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
            page.get_by_role('button', name='CLR 내리기 ↓').click()
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
                trace('Q', 1).hover()
                expect(hovered).to_contain_text('예측 후 공개')
                expect(hovered).not_to_contain_text('상승 엣지')
            expect(circuit.locator('[data-led="Q"]')).to_have_attribute('data-level', 'unknown')
            expect(circuit.locator('[data-pin="15"] [data-value]')).to_have_text('?')
            expect(t3).to_have_count(0)
            expect(page.get_by_role('button', name='예측 확인')).to_be_disabled()
            page.get_by_role('radio', name='② 하강 엣지').check()
            page.get_by_role('button', name='예측 확인').press('Enter')
            expect(wave).to_have_attribute('aria-label', 'CLK 0, 1, 0 / Q 0, 0, 1')
            expect(t3).to_have_attribute('data-rule', 'jk10')
            inspect('Q', 2)
            expect(details).to_contain_text('T3 · 세트')
            expect(page.locator('#feedback')).to_contain_text('맞았어요')
            open_left()
            page.get_by_role('button', name='이 단계 처음부터').press('Enter')
            close_left()
            expect(wave).to_have_attribute('aria-label', 'CLK 0, 1, 0 / Q 0, 나머지는 예측 후 공개')
            page.get_by_role('button', name='건너뛰기').click()
            expect(wave).to_have_attribute('aria-label', 'CLK 0 / Q 0')
            open_left()
            expect(page.get_by_role('button', name='CLK 입력')).to_be_enabled()
            close_left()
            expect(page.get_by_role('button', name='CLK 올리기 ↑', exact=True)).to_be_visible()
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
    shutil.copytree(ROOT / interactive.SKILL, skill)
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
    with pytest.raises(ValueError, match='검증을 마친 실험'):
        interactive.attach(repo, folder, manifest, reviewed_only=True)
    path = interactive.attach(repo, folder, manifest)
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
