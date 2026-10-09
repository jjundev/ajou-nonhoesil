(function (scope) {
  'use strict';
  function grade(card, selected) {
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
  function writeAttempt(storage, key, card, selected) {
    try {
      if (selected === null) storage.removeItem(key);
      else storage.setItem(key, JSON.stringify({version:card.version, selected}));
    } catch {}
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
    for (const [id, data] of Object.entries(model.cards)) {
      const card = root.getElementById(id);
      if (!card || card.classList.contains('review-ready')) continue;
      const aid = Array.from(root.querySelectorAll('.aid')).find(n => n.dataset.cardId === id);
      const solution = (aid || card).querySelector('details.solution');
      const choices = Array.from(card.querySelectorAll('.choices > li'));
      const diagnostics = solution ? Array.from(solution.querySelectorAll('ol.steps > li')) : [];
      const options = data.options;
      // Validate every reference before moving a single original node.
      if (!solution || !Array.isArray(options) || choices.length !== options.length ||
          !options.length || !options.some(o => o.id === data.answer) ||
          new Set(options.map(o => o.index)).size !== options.length ||
          new Set(options.map(o => o.diagnostic)).size !== options.length ||
          options.some(o => !choices[o.index] || !diagnostics[o.diagnostic])) continue;
      const positions = diagnostics.map(n => ({node:n, parent:n.parentNode, next:n.nextSibling}));
      const choiceNodes = choices.map(n => Array.from(n.childNodes));
      const summary = solution.querySelector('summary');
      const summaryText = summary ? summary.textContent : '';
      const originalOpen = solution.open;
      const originalHidden = solution.hidden;
      let status, reset, help, notice;
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
          diagnostic.classList.add('review-diagnostic');
          diagnostic.hidden = true;
          list.append(diagnostic);
          li.append(list);
          return {id:o.id, button, badge, diagnostic, list};
        });
        help = element('p', 'review-help', '답을 선택하면 내 선택과 정답의 해설이 열려요. 다른 보기도 눌러 해설을 확인할 수 있어요.');
        status = element('p', 'review-status');
        status.setAttribute('role', 'status');
        status.setAttribute('aria-live', 'polite');
        reset = element('button', 'review-reset text-btn', '다시 풀기');
        reset.type = 'button';
        card.querySelector('.choices').before(help, status);
        card.querySelector('.choices').after(reset);
        const key = storageKey(model.documentId, id);
        let selected = readAttempt(storage, key, data);
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
          help.hidden = answered;
          reset.hidden = !answered;
          status.textContent = !answered ? '' : result === 'ambiguous'
            ? '단일 정답 판정 주의'
            : result === 'correct' ? '정답이에요.' : '정답이 아니에요. 보기별 이유를 확인해 보세요.';
          status.dataset.result = result || '';
          controls.forEach(c => {
            c.button.dataset.selected = String(c.id === selected);
            if (answered) c.button.removeAttribute('aria-pressed');
            else c.button.setAttribute('aria-pressed', 'false');
            c.button.dataset.result = !answered ? '' : c.id === data.answer
              ? (data.mode === 'ambiguous' ? 'intended' : 'correct') : c.id === selected ? 'selected' : '';
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
          expanded.add(selected);
          expanded.add(data.answer);
          writeAttempt(storage, key, data, selected);
          paint();
          emit(id, selected, grade(data, selected));
        }));
        reset.addEventListener('click', () => {
          selected = null;
          expanded.clear();
          writeAttempt(storage, key, data, null);
          paint();
          emit(id, null, null);
          controls[0].button.focus();
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
        choices.forEach((li, i) => li.replaceChildren(...choiceNodes[i]));
        positions.slice().reverse().forEach(p => {
          p.node.hidden = false;
          p.node.classList.remove('review-diagnostic');
          p.parent.insertBefore(p.node, p.next);
        });
        for (const el of [status, reset, help, notice]) if (el) el.remove();
        solution.hidden = originalHidden;
        solution.open = originalOpen;
        if (summary) summary.textContent = summaryText;
        solution.classList.remove('review-extra');
        card.classList.remove('review-ready');
        win.console.warn('문항 상호작용을 적용하지 못했습니다:', id, error);
      }
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
  const api = {grade, storageKey, readAttempt, writeAttempt, mount};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else scope.ReviewInteraction = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
