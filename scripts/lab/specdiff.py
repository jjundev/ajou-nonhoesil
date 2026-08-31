"""재생성물과 원본을 **계약 필드로만** 대조한다.

`validate.py` 가 한 문서의 내부 정합을 보는 것과 달리, 여기는 **두 문서를**
본다. 격리 재생성의 합격 판정이 사람 눈에 걸려 있으면 매번 기준이 흔들리기
때문이다.

**산문은 보지 않는다.** 제목·`expected`·본문 서술은 같은 사실을 다르게 써도
결함이 아니다. 보는 것은 소비자가 실제로 기대는 필드뿐이다 — 프론트매터의
`week`·`experiment`·`power`, 항목의 `device`·`ics`·`tables`, 표의 `kind`·
`encoding`·`source`·`role` 과 셀 전부.

`kind: capture` 인 표는 셀이 없어(`header=[]`·`rows=[]`) 대조가 항상 같다고
나온다 — 그 표의 기술적 주장은 전부 `expected` 산문에 있는데 산문은 위
이유로 보지 않기 때문이다. `compare_specs` 는 이 표에서 조용히 통과시킬
뿐이므로, 그 사각지대를 사람에게 알리는 `uncovered_tables` 를 따로 둔다.
"""

from .spec_parser import parse_spec

# 대조 대상. **여기 없는 필드는 달라도 결함이 아니다.**
_ITEM_FIELDS = ("device", "ics", "tables")
_TABLE_FIELDS = ("kind", "encoding", "source", "role")

# 이 셋은 "무엇을 참조하는가" 의 목록이라 순서에 의미가 없다 — 재생성물이
# 같은 IC·소자·표를 다른 순서로 적는 것은 결함이 아니다. `sorted()` 로
# 비교한다. `set` 을 쓰면 중복까지 뭉개져 `["A","A","B"]` 와 `["A","B"]`
# 가 같아지므로 쓰지 않는다. 반면 `_TABLE_FIELDS` 는 전부 스칼라(문자열)라
# 순서 개념이 아예 없고, 셀(`rows`)과 헤더(`header`)는 순서 자체가 값이라
# (어느 열이 무엇인지, 어느 행이 어느 입력 조합인지) `_cells` 에서 지금처럼
# 순서 민감 비교를 그대로 둔다.
_UNORDERED_LIST_FIELDS = {"device", "ics", "tables"}


def compare_specs(original, regenerated) -> list:
    """두 명세의 계약 필드를 대조해 차이를 줄 목록으로 돌려준다.

    같으면 빈 리스트다. 파싱조차 안 되면 대조 이전의 문제이므로
    `SpecError` 를 그대로 올려보낸다 — 여기서 삼키면 "차이 없음" 과
    "읽지도 못함" 이 구별되지 않는다.
    """
    a, b = parse_spec(original), parse_spec(regenerated)
    out = []

    for field in ("week", "experiment"):
        x, y = getattr(a, field), getattr(b, field)
        if x != y:
            out.append(f"프론트매터 {field}: 원본 {x!r} / 재생성 {y!r}")

    if sorted(a.power) != sorted(b.power):
        out.append(f"전원 레일 이름: 원본 {sorted(a.power)} / "
                   f"재생성 {sorted(b.power)}")
    else:
        for rail in sorted(a.power):
            if a.power[rail] != b.power[rail]:
                out.append(f"전원 {rail}: 원본 {a.power[rail]!r} / "
                           f"재생성 {b.power[rail]!r}")

    out += _by_id("항목", {i.id: i for i in a.items},
                  {i.id: i for i in b.items}, _ITEM_FIELDS)
    out += _by_id("표", {t.id: t for t in a.tables},
                  {t.id: t for t in b.tables}, _TABLE_FIELDS)

    shared = sorted({t.id for t in a.tables} & {t.id for t in b.tables})
    for tid in shared:
        out += _cells(tid, a.table(tid), b.table(tid))
    return out


def uncovered_tables(spec_path) -> list:
    """`compare_specs` 가 **대조하지 못하는** 표를 이름과 이유로 돌려준다.

    `capture` 표는 셀이 없어(`header=[]`·`rows=[]`) 어떤 재생성물과 짝지어도
    `_cells` 가 항상 "같다" 로 본다. 그 표의 기술적 주장은 전부 `expected`
    산문에 있는데, `compare_specs` 는 산문을 보지 않는다 — 재생성물이 사실을
    완전히 뒤집어 써도(예: "상승" → "하강") 차이 0건으로 나온다.

    그렇다고 `expected` 를 대조에 넣을 수도 없다. 재생성은 같은 사실을 거의
    항상 다른 문장으로 쓰므로, 넣으면 재작문할 때마다 오탐이 난다. 반대로
    아무 신호도 안 내면 이 사각지대는 조용한 구멍으로 남는다. 그래서 이
    함수는 **비교는 하지 않고, 비교 밖이라는 사실만** 목록으로 낸다 — 이
    표들은 사람이 `expected` 원문을 직접 읽고 판단해야 한다는 뜻이다.

    capture 표가 없으면 빈 리스트다.
    """
    spec = parse_spec(spec_path)
    return [
        f"표 {t.id}: 셀이 없어 대조가 성립하지 않는다 — "
        "`expected` 산문을 사람이 읽어야 한다"
        for t in spec.tables if t.kind == "capture"
    ]


def _by_id(label, av, bv, fields) -> list:
    """ID 로 짝지어 대조한다. 한쪽에만 있는 것도 보고한다.

    `_UNORDERED_LIST_FIELDS` 에 속한 필드는 `sorted()` 로 순서를 무시하고
    비교한다. 메시지에는 실제 순서 그대로의 원본값을 보여준다 — 순서만
    다르면 이 분기에 아예 들어오지 않으므로, 여기 나온 차이는 항상
    내용 차이다.
    """
    out = [f"{label} {k}: 원본에만 있다" for k in sorted(set(av) - set(bv))]
    out += [f"{label} {k}: 재생성에만 있다" for k in sorted(set(bv) - set(av))]
    for key in sorted(set(av) & set(bv)):
        for field in fields:
            x, y = getattr(av[key], field), getattr(bv[key], field)
            if field in _UNORDERED_LIST_FIELDS:
                same = sorted(x) == sorted(y)
            else:
                same = x == y
            if not same:
                out.append(f"{label} {key} {field}: 원본 {x!r} / 재생성 {y!r}")
    return out


def _cells(tid, a, b) -> list:
    """셀 대조. 헤더나 행 수가 다르면 그것만 보고하고 셀은 안 본다 —
    어긋난 표에서 셀을 짝지으면 어긋난 자리마다 줄이 나와 목록이 못 읽게 된다.
    """
    if a.header != b.header:
        return [f"표 {tid} 헤더: 원본 {a.header} / 재생성 {b.header}"]
    if len(a.rows) != len(b.rows):
        return [f"표 {tid} 행 수: 원본 {len(a.rows)}행 / "
                f"재생성 {len(b.rows)}행"]
    out = []
    for n, (ra, rb) in enumerate(zip(a.rows, b.rows), start=1):
        if len(ra) != len(rb):
            out.append(f"표 {tid} 행{n} 셀 수: 원본 {len(ra)} / 재생성 {len(rb)}")
            continue
        for i, (ca, cb) in enumerate(zip(ra, rb)):
            if ca != cb:
                col = a.header[i] if i < len(a.header) else f"열{i + 1}"
                out.append(f"표 {tid} 행{n} {col}: 원본 {ca!r} / 재생성 {cb!r}")
    return out
