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
    return _shape_errors(data, schema)

def load_question_bank(path):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    errors = validate_question_bank(data)
    if errors: raise ValueError('\n'.join(errors))
    return data
