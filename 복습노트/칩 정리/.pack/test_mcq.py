import copy
import json
import unittest
from collections import Counter
from pathlib import Path
from mcq import merge_mcq, render_choices

P = Path(__file__).resolve().parent

class McqDataTest(unittest.TestCase):
    def setUp(self):
        self.questions = json.loads((P/'questions.json').read_text(encoding='utf-8'))
        self.rows = json.loads((P/'mcq.json').read_text(encoding='utf-8'))

    def test_contract(self):
        before = copy.deepcopy(self.questions)
        out = merge_mcq(self.questions, self.rows)
        self.assertEqual(len(out), 30)
        self.assertEqual(Counter(q['correctChoiceId'] for q in out), Counter({str(i):6 for i in range(1,6)}))
        self.assertNotEqual([q['correctChoiceId'] for q in out], ['1','2','3','4','5']*6)
        self.assertEqual(self.questions, before)
        self.assertEqual([q['answer'] for q in out], [q['answer'] for q in before])

    def test_reject_invalid_rows(self):
        for kind in ['duplicate_text','wrong_key','duplicate_id','missing','empty_reason']:
            with self.subTest(kind=kind):
                rows = copy.deepcopy(self.rows)
                if kind == 'duplicate_text': rows[0]['choices'][1]['text'] = rows[0]['choices'][0]['text']
                if kind == 'wrong_key': rows[0]['correctChoiceId'] = '6'
                if kind == 'duplicate_id': rows[1]['id'] = rows[0]['id']
                if kind == 'missing': rows.pop()
                if kind == 'empty_reason': rows[0]['choices'][0]['explanation'] = ''
                with self.assertRaises(ValueError): merge_mcq(self.questions, rows)

    def test_render_shared_choices(self):
        from html import escape
        for q in merge_mcq(self.questions, self.rows):
            practice, explain = render_choices(q), render_choices(q, explain=True)
            self.assertEqual(practice.count('class="mcq-choice"'), 5)
            self.assertIn('role="status"', practice)
            for c in q['choices']:
                for doc in [practice, explain]:
                    self.assertIn(escape(c['text']), doc)
                    self.assertIn(escape(c['explanation']), doc)

    def test_escape(self):
        q = merge_mcq(self.questions, self.rows)[0]
        q['choices'][0]['text'] = '<script>bad()</script>'
        self.assertNotIn('<script>', render_choices(q))

if __name__ == '__main__': unittest.main()
