import unittest

from scripts.lab import notation as n


class TestNormalizeCell(unittest.TestCase):
    def test_dont_care_variants_collapse_to_X(self):
        for raw in ("x", "X", "-", "–", "—"):
            with self.subTest(raw=raw):
                self.assertEqual(n.normalize_cell(raw), "X")

    def test_blank_becomes_X_only_in_dont_care_column(self):
        self.assertEqual(n.normalize_cell("", dont_care_column=True), "X")
        self.assertEqual(n.normalize_cell(""), "")

    def test_whitespace_is_collapsed(self):
        self.assertEqual(n.normalize_cell("  0  "), "0")
        self.assertEqual(n.normalize_cell("0  :   Reset"), "0 : Reset")

    def test_never_converts_between_encodings(self):
        """R3. encoding 은 표의 속성이다. H/L 을 0/1 로 바꾸면 안 된다."""
        self.assertEqual(n.normalize_cell("H"), "H")
        self.assertEqual(n.normalize_cell("L"), "L")
        self.assertEqual(n.normalize_row(["L", "H", "L"]), ["L", "H", "L"])

    def test_symbolic_tokens_pass_through(self):
        for raw in ("Q(t-1)", "Q(t-1)'", "0 : Reset", "0->1", "Q=D", "Z", "D0"):
            with self.subTest(raw=raw):
                self.assertEqual(n.normalize_cell(raw), raw)


class TestOverbar(unittest.TestCase):
    def test_parenthesised_scope_promotes_whole_group(self):
        self.assertEqual(n.to_overbar_html("(A·B·C)'"),
                         '<span class="ov">A·B·C</span>')

    def test_bare_variable_promotes_only_itself(self):
        self.assertEqual(n.to_overbar_html("A·B'+C"),
                         'A·<span class="ov">B</span>+C')

    def test_expression_without_prime_is_untouched(self):
        self.assertEqual(n.to_overbar_html("A⊕B"), "A⊕B")

    def test_state_token_would_be_promoted_so_never_call_it_on_cells(self):
        """`Q(t-1)'` 은 문법적으로 승격 대상이다. 그래서 셀에는 부르지 않는다.

        이 테스트는 규칙을 문서화하려고 존재한다 — 함수가 아니라 호출부가
        범위를 지켜야 한다.
        """
        self.assertEqual(n.to_overbar_html("Q(t-1)'"),
                         '<span class="ov">Q(t-1)</span>')
        self.assertEqual(n.normalize_cell("Q(t-1)'"), "Q(t-1)'")


class TestActiveLow(unittest.TestCase):
    def test_marks_only_first_use(self):
        self.assertEqual(n.active_low("RESET", True, 1), "RESET (Active Low)")
        self.assertEqual(n.active_low("RESET", False, 1), "RESET")

    def test_experiment_9_follows_the_manual(self):
        self.assertEqual(n.active_low("GWN", True, 9), "GWN")


if __name__ == "__main__":
    unittest.main()
