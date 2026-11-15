"""Read and validate concept-check authoring data against the existing lab pack."""
from dataclasses import dataclass
from pathlib import Path
import json
import re
import unicodedata

import _paths
from scripts.lab import config
from scripts.lab.boolexpr import eval_boolean, variables
from scripts.lab.review_pack.html2md import Parser
from scripts.lab.review_pack.manifest import load_manifest, output_names
from scripts.lab.review_pack.workbook_render import read_workbook_payload, workbook_source_path

SRC_NAME = "자료_확인문제"
DATA = config.PACK_DATA_DIR
ITEM_ID = re.compile(r"q[1-9][0-9]*")
OBJECTIVE_ID = re.compile(r"o[1-9][0-9]*")
BITS = re.compile(r"[01]+")
CHOICES = "ABCD"
KINDS = {"정의·구별", "신호 해석", "원리", "규칙 적용", "상태 추적"}
STEM_TAGS = {"p", "b", "strong", "em", "code", "br", "ul", "ol", "li",
             "table", "caption", "thead", "tbody", "tr", "th", "td"}


class ContentError(ValueError):
    pass


@dataclass(frozen=True)
class Pack:
    folder: Path
    experiment: int
    manifest: dict
    note: Path
    note_md: Path
    questions: Path
    anchors: frozenset[str]


def experiment_number(value):
    match = re.fullmatch(r"(?:실험\s*)?([0-9]{1,2})", unicodedata.normalize("NFC", value.strip()))
    if match is None:
        raise ContentError("실험 번호 하나를 지정하세요. 예: 실험09")
    number = int(match[1])
    config.experiment_folder_name(number)
    return number


def folder_name(number):
    return config.experiment_folder_name(number)


def quiz_name(number):
    return f"{folder_name(number)}_확인문제.html"


def json_file(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def parse_html(text):
    parser = Parser()
    parser.feed(text)
    parser.close()
    return parser.root


def read_pack(folder):
    folder = Path(folder)
    try:
        manifest = load_manifest(folder / DATA / "manifest.json")
        experiment = manifest["experiment"]
        if unicodedata.normalize("NFC", folder.name) != folder_name(experiment):
            raise ContentError(f"폴더와 manifest 실험 번호가 달라요: {folder}")
        names = output_names(experiment, review_presentation_version=manifest.get("review_presentation_version"))
        note = folder / names["note_html"]
        note_md = folder / DATA / names["note_md"]
        questions = (workbook_source_path(folder, manifest, "question")
                     if manifest.get("review_presentation_version") == 2
                     else folder / names["review_html"])
        for path in (note, note_md, questions):
            if not path.is_file():
                raise ContentError(f"학습팩 근거 파일이 없어요: {path}")
        anchors = frozenset(n.attrs["id"] for n in parse_html(note.read_text(encoding="utf-8")).walk()
                            if n.tag == "article" and n.attrs.get("id"))
        return Pack(folder, experiment, manifest, note, note_md, questions, anchors)
    except (OSError, ValueError) as exc:
        raise ContentError(f"학습팩을 읽을 수 없어요: {exc}") from exc


def _string(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ContentError(f"{label}에 내용이 필요해요")
    return value


def _object(value, label):
    if not isinstance(value, dict):
        raise ContentError(f"{label}은 객체여야 해요")
    return value


def _rows(doc, key):
    rows = doc.get(key)
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        raise ContentError(f"{key}에는 객체가 든 목록이 필요해요")
    return rows


def _indexed(rows, pattern, label):
    indexed = {}
    for row in rows:
        ident = row.get("id")
        if not isinstance(ident, str) or not pattern.fullmatch(ident) or ident in indexed:
            raise ContentError(f"{label} ID가 잘못됐거나 겹쳐요: {ident!r}")
        indexed[ident] = row
    return indexed


def _bits(value):
    if not isinstance(value, str) or not BITS.fullmatch(value):
        raise ContentError(f"0과 1로 된 문자열이 필요해요: {value!r}")
    return value


def _bit(value):
    if type(value) is not int or value not in (0, 1):
        raise ContentError(f"비트는 정수 0 또는 1이어야 해요: {value!r}")
    return value


def compute(spec):
    spec = _object(spec, "compute")
    op = spec.get("op")
    if op == "boolean":
        expression = _string(spec.get("expression"), "expression")
        inputs = _object(spec.get("inputs"), "inputs")
        if set(variables(expression)) != set(inputs):
            raise ContentError("식에 나오는 입력과 inputs의 이름이 달라요")
        return str(eval_boolean(expression, {key: _bit(value) for key, value in inputs.items()}))
    if op == "select":
        address = _bits(spec.get("address"))
        words = spec.get("words")
        if (not isinstance(words, list) or len(words) != 2 ** len(address)
                or len({len(_bits(word)) for word in words}) != 1):
            raise ContentError("주소 폭에 맞는 같은 길이의 데이터 목록이 필요해요")
        return words[int(address, 2)]
    if op == "hold_or_load":
        previous, data = _bits(spec.get("previous")), _bits(spec.get("data"))
        if len(previous) != len(data):
            raise ContentError("기존 상태와 입력의 비트 폭이 달라요")
        return data if _bit(spec.get("enable")) == _bit(spec.get("active")) else previous
    raise ContentError(f"알 수 없는 검산 연산: {op!r}")


def plain_html(html):
    return " ".join(plain_html_from_node(parse_html(html)).split())


def stem_html(value):
    value = _string(value, "stem_html")
    for node in parse_html(value).walk():
        if node.tag == "root":
            continue
        if node.tag not in STEM_TAGS or node.attrs:
            raise ContentError(f"발문에서 허용하지 않는 요소나 속성이 있어요: {node.tag}")
    if not plain_html(value):
        raise ContentError("발문에 읽을 텍스트가 필요해요")
    return value


def normalize(text):
    return "".join(unicodedata.normalize("NFC", text).split()).casefold()


def workbook_stems(pack):
    if pack.manifest.get("review_presentation_version") == 2:
        payload = read_workbook_payload(pack.questions)
        return [normalize(plain_html(p["html"]["ask"])) for p in payload["problems"]]
    tree = parse_html(pack.questions.read_text(encoding="utf-8"))
    return [normalize(plain_html_from_node(node)) for node in tree.walk()
            if "problem" in node.attrs.get("class", "").split()]


def plain_html_from_node(node):
    return node if isinstance(node, str) else " ".join(map(plain_html_from_node, node.children))


def duplicates(stem, existing):
    stem = normalize(plain_html(stem))
    if stem in existing:
        return True
    return any(any(stem[index:index + 20] in other for index in range(len(stem) - 19))
               for other in existing)


def _reference(value, topics, problems, sources):
    value = _string(value, "오답 근거")
    kind, _, key = value.partition(":")
    if kind == "note" and key in topics:
        return
    if kind == "bank" and key in problems:
        return
    if kind == "source":
        source_id, _, page = key.partition("#")
        if (source_id in sources and page.isdecimal()
                and (source_id, int(page)) in {ref for topic in topics.values() for ref in topic}):
            return
    raise ContentError(f"학습팩에서 확인할 수 없는 오답 근거예요: {value}")


def _check_objective(obj, topics, anchors):
    tid = obj.get("topic_id")
    if not isinstance(tid, str) or tid not in topics or tid not in anchors:
        raise ContentError(f"실험설명 토픽 또는 앵커가 없어요: {tid!r}")
    _string(obj.get("concept"), "concept")
    if obj.get("kind") not in KINDS:
        raise ContentError(f"확인 목표 종류가 잘못됐어요: {obj.get('kind')!r}")
    source = _object(obj.get("source"), "source")
    sid, page = source.get("source_id"), source.get("pdf_page")
    if not isinstance(sid, str) or (page is not None and type(page) is not int):
        raise ContentError("출처 ID 또는 PDF 쪽 형식이 잘못됐어요")
    if (sid, page) not in topics[tid]:
        raise ContentError(f"{tid}에 기록된 출처와 쪽을 사용하세요: {sid}, {page}")


def _check_item(item, topics, problems, sources):
    _string(item.get("title"), "title")
    stem_html(item.get("stem_html"))
    hint = _string(item.get("hint"), "hint")
    if "\n" in hint or re.search(r"</?[a-zA-Z][^>]*>", hint):
        raise ContentError("힌트는 HTML 없이 한 줄에 한 문장으로 쓰세요")
    if item.get("format") == "short":
        answer = _object(item.get("answer"), "answer")
        canonical = _string(answer.get("canonical"), "answer.canonical")
        accepted = answer.get("accepted")
        if not isinstance(accepted, list) or not all(isinstance(v, str) and v.strip() for v in accepted):
            raise ContentError("answer.accepted에는 허용답 목록이 필요해요")
        solution = item.get("solution")
        if not isinstance(solution, list) or not solution or not all(isinstance(v, str) and v.strip() for v in solution):
            raise ContentError("값 입력형에 풀이 단계가 필요해요")
        expected = compute(item["compute"]) if item.get("compute") is not None else None
        if expected is not None and expected != canonical:
            raise ContentError(f"검산 값 {expected!r}과 정답 {canonical!r}이 달라요")
        return
    if item.get("format") != "mcq":
        raise ContentError("format은 mcq 또는 short여야 해요")
    options = item.get("options")
    if (not isinstance(options, list) or not all(isinstance(o, dict) for o in options)
            or [option.get("id") for option in options] != list(CHOICES)
            or item.get("answer") not in tuple(CHOICES)):
        raise ContentError("객관식은 A~D 보기 네 개와 해당 정답이 필요해요")
    values = set()
    for option in options:
        value = normalize(_string(option.get("text"), "보기"))
        if value in values:
            raise ContentError("같은 보기가 둘 이상 있어요")
        values.add(value)
        _string(option.get("why"), "보기별 설명")
        if option["id"] != item["answer"]:
            _string(option.get("misconception"), "오개념")
            _reference(option.get("source"), topics, problems, sources)
        elif value in normalize(item["title"]):
            raise ContentError("문항 제목에 정답 보기가 들어 있어요")
    if item.get("compute") is not None:
        expected = compute(item["compute"])
        option = options[CHOICES.index(item["answer"])]
        if expected != option.get("value"):
            raise ContentError(f"검산 값 {expected!r}과 정답 보기의 value가 달라요")


def load_data(src, pack=None):
    src = Path(src)
    pack = pack or read_pack(src.parent.parent)
    objectives_doc = _object(json_file(src / "objectives.json"), "objectives.json")
    items_doc = _object(json_file(src / "items.json"), "items.json")
    for doc in (objectives_doc, items_doc):
        if type(doc.get("experiment")) is not int or doc["experiment"] != pack.experiment:
            raise ContentError("저작 데이터와 학습팩 실험 번호가 달라요")
    objectives = _indexed(_rows(objectives_doc, "objectives"), OBJECTIVE_ID, "목표")
    items = _indexed(_rows(items_doc, "items"), ITEM_ID, "문항")
    if len(items) > 16:
        raise ContentError("전체 문항은 16개 이하여야 해요")

    topics = {row["id"]: {(ref["source_id"], ref.get("pdf_page")) for ref in row["sources"]}
              for row in pack.manifest["topics"]}
    sources = {row["id"] for row in pack.manifest["sources"]}
    problems = {row["id"] for row in pack.manifest["problems"]
                if row["status"] == "included" and row["answer_status"] == "verified"}
    for ident, obj in objectives.items():
        try:
            _check_objective(obj, topics, pack.anchors)
        except (ValueError, TypeError) as exc:
            raise ContentError(f"{ident}: {exc}") from exc

    stems = workbook_stems(pack)
    counts = dict.fromkeys(objectives, 0)
    balance = dict.fromkeys(CHOICES, 0)
    negatives = 0
    for ident, item in items.items():
        try:
            oid = item.get("objective")
            if oid not in objectives:
                raise ContentError(f"존재하지 않는 목표예요: {oid!r}")
            _check_item(item, topics, problems, sources)
            stem = item["stem_html"]
            if duplicates(stem, stems):
                raise ContentError("학습팩 문제나 앞 문항과 발문이 겹쳐요")
            stems.append(normalize(plain_html(stem)))
            counts[oid] += 1
            if item["format"] == "mcq":
                balance[item["answer"]] += 1
            if re.search(r"않은|아닌|틀린|옳지", item["title"] + plain_html(stem)):
                negatives += 1
        except (ValueError, TypeError) as exc:
            raise ContentError(f"{ident}: {exc}") from exc
    if any(not 1 <= n <= 2 for n in counts.values()):
        raise ContentError("모든 목표에 문항을 1~2개씩 두세요")
    if sum(balance.values()) >= 4 and max(balance.values()) - min(balance.values()) > 1:
        raise ContentError(f"객관식 정답 위치를 고르게 배치하세요: {balance}")
    if negatives * 4 > len(items):
        raise ContentError("부정형 발문은 전체의 4분의 1 이하여야 해요")
    return {"pack": pack, "objectives": list(objectives.values()), "items": list(items.values())}
