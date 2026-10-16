/* Local practice state; option order is fixed in the authored document. */
(() => {
  function read(key, allowed) {
    try {
      const value = JSON.parse(sessionStorage.getItem(key));
      return allowed.includes(value) ? value : null;
    } catch { return null; }
  }
  function write(key, value) {
    try { sessionStorage.setItem(key, JSON.stringify(value)); } catch {}
  }
  function mount() {
    document.querySelectorAll('.mcq[data-explain="false"]').forEach(box => {
      const controls = [...box.querySelectorAll('.mcq-choice')];
      const allowed = controls.map(c => c.dataset.choiceId);
      const correct = box.dataset.correct;
      const key = `chip-mcq-v1:${box.dataset.questionId}:${box.dataset.signature}`;
      let selected = read(key, allowed);
      const expanded = new Set(selected === null ? [] : [selected, correct]);
      const status = box.querySelector('.mcq-status');
      const reset = box.querySelector('.mcq-reset');
      function paint() {
        const answered = selected !== null;
        if (answered) box.dataset.selected = selected;
        else delete box.dataset.selected;
        reset.hidden = !answered;
        status.textContent = !answered ? '' : selected === correct
          ? '정답이에요.' : '정답이 아니에요. 보기별 이유를 확인해 보세요.';
        controls.forEach(button => {
          const id = button.dataset.choiceId;
          const open = answered && expanded.has(id);
          button.setAttribute('aria-expanded', String(open));
          button.dataset.result = !answered ? '' : id === correct ? 'correct' : id === selected ? 'selected' : '';
          const label = button.parentElement.querySelector('.mcq-label');
          label.hidden = !answered;
          label.textContent = [id === selected ? '내 선택' : '', id === correct ? '정답' : '정답 아님'].filter(Boolean).join(' · ');
          button.parentElement.querySelector('.mcq-reason').hidden = !open;
        });
      }
      controls.forEach(button => button.addEventListener('click', () => {
        const id = button.dataset.choiceId;
        if (selected === null) {
          selected = id;
          expanded.add(id); expanded.add(correct);
          write(key, selected);
        } else if (expanded.has(id)) expanded.delete(id);
        else expanded.add(id);
        paint();
      }));
      reset.addEventListener('click', () => {
        selected = null; expanded.clear(); write(key, null); paint();
        controls[0].focus();
      });
      paint();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, {once:true});
  else mount();
})();
