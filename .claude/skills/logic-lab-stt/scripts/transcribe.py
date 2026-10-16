"""Gemini transcription for lab recordings; standard library + ffmpeg/ffprobe only."""
import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
import wave

MODEL = 'gemini-3.5-transcribe'
ENDPOINT = f'https://aiplatform.googleapis.com/v1/publishers/google/models/{MODEL}:generateContent'
POLICY = 'lab-verbatim-pcm16-v2'
MAX_REQUEST_BYTES = 20 * 1024 * 1024
RATE = 16000


class SttError(RuntimeError):
    """Only allowlisted error codes cross the credential/transport boundary."""


def actual_path(value):
    path = Path(value).expanduser().absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        if part == '..':
            current = current.parent
            continue
        exact = current / part
        if exact.exists():
            current = exact
            continue
        matches = [p for p in current.iterdir()
                   if unicodedata.normalize('NFC', p.name) == unicodedata.normalize('NFC', part)]
        if len(matches) != 1:
            raise SttError('source_path_missing_or_ambiguous')
        current = matches[0]
    return current.resolve(strict=True)


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def write_json(path, data):
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     delete=False) as f:
        temp = Path(f.name)
        try:
            json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write('\n')
        except Exception:
            temp.unlink(missing_ok=True)
            raise
    temp.replace(path)


def publish_markdown(path, content):
    """Publish a complete sibling atomically, refusing to clobber an existing file."""
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         delete=False) as f:
            temp = Path(f.name)
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.link(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def load_key(env_file=None):
    values = {}
    if env_file is not None:
        try:
            for line in actual_path(env_file).read_text(encoding='utf-8-sig').splitlines():
                if '=' in line and not line.lstrip().startswith('#'):
                    k, v = line.split('=', 1)
                    values[k.strip()] = v.strip().strip('"').strip("'")
        except (OSError, ValueError):
            raise SttError('env_file_unreadable') from None
    key = (os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')
           or values.get('GOOGLE_API_KEY') or values.get('GEMINI_API_KEY'))
    if not key:
        raise SttError('missing_api_key')
    return key


def make_transport(key, sleep=time.sleep):
    def request(payload):
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()
        if len(body) > MAX_REQUEST_BYTES:
            raise SttError('request_too_large')
        for attempt in range(3):
            req = urllib.request.Request(ENDPOINT, data=body, method='POST', headers={
                'Content-Type': 'application/json', 'x-goog-api-key': key})
            try:
                with urllib.request.urlopen(req, timeout=150) as response:
                    return json.load(response)
            except urllib.error.HTTPError as error:
                status = error.code
                error.close()
                if status not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise SttError(f'http_{status}') from None
                sleep(2 ** attempt)
            except (TimeoutError, urllib.error.URLError):
                # Completion is unknown; no automatic potentially duplicated charge.
                raise SttError('network_or_timeout') from None
            except (ValueError, OSError):
                raise SttError('invalid_response') from None
    return request


def media_command(args):
    try:
        result = subprocess.run(args, capture_output=True, check=False)
    except OSError:
        raise SttError('media_tool_unavailable') from None
    if result.returncode:
        raise SttError('media_command_failed')
    return result.stdout


def first_pts(source, selector, fallback):
    frames = json.loads(media_command(['ffprobe', '-v', 'error', '-select_streams', selector,
        '-read_intervals', '%+#8', '-show_frames', '-show_entries',
        'frame=best_effort_timestamp_time', '-of', 'json', str(source)]))['frames']
    value = next((float(f['best_effort_timestamp_time']) for f in frames
                  if 'best_effort_timestamp_time' in f), float(fallback))
    if not math.isfinite(value):
        raise SttError('invalid_media_time')
    return value


def offset_seconds(value):
    if not isinstance(value, str) or not re.fullmatch(r'-?\d+(?:\.\d+)?s', value):
        raise SttError('invalid_word_timestamp')
    return float(value[:-1])


def decode(response, duration, timestamps):
    try:
        candidates = response.get('candidates', [])
        if len(candidates) != 1 or candidates[0].get('finishReason') != 'STOP':
            raise SttError('incomplete_or_blocked_response')
        parts = candidates[0]['content']['parts']
        if not parts:
            raise SttError('empty_response')
        texts, words = [], []
        for part in parts:
            tx = part.get('audioTranscription', {})
            text = part.get('text', tx.get('text', ''))
            if not isinstance(text, str):
                raise SttError('invalid_transcript')
            if text.strip():
                texts.append(text.strip())
            elif not ('text' in tx and tx['text'] == '' and tx.get('words', []) == []):
                raise SttError('empty_response')
            if timestamps:
                for word in tx.get('words', []):
                    start = offset_seconds(word['startOffset'])
                    end = offset_seconds(word['endOffset'])
                    if (not isinstance(word['word'], str) or not word['word'].strip()
                            or not 0 <= start <= end <= duration + .1
                            or words and start < words[-1]['start_s']):
                        raise SttError('invalid_word_timestamp')
                    words.append({'word': word['word'], 'start_s': start, 'end_s': end})
        text = '\n\n'.join(texts)
        if timestamps and text and not words:
            raise SttError('missing_word_timestamps')
        return {'text': text, 'words': words, 'usage': response.get('usageMetadata', {})}
    except (KeyError, TypeError, AttributeError, ValueError):
        raise SttError('invalid_response') from None


def timestamp(seconds):
    sign = '-' if seconds < 0 else ''
    millis = round(abs(seconds) * 1000)
    minutes, remainder = divmod(millis, 60000)
    return f'{sign}{minutes:02d}:{remainder // 1000:02d}.{remainder % 1000:03d}'


def markdown(chunks, timestamps):
    blocks = []
    for chunk in chunks:
        if not chunk['text']:
            continue
        if timestamps:
            # Group consecutive words for a readable search aid, never invent alignment.
            group = []
            for word in chunk['words']:
                group.append(word)
                if word['word'].endswith(('.', '?', '!', '。')) or len(group) >= 20:
                    blocks.append(timestamp(group[0]['start_s']) + '\n' +
                                  ' '.join(w['word'] for w in group))
                    group = []
            if group:
                blocks.append(timestamp(group[0]['start_s']) + '\n' +
                              ' '.join(w['word'] for w in group))
        else:
            blocks.append(chunk['text'])
    return '\n\n'.join(blocks) + '\n' if blocks else '[인식된 발화 없음]\n'


def transcribe(source, output_dir, *, timestamps=False, env_file=None,
               transport=None, chunk_seconds=600):
    if (isinstance(chunk_seconds, bool) or not isinstance(chunk_seconds, (int, float))
            or not math.isfinite(chunk_seconds) or not 0 < chunk_seconds <= 600):
        raise SttError('chunk_seconds_must_be_0_to_600')
    source = actual_path(source)
    source_hash = file_hash(source)
    info = json.loads(media_command(['ffprobe', '-v', 'error', '-show_streams',
                                   '-show_format', '-of', 'json', str(source)]))
    audio = next((s for s in info['streams'] if s['codec_type'] == 'audio'), None)
    if audio is None:
        return {'status': 'no_audio', 'source_sha256': source_hash}
    video = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
    audio_pts = first_pts(source, 'a:0', audio.get('start_time', 0))
    origin = first_pts(source, 'v:0', video.get('start_time', 0)) if video else audio_pts
    offset = audio_pts - origin
    # 600 s PCM16 -> 25.6 MB base64. Cap at 450 s to stay below 20 MiB JSON.
    frames_per_chunk = max(1, int(min(chunk_seconds, 450) * RATE))
    config = {'mode': 'VERBATIM', 'languageCodes': ['ko-KR'], 'wordTimestamp': timestamps}
    identity = {'source_path': str(source), 'source_sha256': source_hash, 'policy': POLICY,
                'model': MODEL, 'endpoint': ENDPOINT, 'config': config,
                'chunk_frames': frames_per_chunk, 'audio_offset_s': offset}
    run = Path(output_dir).expanduser().resolve() / digest(identity)[:24]
    run.mkdir(parents=True, exist_ok=True)
    state_path = run / 'state.json'
    lock = run / '.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    except FileExistsError:
        raise SttError('run_locked_check_for_active_process') from None
    try:
        if state_path.exists():
            state = json.loads(state_path.read_text())
            if state.get('identity') != identity:
                raise SttError('cache_identity_mismatch')
            if state.get('status') == 'complete':
                result = state['result']
                for field in ('md', 'json'):
                    expected = run / ('transcript.md' if field == 'md' else 'transcript.json')
                    if (Path(result[field]) != expected or not expected.is_file()
                            or file_hash(expected) != result[field + '_sha256']):
                        raise SttError('completed_output_changed')
                return result
        state = {'schema_version': 1, 'identity': identity, 'status': 'running'}
        write_json(state_path, state)
        chunks_dir = run / 'chunks'
        chunks_dir.mkdir(exist_ok=True)
        try:
            with tempfile.TemporaryDirectory(prefix='.media-', dir=run) as work:
                wav_path = Path(work) / 'audio.wav'
                media_command(['ffmpeg', '-v', 'error', '-nostdin', '-i', str(source),
                    '-map', '0:a:0', '-vn', '-ac', '1', '-ar', str(RATE),
                    '-af', 'asetpts=PTS-STARTPTS,aresample=16000:async=1:first_pts=0',
                    '-c:a', 'pcm_s16le', str(wav_path)])
                chunks = []
                with wave.open(str(wav_path)) as wav:
                    total = wav.getnframes()
                    if not total:
                        raise SttError('empty_audio_stream')
                    for index, start in enumerate(range(0, total, frames_per_chunk)):
                        count = min(frames_per_chunk, total - start)
                        cache = chunks_dir / f'{index:05d}.json'
                        chunk_id = {'run_key': digest(identity), 'index': index,
                                    'start_sample': start, 'sample_count': count}
                        if cache.exists():
                            receipt = json.loads(cache.read_text())
                            if (receipt.get('identity') != chunk_id
                                    or digest(receipt['data']) != receipt.get('sha256')):
                                raise SttError('chunk_cache_changed')
                            parsed = receipt['data']
                            # Cache hashes detect accidental modification; validate structure too.
                            if not isinstance(parsed.get('text'), str) or not isinstance(parsed.get('words'), list):
                                raise SttError('invalid_chunk_cache')
                            wav.setpos(start + count)
                        else:
                            wav.setpos(start)
                            chunk_path = Path(work) / 'chunk.wav'
                            with wave.open(str(chunk_path), 'wb') as part:
                                part.setparams((1, 2, RATE, 0, 'NONE', 'not compressed'))
                                part.writeframes(wav.readframes(count))
                            payload = {'contents': [{'role': 'user', 'parts': [{'inlineData': {
                                'mimeType': 'audio/wav',
                                'data': base64.b64encode(chunk_path.read_bytes()).decode()}}]}],
                                'generationConfig': {'audioTranscriptionConfig': config}}
                            if len(json.dumps(payload).encode()) > MAX_REQUEST_BYTES:
                                raise SttError('request_too_large')
                            if transport is None:
                                transport = make_transport(load_key(env_file))
                            parsed = decode(transport(payload), count / RATE, timestamps)
                            write_json(cache, {'identity': chunk_id, 'data': parsed,
                                              'sha256': digest(parsed)})
                        base = offset + start / RATE
                        chunks.append({'index': index, 'start_s': base, 'end_s': base + count / RATE,
                            'text': parsed['text'], 'words': [dict(w, start_s=w['start_s'] + base,
                                end_s=w['end_s'] + base) for w in parsed['words']], 'usage': parsed['usage']})
            if file_hash(source) != source_hash:
                raise SttError('source_changed_during_transcription')
            data = {'schema_version': 1, 'status': 'complete', **identity,
                    'time_basis': 'first_display_frame' if video else 'first_audio_sample',
                    'timing_accuracy': 'approximate', 'audio_review': 'not_listened',
                    'duration_s': total / RATE, 'chunks': chunks,
                    'text': '\n\n'.join(c['text'] for c in chunks if c['text']),
                    'words': [w for c in chunks for w in c['words']]}
            md = run / 'transcript.md'
            content = markdown(chunks, timestamps)
            if md.exists() and md.read_text() != content:
                raise SttError('existing_markdown_changed')
            if not md.exists():
                publish_markdown(md, content)
            output_json = run / 'transcript.json'
            if output_json.exists() and json.loads(output_json.read_text()) != data:
                raise SttError('existing_json_changed')
            if not output_json.exists():
                write_json(output_json, data)
            result = {'status': 'complete', 'md': str(md), 'json': str(output_json),
                      'md_sha256': file_hash(md), 'json_sha256': file_hash(output_json),
                      'source_sha256': source_hash, 'model': MODEL}
            write_json(state_path, dict(state, status='complete', result=result))
            return result
        except Exception as error:
            # Never persist exception text, which may contain HTTP headers or credentials.
            message = str(error) if type(error) is SttError else 'transcription_failed'
            write_json(state_path, dict(state, status='failed', error=message))
            raise SttError(message) from None
    finally:
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--timestamps', action='store_true')
    parser.add_argument('--chunk-seconds', type=float, default=600)
    args = parser.parse_args()
    default_env = Path(__file__).resolve().parents[4] / '.env'
    try:
        result = transcribe(args.source, args.output_dir, timestamps=args.timestamps,
                            env_file=args.env_file or (default_env if default_env.is_file() else None),
                            chunk_seconds=args.chunk_seconds)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print('오류: ' + (str(error) if type(error) is SttError else 'transcription_failed'), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
