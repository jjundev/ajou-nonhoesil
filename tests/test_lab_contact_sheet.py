"""시트 캡션의 켜짐·꺼짐은 LED 극성을 따른다.

2026-10-09 실험05 1-2(74HC42, Active Low)의 시트 캡션이 전부 뒤집혀 나왔다 —
`0` 을 늘 꺼짐으로 찍어 켜진 LED 하나가 꺼짐, 꺼진 아홉이 켜짐으로 적혔다.
"""
import unittest

from scripts.lab import contact_sheet
from scripts.lab.contact_sheet import ItemRecord, _caption


def _rec():
    return ItemRecord(id="E5.P1-2", title="실험 1-2) x", token="1-2",
                      inputs=["A"], outputs=["Y0", "Y1"],
                      rows={"0": (["0", "1"], "✓")})


class TestCaptionPolarity(unittest.TestCase):
    def test_Active_High_는_1이_켜짐이다(self):
        self.assertTrue(_caption(_rec(), "0").endswith("Y0 꺼짐 · Y1 켜짐"))

    def test_Active_Low_는_0이_켜짐이다(self):
        cap = _caption(_rec(), "0", frozenset({"Y0", "Y1"}))
        self.assertTrue(cap.endswith("Y0 켜짐 · Y1 꺼짐"))

    def test_실험05_디코더는_사이드카에서_Active_Low_를_읽는다(self):
        plans, _, _ = contact_sheet.plan(5, only="1-2")
        self.assertIn("Y0 켜짐 · Y1 꺼짐", plans[0].captions[0])

    def test_실험05_인코더는_Active_High_그대로다(self):
        plans, _, _ = contact_sheet.plan(5, only="2-2")
        self.assertIn("A3 꺼짐 · A2 꺼짐 · A1 켜짐 · A0 켜짐", plans[0].captions[0])


class TestCaptionWrap(unittest.TestCase):
    def test_긴_캡션은_타일_폭_안에서_줄을_바꾼다(self):
        font = contact_sheet._font(30)
        cap = "Bit3=0 Bit2=0 Bit1=0 Bit0=0  →  " + " · ".join(f"Y{i} 꺼짐" for i in range(10))
        lines = contact_sheet._wrap(cap, font, 1000)
        self.assertGreater(len(lines), 1)
        for ln in lines:
            self.assertLessEqual(font.getlength(ln), 1000 - 2 * contact_sheet.CAPTION_PAD)
        self.assertEqual(" · ".join(lines), cap)

    def test_짧은_캡션은_한_줄_그대로다(self):
        font = contact_sheet._font(30)
        self.assertEqual(contact_sheet._wrap("A=0 B=0  →  L1 꺼짐 · L2 꺼짐", font, 1000),
                         ["A=0 B=0  →  L1 꺼짐 · L2 꺼짐"])


class TestSlug(unittest.TestCase):
    def test_괄호는_파일명에서_뺀다(self):
        self.assertEqual(contact_sheet._slug("실험 1-2) BCD to Decimal Decoder (4x16 Decoder)"),
                         "BCD_to_Decimal_Decoder_4x16_Decoder")


if __name__ == "__main__":
    unittest.main()
