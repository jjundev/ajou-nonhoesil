const byId = id => document.getElementById(id);
const lesson = JSON.parse(byId('lesson').textContent);
const pinByLabel = new Map(lesson.pins.map(pin => [pin.label, pin]));
const traceColors = new Map(lesson.traces.map((label, index) =>
  [label, 'var(--trace-' + (index + 1) + ', var(--accent-ink))']));
const outputs = lesson.pins.filter(pin => pin.role === 'output' && !pin.complement_of);
const traces = byId('traces');
const traceArea = traces.closest('.trace-area');
const traceStage = byId('stage');
const tracePopup = byId('trace-popup');
const traceClose = tracePopup.querySelector('button');
const traceAnnouncement = byId('trace-announcement');
const advance = byId('advance');
const submit = byId('submit');
const prediction = byId('prediction');
const predictionNext = byId('prediction-next');
const guidedPrediction = lesson.guided_prediction === true;
const feedback = byId('feedback');
const dip = byId('circuit').querySelector('[data-dip]');
const nets = new Map(Array.from(byId('circuit').querySelectorAll('[data-net]'), net => [net.dataset.net, net]));
const leds = byId('circuit').querySelectorAll('[data-led]');
const inputButtons = new Map();
const circuitPins = new Map();
const valueTiles = new Map();
const taskButtons = new Map();
const truthRows = new Map();
let task;
let history;
let cursor;
let probeOverrides;
let selectableProbes;
let visibleTraces;
let tracePin;
let tracePinned;
let activeTraceCell;
let hoveredTraceCell;
let hoverPoint;
let choice;
let predictionState;
let error;

function svgNode(tag, attrs, content = '') {
  const element = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.entries(attrs).forEach(([name, value]) => element.setAttribute(name, value));
  element.textContent = content;
  return element;
}

function button(label, handler) {
  const control = document.createElement('button');
  control.type = 'button';
  control.textContent = label;
  control.addEventListener('click', handler);
  return control;
}

function addPin(pin) {
  const half = lesson.pins.length / 2;
  const right = pin.number > half;
  const row = right ? lesson.pins.length - pin.number : pin.number - 1;
  const y = Number(dip.dataset.firstY) + row * Number(dip.dataset.pitch);
  const x = right ? dip.dataset.right : dip.dataset.left;
  const inward = right ? -1 : 1;
  const group = svgNode('g', {'data-pin': pin.number, transform: 'translate(' + x + ' ' + y + ')'});
  if (lesson.traces.includes(pin.label)) {
    const toggleProbe = () => {
      if (!selectableProbes.has(pin.label)) return;
      probeOverrides.set(pin.label, !visibleTraces.includes(pin.label));
      render();
    };
    group.append(svgNode('rect', {
      x: right ? -45 : -46, y: -24, width: 91, height: 48, rx: 4, class: 'pin-hit',
    }));
    group.addEventListener('click', toggleProbe);
    group.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleProbe();
      }
    });
  }
  if (pin.role === 'unused') group.classList.add('pin-unused');
  const value = svgNode('text', {
    'data-value': '', x: 32 * inward, y: 19, 'text-anchor': 'middle', class: 'pin-value',
  });
  group.append(
    svgNode('path', {class: 'fig-ink', d: 'M0 0H' + -22 * inward}),
    svgNode('text', {x: 14 * inward, y: 4, 'text-anchor': 'middle', class: 'pin-number'}, pin.number),
    svgNode('text', {
      x: -15 * inward, y: -8, 'text-anchor': right ? 'start' : 'end', class: 'fig-text',
    }, pin.label),
    value,
  );
  if (pin.active_low) group.append(svgNode('circle', {cx: 3 * inward, cy: 0, r: 3, class: 'fig-ink'}));
  circuitPins.set(pin.label, {group, value});
  dip.append(group);
}

for (let index = 0; index < lesson.pins.length / 2; index++) {
  addPin(lesson.pins[index]);
  addPin(lesson.pins[lesson.pins.length - index - 1]);
}

for (const pin of lesson.pins) {
  if (pin.role === 'input') {
    const control = button('', () => apply({
      pin: pin.label,
      value: 1 - history[cursor].state[pin.label],
    }, null));
    control.className = 'btn input-button';
    const label = document.createElement('strong');
    label.textContent = pin.label;
    const value = document.createElement('span');
    value.className = 'num';
    control.append(label, value);
    if (pin.active_low) {
      const polarity = document.createElement('small');
      polarity.textContent = '0에서 작동';
      control.append(polarity);
    }
    inputButtons.set(pin.label, {control, value});
    byId('inputs').append(control);
  }
  if (pin.role !== 'unused') {
    const tile = document.createElement('div');
    tile.className = 'tile';
    const label = document.createElement('span');
    label.textContent = pin.label + ' · ' + pin.number + '번';
    const value = document.createElement('b');
    valueTiles.set(pin.label, value);
    tile.append(label, value);
    byId('pin-values').append(tile);
  }
}

for (const [index, item] of lesson.tasks.entries()) {
  const tab = button('', () => {
    start(item);
    closeDrawer();
  });
  tab.className = 'btn';
  const number = document.createElement('span');
  number.className = 'step-num';
  number.setAttribute('aria-hidden', 'true');
  number.textContent = index + 1;
  tab.append(number, document.createTextNode(item.title));
  taskButtons.set(item.id, tab);
  byId('tasks').append(tab);
}

const table = byId('truth-table');
const tableHeader = table.createTHead().insertRow();
const tableBody = table.createTBody();
byId('truth-title').textContent = lesson.truth_table.title;
for (const column of lesson.truth_table.columns) {
  const cell = document.createElement('th');
  cell.scope = 'col';
  cell.textContent = column;
  tableHeader.append(cell);
}
for (const {id, cells, label} of lesson.truth_table.rows) {
  const row = tableBody.insertRow();
  row.dataset.rule = id;
  for (const cell of cells) row.insertCell().textContent = cell;
  truthRows.set(id, {row, label});
}

function initialFrame(item) {
  return {state: lesson.presets[item.id], reason: '실험의 시작 상태예요.', progress: 0};
}

function start(item) {
  task = item;
  history = [initialFrame(task)];
  if (task.challenge) {
    task.steps.forEach((action, i) => history.push(frame(history.at(-1), action, i + 1)));
  }
  cursor = 0;
  probeOverrides = new Map();
  tracePin = null;
  tracePinned = false;
  traceAnnouncement.textContent = '';
  choice = null;
  predictionState = 'open';
  error = '';
  traces.scrollLeft = 0;
  traceStage.scrollTop = 0;
  byId('task-title').textContent = item.title;
  byId('prompt').textContent = item.prompt;
  byId('options').replaceChildren(...item.options.map((label, index) => {
    const option = document.createElement('label');
    option.className = 'predict-btn';
    const input = document.createElement('input');
    input.type = 'radio';
    input.name = 'prediction';
    input.addEventListener('change', () => {
      choice = index;
      render();
    });
    option.append(input, label);
    return option;
  }));
  for (const [id, tab] of taskButtons) {
    if (id === item.id) tab.setAttribute('aria-current', 'step');
    else tab.removeAttribute('aria-current');
  }
  render();
}

function frame(previous, action, progress) {
  const result = transition(previous.state, action);
  const previousValue = previous.state[action.pin];
  const change = previousValue === action.value ? '유지' : action.value === 1 ? '↑' : '↓';
  const label = action.label ?? (action.pin + ' ' + change);
  const compactLabel = action.pin + ' ' + (change === '유지' ? action.value + ' 유지' : change);
  return {
    label,
    compactLabel: task.challenge ? label : compactLabel,
    pin: action.pin,
    previous: previous.state,
    state: result.next,
    reason: result.reason,
    rule: result.rule,
    accepted: result.accepted,
    progress,
  };
}

function apply(action, progress) {
  const next = frame(history[cursor], action, progress);
  if (next.accepted) {
    history.splice(cursor + 1, history.length, next);
    cursor += 1;
    tracePinned = false;
    traceAnnouncement.textContent = '';
    error = '';
  } else {
    error = next.reason;
  }
  render();
}

function selectFrame(index) {
  if (index < 0 || index >= history.length || index === cursor) return;
  cursor = index;
  error = '';
  render();
}

function isPreview() {
  return task.challenge && predictionState === 'open';
}

function freeToggleAction(current) {
  const pin = lesson.free_toggle_pin;
  if (current.progress !== null || !pin || isPreview()) return null;
  const value = 1 - current.state[pin];
  const label = pin + (value === 1 ? ' 올리기 ↑' : ' 내리기 ↓');
  return {pin, value, label};
}

byId('reset').addEventListener('click', () => start(task));
byId('previous').addEventListener('click', () => selectFrame(cursor - 1));
byId('next').addEventListener('click', () => selectFrame(cursor + 1));
traces.addEventListener('keydown', event => {
  if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
    event.preventDefault();
    selectFrame(cursor + (event.key === 'ArrowLeft' ? -1 : 1));
    announceTrace();
  } else if (visibleTraces.length && (event.key === 'ArrowUp' || event.key === 'ArrowDown')) {
    event.preventDefault();
    const row = visibleTraces.indexOf(tracePin) + (event.key === 'ArrowUp' ? -1 : 1);
    tracePin = visibleTraces[Math.max(0, Math.min(row, visibleTraces.length - 1))];
    renderTraceSelection();
    announceTrace();
  } else if (tracePin && (event.key === 'Enter' || event.key === ' ')) {
    event.preventDefault();
    inspectTrace(tracePin, cursor);
  }
});
traces.addEventListener('click', event => {
  const cell = event.target.closest('[data-trace-pin]');
  if (cell) {
    inspectTrace(cell.dataset.tracePin, Number(cell.dataset.traceIndex));
    return;
  }
  const marker = event.target.closest('[data-frame]');
  if (marker) {
    selectFrame(Number(marker.dataset.frame));
    traces.focus({preventScroll: true});
  }
});
traceArea.addEventListener('pointermove', event => {
  if (event.pointerType !== 'mouse' && event.pointerType !== 'pen') return;
  hoverPoint = {x: event.clientX, y: event.clientY};
  updateTraceHover(event.target);
});
traceArea.addEventListener('pointerleave', hideTraceHover);
traces.addEventListener('scroll', repositionTracePopup);
traceStage.addEventListener('scroll', repositionTracePopup);
traceClose.addEventListener('click', () => {
  closeTracePopup();
  traces.focus({preventScroll: true});
});
document.addEventListener('keydown', event => {
  if (event.key !== 'Escape' || event.defaultPrevented) return;
  hideTraceHover();
  if (tracePinned) {
    const returnFocus = tracePopup.contains(document.activeElement);
    closeTracePopup();
    if (returnFocus) traces.focus({preventScroll: true});
  }
});
function revealPrediction(state) {
  predictionState = state;
  cursor = history.length - 1;
  render();
  traces.focus({preventScroll: true});
}

byId('skip').addEventListener('click', () => {
  if (isPreview()) {
    if (guidedPrediction) {
      revealPrediction('dismissed');
      traces.scrollIntoView({block: 'nearest', inline: 'nearest'});
      return;
    }
    history = [{...initialFrame(task), progress: null}];
    cursor = 0;
    tracePinned = false;
    traceAnnouncement.textContent = '';
  }
  predictionState = 'dismissed';
  render();
  traces.focus({preventScroll: true});
});
submit.addEventListener('click', () => revealPrediction('revealed'));
advance.addEventListener('click', () => {
  if (advance.hidden) return;
  const current = history[cursor];
  const toggle = freeToggleAction(current);
  apply(toggle ?? task.steps[current.progress], toggle ? null : current.progress + 1);
  if (advance.hidden) traces.focus({preventScroll: true});
});

function signalValue(state, label) {
  const pin = pinByLabel.get(label);
  if (pin.role === 'power') return pin.value;
  if (pin.role === 'unused') return '';
  return pin.complement_of ? 1 - state[pin.complement_of] : state[label];
}

function renderProbes() {
  const defaults = task.probes ?? lesson.default_probes;
  const changedInputs = new Set(history.filter(({pin, previous, state}) =>
    pin && previous[pin] !== state[pin]).map(({pin}) => pin));
  selectableProbes = new Set(lesson.traces.filter(label =>
    pinByLabel.get(label).role === 'output' || changedInputs.has(label)));
  for (const label of probeOverrides.keys()) {
    if (!selectableProbes.has(label)) probeOverrides.delete(label);
  }
  visibleTraces = lesson.traces.filter(label =>
    probeOverrides.get(label) ?? (defaults.includes(label) || changedInputs.has(label)));

  const fixed = [];
  for (const {label, role} of lesson.pins) {
    if (role === 'input' && !visibleTraces.includes(label) && !changedInputs.has(label)) {
      fixed.push(label + '=' + history[0].state[label]);
    }
  }
  byId('fixed-values').textContent = fixed.join(' · ');
  byId('fixed-inputs').hidden = fixed.length === 0;

  if (!visibleTraces.includes(tracePin)) {
    tracePinned = false;
    tracePin = visibleTraces.find(label => pinByLabel.get(label).role === 'output') ?? visibleTraces[0] ?? null;
  }
}

function describeTrace(label, index) {
  const pin = pinByLabel.get(label);
  const heading = pin.number + '번 핀 ' + label;
  const current = history[index];
  if (pin.role === 'output' && isPreview() && index > 0) {
    return {value: heading + ' · ?', reason: '예측 후 공개'};
  }
  const value = signalValue(current.state, label);
  if (!current.previous) return {value: heading + ' = ' + value, reason: current.reason};

  const previous = signalValue(current.previous, label);
  const changed = previous !== value;
  const title = heading + (changed ? ' ' + previous + ' → ' + value : ' = ' + value);
  if (pin.role === 'input') {
    let reason = '이 조작에서 입력은 이전 값 ' + value + '을 유지해요.';
    if (current.pin === label) {
      reason = changed ? '이 조작에서 ' + label + ' 입력을 ' + value + '로 바꿨어요.'
        : label + ' 입력을 ' + value + '에 그대로 뒀어요.';
    }
    if (pin.active_low) reason += ' ' + label + '은 ' + (value === 0 ? '작동' : '비활성') + ' 상태예요.';
    return {value: title, reason};
  }

  let reason = current.reason;
  const actionPin = pinByLabel.get(current.pin);
  if (actionPin?.active_low && current.previous[actionPin.label] === 0 && current.state[actionPin.label] === 1) {
    reason = actionPin.label + '이 1로 올라가 비활성 상태가 됐어요. ' + reason;
  }
  if (pin.complement_of) {
    reason += ' ' + label + '는 ' + pin.complement_of + '와 반대 값이에요.';
  }
  const match = truthRows.get(current.rule);
  const truth = match && (match.label && lesson.truth_table.reference
    ? lesson.truth_table.reference + ' · ' + match.label : lesson.truth_table.title);
  return {value: title, reason, truth};
}

function traceStep(index) {
  return index === 0 ? '시작' : '조작 ' + index + ' · ' + history[index].label;
}

function showTracePopup(label, index, pinned) {
  const {value, reason, truth} = describeTrace(label, index);
  tracePopup.style.setProperty('--signal-color', traceColors.get(label));
  tracePopup.querySelector('[data-trace-value]').textContent = value;
  tracePopup.querySelector('[data-trace-step]').textContent = traceStep(index);
  tracePopup.querySelector('[data-trace-reason]').textContent = reason;
  const reference = tracePopup.querySelector('[data-trace-truth]');
  reference.textContent = truth ?? '';
  reference.hidden = !truth;
  if (pinned) tracePopup.removeAttribute('aria-hidden');
  else tracePopup.setAttribute('aria-hidden', 'true');
  traceClose.hidden = !pinned;
  tracePopup.hidden = false;
}

function updateTraceHover(target, reposition = false) {
  if (tracePinned || !hoverPoint) return;
  const cell = target?.closest('[data-trace-pin]');
  if (!cell) {
    hideTraceHover();
    return;
  }
  if (cell === hoveredTraceCell && !reposition) return;
  if (cell !== hoveredTraceCell) {
    showTracePopup(cell.dataset.tracePin, Number(cell.dataset.traceIndex), false);
    hoveredTraceCell = cell;
  }
  positionTracePopup(hoverPoint.x);
}

function positionTracePopup(x) {
  const graph = traces.getBoundingClientRect();
  const stage = traceStage.getBoundingClientRect();
  const height = tracePopup.offsetHeight;
  const below = stage.bottom - graph.bottom;
  const above = graph.top - stage.top;
  const preferred = below < height && above > below ? -height : graph.height;
  tracePopup.style.left = Math.max(0, Math.min(x - graph.left, graph.width - tracePopup.offsetWidth)) + 'px';
  tracePopup.style.top = Math.max(-above, Math.min(preferred, graph.height + below - height)) + 'px';
}

function repositionTracePopup() {
  if (tracePinned && activeTraceCell) {
    const cell = activeTraceCell.getBoundingClientRect();
    positionTracePopup(cell.left + cell.width / 2);
  } else if (hoverPoint) {
    updateTraceHover(document.elementFromPoint(hoverPoint.x, hoverPoint.y), true);
  }
}

function hideTraceHover() {
  if (!tracePinned) tracePopup.hidden = true;
  hoveredTraceCell = null;
  hoverPoint = null;
}

function renderTraceSelection() {
  activeTraceCell?.classList.remove('is-active', 'is-inspected');
  activeTraceCell = tracePin && traces.querySelector(
    '[data-trace-pin="' + CSS.escape(tracePin) + '"][data-trace-index="' + cursor + '"]'
  );
  activeTraceCell?.classList.add('is-active');
  if (activeTraceCell && tracePinned) {
    activeTraceCell.classList.add('is-inspected');
    showTracePopup(tracePin, cursor, true);
    repositionTracePopup();
  } else if (!hoveredTraceCell) tracePopup.hidden = true;
}

function announceTrace() {
  if (!tracePin) return;
  if (tracePinned) {
    const {value, reason, truth} = describeTrace(tracePin, cursor);
    traceAnnouncement.textContent = [value, traceStep(cursor), reason, truth].filter(Boolean).join('. ');
  } else {
    traceAnnouncement.textContent = tracePin + ' 파형';
  }
}

function inspectTrace(label, index) {
  tracePin = label;
  tracePinned = true;
  hideTraceHover();
  if (index === cursor) renderTraceSelection();
  else selectFrame(index);
  traces.focus({preventScroll: true});
  announceTrace();
}

function closeTracePopup() {
  tracePinned = false;
  hideTraceHover();
  traceAnnouncement.textContent = '';
  renderTraceSelection();
}

function renderCircuit(current, preview) {
  for (const [label, {group, value}] of circuitPins) {
    const pin = pinByLabel.get(label);
    const hidden = preview && pin.role === 'output';
    const shown = hidden ? '?' : signalValue(current.state, label);
    value.textContent = pin.role === 'power' ? '' : shown;
    if (valueTiles.has(label)) valueTiles.get(label).textContent = shown;
    const probed = visibleTraces.includes(label);
    if (selectableProbes.has(label)) {
      group.setAttribute('role', 'button');
      group.setAttribute('tabindex', '0');
      group.setAttribute('aria-label', pin.number + '번 ' + label + ' 프로브');
      group.setAttribute('aria-pressed', probed);
    } else {
      for (const attribute of ['role', 'tabindex', 'aria-label', 'aria-pressed']) group.removeAttribute(attribute);
    }
    group.classList.toggle('is-probed', probed);
    const net = nets.get(label);
    net?.classList.toggle('is-probed', probed);
    const changedOutput = pin.role === 'output' && !hidden && current.previous
      && signalValue(current.previous, label) !== shown;
    const eventPin = current.pin === label || Boolean(changedOutput);
    group.classList.toggle('is-event', eventPin);
    net?.classList.toggle('is-event', eventPin);
  }
  for (const led of leds) {
    led.dataset.level = preview ? 'unknown' : signalValue(current.state, led.dataset.led);
  }
}

function render() {
  const current = history[cursor];
  const preview = isPreview();
  byId('input-error').textContent = error;
  byId('input-error').hidden = !error;
  renderProbes();
  renderCircuit(current, preview);
  for (const [label, {control, value}] of inputButtons) {
    value.textContent = current.state[label];
    control.setAttribute('aria-label', label + ' 입력, 현재 ' + current.state[label]);
    control.disabled = preview;
  }

  const complete = current.progress === task.steps.length;
  const graded = task.challenge ? predictionState === 'revealed' : complete;
  prediction.hidden = predictionState === 'dismissed';
  let skipLabel = '건너뛰기';
  if (guidedPrediction) skipLabel = preview ? '예측 없이 파형 보기' : '예측 건너뛰기';
  byId('skip').textContent = graded ? '닫기' : skipLabel;
  byId('choices').disabled = graded;
  submit.hidden = !preview;
  submit.disabled = choice === null;
  if (guidedPrediction) submit.textContent = '파형 펼쳐서 확인';
  const step = task.challenge ? undefined : task.steps[current.progress];
  const action = freeToggleAction(current) ?? step;
  advance.hidden = !action;
  advance.textContent = action?.label ?? '';
  if (guidedPrediction) {
    const hint = step && choice !== null && !prediction.hidden
      ? '파형에서 ‘' + action.label + '’를 눌러보세요.'
      : '';
    predictionNext.hidden = !hint;
    if (predictionNext.textContent !== hint) predictionNext.textContent = hint;
  }
  feedback.hidden = !graded || choice === null;
  feedback.textContent = feedback.hidden ? '' : (choice === task.answer ? '맞았어요. ' : '') + task.feedback;
  feedback.classList.toggle('is-wrong', choice !== task.answer);

  byId('previous').disabled = cursor === 0;
  byId('next').disabled = cursor >= history.length - 1;
  byId('position').textContent = cursor + ' / ' + (history.length - 1);
  const currentOutputs = outputs.map(pin => pin.label + '=' + current.state[pin.label]).join(', ');
  const previewMessage = guidedPrediction
    ? '답을 고른 뒤 ‘파형 펼쳐서 확인’을 누르거나 ‘예측 없이 파형 보기’를 누르세요.'
    : '예측을 제출하면 출력 파형이 펼쳐져요.';
  byId('event').textContent = preview ? previewMessage :
    (error || current.reason) + ' 현재 ' + currentOutputs + '.';
  for (const [id, {row}] of truthRows) {
    if (!preview && current.rule === id) row.setAttribute('aria-current', 'true');
    else row.removeAttribute('aria-current');
  }
  drawTraces();
}

function drawTraces() {
  hideTraceHover();
  if (visibleTraces.length === 0) {
    const message = document.createElement('p');
    message.textContent = '칩 핀을 선택해 파형을 표시하세요.';
    traces.replaceChildren(message);
    renderTraceSelection();
    return;
  }
  const preview = isPreview();
  const width = Math.max(traces.clientWidth, 64 + history.length * 65);
  const interval = (width - 64) / history.length;
  const x = i => 48 + interval * i;
  const compact = narrowLayout.matches;
  const rowHeight = compact ? 44 : 34;
  const height = visibleTraces.length * rowHeight + 36;
  const diagram = svgNode('svg', {viewBox: '0 0 ' + width + ' ' + height, role: 'img'});
  diagram.style.minWidth = width + 'px';
  const description = [];
  for (let i = 0; i < history.length; i++) {
    const highlight = i === cursor;
    const marker = history[i];
    const label = i === 0 ? '시작' : (compact ? marker.compactLabel : marker.label);
    diagram.append(
      svgNode('line', {x1: x(i), x2: x(i), y1: 24, y2: height - 7, class: highlight ? 'cursor' : 'grid'}),
      svgNode('text', {x: x(i) + 5, y: 17, class: highlight ? 'fig-muted marker' : 'fig-muted'},
        label),
    );
  }
  visibleTraces.forEach((label, row) => {
    const signal = svgNode('g', {'data-signal': label});
    signal.style.setProperty('--signal-color', traceColors.get(label));
    const top = 26 + row * rowHeight;
    const mid = top + rowHeight / 2;
    const y = value => mid + (value === 1 ? -8 : 8);
    signal.append(
      svgNode('text', {x: 9, y: mid + 4, class: 'fig-text signal-label'}, label),
      svgNode('line', {x1: x(0), x2: x(history.length), y1: mid + 13, y2: mid + 13, class: 'grid'}),
    );
    const masked = preview && pinByLabel.get(label).role === 'output';
    const values = (masked ? history.slice(0, 1) : history).map(({state}) => signalValue(state, label));
    let path = 'M ' + x(0) + ' ' + y(values[0]);
    values.forEach((value, index) => {
      if (index > 0) path += ' V ' + y(value);
      path += ' H ' + x(index + 1);
    });
    signal.append(svgNode('path', {d: path, class: 'signal'}));
    if (masked) {
      for (let i = 1; i < history.length; i++) {
        signal.append(svgNode('text', {x: x(i) + 8, y: mid + 4, class: 'fig-muted'}, '?'));
      }
    }
    description.push(label + ' ' + values.join(', ') + (masked ? ', 나머지는 예측 후 공개' : ''));
    for (let i = 0; i < history.length; i++) {
      signal.append(svgNode('rect', {
        'data-trace-pin': label, 'data-trace-index': i, x: x(i), y: top, width: interval, height: rowHeight,
        class: 'trace-cell', 'aria-hidden': 'true',
      }));
    }
    diagram.append(signal);
  });
  for (let i = 0; i < history.length; i++) {
    diagram.append(svgNode('rect', {'data-frame': i, x: x(i), y: 0, width: interval, height: 26, 'aria-hidden': 'true'}));
  }
  diagram.setAttribute('aria-label', description.join(' / '));
  traces.replaceChildren(diagram);
  const left = x(cursor);
  const right = x(cursor + 1);
  if (cursor === 0) traces.scrollLeft = 0;
  else if (left < traces.scrollLeft + 8) traces.scrollLeft = left - 24;
  else if (right > traces.scrollLeft + traces.clientWidth - 8) {
    traces.scrollLeft = right - traces.clientWidth + 8;
  }
  renderTraceSelection();
}

start(lesson.tasks[0]);
let traceWidth = traces.clientWidth;
new ResizeObserver(() => {
  if (traces.clientWidth === traceWidth) return;
  traceWidth = traces.clientWidth;
  drawTraces();
}).observe(traces);
narrowLayout.addEventListener('change', drawTraces);
