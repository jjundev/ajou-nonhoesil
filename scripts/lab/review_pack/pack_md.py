"""발행 팩의 Markdown 은 실험 폴더 루트가 아니라 자료 폴더(`.pack/`) 안에 산다.

작성기는 지금처럼 **루트 기준** 링크(`.pack/figures/..`, `../../강의노트/..`, 형제 `실험NN_*.md`)로
본문을 만들고, 쓰는 순간 `to_data_frame` 으로 자료 폴더 기준으로 한 번 바꾼다.
검사기는 md 부모 기준으로 링크를 풀고, HTML 에서 뽑은 기대 문자열에만 같은 변환을 건다.
"""
import re
from pathlib import Path
from urllib.parse import unquote

from .manifest import DATA

# 링크 대상만 잡는다: `](target)`. 대상 안에는 공백·닫는 괄호가 없다(작성기가 quote 한다).
_TARGET = re.compile(r'(\]\()([^)\s]+)(\))')


def md_path(folder, name):
    """발행 레이아웃에서 md 의 자리. 위치를 정하는 곳은 여기 하나다."""
    return Path(folder) / DATA / name


def _is_relative(target):
    return not (target.startswith('#') or re.match(r'[A-Za-z][A-Za-z0-9+.-]*:', target) or target.startswith('/'))


def _sibling_md(path):
    return '/' not in path and path.endswith('.md')


def rebase_link(target, prefixes=(DATA + '/',)):
    """루트 기준 링크 하나를 자료 폴더 기준으로. prefixes 는 떼어 낼 자료 폴더 접두(디코딩한 꼴)."""
    if not _is_relative(target):
        return target
    path = unquote(target.split('#', 1)[0])
    for prefix in prefixes:
        if path.startswith(prefix):
            # 접두는 인코딩된 채로 있을 수 있다 — 원래 글자 수가 아니라 디코딩 결과로 자른다.
            raw, _, frag = target.partition('#')
            i = next(i for i in range(len(raw) + 1) if unquote(raw[:i]) == prefix)
            return raw[i:] + ('#' + frag if frag else '')
    if _sibling_md(path):
        return target
    return '../' + target


def unbase_link(target):
    """rebase_link 의 역. 왕복 검사용."""
    if not _is_relative(target):
        return target
    if target.startswith('../'):
        return target[3:]
    if _sibling_md(unquote(target.split('#', 1)[0])):
        return target
    return DATA + '/' + target


def to_data_frame(text, prefixes=(DATA + '/',)):
    return _TARGET.sub(lambda m: m.group(1) + rebase_link(m.group(2), prefixes) + m.group(3), text)


def to_root_frame(text):
    return _TARGET.sub(lambda m: m.group(1) + unbase_link(m.group(2)) + m.group(3), text)


def write_pack_md(folder, name, text):
    """루트 기준으로 만든 md 본문을 자료 폴더 기준으로 바꿔 제자리에 쓴다."""
    path = md_path(folder, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_data_frame(text), encoding='utf-8')
    return path
