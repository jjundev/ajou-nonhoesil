"""재생성물과 원본을 **계약 필드로만** 대조한다.

`validate.py` 가 한 문서의 내부 정합을 보는 것과 달리, 여기는 **두 문서를**
본다. 격리 재생성의 합격 판정이 사람 눈에 걸려 있으면 매번 기준이 흔들리기
때문이다.

**본문 산문은 보지 않는다.** `expected` 필드·본문 서술은 같은 사실을
다르게 써도 결함이 아니다. 보는 것은 소비자가 실제로 기대는 필드뿐이다 —
프론트매터의 `week`·`experiment`·`title`·`source_manual`·`power`, 항목의
`title`·`device`·`ics`·`tables`, 표의 `title`·`kind`·`encoding`·`source`·
`role` 과 셀 전부. **제목 셋(명세·항목·표 `title`)은 2026-09-01 이후
본다** — 그 전에는 산문과 같이 대조 밖이었다.

`kind: capture` 인 표는 셀이 없어(`header=[]`·`rows=[]`) 대조가 항상 같다고
나온다 — 그 표의 기술적 주장은 전부 `expected` 산문에 있는데 산문은 위
이유로 보지 않기 때문이다. `compare_specs` 는 이 표에서 조용히 통과시킬
뿐이므로, 그 사각지대를 사람에게 알리는 `uncovered_tables` 를 따로 둔다.
"""

from collections import Counter
from pathlib import Path

from . import md
from .spec_parser import _T_HEAD, parse_spec

# 대조 대상. **여기 없는 필드는 달라도 결함이 아니다.**
# `title` 셋(명세·항목·표)은 2026-09-01 에 들어왔다. 명세·항목 `title` 은
# 계약서가 필수(●)로 싣고(`docs/schema/lab-spec-v1.md:22,47`); 표 `title`
# 은 스키마의 표 필드 표에 행 자체가 없고 `## T<n> · <제목>` 헤딩 형식으로
# 강제될 뿐이다(`docs/schema/lab-spec-v1.md:63,65`). 셋 다 `render.py`·
# `record.py` 가 인쇄용 체크리스트와 `기록.md` 헤딩에 그대로 찍는다(확인:
# `grep -n title scripts/lab/render.py scripts/lab/record.py`). 두 회차
# 연속으로 재생성이 다섯 표 제목을 전부 바꿨는데 대조가 0건을 냈다.
_ITEM_FIELDS = ("title", "device", "ics", "tables")
_TABLE_FIELDS = ("title", "kind", "encoding", "source", "role")

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

    # 표 짝짓기를 여기서 미리 해 둔다 — 아래 `_table_id_shift_notice` 와
    # 뒤쪽 `_table_diffs` 가 같은 짝을 쓴다. 두 번 짝지으면 로직이
    # 갈라질 위험이 있어 한 번만 계산한다.
    pairs, only_a, only_b = _pair_tables(a.tables, b.tables)
    shift_notice = _table_id_shift_notice(pairs, ids_a, ids_b)
    if shift_notice:
        out.append(shift_notice)

    # `source_manual` 은 스키마 필수 필드다(`docs/schema/lab-spec-v1.md` 의
    # 프론트매터 표, `필수` 열에 ●). `write-pre-report`·`write-result-report`
    # 두 스킬이 "손으로 짐작하지 않는다 — 명세의 `source_manual` 이 가리킨다"
    # 로 이 필드를 명시적으로 소비한다(확인:
    # `grep -n "source_manual" .claude/skills/write-pre-report/SKILL.md
    # .claude/skills/write-result-report/SKILL.md`). 이 파일 docstring이
    # 내건 기준("소비자가 실제로 기대는 필드")에 정확히 해당하므로 `week`·
    # `experiment` 와 같은 자리에서 대조한다.
    for field in ("week", "experiment", "title", "source_manual"):
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

    out += _table_diffs(pairs, only_a, only_b, a.tables, b.tables)
    return out


def uncovered_tables(spec_path) -> list:
    """`compare_specs` 가 **대조하지 못하는** 표를 이름과 이유로 돌려준다.

    두 갈래를 합쳐 낸다.

    1. `capture` 표는 셀이 없어(`header=[]`·`rows=[]`) 어떤 재생성물과
       짝지어도 `_cells` 가 항상 "같다" 로 본다. 그 표의 기술적 주장은 전부
       `expected` 산문에 있는데, `compare_specs` 는 산문을 보지 않는다 —
       재생성물이 사실을 완전히 뒤집어 써도(예: "상승" → "하강") 차이 0건
       으로 나온다.
    2. 첫 `## T` 헤딩 **앞**의 본문에 마크다운 표가 있으면, 그 표는
       `spec_parser.parse_spec` 이 아예 스캔하지 않는 영역에 있어
       `LabSpec.tables` 에 실리지 않는다 — `compare_specs` 는 그런 표가
       있는지조차 모른다(자세한 내용은 `_preamble_tables` 참고).

    둘 다 `expected` 산문과 마찬가지로 **비교는 하지 않고, 비교 밖이라는
    사실만** 목록으로 낸다. 그렇다고 이 표들을 대조에 넣을 수도 없다 —
    1번은 재생성이 같은 사실을 거의 항상 다른 문장으로 쓰므로 넣으면
    재작문할 때마다 오탐이 나고, 2번은 표 자체가 `## T<n>` 헤딩도
    `kind`/`source` 속성도 없어 `SpecTable` 계약을 애초에 못 채운다. 반대로
    아무 신호도 안 내면 이 사각지대는 조용한 구멍으로 남으므로, 사람이
    원문을 직접 읽고 판단하라는 뜻으로 목록만 낸다.

    capture 표도 머리말 표도 없으면 빈 리스트다.
    """
    spec = parse_spec(spec_path)
    out = [
        f"표 {t.id}: 셀이 없어 대조가 성립하지 않는다 — "
        "`expected` 산문을 사람이 읽어야 한다"
        for t in spec.tables if t.kind == "capture"
    ]
    out += _preamble_table_notice(spec_path)
    return out


def _preamble_table_notice(spec_path) -> list:
    """첫 `## T` 헤딩 **앞**의 본문에 마크다운 표가 있으면 그 사실을 알린다.

    `spec_parser.parse_spec` 은 `_T_HEAD` 로 찾은 첫 `## T` 헤딩부터만 표를
    읽는다(`heads[0].start()` 이전은 스캔하지 않는다). 그 앞에 마크다운
    표가 있으면 `LabSpec.tables` 에 실리지 않으므로 `compare_specs` 도 그
    표를 절대 보지 못한다.

    실측(컨트롤러, 최종 전체-브랜치 리뷰 I1): 실험03 2개, 실험05 1개,
    실험06 1개, 실험01·02·10 은 0개. 실험06 의 그 표가 하필 셀 값 표기
    규약표다 — `0->1` 이 라이징 엣지라는 뜻을 이 표에서만 정의하는데, 그
    뜻을 뒤집어 적어도(`0->1` → 하강 엣지) `compare_specs` 는 차이 0건을
    낸다. 이 함수는 그 원인 하나를 짚어 알릴 뿐 대조하지는 않는다 — 표를
    `tables` 에 실어 대조하게 만들려면 `## T<n>` 헤딩과 `kind`/`source`
    속성을 새로 요구해야 하는데, 그러면 살아 있는 승인본 다섯이 깨진다.

    표 개수를 셀 때는 `md.parse_tables`(이 프로젝트의 유일한 마크다운 표
    파서)를 그대로 쓴다 — 정규식을 새로 만들면 `_T_HEAD`·`md.parse_tables`
    와 셋이 서로 다른 기준으로 "표"를 셀 위험이 있다.
    """
    front, body = md.split_frontmatter(
        Path(spec_path).read_text(encoding="utf-8"))
    heads = list(_T_HEAD.finditer(body))
    preamble = body[:heads[0].start()] if heads else body
    tables = md.parse_tables(preamble)
    if not tables:
        return []
    return [
        f"머리말(첫 `## T` 헤딩 앞)에 마크다운 표가 {len(tables)}개 있다 — "
        "`compare_specs` 는 `## T` 헤딩이 붙은 표만 본다. 뜻을 정의하는 "
        "표(예: 토큰 규약표)가 여기 있으면 그 뜻이 바뀌어도 차이 0건이 "
        "난다"
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


def _table_id_shift_notice(pairs, ids_a, ids_b):
    """짝지은 표 중 ID 가 어긋난 것이 있으면 요약 한 줄로 경고한다. 없으면 `None`.

    `_pair_tables` 는 `source` 로 짝지으므로 원본 `Tx` 가 재생성 `Ty`(x≠y)
    와 묶일 수 있다. 그 짝의 필드·셀이 완전히 같으면(표 몸통은 그대로 두고
    ID·제목만 바뀐 경우가 실제로 그렇다) `_table_diffs` 는 그 짝에 대해
    **아무 줄도 내지 않는다** — `compare_specs` 가 "차이 0건 = 합격"으로
    쓰이므로, 표 몸통이 다른 ID 로 옮겨간 명세가 조용히 합격 처리된다.
    이 함수가 그 사각지대를 메운다.

    짝마다 한 줄을 내면 정당한 밀림(표 추가로 뒤 ID 가 전부 한 칸씩 밀리는
    흔한 경우)에서도 밀린 짝 수만큼 줄이 늘어난다 — 실측: 실험01 8줄,
    실험06 4줄, 실험03 3줄. 그래서 어긋난 짝 전부를 **하나의 요약 줄**로
    묶는다.

    **원인을 단정할 수 있는 경우와 없는 경우가 갈린다.**

    - `ids_a == ids_b` (표 ID 집합이 같다): 표를 넣거나 뺀 흔적이 없는데
      짝이 어긋났다. 표 추가·삭제로는 설명되지 않으므로, 표 내용이 서로
      다른 ID 로 옮겨갔을 가능성을 **강하게 경고**해도 근거가 있다.
    - `ids_a != ids_b`: 표가 추가·삭제됐다는 사실 자체는 위쪽
      `_table_id_mismatch_notice` 가 이미 알렸지만, **이 짝짓기 어긋남의
      원인까지는 코드가 판별할 수 없다.** "표 추가·삭제로 ID 가 밀렸다"
      와 "표 내용이 다른 ID 로 옮겨갔다"는 **같은 관측 결과**(source 로
      짝지었더니 ID 가 다르다)를 낳는다 — 실험06 에서 정당한 밀림과
      "밀림 + 내용이동"을 각각 재현하면 건수가 똑같이 8건이고, 다른 것은
      화살표 목록의 점프 폭(`T3→T5` 처럼 이웃보다 큰 폭)뿐이었다. 그래서
      이 경우는 원인을 하나로 단정하지 않고 관측 사실과 두 가능성을
      함께 적는다. "오프셋이 전부 같은지" 같은 새 판별 로직은 넣지
      않는다 — 오프셋도 순서 보존도 이 두 경우를 안정적으로 가르지
      못한다(실측). 문구를 정직하게 하는 것으로 그친다.
    """
    mismatched = sorted(
        ((t_a.id, t_b.id) for t_a, t_b in pairs if t_a.id != t_b.id),
        key=lambda pair: pair[0],
    )
    if not mismatched:
        return None
    labels = ", ".join(f"{a_id}→{b_id}" for a_id, b_id in mismatched)
    if ids_a == ids_b:
        return (
            f"[표 ID 가 어긋난 채 짝지어졌다] {labels} — 원본과 재생성의 "
            "표 ID 집합은 같은데 이 짝들은 source 기준으로 서로 다른 ID 에 "
            "붙었다. 표를 넣거나 뺀 흔적이 없으므로, 표 내용이 서로 다른 "
            "ID 로 옮겨갔을 수 있다는 뜻이다. 아래 표 대조는 이 짝짓기를"
            " 신뢰한 결과이니 원문을 직접 대조해 확인하라."
        )
    return (
        f"[표 ID 가 어긋난 채 짝지어졌다] {labels} — source 로 짝지은 결과 "
        "이 짝들의 ID 가 원본과 재생성에서 다르다. 위에서 이미 알린 표 "
        "추가·삭제로 ID 가 밀린 것일 수도, 표 내용이 서로 다른 ID 로 "
        "옮겨간 것일 수도 있다 — 이 둘은 같은 관측 결과를 낳아 코드가 "
        "구별할 수 없다. 화살표가 고르게 밀리지 않았거나 중간이 건너뛰면 "
        "후자를 의심하라."
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
    실험05 는 6개 중 5개, 실험01 은 9개 중 5개다.

    **정확한 건수는 픽스처마다 다르다 — 하나로 우기지 않는다.** 잴 수
    있는 것은 방향뿐이다: 표 하나를 정당하게 끼워 뒤 ID 를 전부 미는
    사본에서, 셀은 하나도 안 건드렸는데도 derived 를 매칭 키에서 빼면
    나던 셀 차이가 derived 를 키로 쓰면 사라진다. 실측 예시 하나(픽스처:
    `실험01/체크리스트/명세.md` 를 `T2`~`T9` 전부 한 칸씩 밀고 `T2` 를
    `source: manual:p99` 로 새로 끼운 사본 —
    `tests/test_lab_specdiff.py` 의 `_shifted(WEEK2, 2, 9)` 와 동일)로는
    derived 를 뺀 매칭이 21건(그중 셀 차이 8건, `T3`·`T4` 의 `derived`
    식이 밀려 다른 표와 짝지어진 탓)이었고, derived 를 키로 쓰면 6건으로
    줄었다 — 진행 원장의 실험01 실측(19→4~5건)과 최종 리뷰어의 합성
    픽스처(21→6)가 서로 다른 것도 이 때문이다: 같은 방향이지만 픽스처가
    다르면 건수도 달라진다.

    식이 잘못 옮겨진 표는 **ID 짝짓기로 구제되지 않는다** — 상대 문서의
    같은 ID 가 이미 (올바른 source 로) 다른 표와 짝지어져 있으면, 아래
    2차 루프의 `t.id not in matched_b`(또는 `matched_a`) 조건에 걸려
    정작 오기재된 그 표 자신은 끝까지 짝을 못 찾는다(실측: 실험01 을
    밀고 `T3` 의 식을 오기재하면 `표 T3: source '...' 가 재생성 어디에도
    없다 (...)`, `표 T4: source '...' 가 원본 어디에도 없다 (...)` 로
    나온다 — `_table_diffs` 참고). 소실은 아니지만(둘 다 여전히 보고된다),
    어느 표가 못 짝졌는지만 말할 뿐 무엇이 어떻게 틀렸는지(정확한 텍스트
    차이)까지는 말해주지 않는다. `derived` 를 매칭 키에서 빼도 이 사각지대는
    그대로였다 — 빼면 이 코퍼스 절반의 정상적인 밀림 정렬까지 함께 깨져
    오정렬 소음만 늘어난다.

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


def _table_diffs(pairs, only_a, only_b, a_tables, b_tables) -> list:
    """짝지은 표는 필드·셀을 대조하고, 짝을 못 지은 표는 네 갈래로 나눠 보고한다.

    "한쪽에만 있다" 한 문구로는 **진짜 삭제/추가**(내용이 정말 한쪽에만
    있음)와 **정렬 부작용**(source 짝짓기가 원본 `Tx` 를 재생성 `Ty`(x≠y)
    와 묶어서 원본 `Ty` 와 재생성 `Tx` 가 둘 다 짝을 잃은 것)이 같은 말로
    나온다. 갈리는 기준은 **`source` 가 상대 문서에 존재하는가** 다 —
    `source` 는 그 표가 무엇에서 왔는지를 가리키는 좌표라 밀리지 않으므로,
    상대 문서에 그 source 가 아예 없으면 그 표는 정말 한쪽에만 있는
    것이다. `only_a` 의 표 `t` 에 대해(`only_b` 는 대칭):

    1. `t.source` 가 아예 없다 → **source 유무를 ID 유무보다 먼저 본다.**
       source 가 없으면 ID 가 상대편에 있든 없든 "판별할 수 없다"는
       참이므로 이 갈래가 맨 앞이다. `SpecTable.source` 는
       `Optional[str]` 이라 재생성이 표를 새로 끼우며 `- source:` 줄을
       빠뜨리면 여기로 떨어지는데, 그냥 "짝을 못 지었다"로만 찍으면
       신규 표가 정렬 잡음처럼 읽힌다. ID 가 상대편에 있는지 여부는
       이 줄 안에 함께 싣는다 — 예전에는 이 검사가 갈래 2 뒤에 있어서,
       source 가 없어도 ID 가 상대 범위를 벗어나기만 하면 갈래 2("정말
       한쪽에만 있다")로 잘못 단정됐다(실측: 같은 표 하나가 원본·재생성
       양쪽에서 서로 다른 줄로 나오고 한쪽은 "재생성에만 있다"는 거짓
       단정이었다).
    2. `t.source` 는 있지만 `t.id` 가 상대의 ID 집합에 아예 없다 → 정말
       한쪽에만 있다.
    3. `t.id` 는 상대에 있지만 `t.source` 가 상대의 source 집합에는
       없다 → **관측한 사실만** 말한다: 이 source 가 상대 문서 어디에도
       없다는 것. 원인은 둘 중 하나일 수 있다 — 표가 정말 빠졌거나,
       source 가 잘못 옮겨졌거나(내용 자체는 상대에 다른 source 로
       멀쩡히 있을 수 있다). 어느 쪽인지 이 함수는 판정하지 않고, 상대에
       같은 ID 가 있다는 사실만 함께 싣는다.
    4. 그 외(source 가 있고 상대편에도 있는데 짝짓기만 실패) → 진짜
       유무는 알 수 없고 그저 짝을 못 지은 것이다.

    **문구는 서로 부분 문자열이 되지 않는다.** 이전에는 "원본에만 있다"
    가 "원본에만 있는 표다"의 부분 문자열이라, 문구로 거르는 소비자가
    한 갈래를 통째로 놓쳤다(`tests/test_lab_specdiff.py` 의 갈래 구별
    회귀 테스트 참고).

    `a_tables`/`b_tables` 는 `compare_specs` 가 이미 가진 원본·재생성의
    전체 표 목록이다 — `pairs`/`only_a`/`only_b` 에서 ID·source 집합을
    다시 만들면 그 셋과 어긋날 때 메시지가 거짓말을 하므로, 여기서
    새로 구하지 않고 그대로 받는다.
    """
    b_ids = {t.id for t in b_tables}
    b_sources = {t.source for t in b_tables if t.source}
    a_ids = {t.id for t in a_tables}
    a_sources = {t.source for t in a_tables if t.source}

    out = []
    for t in sorted(only_a, key=lambda t: t.id):
        if not t.source:
            id_note = ("재생성에도 같은 ID 가 있다" if t.id in b_ids
                       else "재생성에는 같은 ID 도 없다")
            where = f"짝을 못 지었다 (source 가 없어 판별할 수 없다; {id_note})"
        elif t.id not in b_ids:
            where = "원본에만 있다"
        elif t.source not in b_sources:
            where = (f"source {t.source!r} 가 재생성 어디에도 없다 "
                     "(표가 빠졌거나 source 가 잘못 옮겨졌을 수 있다). "
                     "재생성에도 같은 ID 가 있다")
        else:
            where = "짝을 못 지었다 (재생성에도 같은 ID 가 있다)"
        out.append(f"표 {t.id}: {where}")
    for t in sorted(only_b, key=lambda t: t.id):
        if not t.source:
            id_note = ("원본에도 같은 ID 가 있다" if t.id in a_ids
                       else "원본에는 같은 ID 도 없다")
            where = f"짝을 못 지었다 (source 가 없어 판별할 수 없다; {id_note})"
        elif t.id not in a_ids:
            where = "재생성에만 있다"
        elif t.source not in a_sources:
            where = (f"source {t.source!r} 가 원본 어디에도 없다 "
                     "(표가 새로 추가됐거나 source 가 잘못 옮겨졌을 수 있다). "
                     "원본에도 같은 ID 가 있다")
        else:
            where = "짝을 못 지었다 (원본에도 같은 ID 가 있다)"
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
