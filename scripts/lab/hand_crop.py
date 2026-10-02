"""Validated, visual-review supplied crop geometry in rotated PDF page points."""
import hashlib
import json
import math
from pathlib import Path


def _box(value):
    if (not isinstance(value, (list, tuple)) or len(value) != 4
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in value)):
        raise ValueError('box must contain four finite numbers')
    if value[0] >= value[2] or value[1] >= value[3]:
        raise ValueError('box must have positive width and height')
    return tuple(value)


def crop_box(page_rect, board_box, keep):
    px0, py0, px1, py1 = _box(page_rect)
    boxes = [_box(board_box), *[_box(b) for b in keep]]
    for x0, y0, x1, y1 in boxes:
        if not (px0 <= x0 < x1 <= px1 and py0 <= y0 < y1 <= py1):
            raise ValueError('crop content outside page')
    margin = (board_box[2] - board_box[0]) * .02
    return (max(px0, min(b[0] for b in boxes)-margin),
            max(py0, min(b[1] for b in boxes)-margin),
            min(px1, max(b[2] for b in boxes)+margin),
            min(py1, max(b[3] for b in boxes)+margin))


def pixel_box(box, page_rect, image_size):
    x0, y0, x1, y1 = _box(page_rect)
    _box(box)
    w, h = image_size
    sx, sy = w/(x1-x0), h/(y1-y0)
    return (max(0, math.floor((box[0]-x0)*sx)), max(0, math.floor((box[1]-y0)*sy)),
            min(w, math.ceil((box[2]-x0)*sx)), min(h, math.ceil((box[3]-y0)*sy)))


def load_crop_plan(path, pdf_path, pages):
    import fitz
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('schema') != 'hand-crop/v1':
        raise ValueError('unsupported crop-plan schema')
    if data.get('source_sha256') != hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest():
        raise ValueError('crop-plan source SHA-256 mismatch')
    entries = data.get('pages')
    if not isinstance(entries, list):
        raise ValueError('crop-plan pages must be a list')
    result = {}
    with fitz.open(pdf_path) as doc:
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError('page entry must be an object')
            page = entry.get('page')
            if type(page) is not int or not 1 <= page <= len(doc) or page-1 in result:
                raise ValueError('invalid or duplicate crop-plan page')
            actual = tuple(doc[page-1].rect)
            if _box(entry.get('page_rect')) != actual:
                raise ValueError('crop-plan page rectangle mismatch')
            for field in ('keep', 'ambiguous', 'excluded'):
                if not isinstance(entry.get(field), list):
                    raise ValueError(f'{field} must be a list')
                for item in entry[field]:
                    if not isinstance(item, dict) or not isinstance(item.get('label'), str) or not item['label'].strip():
                        raise ValueError(f'{field} requires nonempty label')
                    if field != 'keep' and (not isinstance(item.get('reason'), str) or not item['reason'].strip()):
                        raise ValueError(f'{field} requires reason')
            crop_box(actual, entry.get('board_box'), [i.get('box') for i in entry['keep']+entry['ambiguous']])
            result[page-1] = entry
        if not pages or any(type(p) is not int or p not in result for p in pages):
            raise ValueError('crop-plan missing selected pages')
    return {p: result[p] for p in pages}


def render_crop(im, entry, target_dir, page_number):
    """Return (final image or None, report entry); candidates never replace finals."""
    from PIL import ImageDraw
    rect, board = entry['page_rect'], entry['board_box']
    keep = [item['box'] for item in entry['keep']]
    box = crop_box(rect, board, keep)
    all_boxes = [board, *keep]
    margin = (board[2]-board[0])*.02
    raw = (min(b[0] for b in all_boxes)-margin, min(b[1] for b in all_boxes)-margin,
           max(b[2] for b in all_boxes)+margin, max(b[3] for b in all_boxes)+margin)
    report = dict(page=page_number, status='saved', box=list(box), output=None,
                  margin_clipped=tuple(box) != raw, candidates=[])
    if not entry['ambiguous']:
        return im.crop(pixel_box(box, rect, im.size)), report
    folder = Path(target_dir)/'candidates'
    folder.mkdir(parents=True, exist_ok=True)
    include = crop_box(rect, board, keep+[item['box'] for item in entry['ambiguous']])
    preview = im.copy()
    draw = ImageDraw.Draw(preview)
    for name, candidate, color in [('exclude', box, 'orange'), ('include', include, 'blue')]:
        bounds = pixel_box(candidate, rect, im.size)
        path = folder/f'p{page_number:03d}-{name}.png'
        im.crop(bounds).save(path)
        report['candidates'].append(str(path))
        draw.rectangle(bounds, outline=color, width=max(2,im.width//400))
    path = folder/f'p{page_number:03d}-boundaries.png'
    preview.save(path)
    report.update(status='pending', box=None, preview=str(path), ambiguous=entry['ambiguous'])
    return None, report
