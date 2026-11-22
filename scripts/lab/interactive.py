"""Build and attach a self-contained digital logic lesson to a review pack."""
import argparse
from dataclasses import dataclass
from base64 import b64encode
from hashlib import sha256
import html
import json
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory

from .config import experiment_folder_name
from .review_pack.manifest import DATA, VENDOR_DIR, load_manifest, output_names, safe_relative, sync_shared_vendor

SKILL = Path('.claude/skills/logic-lab-interactive')
FONT_VENDOR = Path('.claude/skills/logic-lab-review-pack/assets/vendor')
MODELS = {'74hc76': '74hc76.mjs', 'd-latch': 'd-latch.mjs'}
EVIDENCE = '자료_인터랙티브'
REQUIRED_CHECKS = {'logic', 'browser', 'visual'}
LESSON_ID = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
LESSON_LINK = re.compile(r'\n?<p><a data-interactive-lab="[a-z0-9-]+" [^>]*>[^<]*</a></p>')


@dataclass
class Attachment:
    lesson: dict
    lesson_id: str | None

    @property
    def key(self):
        return self.lesson_id or self.lesson['model_id']

    @property
    def filename(self):
        prefix = experiment_folder_name(self.lesson['experiment'])
        suffix = self.lesson_id or self.lesson['chip']
        return f'{prefix}_인터랙티브_{suffix}.html'

    def link(self, text):
        return with_link(text, self.lesson['topic_id'], self.key, self.filename, self.lesson['link_label'])


def registered_lessons(directory, manifest):
    code = f"{manifest['experiment']:02d}"
    legacy = directory / f'{code}.json'
    if legacy.is_file():
        yield legacy, Attachment(load_lesson(legacy, manifest), None)
    for author in sorted((directory / code).glob('*.json')):
        if author.name.endswith('.verification.json'):
            continue
        if not LESSON_ID.fullmatch(author.stem):
            raise ValueError('인터랙티브 자료 ID를 확인하세요: ' + author.stem)
        yield author, Attachment(load_lesson(author, manifest), author.stem)


def published_attachment(entry, manifest):
    lesson = load_lesson(entry / 'lesson.json', manifest)
    evidence = read_json(entry / 'verification.json')
    lesson_id = evidence.get('lesson_id')
    if lesson_id is not None and not LESSON_ID.fullmatch(lesson_id):
        raise ValueError('인터랙티브 자료 ID를 확인하세요: ' + entry.name)
    attachment = Attachment(lesson, lesson_id)
    if entry.name != attachment.key:
        raise ValueError('인터랙티브 검증 경로가 자료 ID와 달라요: ' + entry.name)
    return attachment, evidence


def validate_attachment_names(attachments):
    keys, filenames = set(), set()
    for attachment in attachments:
        filename = attachment.filename.casefold()
        if attachment.key in keys or filename in filenames:
            raise ValueError('인터랙티브 자료 ID 또는 파일명이 겹쳐요: ' + attachment.key)
        keys.add(attachment.key)
        filenames.add(filename)



def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def load_lesson(path, manifest):
    lesson = read_json(path)
    if lesson['experiment'] != manifest['experiment']:
        raise ValueError('인터랙티브 실험 번호가 팩과 달라요.')
    if lesson['topic_id'] not in {topic['id'] for topic in manifest['topics']}:
        raise ValueError('인터랙티브 자료의 실험설명 토픽이 없어요: ' + lesson['topic_id'])
    if lesson['model_id'] not in MODELS or not re.fullmatch(r'[A-Za-z0-9-]+', lesson['chip']):
        raise ValueError('등록된 회로 모델과 칩 이름을 지정하세요.')
    pins = lesson['pins']
    labels = {p['label'] for p in pins}
    number_order = [p['number'] for p in pins]
    if (len(pins) % 2 or number_order != list(range(1, len(pins) + 1))
            or len(labels) != len(pins) or not set(lesson['traces']) <= labels):
        raise ValueError('DIP 번호·신호 이름·파형 목록을 확인하세요.')
    inputs = {p['label'] for p in pins if p['role'] == 'input'}
    if 'free_toggle_pin' in lesson and lesson['free_toggle_pin'] not in inputs:
        raise ValueError('자유 조작 버튼에 쓸 입력 핀을 지정하세요.')
    state_pins = inputs | {p['label'] for p in pins if p['role'] == 'output' and not p.get('complement_of')}
    task_ids = [task['id'] for task in lesson['tasks']]
    if not task_ids or len(set(task_ids)) != len(task_ids) or set(task_ids) != lesson['presets'].keys():
        raise ValueError('각 실험에 고유 ID와 시작 상태를 지정하세요.')
    for task in lesson['tasks']:
        preset = lesson['presets'][task['id']]
        probes = task.get('probes', lesson['default_probes'])
        if (not state_pins <= preset.keys() or any(v not in (0, 1) for v in preset.values())
                or (lesson['model_id'] == '74hc76' and preset['PR'] == preset['CLR'] == 0)
                or not set(probes) <= set(lesson['traces'])
                or not 0 <= task['answer'] < len(task['options'])
                or not task['steps']
                or any(s['pin'] not in inputs or s['value'] not in (0, 1) for s in task['steps'])):
            raise ValueError('시작 상태·핀 입력·예측 문항을 확인하세요: ' + task['id'])
    if not lesson.get('sources'):
        raise ValueError('핀과 동작 규칙의 근거를 지정하세요.')
    table = lesson['truth_table']
    row_ids = {row['id'] for row in table['rows']}
    if (not table['columns'] or not row_ids or len(row_ids) != len(table['rows'])
            or any(len(row['cells']) != len(table['columns']) for row in table['rows'])):
        raise ValueError('진리표의 행 ID와 열 개수를 확인하세요.')
    return lesson


def embedded_fonts(vendor):
    folder = vendor / 'pretendard'
    license_text = '\n'.join(line.rstrip() for line in (folder / 'LICENSE').read_text(encoding='utf-8').splitlines())
    faces = ['/*!\n' + license_text + '\n*/']
    for weight, name in [(400, 'Regular'), (500, 'Medium'), (600, 'SemiBold'), (700, 'Bold')]:
        font = b64encode((folder / f'Pretendard-{name}.woff2').read_bytes()).decode('ascii')
        faces.append(
            f"@font-face {{ font-family: 'Pretendard'; font-weight: {weight}; "
            f"font-display: swap; src: url(data:font/woff2;base64,{font}) format('woff2'); }}"
        )
    return '\n'.join(faces)


def render(lesson, assets, note_name, vendor):
    def read(name):
        return (assets / name).read_text(encoding='utf-8')

    payload = {key: value for key, value in lesson.items() if key != 'sources'}
    prediction_sidebar = payload.pop('prediction_sidebar', False)
    css = read('lesson.css')
    sync_prediction = ''
    if prediction_sidebar:
        css += read('prediction-sidebar.css')
        sync_prediction = "  syncPredictionPlacement(!narrowLayout.matches && panelControls.get('right').open);\n"
    default_hint = '바뀐 입력과 출력 핀에서 파형을 선택해요.'
    if lesson['model_id'] == '74hc76':
        default_hint += ' PR·CLR은 0에서 작동해요.'
    values = {
        'TITLE': html.escape(lesson['title']),
        'CHIP': html.escape(lesson['chip']),
        'CIRCUIT_HINT': html.escape(lesson.get('circuit_hint', default_hint)),
        'EXPERIMENT': f"{lesson['experiment']:02d}",
        'NOTE': html.escape(note_name + '#' + lesson['topic_id']),
        'FONTS': embedded_fonts(vendor),
        'CSS': css,
        'CIRCUIT': read(lesson['model_id'] + '.svg'),
        'LESSON': json.dumps(payload, ensure_ascii=False, separators=(',', ':')).replace('<', r'\u003c'),
        'MODEL': read(MODELS[lesson['model_id']]),
        'RUNTIME': read('lesson.js'),
        'PREDICTION_LAYOUT': read('prediction-sidebar.js') + '\n' if prediction_sidebar else '',
        'SHELL': read('shell.js').replace('@@SYNC_PREDICTION@@', sync_prediction),
    }
    return re.sub(r'@@([A-Z_]+)@@', lambda match: values[match[1]], read('lesson.html'))


def with_link(text, topic, key, filename, label):
    marker = 'data-interactive-lab="' + key + '"'
    article = re.compile(r'(<article class="topic" id="' + re.escape(html.escape(topic))
                         + r'">.*?)(</article>)', re.S)
    link = (f'\n<p><a {marker} href="{html.escape(filename)}">'
            f'{html.escape(label)}</a></p>')
    text, count = article.subn(lambda match: match[1] + link + match[2], text)
    if count != 1:
        raise ValueError('실험설명에서 링크의 대상 절을 하나로 찾을 수 없어요: ' + topic)
    return text


def has_required_checks(checks):
    return isinstance(checks, dict) and all(
        isinstance(checks.get(name), dict) and checks[name].get('status') == 'pass'
        for name in REQUIRED_CHECKS
    )


def build_attachment(root, skill, note_name, author, attachment, *, reviewed_only):
    lesson = attachment.lesson
    sources = []
    for source in lesson['sources']:
        if not safe_relative(source['path']):
            raise ValueError('자료 근거는 저장소 안의 상대 경로여야 해요.')
        candidate = (root / source['path']).resolve()
        if not candidate.is_relative_to(root):
            raise ValueError('자료 근거가 저장소 밖을 가리켜요.')
        sources.append({**source, 'sha256': digest(candidate)})

    document = render(lesson, skill / 'assets', note_name, root / FONT_VENDOR)
    evidence = {
        'topic_id': lesson['topic_id'],
        'html_sha256': sha256(document.encode('utf-8')).hexdigest(),
        'lesson_sha256': digest(author),
        'sources': sources,
    }
    if attachment.lesson_id is not None:
        evidence['lesson_id'] = attachment.lesson_id
    receipt = author.with_suffix('.verification.json')
    reviewed = read_json(receipt) if receipt.is_file() else {}
    if reviewed.get('basis') == evidence and has_required_checks(reviewed.get('checks')):
        evidence['checks'] = reviewed['checks']
    elif reviewed_only:
        raise ValueError(f'{attachment.key}: 현재 원고와 근거에 맞는 논리·브라우저·화면 검증 기록이 필요해요.')
    return document, evidence


def attach(root, folder, manifest, *, reviewed_only=False):
    """Rebuild all registered lessons in a stage before converting the note to Markdown."""
    root, folder = Path(root).resolve(), Path(folder)
    skill = root / SKILL
    registered = list(registered_lessons(skill / 'lessons', manifest))
    registered.sort(key=lambda item: item[1].key)
    validate_attachment_names(attachment for _, attachment in registered)
    directory = folder / DATA / EVIDENCE
    previous = []
    if directory.exists():
        previous = [published_attachment(entry, manifest)[0] for entry in sorted(directory.iterdir())]
    if not registered and not previous:
        return []

    note = folder / output_names(manifest['experiment'])['note_html']
    linked = LESSON_LINK.sub('', note.read_text(encoding='utf-8'))
    generated = []
    for author, attachment in registered:
        try:
            document, evidence = build_attachment(
                root, skill, note.name, author, attachment, reviewed_only=reviewed_only,
            )
            linked = attachment.link(linked)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ValueError(f'{author.name}: {exc}') from exc
        generated.append((author, attachment, document, evidence))

    filenames = {attachment.filename for _, attachment in registered}
    keys = {attachment.key for _, attachment in registered}
    previous_filenames = {attachment.filename.casefold() for attachment in previous}
    new_filenames = {name.casefold() for name in filenames} - previous_filenames
    for path in folder.iterdir():
        if path.name.casefold() in new_filenames:
            raise ValueError('인터랙티브 출력 파일명이 기존 파일과 겹쳐요: ' + path.name)
    for old in previous:
        if old.filename not in filenames:
            (folder / old.filename).unlink(missing_ok=True)
        if old.key not in keys:
            shutil.rmtree(directory / old.key)

    paths = []
    for author, attachment, document, evidence in generated:
        path = folder / attachment.filename
        provenance = directory / attachment.key
        provenance.mkdir(parents=True, exist_ok=True)
        shutil.copy2(author, provenance / 'lesson.json')
        write_json(provenance / 'verification.json', evidence)
        path.write_bytes(document.encode('utf-8'))
        paths.append(path)
    note.write_bytes(linked.encode('utf-8'))
    return paths


def check_attachment(folder, manifest, root=None):
    directory = folder / DATA / EVIDENCE
    note = folder / output_names(manifest['experiment'])['note_html']
    try:
        text = note.read_text(encoding='utf-8') if note.is_file() else ''
        linked = LESSON_LINK.sub('', text)
        entries = sorted(directory.iterdir()) if directory.exists() else []
        records = [published_attachment(entry, manifest) for entry in entries]
        validate_attachment_names(attachment for attachment, _ in records)
        if root is not None:
            root = Path(root).resolve()
            skill = root / SKILL
            registered = list(registered_lessons(skill / 'lessons', manifest))
            validate_attachment_names(attachment for _, attachment in registered)
            expected = {attachment.key: (author, attachment) for author, attachment in registered}
            differences = sorted(expected.keys() ^ {attachment.key for attachment, _ in records})
            if differences:
                raise ValueError('스테이지와 등록 원고의 자료 목록이 달라요: ' + ', '.join(differences))
        for entry, (attachment, evidence) in zip(entries, records, strict=True):
            lesson = attachment.lesson
            filename = attachment.filename
            if (evidence['topic_id'] != lesson['topic_id']
                    or evidence['lesson_sha256'] != digest(entry / 'lesson.json')
                    or evidence['html_sha256'] != digest(folder / filename)
                    or not has_required_checks(evidence.get('checks'))):
                raise ValueError('현재 파일과 일치하는 검증 기록이 필요해요: ' + filename)
            linked = attachment.link(linked)
            if root is not None:
                author, registered_attachment = expected[attachment.key]
                _, current_evidence = build_attachment(
                    root, skill, note.name, author, registered_attachment, reviewed_only=True,
                )
                if registered_attachment.filename != filename or current_evidence != evidence:
                    raise ValueError('스테이지의 기록이 등록 원고 및 검증 기록과 달라요: ' + filename)
        if text != linked or text.count('data-interactive-lab=') != len(records):
            raise ValueError('실험설명 링크의 대상·위치와 검증 기록을 확인하세요.')
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return ['인터랙티브 자료: ' + str(exc)]
    return []


def prepare_existing(root, target, stage, *, reviewed_only=False):
    """Copy pack-owned files and update the note, its Markdown and the lesson in a stage."""
    from .review_pack.html2md import convert_pack

    manifest_path = Path(DATA) / 'manifest.json'
    manifest = load_manifest(target / manifest_path)
    if stage.exists() or stage.is_relative_to(target) or target.is_relative_to(stage):
        raise ValueError('기존 팩과 겹치지 않는 새 스테이지 경로를 지정하세요.')
    stage.mkdir(parents=True)
    for name in manifest['generated_files']:
        source = target / name
        if not safe_relative(name) or source.is_symlink() or not source.resolve().is_relative_to(target):
            raise ValueError('스테이지에 복제할 수 없는 경로예요: ' + name)
        destination = stage / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    had_lessons = (stage / DATA / EVIDENCE).is_dir()
    paths = attach(root, stage, manifest, reviewed_only=reviewed_only)
    if not paths and not had_lessons:
        raise ValueError('등록된 실험 원고가 없어요.')
    names = output_names(manifest['experiment'], review_presentation_version=manifest.get('review_presentation_version'))
    review = None if manifest.get('review_presentation_version') == 2 else stage / names['review_html']
    convert_pack(stage / names['note_html'], review, manifest)
    manifest['generated_files'] = sorted(p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file())
    write_json(stage / manifest_path, manifest)
    return paths


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment', type=int)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--stage', type=Path)
    action.add_argument('--install', action='store_true')
    args = parser.parse_args(argv)
    root = args.root.resolve()
    target = root / '복습노트' / experiment_folder_name(args.experiment)

    from .review_pack.publish import _publish_locked
    from .review_pack.workbook_storage import pack_write_lock

    try:
        with pack_write_lock(target):
            if args.stage:
                stage = args.stage.resolve()
                paths = prepare_existing(root, target, stage)
                vendor = stage.parent / VENDOR_DIR
                if not vendor.exists():
                    sync_shared_vendor(target.parent / VENDOR_DIR, vendor)
                for path in paths:
                    print(path)
            else:
                with TemporaryDirectory(prefix='logic-lab-interactive-') as tmp:
                    stage = Path(tmp) / 'stage'
                    sync_shared_vendor(target.parent / VENDOR_DIR, stage.parent / VENDOR_DIR)
                    paths = prepare_existing(root, target, stage, reviewed_only=True)
                    backup = _publish_locked(stage, target, root)
                for path in paths:
                    print(target / path.name)
                print('백업: ' + str(backup))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f'실패: {exc}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
