"""블라인드 사본(make)·대조 장부(record)·상태(status). 풀이자는 정답이 없는 사본만 본다."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

from content import parse_html, plain_html_from_node
from build import load_source
from scripts.lab.review_pack.html2md import Node

ID_RE = re.compile(r"^q\d+$")


def item_hash(item: dict, objective: dict) -> str:
    """블라인드 풀이 판정에 쓰는 문항 데이터와 목표 근거를 해시한다.
    블라인드 사본에서 접혀 있는 힌트는 해시에서 제외한다."""
    item_for_blind = {key: value for key, value in item.items() if key != "hint"}
    shown = dict(concept=objective["concept"], topic_id=objective["topic_id"], source=objective["source"])
    blob = json.dumps(dict(item=item_for_blind, objective=shown), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _stem(node):
    if isinstance(node, str):
        return node
    if node.tag == "table":
        caption = next((plain_html_from_node(n).strip() for n in node.walk() if n.tag == "caption"), "")
        rows = []
        for row in node.walk():
            if row.tag != "tr":
                continue
            cells = [plain_html_from_node(cell).strip().replace("|", r"\|")
                     for cell in row.children if isinstance(cell, Node) and cell.tag in {"th", "td"}]
            rows.append(cells)
        if not rows:
            return caption
        rows.insert(1, ["---"] * len(rows[0]))
        return "\n\n" + (caption + "\n\n" if caption else "") + "\n".join(
            "| " + " | ".join(row) + " |" for row in rows
        ) + "\n\n"
    body = "".join(_stem(child) for child in node.children)
    if node.tag == "li":
        return f"\n- {body.strip()}\n"
    if node.tag in {"p", "ol", "ul", "br"}:
        return f"\n\n{body.strip()}\n\n"
    return body


def _card(item: dict) -> str:
    lines = [f"## {item['id']}. {item['title']}", "", _stem(parse_html(item["stem_html"])).strip(), ""]
    if item["format"] == "mcq":
        lines += [f"{option['id']}. {option['text']}" for option in item["options"]]
    else:
        lines.append("(값을 쓰세요)")
    return "\n".join(lines) + "\n"


def make(src: Path, out: Path, only: set[str] | None = None) -> None:
    s = load_source(src)
    items = [it for it in s["items"] if only is None or it["id"] in only]
    if only is not None and {it["id"] for it in items} != only:
        raise ValueError("--only에 모르는 문항 ID가 있어요")
    head = "# 확인문제 블라인드 사본\n\n각 문항의 답과 풀이 근거를 표에 적으세요.\n"
    Path(out).write_text(head + "\n" + "\n".join(_card(it) for it in items),
                         encoding="utf-8")


def parse_answers(text: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if not line.endswith("|"):
            continue
        cells = [c.strip().replace(r"\|", "|") for c in re.split(r"(?<!\\)\|", line[1:-1])]
        if len(cells) < 2 or not ID_RE.match(cells[0]):
            continue
        if cells[0] in out:
            raise ValueError(f"문항 {cells[0]} 이(가) 표에 두 번 있어요")
        if len(cells) != 4:
            raise ValueError(f"문항 {cells[0]} 답안표의 네 칸을 확인하세요")
        out[cells[0]] = dict(answer=cells[1], rationale=cells[2], objection=cells[3])
    return out


def _load(ledger: Path) -> dict:
    ledger = Path(ledger)
    return json.loads(ledger.read_text(encoding="utf-8")) if ledger.is_file() else {}


def record(src: Path, answers_md: Path, ledger: Path, round_no: int) -> dict:
    s = load_source(src)
    objs = {o["id"]: o for o in s["objectives"]}
    items = {it["id"]: it for it in s["items"]}
    answers = parse_answers(Path(answers_md).read_text(encoding="utf-8"))
    data = _load(ledger)
    for id_, a in answers.items():
        if id_ not in items:
            raise ValueError(f"소스에 없는 문항: {id_}")
        data[id_] = {
            **a, "hash": item_hash(items[id_], objs[items[id_]["objective"]]), "round": round_no,
        }
    Path(ledger).write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return data


def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", str(s)).strip().casefold()


def _accepted(item: dict) -> set[str]:
    if item["format"] == "mcq":
        return {_norm(item["answer"])}
    ans = item["answer"]
    canon = ans["canonical"]
    return {_norm(v) for v in [canon, *ans.get("accepted", [])]}


def status(src: Path, ledger: Path) -> list[str]:
    data = _load(ledger)
    s = load_source(src)
    objs = {o["id"]: o for o in s["objectives"]}
    out: list[str] = []
    for item in s["items"]:
        id_ = item["id"]
        row = data.get(id_)
        if row is None:
            out.append(f"{id_}: 장부에 없음")
            continue
        if row.get("hash") != item_hash(item, objs[item["objective"]]):
            out.append(f"{id_}: 수정됨")
            continue
        if not row.get("rationale", "").strip():
            out.append(f"{id_}: 풀이 근거 없음")
        if _norm(row["answer"]) not in _accepted(item):
            correct = item["answer"] if item["format"] == "mcq" else item["answer"]["canonical"]
            out.append(f"{id_}: 답 불일치 ({row['answer']} ≠ {correct})")
        if row.get("objection", "").strip():
            out.append(f"{id_}: 이의 — {row['objection'].strip()}")
    return out


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="blind.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make"); m.add_argument("src"); m.add_argument("out"); m.add_argument("--only")
    r = sub.add_parser("record"); r.add_argument("src"); r.add_argument("answers"); r.add_argument("ledger")
    r.add_argument("--round", type=int, required=True)
    s = sub.add_parser("status"); s.add_argument("src"); s.add_argument("ledger")
    a = p.parse_args(argv[1:])
    try:
        if a.cmd == "make":
            make(Path(a.src), Path(a.out), set(a.only.split(",")) if a.only else None)
        elif a.cmd == "record":
            record(Path(a.src), Path(a.answers), Path(a.ledger), a.round)
        else:
            lines = status(Path(a.src), Path(a.ledger))
            print("\n".join(lines) if lines else "OK")
            return 1 if lines else 0
    except (OSError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
