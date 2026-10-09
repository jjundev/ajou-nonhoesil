"""`scripts.lab.photo_label` — LED 판독 패턴에서 진리표 행을 역산해 사진 이름을 짓는다.

픽스처는 저장소의 승인된 실험05·실험04 명세와 결선도 사이드카다. 1-2·2-2 패턴은
2026-10-09 세션에서 사진 16장을 손으로 판독·라벨한 결과(main 9cb57ad)를 그대로 옮겼다.
"""
from pathlib import Path

import pytest

from scripts.lab import photo_label as pl

ROOT = Path(__file__).resolve().parents[1]


def _one_hot(n, k):
    return ''.join('1' if i == k else '0' for i in range(n))


# ---------------- LED 순서·극성 ----------------

def test_led_order_follows_board_rows_not_table_columns():
    leds = pl.led_order(5, '1-2', root=ROOT)
    assert [l.signal for l in leds] == ['Y0', 'Y1', 'Y2', 'Y3', 'Y4', 'Y5', 'Y9', 'Y6', 'Y8', 'Y7']
    assert all(l.active_low for l in leds)
    assert all(l.table == 'T1' for l in leds)


def test_led_order_active_high_when_sidecar_says_nothing():
    leds = pl.led_order(5, '2-2', root=ROOT)
    assert [l.signal for l in leds] == ['A3', 'A2', 'A1', 'A0']
    assert not any(l.active_low for l in leds)


def test_led_order_finds_final_sidecar_with_underscore_name():
    # 실험01 완성본 이름 `3입력_AND` 에 밑줄이 있다 — 단계·걷기 파일만 거른다
    leds = pl.led_order(1, '1-1', root=ROOT)
    assert [l.signal for l in leds] == ['L1', 'L2']  # 중간단 L1 도 LED 다


def test_led_order_missing_sidecar_raises():
    with pytest.raises(pl.LabelError):
        pl.led_order(5, '9-9', root=ROOT)


# ---------------- 역산 ----------------

E5_12 = {  # 위에서 k 번째 LED 하나만 켜짐 → 입력 비트
    0: '0000', 1: '0001', 2: '0010', 3: '0011', 4: '0100',
    5: '0101', 6: '1001', 7: '0110', 8: '1000', 9: '0111',
}


def test_bcd_decoder_session_labels_reproduce():
    reads = [(f'p{k}.jpg', _one_hot(10, k)) for k in range(10)]
    res = pl.resolve(5, '1-2', reads, root=ROOT)
    assert [r.status for r in res.rows] == ['unique'] * 10
    assert {r.source: r.bits for r in res.rows} == {f'p{k}.jpg': b for k, b in E5_12.items()}
    assert all(r.check == '✓' for r in res.rows)
    assert res.problems == []


def test_bcd_decoder_is_order_sensitive():
    reads = [(f'p{k}.jpg', _one_hot(10, k)) for k in range(10)]
    res = pl.resolve(5, '1-2', reads, root=ROOT)
    assert res.order_sensitive  # 열 순서로 읽으면 Y9·Y6·Y8·Y7 자리 라벨이 바뀐다


def test_excess3_session_labels_reproduce_and_not_order_sensitive():
    reads = [('a.jpg', '0011'), ('b.jpg', '0100'), ('c.jpg', '0101'),
             ('d.jpg', '0110'), ('e.jpg', '0111'), ('f.jpg', '1000')]
    res = pl.resolve(5, '2-2', reads, root=ROOT)
    assert [r.bits for r in res.rows] == ['000001', '000010', '000100', '001000', '010000', '100000']
    assert not res.order_sensitive
    assert res.problems == []


def test_pattern_matching_no_row_is_none():
    res = pl.resolve(5, '2-2', [('x.jpg', '1111')], root=ROOT)
    assert res.rows[0].status == 'none'
    assert res.rows[0].bits is None
    assert res.problems


def test_duplicate_rows_are_flagged():
    res = pl.resolve(5, '2-2', [('a.jpg', '0011'), ('b.jpg', '0011')], root=ROOT)
    assert {r.status for r in res.rows} == {'duplicate'}
    assert res.problems


def test_wrong_pattern_length_raises():
    with pytest.raises(pl.LabelError):
        pl.resolve(5, '2-2', [('a.jpg', '001')], root=ROOT)


def test_non_injective_table_is_ambiguous():
    # 실험04 1-1 4x1 MUX — 출력 하나라 같은 패턴의 행이 여럿이다
    res = pl.resolve(4, '1-1', [('a.jpg', '1')], root=ROOT)
    assert res.rows[0].status == 'ambiguous'
    assert len(res.rows[0].candidates) > 1


# ---------------- 사용자가 준 입력 ----------------

def test_assign_overrides_and_records_observed_value():
    # D1 을 넣었는데 0011 이 나왔다고 가정 — 관찰값을 확인 칸에 남긴다
    res = pl.resolve(5, '2-2', [('a.jpg', '0011')], assign={'a.jpg': '000010'}, root=ROOT)
    r = res.rows[0]
    assert r.status == 'assigned'
    assert r.bits == '000010'
    assert r.check != '✓'
    assert r.observed == {'A3': '0', 'A2': '0', 'A1': '1', 'A0': '1'}


def test_sequence_labels_by_row_order():
    rows_patterns = ['0011', '0100', '0101', '0110', '0111', '1000']
    reads = [(f'{i}.jpg', p) for i, p in enumerate(rows_patterns)]
    res = pl.resolve(5, '2-2', reads, sequence=True, root=ROOT)
    assert [r.status for r in res.rows] == ['assigned'] * 6
    assert all(r.check == '✓' for r in res.rows)


def test_assign_unknown_input_is_problem():
    res = pl.resolve(5, '2-2', [('a.jpg', '0011')], assign={'a.jpg': '111111'}, root=ROOT)
    assert res.rows[0].status == 'none'
    assert res.problems


# ---------------- 복사 ----------------

def test_apply_copies_with_rule_names_and_keeps_source(tmp_path):
    src = tmp_path / 'src'
    src.mkdir()
    (src / '1.jpg').write_bytes(b'x')
    dest = tmp_path / '실험사진'
    res = pl.resolve(5, '2-2', [(str(src / '1.jpg'), '0011')], root=ROOT)
    written = pl.apply(res, dest)
    assert [p.name for p in written] == ['2-2 000001.jpg']
    assert (src / '1.jpg').exists()


def test_apply_refuses_existing_destination(tmp_path):
    src = tmp_path / '1.jpg'
    src.write_bytes(b'new')
    dest = tmp_path / '실험사진'
    dest.mkdir()
    (dest / '2-2 000001.jpg').write_bytes(b'old')
    res = pl.resolve(5, '2-2', [(str(src), '0011')], root=ROOT)
    with pytest.raises(pl.LabelError):
        pl.apply(res, dest)
    assert (dest / '2-2 000001.jpg').read_bytes() == b'old'


def test_apply_refuses_when_problems(tmp_path):
    src = tmp_path / '1.jpg'
    src.write_bytes(b'x')
    res = pl.resolve(5, '2-2', [(str(src), '1111')], root=ROOT)
    with pytest.raises(pl.LabelError):
        pl.apply(res, tmp_path / 'out')
