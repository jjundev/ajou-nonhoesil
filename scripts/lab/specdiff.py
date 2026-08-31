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

from collections import Counter

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

    # 표 ID 집합이 다르면 다른 무엇보다 먼저 알린다 — 표 추가·삭제로
    # 이후 ID 가 밀리면 순서 상관없이 아래 표 대조 결과 전체가 오정렬을
    # 의심해야 하는 상태이기 때문이다. 아래에서 실제 짝짓기는 가능하면
    # `source` 로 하지만(밀리지 않는다), 이 알림 자체는 ID 집합만으로
    # 낸다 — source 로 완전히 구제되는 경우에도 "표가 추가·삭제됐다"는
    # 사실 자체는 읽는 사람에게 여전히 유의미하다.
    ids_a = {t.id for t in a.tables}
    ids_b = {t.id for t in b.tables}
    if ids_a != ids_b:
        out.append(_table_id_mismatch_notice(ids_a, ids_b))

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

    pairs, only_a, only_b = _pair_tables(a.tables, b.tables)
    out += _table_diffs(pairs, only_a, only_b)
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


def _table_id_mismatch_notice(ids_a, ids_b) -> str:
    """표 ID 집합이 다르다는 사실을, 다른 어떤 표 차이보다도 먼저 알린다.

    실측: 재생성이 교안의 표를 하나 더 정당하게 실으면(예: 이론표를 `T2`
    로 끼워 넣음) 그 뒤 모든 표의 ID 가 한 칸씩 밀린다. ID 만 보고 짝지으면
    원본 `T3` 과 재생성 `T3` 이 서로 다른 표인데도 짝지어져, 셀 내용이
    완전히 같아도 차이가 쏟아진다 — 실측 19건, 그중 진짜 내용 오류는
    0건이었다. 이 함수는 그 오정렬 가능성 자체를 먼저 경고해, 아래에
    나오는 표 관련 차이를 읽는 사람이 "ID 정렬이 어긋났을 수 있다"는
    전제를 깔고 읽게 한다.
    """
    only_a = sorted(ids_a - ids_b)
    only_b = sorted(ids_b - ids_a)
    return (
        f"[표 ID 집합이 다르다] 원본에만 있는 ID {only_a} / "
        f"재생성에만 있는 ID {only_b} — 표가 추가·삭제되면 그 뒤 ID 가 "
        "전부 밀릴 수 있다. 아래 표 대조는 `source` 가 양쪽에서 유일하게 "
        "일치하는 표를 먼저 그것으로 짝짓고, source 로 못 짝지은 나머지만 "
        "ID 로 짝졌다 — ID 로 짝진 표는 실제로는 다른 표를 비교한 것일 "
        "수 있으니 먼저 의심하라."
    )


def _pair_tables(a_tables, b_tables):
    """원본과 재생성의 표를 짝짓는다. 표는 최대 한 짝에만 쓰인다.

    ID 는 표가 추가·삭제되면 그 뒤 전부 밀린다(`_table_id_mismatch_notice`
    참고) — 이 코퍼스에서 실제로 일어났다. `source`(`manual:p9` 든
    `derived (Y = A·B·C)` 든)는 그 표가 무엇에서 왔는지를 가리키는
    좌표라 밀리지 않으므로, 두 문서 모두에서 **유일하게** 등장하는
    source 를 우선 매칭 키로 쓴다.

    **`derived (...)` 도 키로 쓴다.** 처음엔 뺐는데, 이 코퍼스의 절반이
    derived 라 그러면 오정렬이 그대로 남는다 — 실험03 은 표 4개가 전부,
    실험05 는 6개 중 5개, 실험01 은 9개 중 5개다. 실측으로 실험01 에서
    19건(셀 차이 8건)이 4건으로 줄었다. 식이 잘못 옮겨졌으면 그냥 ID
    짝짓기로 떨어질 뿐이라 빼서 얻는 것이 없었다.

    source 가 없거나 한쪽 문서 안에서 중복이면 믿을 수 없으므로 쓰지
    않는다 — 그런 표는 ID 로 짝짓고, ID 매칭은 여전히 밀림에 취약하다.

    반환: `(짝 목록[(원본표, 재생성표), ...], 원본에만 있는 표 목록,
    재생성에만 있는 표 목록)`.
    """
    def source_counts(tables):
        return Counter(t.source for t in tables if t.source)

    a_src_counts = source_counts(a_tables)
    b_src_counts = source_counts(b_tables)

    pairs = []
    matched_a, matched_b = set(), set()

    # 1차: source 가 양쪽에서 유일하게 일치하는 표부터 짝짓는다.
    for t in a_tables:
        src = t.source
        if src and a_src_counts[src] == 1 and b_src_counts.get(src) == 1:
            match = next(u for u in b_tables if u.source == src)
            pairs.append((t, match))
            matched_a.add(t.id)
            matched_b.add(match.id)

    # 2차: source 로 못 짝지은 나머지는 ID 로 짝짓는다(기존 방식).
    b_by_id = {t.id: t for t in b_tables}
    for t in a_tables:
        if t.id in matched_a:
            continue
        if t.id in b_by_id and t.id not in matched_b:
            pairs.append((t, b_by_id[t.id]))
            matched_a.add(t.id)
            matched_b.add(t.id)

    only_a = [t for t in a_tables if t.id not in matched_a]
    only_b = [t for t in b_tables if t.id not in matched_b]
    return pairs, only_a, only_b


def _table_diffs(pairs, only_a, only_b) -> list:
    """짝지은 표는 필드·셀을 대조하고, 짝을 못 지은 표는 그렇게만 보고한다.

    **"한쪽에만 있다" 와 "짝을 못 지었다" 를 구별한다.** source 짝짓기가
    원본 `Tx` 를 재생성 `Ty`(x≠y) 와 묶으면 원본 `Ty` 와 재생성 `Tx` 가
    둘 다 짝을 잃는데, 그것을 "한쪽에만 있다" 로 찍으면 **양쪽 문서에 다
    있는 ID 를 없다고 말하는 셈**이라 읽는 사람이 오독한다.
    """
    a_ids = {t.id for t in only_a} | {p[0].id for p in pairs}
    b_ids = {t.id for t in only_b} | {p[1].id for p in pairs}
    out = []
    for t in sorted(only_a, key=lambda t: t.id):
        where = "짝을 못 지었다 (재생성에도 같은 ID 가 있다)" \
            if t.id in b_ids else "원본에만 있다"
        out.append(f"표 {t.id}: {where}")
    for t in sorted(only_b, key=lambda t: t.id):
        where = "짝을 못 지었다 (원본에도 같은 ID 가 있다)" \
            if t.id in a_ids else "재생성에만 있다"
        out.append(f"표 {t.id}: {where}")
    for t_a, t_b in sorted(pairs, key=lambda p: p[0].id):
        label = t_a.id if t_a.id == t_b.id else f"{t_a.id}→{t_b.id}"
        for field in _TABLE_FIELDS:
            x, y = getattr(t_a, field), getattr(t_b, field)
            if x != y:
                out.append(f"표 {label} {field}: 원본 {x!r} / 재생성 {y!r}")
        out += _cells(label, t_a, t_b)
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
