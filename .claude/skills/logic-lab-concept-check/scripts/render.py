"""Render learner text into the upstream concept-check card markup."""
from html import escape
import json


NOTE_LINK_TEXT = "실험설명에서 이 개념 다시 보기 →"


def card_html(item, objective, number, note_name):
    cid = item["id"]
    if item["format"] == "short":
        answer = item["answer"]
        data = json.dumps(dict(canonical=answer["canonical"], accepted=answer["accepted"],
                               case_sensitive=False), ensure_ascii=False)
        attrs = f' data-format="short" data-short-answer="{escape(data)}"'
        choices = ""
        controls = (
            f'<div class="short-input"><label for="answer-{cid}">답</label>'
            f'<input type="text" id="answer-{cid}" autocomplete="off">'
            '<button class="btn btn-primary check-answer" type="button">답 확인</button></div>'
        )
        steps = "".join(f"<li>{escape(step)}</li>" for step in item["solution"])
        canonical = answer["canonical"]
    else:
        options = item["options"]
        canonical = item["answer"]
        attrs = controls = ""
        choices = '<ol class="choices">' + "".join(
            f'<li data-choice="{option["id"]}">{escape(option["text"])}</li>' for option in options
        ) + "</ol>"
        steps = []
        for option in options:
            why = escape(option["why"])
            if option["id"] != canonical:
                why = f'"{escape(option["misconception"])}" — {why}'
            steps.append(f'<li data-explains="{option["id"]}">{why}</li>')
        steps = "".join(steps)
    href = escape(f'{note_name}#{objective["topic_id"]}')
    return (
        f'<article class="card" id="{cid}" data-objective="{escape(objective["id"])}"{attrs}>'
        f'<h3>Q{number}. {escape(item["title"])}</h3>'
        f'<div class="problem">{item["stem_html"]}{choices}</div>{controls}'
        f'<details class="hint" open><summary>힌트 보기</summary><p>{escape(item["hint"])}</p></details>'
        f'<details class="solution"><summary>풀이 보기</summary><ol class="steps">{steps}</ol>'
        f'<p class="answer">정답: {escape(canonical)}</p>'
        f'<p class="note-link"><a href="{href}">{NOTE_LINK_TEXT}</a></p></details></article>'
    )
