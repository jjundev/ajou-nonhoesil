import itertools
import unittest

from scripts.lab.boolexpr import eval_boolean, variables


def truth_column(expr, names):
    return [eval_boolean(expr, dict(zip(names, bits)))
            for bits in itertools.product([0, 1], repeat=len(names))]


class TestOperators(unittest.TestCase):
    def test_and_or_over_three_inputs(self):
        self.assertEqual(truth_column("A·B·C", "ABC"), [0, 0, 0, 0, 0, 0, 0, 1])
        self.assertEqual(truth_column("A+B+C", "ABC"), [0, 1, 1, 1, 1, 1, 1, 1])

    def test_complement_of_a_group(self):
        self.assertEqual(truth_column("(A·B·C)'", "ABC"), [1, 1, 1, 1, 1, 1, 1, 0])
        self.assertEqual(truth_column("(A+B+C)'", "ABC"), [1, 0, 0, 0, 0, 0, 0, 0])

    def test_xor(self):
        self.assertEqual(truth_column("A⊕B", "AB"), [0, 1, 1, 0])


class TestPrecedence(unittest.TestCase):
    """문자열 치환 + eval 로는 여기서 조용히 틀린다."""

    def test_and_binds_tighter_than_or(self):
        self.assertEqual(truth_column("A+B·C", "ABC"), [0, 0, 0, 1, 1, 1, 1, 1])

    def test_and_binds_tighter_than_xor(self):
        self.assertEqual(truth_column("A⊕B·C", "ABC"), [0, 0, 0, 1, 1, 1, 1, 0])

    def test_de_morgan_identity(self):
        self.assertEqual(truth_column("(A·B)'", "AB"), truth_column("A'+B'", "AB"))
        self.assertEqual(truth_column("(A+B)'", "AB"), truth_column("A'·B'", "AB"))


class TestErrors(unittest.TestCase):
    def test_unknown_variable(self):
        with self.assertRaises(ValueError) as ctx:
            eval_boolean("A·D", {"A": 1, "B": 0})
        self.assertIn("D", str(ctx.exception))

    def test_truncated_expression(self):
        with self.assertRaises(ValueError):
            eval_boolean("A·", {"A": 1})

    def test_unbalanced_parenthesis(self):
        with self.assertRaises(ValueError):
            eval_boolean("A)B", {"A": 1, "B": 1})

    def test_unknown_character_is_rejected_not_dropped(self):
        """`findall` 은 모르는 문자를 조용히 버린다 — `!A` 가 `A` 로 평가돼
        틀린 진리표를 통과시킨다. 이 과목 표기는 후위 `'` 뿐이므로
        `!`·`*`·`^` 는 인접 표기에서 흔한 오타다."""
        for expr in ("!A", "A*B", "A^B", "A&B"):
            with self.subTest(expr=expr):
                with self.assertRaises(ValueError) as ctx:
                    eval_boolean(expr, {"A": 1, "B": 1})
                self.assertIn("알 수 없는 문자", str(ctx.exception))


class TestVariables(unittest.TestCase):
    """단계 진리표의 입력 열 — 노드 식에 나오는 변수만 쓴다."""

    def test_처음_나온_순서대로_중복_없이(self):
        self.assertEqual(variables("(A⊕B)'·Ci + A·B"), ["A", "B", "Ci"])

    def test_여러_글자_이름을_한_변수로_읽는다(self):
        self.assertEqual(variables("(E'·S1'·S0'·D0)'"), ["E", "S1", "S0", "D0"])

    def test_알_수_없는_문자는_거절한다(self):
        with self.assertRaises(ValueError):
            variables("!A·B")


if __name__ == "__main__":
    unittest.main()
