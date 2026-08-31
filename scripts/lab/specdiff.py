"""재생성물과 원본을 **계약 필드로만** 대조한다.

`validate.py` 가 한 문서의 내부 정합을 보는 것과 달리, 여기는 **두 문서를**
본다. 격리 재생성의 합격 판정이 사람 눈에 걸려 있으면 매번 기준이 흔들리기
때문이다.

**산문은 보지 않는다.** 제목·`expected`·본문 서술은 같은 사실을 다르게 써도
결함이 아니다. 보는 것은 소비자가 실제로 기대는 필드뿐이다 — 프론트매터의
`week`·`experiment`·`power`, 항목의 `device`·`ics`·`tables`, 표의 `kind`·
`encoding`·`source`·`role` 과 셀 전부.
"""

from .spec_parser import parse_spec

# 대조 대상. **여기 없는 필드는 달라도 결함이 아니다.**
_ITEM_FIELDS = ("device", "ics", "tables")
_TABLE_FIELDS = ("kind", "encoding", "source", "role")


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


def _by_id(label, av, bv, fields) -> list:
    """ID 로 짝지어 대조한다. 한쪽에만 있는 것도 보고한다."""
    out = [f"{label} {k}: 원본에만 있다" for k in sorted(set(av) - set(bv))]
    out += [f"{label} {k}: 재생성에만 있다" for k in sorted(set(bv) - set(av))]
    for key in sorted(set(av) & set(bv)):
        for field in fields:
            x, y = getattr(av[key], field), getattr(bv[key], field)
            if x != y:
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
