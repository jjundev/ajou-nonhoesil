import itertools
import unittest

from scripts.lab.boolexpr import eval_boolean


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


if __name__ == "__main__":
    unittest.main()
