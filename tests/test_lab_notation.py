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

    def test_nested_complement_scope(self):
        """2주차 T5 의 실제 식이 이 형태다 — `Z = (A'·B)'`.
        평평한 정규식으로는 안쪽 `A'` 가 승격되지 않고 따옴표가 남는다."""
        self.assertEqual(
            n.to_overbar_html("(A'·B)'"),
            '<span class="ov"><span class="ov">A</span>·B</span>')

    def test_parenthesised_group_without_prime_keeps_its_parens(self):
        self.assertEqual(n.to_overbar_html("((A+B)·C)'"),
                         '<span class="ov">(A+B)·C</span>')

    def test_double_prime_nests_twice(self):
        self.assertEqual(
            n.to_overbar_html("A''"),
            '<span class="ov"><span class="ov">A</span></span>')

    def test_unbalanced_parens_degrade_instead_of_crashing(self):
        for expr in ("(A·B", "A)B", "'A", ""):
            with self.subTest(expr=expr):
                self.assertEqual(n.to_overbar_html(expr), expr)

    def test_real_week2_source_expression_renders(self):
        """명세 T5 의 source 식 전문. 이 모듈이 존재하는 이유다."""
        rendered = n.to_overbar_html("X = A + (A'·B)' ; Y = A + B ; Z = (A'·B)'")
        self.assertNotIn("'", rendered)          # 따옴표가 남으면 안 된다
        self.assertEqual(rendered.count('<span class="ov">'), 4)


class TestCellValueGuard(unittest.TestCase):
    """셀 값과 부울식은 문법적으로 구별되지 않는다 — `Q(t-1)'` 과 `(A·B)'` 은
    같은 모양이다. 문서와 규율만으로는 못 막으므로 타입으로 막는다."""

    def test_normalize_cell_returns_a_cell_value(self):
        self.assertIsInstance(n.normalize_cell("0"), n.CellValue)
        self.assertTrue(all(isinstance(c, n.CellValue)
                            for c in n.normalize_row(["L", "H"])))

    def test_cell_value_still_behaves_as_a_string(self):
        cell = n.normalize_cell("Q(t-1)'")
        self.assertEqual(cell, "Q(t-1)'")
        self.assertEqual(f"{cell}!", "Q(t-1)'!")

    def test_overbar_refuses_a_cell_value(self):
        with self.assertRaises(TypeError):
            n.to_overbar_html(n.normalize_cell("Q(t-1)'"))

    def test_overbar_still_accepts_a_plain_string(self):
        self.assertEqual(n.to_overbar_html("(A·B)'"),
                         '<span class="ov">A·B</span>')


class TestActiveLow(unittest.TestCase):
    def test_marks_only_first_use(self):
        self.assertEqual(n.active_low("RESET", True, 1), "RESET (Active Low)")
        self.assertEqual(n.active_low("RESET", False, 1), "RESET")

    def test_experiment_9_follows_the_manual(self):
        self.assertEqual(n.active_low("GWN", True, 9), "GWN")


class TestBitOf(unittest.TestCase):
    """`bit_of` 는 검산·기대값 계산 전용이다 — 데이터를 바꾸지 않는다."""

    def test_0_1_표는_0과_1만_읽는다(self):
        from scripts.lab.notation import bit_of
        self.assertEqual(bit_of("0", "0/1"), 0)
        self.assertEqual(bit_of(" 1 ", "0/1"), 1)
        self.assertIsNone(bit_of("H", "0/1"))

    def test_H_L_표는_H와_L만_읽는다(self):
        from scripts.lab.notation import bit_of
        self.assertEqual(bit_of("L", "H/L"), 0)
        self.assertEqual(bit_of("H", "H/L"), 1)
        self.assertIsNone(bit_of("1", "H/L"))

    def test_dont_care_와_빈칸은_None(self):
        from scripts.lab.notation import bit_of
        for cell in ("X", "x", "-", "", "  "):
            with self.subTest(cell=cell):
                self.assertIsNone(bit_of(cell, "0/1"))

    def test_validate_의_bit_은_같은_함수다(self):
        from scripts.lab import validate
        from scripts.lab.notation import bit_of
        self.assertIs(validate._bit, bit_of)


if __name__ == "__main__":
    unittest.main()
