"""Validated choice/diagnostic mapping and self-contained review enhancement."""
from __future__ import annotations
import hashlib
import json
import re
import _paths
from scripts.lab.review_pack.html2md import Parser, Node

LABEL = re.compile(r'^\s*(?:\((\d+)\)|([A-Z])[.)])\s*')
ANSWER = re.compile(r'^\s*정답:\s*(?:\((\d+)\)|([A-Z]))\s*$')
CAUTION = re.compile(r'모호|모두 가능|단일 정답|엄밀한.*정답|복수.?정답|답이 하나|성립할 여지|해석에 따라|옳은 설명으로 볼 여지|완전히 옳다고 보기 어려|같은 뜻이 되지만|자료도 있으니')


def find(node, cls):
    return [n for n in node.walk() if cls in n.attrs.get('class', '').split()]


def children(node, tag):
    return [n for n in node.children if isinstance(n, Node) and n.tag == tag]


def node_text(node):
    return node if isinstance(node, str) else ''.join(node_text(n) for n in node.children)


def label(node, attr):
    explicit = node.attrs.get(attr)
    if explicit:
        if not re.fullmatch(r'\d+|[A-Z]', explicit):
            raise ValueError('보기 식별자 형식 오류')
        return explicit
    match = LABEL.match(node_text(node))
    if not match:
        return None
    return next(g for g in match.groups() if g is not None)


def snapshot(node):
    if isinstance(node, str):
        return node
    return [node.tag, sorted(node.attrs.items()), [snapshot(n) for n in node.children]]


def load_overrides():
    return {}


def build_model(source: str, document_id: str, overrides: dict | None = None) -> dict:
    tree = Parser()
    tree.feed(source)
    result = dict(schema=1, documentId=document_id, cards={}, skipped=[], errors=[])
    overrides = (load_overrides() if overrides is None else overrides).get(document_id, {})
    seen = set()
    for card in find(tree.root, 'card'):
        cid = card.attrs.get('id', '')
        try:
            if not cid or cid in seen:
                raise ValueError('문항 id 누락 또는 중복')
            seen.add(cid)
            if card.attrs.get('data-format') == 'short':
                answer = json.loads(card.attrs.get('data-short-answer', '{}'))
                if (not isinstance(answer, dict) or not isinstance(answer.get('canonical'), str)
                    or not answer['canonical'].strip() or not isinstance(answer.get('accepted'), list)
                    or not all(isinstance(x, str) and x.strip() for x in answer['accepted'])
                    or type(answer.get('case_sensitive')) is not bool):
                    raise ValueError('단답형 정답/허용답 형식 오류')
                if len(find(card, 'solution')) != 1:
                    raise ValueError('단답형 풀이 누락 또는 중복')
                result['cards'][cid] = dict(format='short', answer=answer,
                    version=hashlib.sha256(json.dumps(snapshot(card), ensure_ascii=False).encode()).hexdigest())
                continue
            lists = find(card, 'choices')
            if not lists:
                result['skipped'].append(cid)
                continue
            if len(lists) != 1:
                raise ValueError('보기 목록은 하나여야 함')
            choices = children(lists[0], 'li')
            solutions = find(card, 'solution')
            answers = find(card, 'answer')
            if len(solutions) != 1 or len(answers) != 1:
                raise ValueError('풀이 또는 정답이 없거나 중복됨')
            steps = find(solutions[0], 'steps')
            if len(steps) != 1:
                raise ValueError('보기별 해설 목록이 없거나 중복됨')
            diagnostics = children(steps[0], 'li')
            match = ANSWER.fullmatch(node_text(answers[0]))
            if not match:
                raise ValueError('명시 정답 형식을 해석할 수 없음')
            answer = next(g for g in match.groups() if g is not None)
            ids = [label(n, 'data-choice') for n in choices]
            if len(ids) < 2 or None in ids or len(set(ids)) != len(ids) or answer not in ids:
                raise ValueError('보기 식별자 누락/중복 또는 정답이 보기에 없음')
            override = overrides.get(cid, {})
            mapping = {}
            for i, n in enumerate(diagnostics):
                key = label(n, 'data-explains')
                if key is not None:
                    if key in mapping:
                        raise ValueError('보기별 해설 식별자 중복')
                    mapping[key] = i
            mapping.update(override.get('diagnostics', {}))
            positions = [mapping.get(key) for key in ids]
            if any(type(i) is not int or not 0 <= i < len(diagnostics) for i in positions):
                raise ValueError('보기별 해설 연결 누락 또는 범위 오류')
            if len(set(positions)) != len(positions):
                raise ValueError('여러 보기에 동일 해설 연결')
            mode = override.get('mode', card.attrs.get('data-grade-mode', 'single'))
            notice = override.get('notice', card.attrs.get('data-grade-notice', ''))
            if mode not in ('single', 'ambiguous') or (mode == 'ambiguous' and not notice.strip()):
                raise ValueError('채점 모드 또는 모호성 설명 오류')
            if CAUTION.search(node_text(solutions[0])) and 'mode' not in override and 'data-grade-mode' not in card.attrs:
                raise ValueError('모호성 문구 수동 검토 필요')
            model = dict(answer=answer, mode=mode, notice=notice,
                         options=[dict(id=key, index=i, diagnostic=mapping[key]) for i, key in enumerate(ids)])
            payload = json.dumps([snapshot(card), model], ensure_ascii=False, sort_keys=True)
            model['version'] = hashlib.sha256(payload.encode('utf-8')).hexdigest()
            result['cards'][cid] = model
        except ValueError as exc:
            result['cards'].pop(cid, None)
            result['errors'].append(dict(cardId=cid, reason=str(exc)))
    return result


def validate_model(source: str, model: dict) -> list[dict]:
    if not isinstance(model, dict):
        return [dict(cardId='', reason='채점 모델은 객체여야 함')]
    expected = build_model(source, model.get('documentId', ''))
    errors = list(expected['errors'])
    if model != expected:
        errors.append(dict(cardId='', reason='내장 채점 데이터와 원본이 일치하지 않음'))
    return errors


START = '<!-- review-interaction:start -->'
END = '<!-- review-interaction:end -->'
BLOCK = re.compile(re.escape(START) + r'.*?' + re.escape(END) + r'\n?', re.S)
ANSWER_EVENT = """        document.addEventListener('od:answer', ({detail}) => {
          if (!cards.some(c => c.id === detail.id)) return;
          if (detail.restored && detail.selected !== null) return;
          if (detail.selected === null) solved.delete(detail.id);
          else solved.add(detail.id);
          if (curId) paintBtn();
          markToc(solved, cards.length, '푼 문제');
        });
"""


LEAVE_ANCHOR = "          if (cur >= 0) screens[cur].classList.remove('is-current', 'enter-next', 'enter-prev');\n"
LEAVE_LINE = ("          if (cur >= 0) document.dispatchEvent(new CustomEvent('od:leave', "
              "{ detail: { index: cur, screen: screens[cur] } }));\n")


def patch_pager_shell(source: str) -> str:
    if '<script id="pager-ui">' not in source or "detail: { index: cur, screen: screens[cur] }" in source:
        return source
    if source.count(LEAVE_ANCHOR) != 1:
        raise ValueError('pager 화면 전환 구조 불일치')
    return source.replace(LEAVE_ANCHOR, LEAVE_LINE + LEAVE_ANCHOR)


def patch_review_shell(source: str) -> str:
    if 'function setupReview()' not in source:
        return source
    begin = source.index('function setupReview()')
    end = source.index('function setupNote()', begin)
    section = source[begin:end]
    if "g.dataset.cardId = card.id;" not in section:
        needle = "g.className = 'aid';"
        if section.count(needle) != 1:
            raise ValueError('setupReview aid 구조 불일치')
        section = section.replace(needle, needle + '\n          g.dataset.cardId = card.id;')
    if "if (detail.selected === null) solved.delete(detail.id);" not in section:
        needle = "        document.addEventListener('od:screen', (e) => {"
        if section.count(needle) != 1:
            raise ValueError('setupReview 이벤트 구조 불일치')
        section = section.replace(needle, ANSWER_EVENT + needle)
    elif 'if (detail.restored && detail.selected !== null) return;' not in section:
        needle = "          if (!cards.some(c => c.id === detail.id)) return;"
        if section.count(needle) != 1:
            raise ValueError('setupReview 완료 상태 연결 구조 불일치')
        section = section.replace(needle, needle + '\n          if (detail.restored && detail.selected !== null) return;')
    section = patch_solved_history(section)
    return source[:begin] + section + source[end:]


SOLVED_LOAD = "new Set(store.get(KEY, []).filter((id) => cards.some((c) => c.id === id)))"
LEGACY_SOLVED_LOAD = "new Set([].filter((id) => cards.some((c) => c.id === id)))"
SOLVED_SAVE = "          store.set(KEY, Array.from(solved));\n"
LEGACY_SOLVED_SAVE = "          // concept-check: 푼 문제 기록은 저장하지 않는다\n"
STORAGE_EVENT = """        let storage;
        const saveSolved = () => storage?.setItem(KEY, JSON.stringify(Array.from(solved)));
        document.addEventListener('od:review-storage', ({detail}) => {
          storage = detail;
          const saved = JSON.parse(storage.getItem(KEY) || '[]');
          cards.forEach(card => { if (saved.includes(card.id)) solved.add(card.id); });
          markToc(solved, cards.length, '푼 문제');
          if (curId) paintBtn();
        }, {once: true});
"""


def patch_solved_history(section: str) -> str:
    """Use the quiz history entry for progress instead of persistent preferences."""
    if "od:review-storage" in section:
        return section
    load = LEGACY_SOLVED_LOAD if LEGACY_SOLVED_LOAD in section else SOLVED_LOAD
    save = LEGACY_SOLVED_SAVE if LEGACY_SOLVED_SAVE in section else SOLVED_SAVE
    button = "        btn.addEventListener('click', () => {"
    answered = "          else solved.add(detail.id);\n"
    if any(section.count(anchor) != 1 for anchor in (load, save, button, answered)):
        raise ValueError('setupReview 푼 문제 저장 구조 불일치')
    section = section.replace(load, "new Set()").replace(save, "          saveSolved();\n")
    section = re.sub(r"^          // 저장하지 않는다: 새로고침하면 진행이 초기화된다[^\n]*\n",
                     "", section, flags=re.M)
    section = section.replace(answered, answered + "          saveSolved();\n")
    return section.replace(button, STORAGE_EVENT + button)


def install(source: str, document_id: str, overrides: dict | None = None, strict: bool = True) -> str:
    source = BLOCK.sub('', source)
    source = patch_review_shell(source)
    source = patch_pager_shell(source)
    model = build_model(source, document_id, overrides)
    if strict and model['errors']:
        raise ValueError(json.dumps(model['errors'], ensure_ascii=False))
    if source.count('</body>') != 1:
        raise ValueError('body 종료 태그는 하나여야 함')
    payload = json.dumps(model, ensure_ascii=False, sort_keys=True).replace('<', '\\u003c')
    css = _paths.read_asset('review-interaction.css')
    js = _paths.read_asset('review-prompt.js') + '\n' + _paths.read_asset('review-interaction.js')
    if not any(card.get('format') == 'short' for card in model['cards'].values()):
        js = re.sub(r'^// short-support:start\n.*?^// short-support:end\n', '', js, flags=re.S | re.M)
    boot = """(function () {
      function start() {
        try {
          const storage = ReviewInteraction.historyStore(window);
          document.dispatchEvent(new CustomEvent('od:review-storage', {detail: storage}));
          ReviewInteraction.mount(document, JSON.parse(document.getElementById('review-interaction-model').textContent), storage);
        } catch (error) { console.warn('복습문제 상호작용 초기화 실패:', error); }
      }
      if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once:true});
      else start();
    })();"""
    block = (START + '\n<style>\n' + css + '\n</style>\n'
             + '<script id="review-interaction-model" type="application/json">' + payload + '</script>\n'
             + '<script>\n' + js + '\n</script>\n<script>' + boot + '</script>\n' + END + '\n')
    return source.replace('</body>', block + '</body>')
