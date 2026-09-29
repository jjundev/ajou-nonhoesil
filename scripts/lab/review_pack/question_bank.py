"""Read-only validation of the independent extraction contract."""
import json
import math
import re
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[3] / '.claude/skills/logic-lab-review-pack/references/question-bank.schema.json'

def _shape_errors(value, rule, at='$'):
    kinds = {'object': lambda v: isinstance(v, dict), 'array': lambda v: isinstance(v, list),
             'string': lambda v: isinstance(v, str), 'integer': lambda v: type(v) is int,
             'number': lambda v: type(v) in (int, float) and math.isfinite(v), 'null': lambda v: v is None}
    errors = []
    expected = rule.get('type')
    if expected is not None:
        names = expected if isinstance(expected, list) else [expected]
        if not any(kinds[n](value) for n in names): return [f'{at}: invalid type']
    if 'enum' in rule and not any(type(value) is type(v) and value == v for v in rule['enum']):
        errors.append(f'{at}: invalid value')
    if value is None: return errors
    if isinstance(value, dict):
        props = rule.get('properties', {})
        for key in rule.get('required', []):
            if key not in value: errors.append(f'{at}.{key}: required')
        for key, item in value.items():
            if key in props: errors.extend(_shape_errors(item, props[key], f'{at}.{key}'))
            elif rule.get('additionalProperties') is False: errors.append(f'{at}.{key}: unknown field')
    if isinstance(value, list):
        if len(value) < rule.get('minItems', 0) or len(value) > rule.get('maxItems', len(value)):
            errors.append(f'{at}: invalid length')
        for i, item in enumerate(value): errors.extend(_shape_errors(item, rule['items'], f'{at}[{i}]'))
    if isinstance(value, str) and 'pattern' in rule and not re.fullmatch(rule['pattern'], value):
        errors.append(f'{at}: invalid pattern')
    if type(value) in (int, float):
        if value < rule.get('minimum', value) or value > rule.get('maximum', value): errors.append(f'{at}: out of range')
    return errors

def validate_question_bank(data):
    schema = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
    errors = _shape_errors(data, schema)
    if errors:
        return errors
    validator = _EvidenceValidator(data)
    return validator.check()

def load_question_bank(path):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    errors = validate_question_bank(data)
    if errors: raise ValueError('\n'.join(errors))
    return data


class _EvidenceValidator:
    """Semantic checks on shape-checked input; never repairs or merges records."""

    def __init__(self, data):
        self.data = data
        self.errors = []
        self.ids = set()
        self.index = {}
        self.parts = {}
        self.linked_answers = set()
        self.unresolved = {r['target_id'] for r in data['audit']['unresolved']}

    def error(self, at, message):
        self.errors.append(f'{at}: {message}')

    def required_text(self, text, at):
        if not text.strip():
            self.error(at, 'must not be blank')

    def register(self, ident, at):
        if ident in self.ids:
            self.error(at, 'duplicate id')
        self.ids.add(ident)

    def check(self):
        for name in ('sources', 'assets', 'occurrences', 'questions'):
            self.index[name] = {}
            for i, row in enumerate(self.data[name]):
                self.register(row['id'], f'$.{name}[{i}].id')
                self.index[name][row['id']] = row
        for i, row in enumerate(self.data['occurrences']):
            for j, block in enumerate(row['blocks']):
                self.register(block['id'], f'$.occurrences[{i}].blocks[{j}].id')
        for i, row in enumerate(self.data['questions']):
            for j, part in enumerate(row['subparts']):
                self.register(part['id'], f'$.questions[{i}].subparts[{j}].id')
                self.parts[part['id']] = row['id']
        self.locations(self.data, '$')
        self.sources()
        self.occurrences()
        self.questions()
        self.relations()
        self.audit()
        return self.errors

    def locations(self, value, at):
        if isinstance(value, dict):
            if 'source_id' in value and 'pdf_page' in value:
                self.location(value, at)
            else:
                for key, item in value.items():
                    self.locations(item, f'{at}.{key}')
        elif isinstance(value, list):
            for i, item in enumerate(value):
                self.locations(item, f'{at}[{i}]')

    def location(self, loc, at):
        source = self.index['sources'].get(loc['source_id'])
        if source is None:
            self.error(at + '.source_id', 'unknown source')
            return
        self.required_text(loc['locator'], at + '.locator')
        page = loc['pdf_page']
        if source['format'] == 'pdf':
            count = source['unit_count']
            if page is None or (count is not None and page > count):
                self.error(at + '.pdf_page', 'missing or outside PDF page range')
        elif page is not None:
            self.error(at + '.pdf_page', 'non-PDF location must use null')
        if loc['bbox'] is not None:
            x0, y0, x1, y1 = loc['bbox']
            if not (x0 < x1 and y0 < y1) or loc['image_size'] is None:
                self.error(at + '.bbox', 'requires ordered coordinates and image_size')

    def sources(self):
        for i, source in enumerate(self.data['sources']):
            at = f'$.sources[{i}]'
            expected = 'page' if source['format'] == 'pdf' else 'image' if source['format'] == 'image' else 'document'
            if source['unit_kind'] != expected:
                self.error(at + '.unit_kind', 'does not match format')
            if expected != 'page' and source['unit_count'] != 1:
                self.error(at + '.unit_count', 'non-PDF count must be 1')
            if expected == 'page' and source['unit_count'] is None and source['processing'] != 'held':
                self.error(at + '.processing', 'unknown page count requires held')
            if source['processing'] == 'held':
                self.required_text(source['reason'], at + '.reason')
                if source['id'] not in self.unresolved:
                    self.error(at, 'held source needs unresolved reason')
            expected_conflicts = {}
            for field in ('year', 'term'):
                first = source['filename_metadata'][field]
                second = source['observed_metadata'][field]
                if first is not None and second is not None and first != second:
                    expected_conflicts[field] = (first, second)
            seen = set()
            for j, conflict in enumerate(source['conflicts']):
                field = conflict['field']
                pair = (conflict['filename_value'], conflict['observed_value'])
                if field in seen or expected_conflicts.get(field) != pair or conflict['location']['source_id'] != source['id']:
                    self.error(f'{at}.conflicts[{j}]', 'does not match source metadata conflict')
                seen.add(field)
            if seen != set(expected_conflicts):
                self.error(at + '.conflicts', 'missing metadata conflict evidence')
        for i, asset in enumerate(self.data['assets']):
            if asset['role'] == 'problem' and asset['answer_exposure'] != 'none':
                self.error(f'$.assets[{i}].answer_exposure', 'problem image exposes or may expose answers')

    def occurrences(self):
        for i, row in enumerate(self.data['occurrences']):
            at = f'$.occurrences[{i}]'
            blocks = {b['id']: b for b in row['blocks']}
            if row['reading'] == 'readable' and not blocks:
                self.error(at + '.blocks', 'readable occurrence needs content')
            if row['reading'] != 'readable':
                if not row['uncertainties']:
                    self.error(at + '.uncertainties', 'partial/unreadable needs evidence')
                if row['id'] not in self.unresolved:
                    self.error(at, 'partial/unreadable needs unresolved reason')
            for j, uncertainty in enumerate(row['uncertainties']):
                where = f'{at}.uncertainties[{j}]'
                self.required_text(uncertainty['reason'], where + '.reason')
                if uncertainty['block_id'] is not None and uncertainty['block_id'] not in blocks:
                    self.error(where + '.block_id', 'not a block of this occurrence')
            for j, block in enumerate(row['blocks']):
                where = f'{at}.blocks[{j}]'
                field = {'math': 'tex', 'table': 'cells', 'figure': 'asset_id'}.get(block['type'])
                for key in ('tex', 'cells', 'asset_id'):
                    if key != field and block[key] is not None:
                        self.error(where + '.' + key, 'must be null for this block type')
                if field is not None and block[field] is None:
                    self.error(where + '.' + field, 'required for this block type')
                if block['type'] == 'text':
                    self.required_text(block['text'], where + '.text')
                if block['type'] == 'math' and block['tex'] is not None:
                    self.required_text(block['tex'], where + '.tex')
                if block['type'] == 'table' and block['cells'] is not None:
                    cells = block['cells']
                    if not cells or not cells[0] or any(len(r) != len(cells[0]) for r in cells):
                        self.error(where + '.cells', 'table must be nonempty and rectangular')
                if block['type'] == 'figure' and block['asset_id'] not in self.index['assets']:
                    self.error(where + '.asset_id', 'unknown asset')

    def questions(self):
        owners = {}
        occurrences = self.index['occurrences']
        for i, question in enumerate(self.data['questions']):
            at = f'$.questions[{i}]'
            self.required_text(question['classification_reason'], at + '.classification_reason')
            refs = question['occurrence_ids']
            if len(refs) != len(set(refs)):
                self.error(at + '.occurrence_ids', 'duplicate occurrence reference')
            if question['representative_occurrence_id'] not in refs:
                self.error(at + '.representative_occurrence_id', 'not a member')
            for ref in refs:
                occurrence = occurrences.get(ref)
                if occurrence is None or occurrence['role'] not in ('question', 'mixed'):
                    self.error(at + '.occurrence_ids', 'unknown or non-question occurrence')
                if ref in owners:
                    self.error(at + '.occurrence_ids', 'occurrence belongs to multiple questions')
                owners[ref] = question['id']
            for j, part in enumerate(question['subparts']):
                where = f'{at}.subparts[{j}]'
                occurrence = occurrences.get(part['occurrence_id'])
                self.required_text(part['label'], where + '.label')
                if occurrence is None or part['occurrence_id'] not in refs:
                    self.error(where + '.occurrence_id', 'not a member')
                else:
                    blocks = {b['id'] for b in occurrence['blocks']}
                    if len(part['block_ids']) != len(set(part['block_ids'])) or not set(part['block_ids']) <= blocks:
                        self.error(where + '.block_ids', 'unknown/duplicate blocks')
            targets = {question['id']} | {p['id'] for p in question['subparts']}
            for j, answer in enumerate(question['answers']):
                where = f'{at}.answers[{j}]'
                occurrence = occurrences.get(answer['occurrence_id'])
                if occurrence is None or occurrence['role'] not in ('answer', 'explanation', 'mixed'):
                    self.error(where + '.occurrence_id', 'not an answer occurrence')
                if answer['target_id'] not in targets:
                    self.error(where + '.target_id', 'not this question or its subpart')
                self.required_text(answer['reason'], where + '.reason')
                self.linked_answers.add(answer['occurrence_id'])
        for i, occurrence in enumerate(self.data['occurrences']):
            if occurrence['role'] in ('question', 'mixed') and occurrence['id'] not in owners:
                self.error(f'$.occurrences[{i}]', 'question occurrence must have one owner')

    def relations(self):
        seen = set()
        questions = self.index['questions']
        for i, row in enumerate(self.data['relations']):
            at = f'$.relations[{i}]'
            self.required_text(row['reason'], at + '.reason')
            first, second = row['from_id'], row['to_id']
            if row['type'] == 'answer_candidate':
                source = self.index['occurrences'].get(first)
                if source is None or source['role'] not in ('answer', 'explanation', 'mixed'):
                    self.error(at + '.from_id', 'not an answer occurrence')
                if second not in questions and second not in self.parts:
                    self.error(at + '.to_id', 'unknown question/subpart')
                self.linked_answers.add(first)
                pair = (first, second)
            else:
                if first not in questions or second not in questions or first == second:
                    self.error(at, 'requires two different questions')
                pair = tuple(sorted((first, second)))
            key = (row['type'], pair)
            if key in seen:
                self.error(at, 'duplicate relation')
            seen.add(key)

    def audit(self):
        audit = self.data['audit']
        finished = audit['status'] != 'draft'
        for i, unresolved in enumerate(audit['unresolved']):
            at = f'$.audit.unresolved[{i}]'
            if unresolved['target_id'] not in self.ids:
                self.error(at + '.target_id', 'unknown target')
            self.required_text(unresolved['reason'], at + '.reason')
        units = {}
        for i, unit in enumerate(audit['units']):
            at = f'$.audit.units[{i}]'
            key = (unit['source_id'], unit['index'])
            if key in units:
                self.error(at, 'duplicate audit unit')
            units[key] = unit
            source = self.index['sources'].get(unit['source_id'])
            if source is None:
                self.error(at + '.source_id', 'unknown source')
                continue
            if unit['index'] > (source['unit_count'] or 1):
                self.error(at + '.index', 'outside source units')
            if source['unit_count'] is None and unit['outcome'] != 'held':
                self.error(at + '.outcome', 'unknown count needs held file unit')
            refs = unit['occurrence_ids']
            if len(refs) != len(set(refs)):
                self.error(at + '.occurrence_ids', 'duplicate occurrence reference')
            for ref in refs:
                occurrence = self.index['occurrences'].get(ref)
                if occurrence is None or occurrence['location']['source_id'] != unit['source_id']:
                    self.error(at + '.occurrence_ids', 'unknown occurrence or different source')
            if unit['outcome'] == 'questions' and not refs:
                self.error(at, 'questions unit needs occurrences')
            if unit['outcome'] in ('blank', 'reference') and refs:
                self.error(at, 'blank/reference cannot contain occurrences')
            if unit['outcome'] == 'held':
                self.required_text(unit['reason'], at + '.reason')
                if unit['source_id'] not in self.unresolved:
                    self.error(at, 'held unit needs unresolved source reason')
        for i, source in enumerate(self.data['sources']):
            if finished or source['processing'] == 'complete':
                expected = source['unit_count'] or 1
                actual = {n for (sid, n) in units if sid == source['id']}
                if len(actual) != expected or any(n > expected for n in actual):
                    self.error(f'$.sources[{i}]', 'not every source unit audited')
            if finished and source['processing'] == 'pending':
                self.error(f'$.sources[{i}].processing', 'finished audit has pending source')
        for i, occurrence in enumerate(self.data['occurrences']):
            loc = occurrence['location']
            key = (loc['source_id'], loc['pdf_page'] or 1)
            unit = units.get(key)
            if (finished or unit is not None) and (unit is None or occurrence['id'] not in unit['occurrence_ids']):
                self.error(f'$.occurrences[{i}]', 'missing from primary audit unit')
            if occurrence['role'] in ('answer', 'explanation') and occurrence['id'] not in self.linked_answers and occurrence['id'] not in self.unresolved:
                self.error(f'$.occurrences[{i}]', 'unlinked answer needs unresolved reason')
        if finished and not self.data['sources']:
            self.error('$.audit.status', 'empty bank is not complete')
        has_holds = bool(audit['unresolved']) or any(u['outcome'] == 'held' for u in audit['units']) or any(s['processing'] == 'held' for s in self.data['sources']) or any(o['reading'] != 'readable' for o in self.data['occurrences'])
        if audit['status'] == 'complete' and (has_holds or audit['checks']['source_visual'] != 'pass'):
            self.error('$.audit.status', 'complete requires no holds and visual pass')
        if audit['status'] == 'complete_with_holds' and (not audit['unresolved'] or audit['checks']['source_visual'] == 'not_run'):
            self.error('$.audit.status', 'complete_with_holds needs unresolved evidence and visual review')


def summarize_question_bank(data):
    """Count shape-checked data without interpreting answers or merging questions."""
    result = {key: len(data[key]) for key in ('sources', 'occurrences')}
    result['unique_questions'] = len(data['questions'])
    for kind in ('past', 'predicted', 'unknown'):
        result[kind] = sum(q['kind'] == kind for q in data['questions'])
    for state in ('unreadable', 'partial'):
        result[state] = sum(o['reading'] == state for o in data['occurrences'])
    result['candidate_relations'] = sum(r['type'] != 'variant_of' for r in data['relations'])
    result['unresolved'] = len(data['audit']['unresolved'])
    return result
