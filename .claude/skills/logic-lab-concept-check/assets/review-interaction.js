(function (scope) {
  'use strict';
  function stripDiagnosticPrefix(text, id) {
    const match = text.match(/^\s*(?:\((\d+)\)|([A-Z])[.)])\s*/);
    return match && (match[1] || match[2]) === id ? text.slice(match[0].length) : text;
  }
  function scrollAnswerIntoView(scroller, selectedLi, answerLi, selectedButton, answerButton) {
    if (!scroller || !selectedLi.getClientRects().length) return;
    const viewport = scroller.getBoundingClientRect();
    const height = scroller.clientHeight;
    const margin = 16;
    const span = (a, b) => {
      const x = a.getBoundingClientRect(), y = b.getBoundingClientRect();
      return {top:Math.min(x.top, y.top), bottom:Math.max(x.bottom, y.bottom)};
    };
    let target = span(selectedLi, answerLi);
    if (target.bottom - target.top > height - 2 * margin)
      target = span(selectedButton, answerButton);
    if (target.bottom - target.top > height - 2 * margin)
      target = span(selectedButton, selectedButton);
    scroller.scrollTop += (target.top + target.bottom - viewport.top - viewport.bottom) / 2;
  }
  function grade(card, selected) {
// short-support:start
    if (card.format === 'short') {
      if (typeof selected !== 'string' || !selected.trim()) return null;
      const normalize = value => {
        const text = value.normalize('NFC').trim();
        return card.answer.case_sensitive ? text : Array.from(text).map(c => (scope.ReviewShortCasefold || {})[c] ?? c.toLowerCase()).join('');
      };
      return [card.answer.canonical, ...card.answer.accepted].some(x => normalize(x) === normalize(selected)) ? 'correct' : 'pending';
    }
// short-support:end
    if (!card.options.some(o => o.id === selected)) return null;
    if (card.mode === 'ambiguous') return 'ambiguous';
    return selected === card.answer ? 'correct' : 'incorrect';
  }
  function storageKey(documentId, cardId) {
    return 'od-review-attempt:v1:' + encodeURIComponent(documentId) + ':' + encodeURIComponent(cardId);
  }
  function readAttempt(storage, key, card) {
    try {
      const value = JSON.parse(storage.getItem(key));
      return value && value.version === card.version && grade(card, value.selected) !== null ? value.selected : null;
    } catch { return null; }
  }
  function readUnsure(storage, key, card) {
    try {
      const value = JSON.parse(storage.getItem(key));
      return !!value && value.version === card.version && grade(card, value.selected) === 'correct' && value.unsure === true;
    } catch { return false; }
  }
  function writeAttempt(storage, key, card, selected, unsure) {
    try {
      if (selected === null) storage.removeItem(key);
      else storage.setItem(key, JSON.stringify({version:card.version, selected, unsure:unsure === true}));
    } catch {}
  }
  function promptApi(scope) {
    if (scope && scope.ReviewPrompt) return scope.ReviewPrompt;
    if (typeof require === 'function') {
      try { return require('./review-prompt.js'); } catch {}
    }
    return null;
  }
  // Capture plain text before enhancement moves nodes or adds badges.
  function captureCardText(card, choices, diagnostics, options, solution) {
    const prompt = promptApi(card.ownerDocument && card.ownerDocument.defaultView);
    const read = el => !el ? '' : prompt ? prompt.problemText(el) : el.textContent.replace(/\s+/g, ' ').trim();
    const heading = card.querySelector('h3');
    const problem = card.querySelector('.problem');
    const list = Array.isArray(options) ? options : [];
    const used = new Set(list.map(o => o.diagnostic));
    const texts = {
      // The prompt already prints the card id, so drop the "P1." label from the heading.
      title: heading ? heading.textContent.replace(/\s+/g, ' ').trim().replace(/^P\d+\.\s*/i, '') : '',
      stem: read(problem),
      options: list.map(o => ({id:o.id, text:stripDiagnosticPrefix(read(choices[o.index]).trim(), o.id)})),
      diagnostics: {},
      extras: diagnostics.filter((_, i) => !used.has(i)).map(read).filter(Boolean)
    };
    list.forEach(o => { texts.diagnostics[o.id] = stripDiagnosticPrefix(read(diagnostics[o.diagnostic]).trim(), o.id); });
    return texts;
  }
  function buildPromptRecord(model, texts, ids, selectedById, unsureById, range) {
    const items = ids.map(id => {
      const data = model.cards[id];
      const t = texts[id] || {title:'', stem:'', options:[], diagnostics:{}, extras:[]};
      const raw = selectedById[id];
      const result = grade(data, raw);
// short-support:start
      if (data.format === 'short') return {
        id, title:t.title, stem:t.stem, format:'short', options:[], selected:result === null ? null : raw,
        answer:data.answer.canonical, accepted:data.answer.accepted, status:result === null ? 'unanswered' : result,
        explanations:t.extras.map(text => ({label:'풀이', text}))
      };
// short-support:end
      const selected = result === null ? null : raw;
      const status = result === null ? 'unanswered'
        : result === 'correct' && unsureById && unsureById[id] === true ? 'unsure' : result;
      const diagnostic = optionId => (t.diagnostics || {})[optionId] || '';
      const explanations = [];
      if (selected !== null && selected !== data.answer)
        explanations.push({label:'내 선택 [' + selected + ']', text:diagnostic(selected)});
      explanations.push({label:(data.mode === 'ambiguous' ? '출제 의도상 답 [' : '정답 [') + data.answer + ']',
        text:diagnostic(data.answer)});
      (t.extras || []).forEach(text => explanations.push({label:'', text}));
      if (data.notice) explanations.push({label:'출제 주의', text:data.notice});
      return {id, title:t.title, stem:t.stem, format:'mcq', options:t.options, selected,
        answer:data.answer, accepted:null, status, explanations};
    });
    return {kind:'review', documentId:model.documentId, range:range || '', items};
  }
  function mount(root, model, storage) {
    if (!model || model.schema !== 1 || !model.cards) return;
    const win = root.defaultView;
    const emit = (id, selected, result, restored = false) => root.dispatchEvent(
      new win.CustomEvent('od:answer', {detail:{id, selected, result, restored}}));
    const element = (tag, cls, text) => {
      const el = root.createElement(tag);
      el.className = cls;
      if (text !== undefined) el.textContent = text;
      return el;
    };
    const selectedById = {};
    const unsureById = {};
    const texts = {};
    let feedback = null;
    let feedbackTimer = null;
    let feedbackOwner = null;
    function clearFeedback(owner = null) {
      if (owner !== null && owner !== feedbackOwner) return;
      if (feedbackTimer !== null) win.clearTimeout(feedbackTimer);
      feedbackTimer = null;
      if (feedback) feedback.remove();
      feedback = null;
      feedbackOwner = null;
    }
    function showFeedback(result, id, message, duration) {
      clearFeedback();
      if (!message && result !== 'correct' && result !== 'incorrect') return;
      feedback = element('div', 'review-feedback');
      feedback.dataset.reviewFeedback = '';
      feedback.dataset.result = result;
      if (result === 'copied') feedback.setAttribute('role', 'status');
      else feedback.setAttribute('aria-hidden', 'true');
      feedback.append(
        element('span', 'review-feedback-icon'),
        element('span', 'review-feedback-text', message || (result === 'correct' ? '정답이에요' : '다시 확인해요'))
      );
      root.body.append(feedback);
      feedbackOwner = id;
      feedbackTimer = win.setTimeout(clearFeedback, duration || 1100);
    }
    const UNSURE_ICON_OFF = '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/></svg>';
    const UNSURE_ICON_ON = '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.8 2.8L16 10"/></svg>';
    for (const [id, data] of Object.entries(model.cards)) {
      const card = root.getElementById(id);
      if (!card || card.classList.contains('review-ready')) continue;
      const aid = Array.from(root.querySelectorAll('.aid')).find(n => n.dataset.cardId === id);
      const solution = (aid || card).querySelector('details.solution');
      const choices = Array.from(card.querySelectorAll('.choices > li'));
      const diagnostics = solution ? Array.from(solution.querySelectorAll('ol.steps > li')) : [];
      const options = data.options;
      try { texts[id] = captureCardText(card, choices, diagnostics, options, solution); } catch {}
// short-support:start
      if (data.format === 'short' && solution) {
        const input = card.querySelector('input[type=text]');
        const check = card.querySelector('.check-answer');
        if (!input || !check) continue;
        texts[id].extras = diagnostics.map(n => n.textContent.replace(/\s+/g, ' ').trim());
        const status = element('p', 'review-status'); status.setAttribute('role', 'status');
        const reset = element('button', 'review-reset text-btn', '다시 풀기'); reset.type = 'button';
        card.querySelector('.short-input').append(status, reset);
        input.value = ''; input.autocomplete = 'off';
        selectedById[id] = null;
        solution.hidden = true; reset.hidden = true;
        const reveal = () => {
          if (!input.value.trim() || input.disabled) return;
          selectedById[id] = input.value;
          const result = grade(data, input.value);
          input.disabled = true; check.hidden = true; reset.hidden = false;
          status.textContent = result === 'correct' ? '자동 일치' : '자기채점 대기';
          solution.hidden = false; solution.open = true;
          emit(id, input.value, result);
        };
        check.addEventListener('click', reveal);
        input.addEventListener('keydown', e => {if (e.key === 'Enter') {e.preventDefault(); reveal();}});
        reset.addEventListener('click', () => {
          selectedById[id] = null; input.disabled = false; input.value = '';
          check.hidden = false; reset.hidden = true; status.textContent = '';
          solution.hidden = true; solution.open = false;
          emit(id, null, null); input.focus();
        });
        card.classList.add('review-ready');
        continue;
      }
// short-support:end
      // Validate every reference before moving a single original node.
      if (!solution || !Array.isArray(options) || choices.length !== options.length ||
          !options.length || !options.some(o => o.id === data.answer) ||
          new Set(options.map(o => o.index)).size !== options.length ||
          new Set(options.map(o => o.diagnostic)).size !== options.length ||
          options.some(o => !choices[o.index] || !diagnostics[o.diagnostic])) continue;
      const positions = diagnostics.map(n => ({node:n, parent:n.parentNode, next:n.nextSibling}));
      const diagnosticTexts = [];
      const choiceNodes = choices.map(n => Array.from(n.childNodes));
      const summary = solution.querySelector('summary');
      const summaryText = summary ? summary.textContent : '';
      const originalOpen = solution.open;
      const originalHidden = solution.hidden;
      let status, reset, notice, unsureBtn;
      try {
        // Some future cards supply the caution only as metadata. Keep its full
        // explanation in the solution panel, without duplicating existing prose.
        const compact = text => text.replace(/\s+/g, '');
        if (data.mode === 'ambiguous' && data.notice &&
            !compact(solution.textContent).includes(compact(data.notice))) {
          notice = element('p', 'review-notice', data.notice);
          solution.append(notice);
        }
        const controls = options.map(o => {
          const li = choices[o.index];
          const button = element('button', 'review-choice');
          button.type = 'button';
          const complex = li.querySelector('a,button,input,select,textarea,table,div,p,figure,ul,ol');
          if (complex) {
            button.textContent = o.id + '번 선택';
            const content = element('div', 'review-choice-content');
            content.id = id + '-choice-content-' + o.index;
            content.append(...Array.from(li.childNodes));
            button.setAttribute('aria-describedby', content.id);
            li.append(button, content);
          } else {
            button.append(...Array.from(li.childNodes));
            li.append(button);
          }
          const badge = element('span', 'review-choice-label');
          badge.hidden = true;
          button.append(badge);
          button.setAttribute('aria-pressed', 'false');
          const list = element('ol', 'review-diagnostics');
          list.id = id + '-review-diagnostics-' + o.index;
          const diagnostic = diagnostics[o.diagnostic];
          const first = diagnostic.firstChild;
          if (first && first.nodeType === 3) {
            diagnosticTexts.push({node:first, text:first.textContent});
            first.textContent = stripDiagnosticPrefix(first.textContent, o.id);
          }
          diagnostic.classList.add('review-diagnostic');
          diagnostic.hidden = true;
          list.append(diagnostic);
          li.append(list);
          return {id:o.id, button, badge, diagnostic, list};
        });
        status = element('p', 'review-status');
        status.setAttribute('role', 'status');
        status.setAttribute('aria-live', 'polite');
        reset = element('button', 'review-reset text-btn', '다시 풀기');
        reset.type = 'button';
        card.querySelector('.choices').before(status);
        card.querySelector('.choices').after(reset);
        const key = storageKey(model.documentId, id);
        let selected = readAttempt(storage, key, data);
        let unsure = selected !== null && readUnsure(storage, key, data);
        selectedById[id] = selected;
        unsureById[id] = unsure;
        unsureBtn = element('button', 'review-unsure solved-btn');
        unsureBtn.type = 'button';
        // Same look and place as the 푼 문제 button: bottom of the aid panel.
        (aid || solution).append(unsureBtn);
        const expanded = new Set(selected === null ? [] : [selected, data.answer]);
        function paintDisclosure(c) {
          const answered = selected !== null;
          const open = answered && expanded.has(c.id);
          c.diagnostic.hidden = !open;
          c.list.hidden = !open;
          if (answered) {
            c.button.setAttribute('aria-expanded', String(open));
            c.button.setAttribute('aria-controls', c.list.id);
          } else {
            c.button.removeAttribute('aria-expanded');
            c.button.removeAttribute('aria-controls');
          }
        }
        function paint() {
          const answered = selected !== null;
          const result = grade(data, selected);
          reset.hidden = !answered;
          unsureBtn.hidden = result !== 'correct';
          unsureBtn.innerHTML = (unsure ? UNSURE_ICON_ON : UNSURE_ICON_OFF) +
            '<span>' + (unsure ? '애매함 표시 취소' : '애매함으로 표시') + '</span>';
          unsureBtn.setAttribute('aria-pressed', String(unsure));
          unsureBtn.dataset.unsure = String(unsure);
          status.textContent = !answered ? '' : result === 'ambiguous'
            ? '단일 정답 판정 주의'
            : result === 'correct' ? '정답이에요.' : '정답이 아니에요. 보기별 이유를 확인해 보세요.';
          status.dataset.result = result || '';
          controls.forEach(c => {
            c.button.dataset.selected = String(c.id === selected);
            if (answered) c.button.removeAttribute('aria-pressed');
            else c.button.setAttribute('aria-pressed', 'false');
            c.button.dataset.result = !answered ? '' : c.id === data.answer
              ? (data.mode === 'ambiguous' ? 'intended' : 'correct')
              : c.id === selected ? (data.mode === 'ambiguous' ? 'uncertain' : 'selected') : '';
            c.badge.hidden = !answered;
            c.badge.textContent = !answered ? '' : [
              c.id === selected ? '내 선택' : '',
              c.id === data.answer ? (data.mode === 'ambiguous' ? '출제 의도상 답' : '정답')
                : data.mode === 'single' ? '정답 아님' : ''
            ].filter(Boolean).join(' · ');
            paintDisclosure(c);
          });
          solution.hidden = !answered;
          solution.open = answered;
          if (summary) summary.textContent = '추가 해설 · 수업과의 연결';
        }
        controls.forEach(c => c.button.addEventListener('click', () => {
          if (selected !== null) {
            if (expanded.has(c.id)) expanded.delete(c.id);
            else expanded.add(c.id);
            paintDisclosure(c);
            return;
          }
          selected = c.id;
          selectedById[id] = selected;
          unsure = false;
          unsureById[id] = false;
          expanded.add(selected);
          expanded.add(data.answer);
          writeAttempt(storage, key, data, selected);
          paint();
          emit(id, selected, grade(data, selected));
          showFeedback(grade(data, selected), id);
          const selectedOption = options.find(o => o.id === selected);
          const answerOption = options.find(o => o.id === data.answer);
          const selectedControl = controls.find(control => control.id === selected);
          const answerControl = controls.find(control => control.id === data.answer);
          win.requestAnimationFrame(() => {
            if (!card.isConnected || !card.getClientRects().length) return;
            scrollAnswerIntoView(root.querySelector('.content'),
              choices[selectedOption.index], choices[answerOption.index],
              selectedControl.button, answerControl.button);
          });
        }));
        reset.addEventListener('click', () => {
          clearFeedback(id);
          selected = null;
          selectedById[id] = null;
          unsure = false;
          unsureById[id] = false;
          expanded.clear();
          writeAttempt(storage, key, data, null);
          paint();
          emit(id, null, null);
          controls[0].button.focus();
        });
        unsureBtn.addEventListener('click', () => {
          if (selected === null) return;
          unsure = !unsure;
          unsureById[id] = unsure;
          writeAttempt(storage, key, data, selected, unsure);
          paint();
          showFeedback('unsure', id, unsure ? '애매함으로 표시했어요' : '애매함 표시를 취소했어요');
        });
        card.classList.add('review-ready');
        solution.classList.add('review-extra');
        paint();
        if (selected !== null) emit(id, selected, grade(data, selected), true);
        else {
          try {
            if (storage.getItem(key) !== null) {
              writeAttempt(storage, key, data, null);
              emit(id, null, null, true);
            }
          } catch {}
        }
      } catch (error) {
        // Keep a readable static question if enhancement cannot be completed.
        diagnosticTexts.forEach(p => { p.node.textContent = p.text; });
        choices.forEach((li, i) => li.replaceChildren(...choiceNodes[i]));
        positions.slice().reverse().forEach(p => {
          p.node.hidden = false;
          p.node.classList.remove('review-diagnostic');
          p.parent.insertBefore(p.node, p.next);
        });
        for (const el of [status, reset, notice, unsureBtn]) if (el) el.remove();
        solution.hidden = originalHidden;
        solution.open = originalOpen;
        if (summary) summary.textContent = summaryText;
        solution.classList.remove('review-extra');
        card.classList.remove('review-ready');
        win.console.warn('문항 상호작용을 적용하지 못했습니다:', id, error);
      }
    }
    const exportCards = Array.from(root.querySelectorAll('main article.card')).filter(el => model.cards[el.id]);
    const pager = root.querySelector('.pager');
    const prompt = promptApi(win);
    if (prompt && exportCards.length && pager && !pager.querySelector('.review-export-bar')) {
      const ids = exportCards.map(el => el.id);
      const bar = element('div', 'review-export-bar');
      bar.hidden = true;
      const button = element('button', 'btn btn-ghost review-export', '복기 열기');
      button.type = 'button';
      button.setAttribute('aria-haspopup', 'dialog');
      bar.append(button);
      pager.prepend(bar);
      const openReview = () => {
        const record = buildPromptRecord(model, texts, ids, selectedById, unsureById, root.body.dataset.range || '');
        prompt.openPromptDialog(root, record, () => {
          showFeedback('copied', 'export', '복사했어요. AI 채팅에 붙여 넣으세요', 3000);
        });
      };
      button.addEventListener('click', openReview);
      root.addEventListener('od:answer', ({detail}) => {
        if (!bar.hidden || detail.id !== ids.at(-1) || detail.restored || detail.result === null) return;
        bar.hidden = false;
        openReview();
      });
    }
    // Existing page CSS hides side panels when printing. Move original details,
    // including static questions, into their cards for print, then restore them.
    if (!root.documentElement.dataset.reviewPrint) {
      root.documentElement.dataset.reviewPrint = 'ready';
      let printPositions = [];
      win.addEventListener('beforeprint', () => {
        if (printPositions.length) return;
        root.querySelectorAll('.aid[data-card-id]').forEach(aid => {
          const card = root.getElementById(aid.dataset.cardId);
          if (!card) return;
          Array.from(aid.children).forEach(node => {
            printPositions.push({node, parent:aid, open:node.open});
            if (node.tagName === 'DETAILS') node.open = true;
            card.append(node);
          });
        });
      });
      win.addEventListener('afterprint', () => {
        printPositions.forEach(p => {p.parent.append(p.node); p.node.open = p.open;});
        printPositions = [];
      });
    }
  }
  const api = {stripDiagnosticPrefix, grade, storageKey, readAttempt, readUnsure, writeAttempt, mount,
    captureCardText, buildPromptRecord};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else scope.ReviewInteraction = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
