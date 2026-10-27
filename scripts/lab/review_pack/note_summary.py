"""Three-part note summaries (rules / why / traps) kept as data beside table-layout.json.

Strings are authored HTML fragments, inserted as-is like experiment 07's h.sumparts.
"""
from pathlib import Path
import html
import json
import re

SUMMARY_FILE='sections/note-summaries.json'
SUM=re.compile(r'<div class="sum" hidden>(.*?)</div>',re.S)
# 사실 토큰: 영숫자 덩어리(단위·위첨자·프라임 포함)와 방향·부등호·식 기호 한 글자씩. 집합 비교라 ↑↔↓ 맞바꿈은 못 잡는다.
TOKEN=re.compile(r"[A-Za-z0-9][A-Za-z0-9′'̄⊕’ⁿΩ°]*|[↑↓≠≤≥−+=]")
TOPIC=re.compile(r'<article class="topic" id="([^"]+)">(.*?)</article>',re.S)

def _text(value):
    return isinstance(value,str) and bool(value.strip())

def load_note_summaries(root):
    path=Path(root)/SUMMARY_FILE
    if not path.exists():return None
    data=json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema_version')!=1 or not isinstance(data.get('topics'),dict):
        raise ValueError(f'{path}: expected schema_version 1 and topics object')
    for topic_id,parts in data['topics'].items():
        bad=lambda why:ValueError(f'{path}: {topic_id}: {why}')
        if not isinstance(parts,dict) or set(parts)-{'rules','why','traps'}:raise bad('only rules, why and traps are allowed')
        rules=parts.get('rules')
        if not isinstance(rules,list) or not rules or not all(isinstance(r,list) and len(r)==2 and all(map(_text,r)) for r in rules):
            raise bad('rules needs one or more [condition, result] pairs')
        if 'why' in parts and not _text(parts['why']):raise bad('why must be non-empty text')
        if 'traps' in parts and not (isinstance(parts['traps'],list) and parts['traps'] and all(map(_text,parts['traps']))):
            raise bad('traps must be a list of non-empty text')
    return data['topics']

def render_summary(parts):
    out='<p class="sum-label">외울 규칙</p><ul class="sum-rules">'+''.join(f'<li><b>{c}</b> → {r}</li>' for c,r in parts['rules'])+'</ul>'
    if parts.get('why'):
        out+=f'<p class="sum-label">이유</p><p class="sum-why">{parts["why"]}</p>'
    if parts.get('traps'):
        out+='<p class="sum-label sum-label-warn">헷갈리지 마요</p><ul class="sum-traps">'+''.join(f'<li>{t}</li>' for t in parts['traps'])+'</ul>'
    return f'<div class="sum" hidden>{out}</div>'

def replace_summary(topic_id,fragment,parts):
    found=SUM.findall(fragment)
    if len(found)!=1:raise ValueError(f'{topic_id}: expected one div.sum, found {len(found)}')
    if '<div' in found[0]:raise ValueError(f'{topic_id}: div.sum must not contain nested div')
    return SUM.sub(lambda _:render_summary(parts),fragment)

def summary_text(fragment):
    found=SUM.findall(fragment)
    return html.unescape(re.sub(r'<[^>]+>',' ',found[0])) if found else ''

def lost_tokens(old_html,new_html):
    kept=set(TOKEN.findall(summary_text(new_html)))
    return list(dict.fromkeys(t for t in TOKEN.findall(summary_text(old_html)) if t not in kept))

def check_topic_ids(summaries,topic_ids):
    for topic_id in topic_ids:
        if topic_id not in summaries:raise ValueError(topic_id+': missing summary')
    for topic_id in summaries:
        if topic_id not in topic_ids:raise ValueError(topic_id+': unknown topic')

def check_published_summaries(data_root,manifest,html_text):
    """발행본 실험설명의 요약이 세 칸 구조이고, 정본 JSON 이 있으면 그것을 그린 결과와 같은지 본다."""
    if manifest.get('note_summary_version')!=2:return []
    from .note_metadata import summary_structure_errors
    try:
        summaries=load_note_summaries(data_root)
        if summaries is not None:check_topic_ids(summaries,[t['id'] for t in manifest['topics']])
    except ValueError as exc:return [str(exc)]
    errors=[]
    for topic_id,fragment in TOPIC.findall(html_text):
        errors+=summary_structure_errors(topic_id,fragment)
        if summaries is not None and topic_id in summaries and render_summary(summaries[topic_id]) not in fragment:
            errors.append(f'{topic_id}: summary differs from {SUMMARY_FILE}')
    return errors
