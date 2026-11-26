(() => {
  const layout = document.querySelector('.layout');
  const wide = matchMedia('(min-width: 1024px)');
  const printing = matchMedia('print');
  const problems = new Map();

  for (const block of document.querySelectorAll('main [data-problem-reading]')) {
    const inline = document.createElement('details');
    inline.className = 'problem-inline';
    const summary = document.createElement('summary');
    summary.textContent = '문제 보기';
    block.before(inline);
    inline.append(summary, block);
    problems.set(block.dataset.problemReading, { block, inline, summary });
  }

  const panel = document.createElement('aside');
  panel.id = 'panel-prob';
  panel.className = 'panel';
  panel.hidden = true;
  panel.setAttribute('aria-labelledby', 'panel-prob-title');
  panel.innerHTML = `
    <div class="panel-inner">
      <div class="panel-head problem-panel-head">
        <button class="text-btn problem-panel-move" type="button" aria-label="문제 창 이동"
          title="끌거나 화살표로 이동, Shift와 화살표로 크기 조절" hidden>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path class="grip" d="M9 6h.01M15 6h.01M9 12h.01M15 12h.01M9 18h.01M15 18h.01"/></svg>
        </button>
        <h2 id="panel-prob-title">문제</h2>
        <div class="problem-panel-actions" role="group" aria-label="문제 패널 위치">
          <button class="text-btn" type="button" data-dock="left" aria-label="왼쪽에 붙이기" title="왼쪽에 붙이기">
            <svg viewBox="0 0 24 24" aria-hidden="true"><rect class="strip" x="3" y="4" width="7" height="16" rx="1"/><rect x="3" y="4" width="18" height="16" rx="3"/></svg>
          </button>
          <button class="text-btn" type="button" data-dock="right" aria-label="오른쪽에 붙이기" title="오른쪽에 붙이기">
            <svg viewBox="0 0 24 24" aria-hidden="true"><rect class="strip" x="14" y="4" width="7" height="16" rx="1"/><rect x="3" y="4" width="18" height="16" rx="3"/></svg>
          </button>
          <button class="text-btn" type="button" data-dock="float" aria-label="띄우기" title="띄우기">
            <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="3"/><rect class="strip" x="11" y="8" width="7" height="6" rx="1"/></svg>
          </button>
        </div>
      </div>
      <div class="problem-panel-body"></div>
    </div>
    <button class="problem-panel-resize" type="button" aria-label="문제 창 크기 조절"
      title="끌거나 화살표를 눌러 크기 조절" hidden></button>`;
  layout.querySelector('.content').before(panel);
  const workspace = panel.querySelector('.problem-panel-body');
  const move = panel.querySelector('.problem-panel-move');
  const head = panel.querySelector('.problem-panel-head');
  const sizer = panel.querySelector('.problem-panel-resize');
  const buttons = panel.querySelectorAll('[data-dock]');

  const toggle = document.createElement('button');
  toggle.id = 'toggle-prob';
  toggle.type = 'button';
  toggle.className = 'text-btn panel-toggle';
  toggle.textContent = '문제';
  toggle.hidden = true;
  toggle.setAttribute('aria-controls', panel.id);
  const tocToggle = document.getElementById('toggle-left');
  const summaryToggle = document.getElementById('toggle-right');
  const topbar = document.querySelector('.topbar');
  const pager = document.querySelector('.pager');

  let current;
  let mounted;
  let open = true;
  let dock;
  let floating;
  let endDrag;
  let printOpen;

  const clamp = (value, min, max) => Math.min(Math.max(value, min), Math.max(min, max));

  function bounds() {
    return {
      right: document.documentElement.clientWidth,
      top: Math.round(topbar.getBoundingClientRect().bottom),
      bottom: Math.round(pager.getBoundingClientRect().top),
    };
  }

  function placeFloating(request = floating) {
    const { right, top, bottom } = bounds();
    const available = Math.max(1, bottom - top);
    const width = clamp(request?.width ?? 420, Math.min(right, 280), right);
    const height = clamp(request?.height ?? Math.min(560, Math.round(innerHeight * 0.7)), Math.min(available, 200), available);
    const geometry = {
      x: clamp(request?.x ?? right - width - 24, 0, right - width),
      y: clamp(request?.y ?? top + 16, top, bottom - height),
      width,
      height,
    };
    for (const [key, value] of Object.entries(geometry)) panel.style.setProperty(`--problem-${key}`, `${value}px`);
    return geometry;
  }

  function resizeFloating(start, dx, dy) {
    const { right, bottom } = bounds();
    floating = placeFloating({
      ...start,
      width: Math.min(start.width + dx, right - start.x),
      height: Math.min(start.height + dy, bottom - start.y),
    });
  }

  function restoreProblem() {
    if (!mounted) return;
    mounted.inline.append(mounted.block);
    mounted.inline.hidden = false;
    mounted = undefined;
  }

  function sync() {
    const visible = Boolean(current) && wide.matches && !printing.matches;
    const show = visible && open;
    const previousFocus = panel.contains(document.activeElement);
    toggle.hidden = !visible;
    toggle.setAttribute('aria-expanded', String(show));
    panel.hidden = !show;
    if (show) layout.dataset.problemDock = dock;
    else delete layout.dataset.problemDock;
    if (dock === 'float') panel.setAttribute('role', 'dialog');
    else panel.removeAttribute('role');
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.dock === dock)));
    move.hidden = dock !== 'float';
    sizer.hidden = dock !== 'float';
    if (mounted && (!show || mounted !== current)) restoreProblem();
    if (show && !mounted) {
      current.inline.hidden = true;
      workspace.append(current.block);
      panel.querySelector('.panel-inner').scrollTop = 0;
      mounted = current;
    }
    if (show && dock === 'float') placeFloating();
    if (!show && previousFocus && !printing.matches) {
      if (visible) toggle.focus();
      else current?.summary.focus();
    }
  }

  function select(screen) {
    current = problems.get(screen?.id);
    sync();
  }

  toggle.addEventListener('click', () => {
    open = !open;
    sync();
  });
  function setDock(side) {
    dock = side;
    if (dock === 'right' && toggle.nextElementSibling !== summaryToggle) summaryToggle.before(toggle);
    else if (dock !== 'right' && toggle.previousElementSibling !== tocToggle) tocToggle.after(toggle);
    sync();
  }

  panel.querySelector('.problem-panel-actions').addEventListener('click', event => {
    const button = event.target.closest('[data-dock]');
    if (button) setDock(button.dataset.dock);
  });

  function trackPointer(handle, event, onMove, onEnd) {
    const { pointerId } = event;
    const drag = next => { if (next.pointerId === pointerId) onMove(next); };
    function stop(next) {
      if (next && next.pointerId !== pointerId) return;
      endDrag = undefined;
      handle.removeEventListener('pointermove', drag);
      for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) handle.removeEventListener(type, stop);
      if (handle.hasPointerCapture(pointerId)) handle.releasePointerCapture(pointerId);
      onEnd?.(next?.type === 'pointerup');
    }
    endDrag = stop;
    handle.setPointerCapture(pointerId);
    handle.addEventListener('pointermove', drag);
    for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) handle.addEventListener(type, stop);
  }

  head.addEventListener('pointerdown', event => {
    if (event.button !== 0 || endDrag || event.target.closest('button:not(.problem-panel-move)')) return;
    event.preventDefault();
    if (move.contains(event.target)) move.focus();
    let origin = event;
    let start = dock === 'float' ? placeFloating() : undefined;
    let snap;
    trackPointer(head, event, next => {
      const dx = next.clientX - origin.clientX;
      const dy = next.clientY - origin.clientY;
      if (!start) {
        if (Math.hypot(dx, dy) <= 24) return;
        floating = placeFloating({ ...floating, x: next.clientX - (floating?.width ?? 420) / 2, y: next.clientY - 20 });
        setDock('float');
        start = floating;
        origin = next;
      } else floating = placeFloating({ ...start, x: start.x + dx, y: start.y + dy });
      const { right, top, bottom } = bounds();
      snap = next.clientX <= 32 ? 'left' : next.clientX >= right - 32 ? 'right' : undefined;
      if (snap) {
        layout.dataset.problemSnap = snap;
        layout.style.setProperty('--problem-snap-top', `${top}px`);
        layout.style.setProperty('--problem-snap-height', `${bottom - top}px`);
      } else delete layout.dataset.problemSnap;
    }, dropped => {
      delete layout.dataset.problemSnap;
      if (dropped && snap) {
        const restoreFocus = document.activeElement === move;
        setDock(snap);
        if (restoreFocus) panel.querySelector(`[data-dock="${snap}"]`).focus();
      }
    });
  });

  sizer.addEventListener('pointerdown', event => {
    if (event.button !== 0 || endDrag) return;
    event.preventDefault();
    sizer.focus();
    const start = placeFloating();
    trackPointer(sizer, event, next => resizeFloating(start, next.clientX - event.clientX, next.clientY - event.clientY));
  });

  const directions = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
  function nudge(event, resize) {
    const direction = directions[event.key];
    if (!direction) return;
    event.preventDefault();
    const [dx, dy] = direction.map(value => value * (event.currentTarget === sizer && event.shiftKey ? 64 : 16));
    const start = placeFloating();
    if (resize) resizeFloating(start, dx, dy);
    else floating = placeFloating({ ...start, x: start.x + dx, y: start.y + dy });
  }
  move.addEventListener('keydown', event => nudge(event, event.shiftKey));
  sizer.addEventListener('keydown', event => nudge(event, true));

  document.addEventListener('od:screen', event => select(event.detail.screen));
  wide.addEventListener('change', () => endDrag?.());
  window.addEventListener('resize', sync);
  function preparePrint() {
    if (printOpen) return;
    restoreProblem();
    printOpen = Array.from(problems.values(), ({ inline }) => inline.open);
    for (const { inline } of problems.values()) inline.open = true;
  }
  function finishPrint() {
    if (!printOpen) return;
    Array.from(problems.values()).forEach(({ inline }, i) => { inline.open = printOpen[i]; });
    printOpen = undefined;
    sync();
  }
  window.addEventListener('beforeprint', preparePrint);
  window.addEventListener('afterprint', finishPrint);
  printing.addEventListener('change', event => {
    if (event.matches) preparePrint();
    else finishPrint();
  });
  setDock('right');
  select(document.querySelector('article.topic.is-current'));
})();
