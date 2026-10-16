"""Validate authored choices and render the shared practice/explanation markup."""
from html import escape as E
import hashlib
import json

def merge_mcq(questions, rows):
    ids = [q['id'] for q in questions]
    if len(rows) != len(ids) or {r['id'] for r in rows} != set(ids):
        raise ValueError('문항 ID 누락 또는 중복')
    by_id = {r['id']: r for r in rows}
    out = []
    for q in questions:
        r = by_id[q['id']]
        choices = r['choices']
        if [c['id'] for c in choices] != ['1','2','3','4','5']:
            raise ValueError(q['id'] + ': 보기 ID')
        if len({c['text'].strip() for c in choices}) != 5:
            raise ValueError(q['id'] + ': 중복 보기')
        if r['correctChoiceId'] not in {'1','2','3','4','5'}:
            raise ValueError(q['id'] + ': 정답 ID')
        if not r['prompt'].strip() or any(not c['text'].strip() or not c['explanation'].strip() for c in choices):
            raise ValueError(q['id'] + ': 빈 원고')
        out.append({**q, **r})
    return out

def render_choices(q, explain=False):
    signature = hashlib.sha256(json.dumps({k:q[k] for k in ['prompt','choices','correctChoiceId']}, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    cards = []
    for c in q['choices']:
        correct = c['id'] == q['correctChoiceId']
        hidden = '' if explain else ' hidden'
        number = '①②③④⑤'[int(c['id'])-1]
        label = '정답' if correct else '정답 아님'
        control = (f'<div class="mcq-option">{number} {E(c["text"])}</div>' if explain else
            f'<button type="button" class="mcq-choice" data-choice-id="{c["id"]}" aria-expanded="false" aria-controls="{q["id"]}-reason-{c["id"]}">{number} {E(c["text"])}</button>')
        cards.append(f'<li data-option-id="{c["id"]}">{control}<span class="mcq-label"{hidden}>{label}</span><div class="mcq-reason" id="{q["id"]}-reason-{c["id"]}"{hidden}>{E(c["explanation"])}</div></li>')
    return f'''<div class="mcq" data-question-id="{q['id']}" data-correct="{q['correctChoiceId']}" data-signature="{signature}" data-explain="{str(explain).lower()}">
    <ol class="mcq-choices">{''.join(cards)}</ol>
    <p class="mcq-status" role="status" aria-live="polite"></p>
    <button type="button" class="mcq-reset" hidden>다시 풀기</button></div>'''
