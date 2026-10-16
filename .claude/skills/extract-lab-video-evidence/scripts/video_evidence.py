"""Local, source-preserving mechanics for agent-selected laboratory video evidence.

No speech recognition or circuit inference. Selection lives in manifest.json.
Requires ffmpeg/ffprobe on PATH and Pillow for images/Korean captions.
"""
import argparse
from bisect import bisect_left
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import zipfile

from PIL import Image, ImageDraw, ImageFont


def actual_path(value):
    """Resolve each Unicode component without inventing a second NFC/NFD directory."""
    path = Path(value).expanduser().absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        if part == "..":
            current = current.parent
            continue
        matches = [p for p in current.iterdir()
                   if unicodedata.normalize("NFC", p.name) == unicodedata.normalize("NFC", part)]
        exact = [p for p in matches if p.name == part]
        if exact:
            current = exact[0]
            continue
        if len(matches) != 1:
            raise ValueError(f"경로 없음 또는 정규화 이름 중복: {path}")
        current = matches[0]
    return current.resolve()


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def execute(args, run_dir=None):
    if run_dir:
        with (Path(run_dir) / "재현명령.txt").open("a") as f:
            f.write(shlex.join([str(x) for x in args]) + "\n\n")
    result = subprocess.run([str(x) for x in args], capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace")[-4000:])
    return result.stdout


def binary(name):
    value = shutil.which(name)
    if not value:
        raise ValueError(f"{name} 실행 파일이 PATH에 없습니다.")
    return value


def probe(path, run_dir=None):
    return json.loads(execute([binary("ffprobe"), "-v", "error", "-show_streams",
                               "-show_format", "-of", "json", path], run_dir))


def save(path, data):
    path = Path(path)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, encoding="utf-8", delete=False) as f:
        temp = Path(f.name)
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    temp.replace(path)


def load(path):
    path = actual_path(path)
    data = json.loads(path.read_text())
    if data.get("schema_version") != 1 or Path(data["run_dir"]).resolve() != path.parent:
        raise ValueError("manifest 버전 또는 실행 폴더가 일치하지 않습니다.")
    return data


def safe_name(value):
    return re.sub(r"[^\w가-힣-]+", "_", unicodedata.normalize("NFC", value)).strip("_")[:64] or "장면"


def video_stream(info):
    return next(s for s in info["streams"] if s["codec_type"] == "video")


def display_size(stream):
    rotation = next((x["rotation"] for x in stream.get("side_data_list", []) if "rotation" in x), 0)
    w, h = stream["width"], stream["height"]
    return (h, w) if round(rotation) % 180 else (w, h)


def inspect_run(experiment_dir, label, sources, transcripts, mode, deliver_dir):
    experiment_dir = actual_path(experiment_dir)
    if mode not in ("photos", "video", "both") or not sources:
        raise ValueError("mode와 원본 영상을 지정해야 합니다.")
    if not label or label in (".", "..") or any(x in label for x in ("/", "\\", "\n", "\r")):
        raise ValueError("촬영명에는 경로 구분자/줄바꿈을 쓸 수 없습니다.")
    source_paths = [actual_path(p) for p in sources]
    if len(set(source_paths)) != len(source_paths):
        raise ValueError("원본 영상이 중복 지정됐습니다.")
    inputs = {}
    for i, path in enumerate(source_paths, 1):
        info = probe(path)
        try:
            stream = video_stream(info)
        except StopIteration as error:
            raise ValueError(f"비디오 스트림 없음: {path}") from error
        duration = float(stream.get("duration", info["format"].get("duration", 0)))
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError(f"영상 길이를 확인할 수 없습니다: {path}")
        inputs[f"p{i}"] = {"kind": "video", "path": str(path), "sha256_before": sha256(path),
                           "size": path.stat().st_size, "duration_s": duration, "probe": info}
    for sid, value in transcripts.items():
        if sid not in inputs:
            raise ValueError(f"전사본의 원본 식별자 없음: {sid}")
        path = actual_path(value)
        if path in source_paths:
            raise ValueError("전사본 경로와 영상 경로가 같습니다.")
        inputs[f"transcript_{sid}"] = {"kind": "transcript", "video_id": sid, "path": str(path),
                                      "sha256_before": sha256(path), "size": path.stat().st_size}
    deliver_dir = Path(deliver_dir).expanduser().absolute()
    deliver_dir.mkdir(parents=True, exist_ok=True)
    prefix = experiment_dir.name + "_"
    attempt = 1
    while True:
        run_label = label + (f"_v{attempt}" if attempt > 1 else "")
        run_dir = experiment_dir / "output" / f"{run_label}_영상분석"
        photos = experiment_dir / "실험사진" / f"{run_label}_영상추출"
        video = deliver_dir / f"{prefix}{run_label}_편집본.mp4"
        archive = deliver_dir / f"{prefix}{run_label}_실험사진.zip"
        if any(p.exists() or p.is_symlink() for p in (run_dir, photos, video, archive)):
            attempt += 1
            continue
        run_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            run_dir.mkdir()
        except FileExistsError:
            attempt += 1
            continue
        break
    m = {"schema_version": 1, "run_dir": str(run_dir), "run_label": run_label, "mode": mode,
         "sources": inputs, "scenes": [], "captures": [], "pairs": [], "cuts": [],
         "unknowns": [], "render": {"crf": 26, "preset": "slow", "audio_bitrate": "128k", "max_fps": 30},
         "review": {"photos": "pending", "boundaries": "pending", "audio": "pending"},
         "outputs": {"photos": str(photos), "video": str(video),
                     "video_local": str(photos / video.name), "zip": str(archive)}, "checks": {}}
    manifest = run_dir / "manifest.json"
    save(manifest, m)
    return manifest


def inputs_unchanged(m):
    return all(Path(s["path"]).is_file() and sha256(s["path"]) == s["sha256_before"]
               for s in m["sources"].values())


def catalog(m, sid):
    source = m["sources"][sid]
    cache = Path(m["run_dir"]) / "frames" / f"{sid}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    data = json.loads(execute([binary("ffprobe"), "-v", "error", "-select_streams", "v:0",
                              "-show_frames", "-show_entries", "frame=best_effort_timestamp_time",
                              "-of", "json", source["path"]], m["run_dir"]))
    raw = data["frames"]
    if not raw or any("best_effort_timestamp_time" not in f for f in raw):
        raise ValueError(f"프레임 PTS를 확인할 수 없습니다: {sid}")
    times = [float(f["best_effort_timestamp_time"]) for f in raw]
    if any(not math.isfinite(t) for t in times) or any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError(f"프레임 PTS가 증가하지 않습니다: {sid}")
    frames = [{"index": i, "pts_s": t, "time_s": t - times[0]} for i, t in enumerate(times)]
    cache.parent.mkdir(exist_ok=True)
    save(cache, frames)
    return frames


def frame_at(m, sid, at):
    frames = catalog(m, sid)
    i = bisect_left([x["time_s"] for x in frames], float(at) - 1e-8)
    if i == len(frames):
        raise ValueError(f"지정 시각 이후 프레임이 없습니다: {sid} {at}")
    return frames[i]


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_selection(m):
    videos = {k: s for k, s in m["sources"].items() if s["kind"] == "video"}

    def interval(sid, start, end):
        if sid not in videos or not all(number(x) for x in (start, end)):
            raise ValueError("잘못된 source_id 또는 시각")
        if not 0 <= start < end <= videos[sid]["duration_s"] + 1e-6:
            raise ValueError(f"원본 범위를 벗어난 구간: {sid} {start}~{end}")

    def unique(items):
        ids = [x["id"] for x in items]
        if len(ids) != len(set(ids)) or any(not re.fullmatch(r"[A-Za-z0-9_-]+", x) for x in ids):
            raise ValueError("id는 중복 없는 영문/숫자/_/-여야 합니다.")

    for key in ("scenes", "captures", "pairs"):
        unique(m[key])
    scenes = {x["id"]: x for x in m["scenes"]}
    for x in scenes.values():
        interval(x["source_id"], x["start_s"], x["end_s"])
        for speech in x.get("speech", []):
            ref = m["sources"].get(speech["source_id"], {})
            if ref.get("kind") != "transcript" or not number(speech["at_s"]):
                raise ValueError("발언에는 전사본 식별자와 수치 시각이 필요합니다.")
            owner = ref["video_id"]
            if not 0 <= speech["at_s"] <= videos[owner]["duration_s"]:
                raise ValueError("전사 시각이 원본 범위를 벗어납니다.")
    captures = {x["id"]: x for x in m["captures"]}
    for x in captures.values():
        scene = scenes.get(x["scene_id"])
        at = x["at_s"]
        if not scene or scene["source_id"] != x["source_id"] or not number(at):
            raise ValueError("사진과 장면의 원본 대응이 일치하지 않습니다.")
        if not scene["start_s"] <= at < scene["end_s"]:
            raise ValueError("사진 시각이 장면 밖입니다.")
        frame = frame_at(m, x["source_id"], at)
        if frame["time_s"] >= scene["end_s"]:
            raise ValueError("선택된 실제 프레임이 장면 끝을 벗어납니다.")
    for pair in m["pairs"]:
        ids = pair["capture_ids"]
        if len(ids) != 2 or len(set(ids)) != 2 or any(i not in captures for i in ids):
            raise ValueError("비교 시트에는 서로 다른 사진 id 2개가 필요합니다.")
        continuity = pair["continuity"]
        if continuity not in ("same_recording", "interrupted"):
            raise ValueError("비교의 연속성 표시가 필요합니다.")
        if captures[ids[0]]["source_id"] != captures[ids[1]]["source_id"] and continuity != "interrupted":
            raise ValueError("다른 촬영본은 촬영 중단 전후 비교로 표시해야 합니다.")
    for cut in m["cuts"]:
        interval(cut["source_id"], cut["start_s"], cut["end_s"])
        if not cut.get("reason"):
            raise ValueError("편집 구간에는 보존 이유가 필요합니다.")
        card = cut.get("break_before")
        if card and (not card.get("text") or not number(card["duration_s"]) or card["duration_s"] <= 0):
            raise ValueError("중단 안내에는 문구와 양수 길이가 필요합니다.")
    if m["mode"] in ("photos", "both") and not captures:
        raise ValueError("사진 요청에 선택한 사진이 없습니다.")
    if m["mode"] in ("video", "both") and not m["cuts"]:
        raise ValueError("영상 요청에 보존 구간이 없습니다.")


def extract_batch(m, sid, selections, folder, scale=None):
    """Decode each source once; selected frame indices match the ffprobe catalog."""
    indices = sorted(set(x["index"] for x in selections))
    expression = "+".join(f"eq(n,{i})" for i in indices)
    filters = f"select='{expression}'" + (f",scale={scale}:-2" if scale else "")
    execute([binary("ffmpeg"), "-v", "error", "-n", "-i", m["sources"][sid]["path"],
             "-vf", filters, "-frames:v", str(len(indices)), "-fps_mode", "passthrough",
             "-threads", "2", str(folder / "%06d.png")], m["run_dir"])
    paths = sorted(folder.glob("*.png"))
    if len(paths) != len(indices):
        raise ValueError("선택한 프레임 수와 추출 결과가 다릅니다.")
    return dict(zip(indices, paths))


def font(size):
    candidates = [os.environ.get("LAB_VIDEO_FONT", ""),
                  "/System/Library/Fonts/AppleSDGothicNeo.ttc",
                  "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                  "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    raise ValueError("한글 폰트가 없습니다. LAB_VIDEO_FONT에 폰트 경로를 지정하세요.")


def wrapped(draw, text, width, size):
    ft = font(size)
    lines, line = [], ""
    for char in text:
        if char == "\n" or (line and draw.textlength(line + char, font=ft) > width):
            lines.append(line)
            line = ""
        if char != "\n":
            line += char
    lines.append(line)
    return lines, ft


def heading(image, text, top, size, fill="black"):
    draw = ImageDraw.Draw(image)
    lines, ft = wrapped(draw, text, image.width - 40, size)
    for line in lines:
        draw.text(((image.width - draw.textlength(line, font=ft)) / 2, top), line, font=ft, fill=fill)
        top += int(size * 1.45)
    return top


def publish(source, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as target, Path(source).open("rb") as src:
        shutil.copyfileobj(src, target)


def preview_run(manifest, sid, start=0, end=None, step=1):
    m = load(manifest)
    if not inputs_unchanged(m):
        raise ValueError("원본 해시가 변경됐습니다.")
    if sid not in m["sources"] or m["sources"][sid]["kind"] != "video":
        raise ValueError("영상 source_id가 필요합니다.")
    duration = m["sources"][sid]["duration_s"]
    end = duration if end is None else end
    if not all(number(x) for x in (start, end, step)) or not 0 <= start < end <= duration or step <= 0:
        raise ValueError("미리보기 구간/간격이 잘못됐습니다.")
    selected = {}
    count = math.ceil((end - start) / step)
    for i in range(count):
        try:
            frame = frame_at(m, sid, start + i * step)
        except ValueError:
            break
        selected[frame["index"]] = frame
    output = Path(m["run_dir"]) / "previews"
    output.mkdir(exist_ok=True)
    tag = f"{sid}_{start:g}_{end:g}_{step:g}"
    existing = list(output.glob(tag + "_*.jpg"))
    if existing:
        raise FileExistsError(existing[0])
    result = []
    with tempfile.TemporaryDirectory(dir=m["run_dir"]) as work:
        paths = extract_batch(m, sid, list(selected.values()), Path(work), 240)
        frames = list(selected.values())
        for offset in range(0, len(frames), 24):
            subset = frames[offset:offset + 24]
            with Image.open(paths[subset[0]["index"]]) as first_image:
                tile_h = first_image.height
            sheet = Image.new("RGB", (4 * 240, math.ceil(len(subset) / 4) * (tile_h + 32)), "white")
            draw = ImageDraw.Draw(sheet)
            for j, item in enumerate(subset):
                xx, yy = j % 4 * 240, j // 4 * (tile_h + 32)
                with Image.open(paths[item["index"]]) as im:
                    sheet.paste(im, (xx, yy))
                draw.text((xx + 4, yy + tile_h), f"{sid} {item['time_s']:.6f}s", font=font(17), fill="black")
            target = output / f"{tag}_{offset // 24 + 1:03d}.jpg"
            sheet.save(target)
            result.append(str(target))
    return result


def build_photos(m):
    folder = Path(m["outputs"]["photos"])
    folder.mkdir(parents=True)
    for sid in {x["source_id"] for x in m["captures"]}:
        subset = [x for x in m["captures"] if x["source_id"] == sid]
        frames = [frame_at(m, sid, x["at_s"]) for x in subset]
        with tempfile.TemporaryDirectory(dir=m["run_dir"]) as work:
            paths = extract_batch(m, sid, frames, Path(work))
            for item, frame in zip(subset, frames):
                i = m["captures"].index(item) + 1
                target = folder / f"{i:02d}_{safe_name(item['title'])}_{sid}_{frame['time_s']:09.3f}.png"
                publish(paths[frame["index"]], target)
                item.update(path=str(target), sha256=sha256(target), frame_index=frame["index"],
                            frame_pts_s=frame["pts_s"], source_time_s=frame["time_s"])
    captures = {x["id"]: x for x in m["captures"]}
    for i, pair in enumerate(m["pairs"], 1):
        items = [captures[k] for k in pair["capture_ids"]]
        # Uniform display panels may resize copies; source PNGs stay full frame.
        panel_w = 800
        images = []
        for x in items:
            with Image.open(x["path"]) as src:
                images.append(src.convert("RGB").resize((panel_w, round(src.height * panel_w / src.width))))
        note = pair.get("note", "")
        if pair["continuity"] == "interrupted":
            note += "\n촬영 중단 전후 · 연속 동작의 증거가 아님"
        canvas = Image.new("RGB", (panel_w * 2, 600 + max(im.height for im in images)), "white")
        y = heading(canvas, pair["title"], 15, 38)
        y = heading(canvas, note, y + 5, 26) + 20
        for col, (item, im) in enumerate(zip(items, images)):
            label = Image.new("RGB", (panel_w, 70), "white")
            heading(label, f"{item['source_id']} · {item['source_time_s']:.3f}초", 0, 28)
            canvas.paste(label, (col * panel_w, y))
            canvas.paste(im, (col * panel_w, y + 70))
        canvas = canvas.crop((0, 0, canvas.width, y + 70 + max(im.height for im in images) + 10))
        target = folder / "비교" / f"{i:02d}_{safe_name(pair['title'])}.png"
        target.parent.mkdir(exist_ok=True)
        canvas.save(target)
        pair["path"] = str(target)


def choose_fps(stream):
    # r_frame_rate can advertise 120 for a ~30 fps phone recording.
    avg = float(Fraction(stream["avg_frame_rate"]))
    if not math.isfinite(avg) or avg <= 0:
        raise ValueError("평균 프레임률을 확인할 수 없습니다. render.fps를 명시하세요.")
    common = [Fraction(x) for x in ("10", "15", "24", "25", "30", "50", "60", "120",
                                    "24000/1001", "30000/1001", "60000/1001")]
    closest = min(common, key=lambda f: abs(float(f) - avg))
    return str(closest) if abs(float(closest) - avg) < 0.1 else str(Fraction(avg).limit_denominator(1001))


def build_video(m):
    cuts = m["cuts"]
    first = video_stream(m["sources"][cuts[0]["source_id"]]["probe"])
    render = m["render"]
    # Old manifests without the new fields retain their original encoding behavior.
    encoding = {"crf": render.get("crf", 18), "preset": render.get("preset", "medium"),
                "audio_bitrate": render.get("audio_bitrate", "192k")}
    if not number(encoding["crf"]) or not 0 <= encoding["crf"] <= 51:
        raise ValueError("render.crf는 0~51이어야 합니다.")
    if encoding["preset"] not in ("ultrafast", "superfast", "veryfast", "faster", "fast",
                                   "medium", "slow", "slower", "veryslow"):
        raise ValueError("지원하지 않는 H.264 preset입니다.")
    if not re.fullmatch(r"[1-9][0-9]*k", str(encoding["audio_bitrate"])):
        raise ValueError("audio_bitrate는 128k 같은 형식이어야 합니다.")
    fps_text = str(render["fps"] if "fps" in render else choose_fps(first))
    if "fps" not in render and "max_fps" in render:
        cap = render["max_fps"]
        if not number(cap) or cap <= 0:
            raise ValueError("render.max_fps는 양수여야 합니다.")
        fps_text = str(min(Fraction(fps_text), Fraction(str(cap))))
    fps = float(Fraction(fps_text))
    if fps <= 0 or not math.isfinite(fps):
        raise ValueError("출력 fps는 양수여야 합니다.")
    w, h = m["render"].get("size", display_size(first))
    if any(not isinstance(x, int) or x < 2 or x % 2 for x in (w, h)):
        raise ValueError("H.264 출력 크기는 2 이상의 짝수여야 합니다.")
    args = [binary("ffmpeg"), "-v", "error", "-n", "-copyts"]
    filters, concat, timeline = [], [], []
    input_index, unit, clock = 0, 0, 0.0
    with tempfile.TemporaryDirectory(dir=m["run_dir"]) as work:
        work = Path(work)
        for cut in cuts:
            sid = cut["source_id"]
            card = cut.get("break_before")
            if card:
                duration = math.ceil(card["duration_s"] * fps - 1e-7) / fps
                image = Image.new("RGB", (max(w, 640), max(h, 640)), "#17202a")
                heading(image, card["text"], image.height // 2 - 80, 42, "white")
                image = image.resize((w, h))
                path = work / f"card{unit}.png"
                image.save(path)
                args += ["-loop", "1", "-framerate", fps_text, "-i", str(path)]
                filters += [f"[{input_index}:v]trim=duration={duration},setpts=PTS-STARTPTS,"
                            f"fps={fps_text},setsar=1,format=yuv420p,settb=AVTB[v{unit}]",
                            f"anullsrc=r=48000:cl=stereo,atrim=duration={duration},asetpts=PTS-STARTPTS[a{unit}]"]
                concat.append(f"[v{unit}][a{unit}]")
                timeline.append({"kind": "break", "text": card["text"], "output_start_s": clock,
                                 "output_end_s": clock + duration})
                clock += duration
                input_index += 1
                unit += 1
            source = m["sources"][sid]
            frames = catalog(m, sid)
            start = frame_at(m, sid, cut["start_s"])["time_s"]
            end = (source["duration_s"] if cut["end_s"] > frames[-1]["time_s"]
                   else frame_at(m, sid, cut["end_s"])["time_s"])
            if end <= start:
                raise ValueError("프레임에 맞춘 편집 구간이 비었습니다.")
            duration = math.ceil((end - start) * fps - 1e-7) / fps
            origin = frames[0]["pts_s"]
            absolute_start, absolute_end = origin + start, origin + end
            args += ["-i", source["path"]]
            filters.append(f"[{input_index}:v]trim=start={absolute_start}:end={absolute_end},"
                           f"setpts=PTS-({absolute_start})/TB,fps={fps_text},"
                           f"scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
                           f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p,"
                           f"tpad=stop_mode=clone:stop_duration={1/fps},trim=duration={duration},settb=AVTB[v{unit}]")
            has_audio = any(s["codec_type"] == "audio" for s in source["probe"]["streams"])
            if has_audio:
                audio = (f"[{input_index}:a:0]atrim=start={absolute_start}:end={absolute_end},"
                         f"asetpts=PTS-({absolute_start})/TB,aresample=48000:async=1:first_pts=0,"
                         f"aformat=sample_fmts=fltp:channel_layouts=stereo,apad,atrim=duration={duration}")
            else:
                audio = f"anullsrc=r=48000:cl=stereo,atrim=duration={duration},asetpts=PTS-STARTPTS"
            filters.append(audio + f"[a{unit}]")
            concat.append(f"[v{unit}][a{unit}]")
            timeline.append({"kind": "source", "source_id": sid, "source_start_s": start,
                             "source_end_s": end, "output_start_s": clock, "output_end_s": clock + duration,
                             "padding_s": duration - (end - start), "has_original_audio": has_audio})
            clock += duration
            input_index += 1
            unit += 1
        filters.append("".join(concat) + f"concat=n={unit}:v=1:a=1[v][a]")
        staged = work / "render.mp4"
        args += ["-filter_complex_threads", "2", "-filter_complex", ";".join(filters),
                 "-map", "[v]", "-map", "[a]", "-map_metadata", "-1", "-c:v", "libx264",
                 "-preset", encoding["preset"], "-crf", str(encoding["crf"]), "-threads", "4", "-pix_fmt", "yuv420p",
                 "-c:a", "aac", "-b:a", encoding["audio_bitrate"], "-ar", "48000", "-ac", "2",
                 "-movflags", "+faststart", str(staged)]
        execute(args, m["run_dir"])
        publish(staged, m["outputs"]["video"])
    output = Path(m["outputs"]["video"])
    source_bytes = sum(m["sources"][sid]["size"] for sid in {x["source_id"] for x in cuts})
    m["rendered"] = {"timeline": timeline, "duration_s": clock, "fps": fps_text, "size": [w, h],
                     "encoding": encoding, "source_bytes": source_bytes, "output_bytes": output.stat().st_size,
                     "reduction_percent": 100 * (1 - output.stat().st_size / source_bytes),
                     "video_sha256": sha256(output)}


def markdown_documents(m):
    run = Path(m["run_dir"])
    lines = ["# 미확인 사항", "", "발언·화면 관찰·사용자 설명을 구분한 기록이다. 입력값을 출력에서 역산해 확정하지 않는다.", ""]
    for x in m.get("unknowns", []):
        lines.append(f"- {x}")
    for scene in m["scenes"]:
        lines += [f"\n## {scene['id']} · {scene['source_id']} · {scene['start_s']:g}~{scene['end_s']:g}초",
                  "", f"화면 관찰: {scene.get('observation', '미기록')}"]
        for speech in scene.get("speech", []):
            lines.append(f"\n전사 근거: {speech['source_id']} {speech['at_s']:g}초 — {speech['text']}")
        lines += [f"\n- 미확인: {s}" for s in scene.get("unknowns", [])]
    for sid, source in m["sources"].items():
        if source["kind"] == "video" and not any(s["codec_type"] == "audio" for s in source["probe"]["streams"]):
            lines.append(f"\n- {sid}: 원본 음성 트랙 없음. 연결에 필요한 경우 무음 트랙을 사용했다.")
    if m["review"].get("audio") != "verified":
        lines.append("\n- 오디오 직접 청취 확인 없음. 전사 대조와 수치상 동기 검증은 청감 자연스러움 검증과 다르다.")
    (run / "미확인사항.md").write_text("\n".join(lines) + "\n")
    lines = ["# 추출 사진 안내", "", "조건은 연결된 장면의 근거를 확인한다. 전체 프레임 PNG에는 주석·색 보정을 적용하지 않았다.", ""]
    for x in m["captures"]:
        if "path" in x:
            lines += [f"- [{Path(x['path']).name}]({Path(x['path']).name}) · {x['source_id']} · "
                      f"{x['source_time_s']:.6f}초 · {x.get('observation', '관찰 미기록')}"]
    for pair in m["pairs"]:
        if "path" in pair:
            relative = "비교/" + Path(pair["path"]).name
            lines.append(f"- [{pair['title']}]({relative}) · {pair['note']} · {pair['continuity']}")
    (run / "사진안내.md").write_text("\n".join(lines) + "\n")
    if m["mode"] in ("photos", "both"):
        folder = Path(m["outputs"]["photos"])
        for name in ("미확인사항.md", "사진안내.md"):
            publish(run / name, folder / name)


def build_run(manifest):
    m = load(manifest)
    if not inputs_unchanged(m):
        raise ValueError("원본 해시가 변경됐습니다. 기존 실행을 계속하지 않습니다.")
    validate_selection(m)
    requested = (["photos", "zip"] if m["mode"] in ("photos", "both") else [])
    requested += ["video"] if m["mode"] in ("video", "both") else []
    if m["mode"] in ("video", "both") and "video_local" in m["outputs"]:
        requested.append("video_local")
    for key in requested:
        path = Path(m["outputs"][key])
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"덮어쓰기하지 않습니다. 새 inspect 실행을 사용하세요: {path}")
    if m["mode"] in ("photos", "both"):
        build_photos(m)
    if m["mode"] in ("video", "both"):
        build_video(m)
    markdown_documents(m)
    if m["mode"] in ("photos", "both"):
        folder = Path(m["outputs"]["photos"])
        with zipfile.ZipFile(m["outputs"]["zip"], "x", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    archive.write(path, Path(folder.name) / path.relative_to(folder))
    # Copy after making the photo ZIP so the archive remains photos and notes only.
    if m["mode"] in ("video", "both") and "video_local" in m["outputs"]:
        source = Path(m["outputs"]["video"])
        local = Path(m["outputs"]["video_local"])
        if source.resolve() != local.resolve():
            publish(source, local)
    m["checks"] = {}
    save(manifest, m)
    return m["outputs"]


def verify_run(manifest):
    m = load(manifest)
    checks = {"originals_unchanged": inputs_unchanged(m)}
    details = {}
    if m["mode"] in ("photos", "both"):
        valid = True
        for x in m["captures"]:
            path = Path(x.get("path", ""))
            if not path.is_file():
                valid = False
                continue
            frame = frame_at(m, x["source_id"], x["at_s"])
            with Image.open(path) as im:
                valid &= im.size == display_size(video_stream(m["sources"][x["source_id"]]["probe"]))
            valid &= frame["index"] == x["frame_index"] and abs(frame["pts_s"] - x["frame_pts_s"]) < 1e-7
            valid &= sha256(path) == x.get("sha256")
        checks["photo_dimensions_and_provenance"] = bool(valid and m["captures"])
        checks["comparison_files"] = all(Path(p.get("path", "")).is_file() for p in m["pairs"])
        archive = Path(m["outputs"]["zip"])
        checks["zip_integrity"] = False
        if archive.is_file():
            with zipfile.ZipFile(archive) as z:
                checks["zip_integrity"] = z.testzip() is None
    if m["mode"] in ("video", "both"):
        path = Path(m["outputs"]["video"])
        checks["video_exists"] = path.is_file()
        if "video_local" in m["outputs"]:
            local = Path(m["outputs"]["video_local"])
            expected = m.get("rendered", {}).get("video_sha256")
            checks["video_copy_integrity"] = bool(expected and path.is_file() and local.is_file()
                and sha256(path) == expected and sha256(local) == expected)
        if path.is_file():
            info = probe(path, m["run_dir"])
            v = video_stream(info)
            audio = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
            rotation = [x.get("rotation", 0) for x in v.get("side_data_list", [])]
            duration = float(info["format"]["duration"])
            rendered = m["rendered"]
            checks["video_format"] = (v["codec_name"] == "h264" and v["pix_fmt"] == "yuv420p"
                                      and [v["width"], v["height"]] == rendered["size"] and not any(rotation))
            checks["fps"] = abs(float(Fraction(v["avg_frame_rate"])) - float(Fraction(rendered["fps"]))) < .001
            checks["audio_format"] = bool(audio and audio["codec_name"] == "aac" and audio["sample_rate"] == "48000" and audio["channels"] == 2)
            tolerance = max(.1, 2 / float(Fraction(rendered["fps"])))
            checks["duration"] = abs(duration - rendered["duration_s"]) <= tolerance
            av_gap = (abs(float(v.get("start_time", 0)) + float(v["duration"])
                          - float(audio.get("start_time", 0)) - float(audio["duration"]))
                      if audio else None)
            checks["av_end_difference"] = av_gap is not None and av_gap <= .1
            error = None
            try:
                execute([binary("ffmpeg"), "-v", "error", "-xerror", "-i", path, "-f", "null", "-"], m["run_dir"])
            except RuntimeError as exc:
                error = str(exc)
            checks["full_decode"] = error is None
            details.update(video_duration_s=duration, av_end_difference_s=av_gap, decode_error=error)
    needed_review = (["photos"] if m["mode"] in ("photos", "both") else [])
    needed_review += ["boundaries"] if m["mode"] in ("video", "both") else []
    technical = all(checks.values())
    audio_recorded = (m["mode"] == "photos" or m["review"].get("audio") in ("verified", "unavailable"))
    report = {"technical_pass": technical,
              "complete": technical and audio_recorded and all(m["review"].get(k) == "verified" for k in needed_review),
              "checks": checks, "review": m["review"], **details}
    m["checks"] = report
    for s in m["sources"].values():
        s["sha256_after"] = sha256(s["path"]) if Path(s["path"]).is_file() else None
    save(manifest, m)
    save(Path(m["run_dir"]) / "검증결과.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="원본 조사 및 덮어쓰지 않는 실행 폴더 생성")
    location = inspect.add_mutually_exclusive_group(required=True)
    location.add_argument("--experiment", type=int)
    location.add_argument("--experiment-dir", type=Path)
    inspect.add_argument("--label", required=True)
    inspect.add_argument("--source", action="append", type=Path, required=True)
    inspect.add_argument("--transcript", action="append", default=[], metavar="p1=PATH")
    inspect.add_argument("--mode", choices=["photos", "video", "both"], default="photos")
    inspect.add_argument("--deliver-dir", type=Path, default=Path.home() / "Downloads")
    preview = commands.add_parser("preview", help="시각을 표시한 전체/상세 프레임 미리보기")
    preview.add_argument("manifest", type=Path)
    preview.add_argument("--source-id", required=True)
    preview.add_argument("--start", type=float, default=0)
    preview.add_argument("--end", type=float)
    preview.add_argument("--step", type=float, default=1)
    for name in ("build", "verify"):
        sub = commands.add_parser(name)
        sub.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            folder = args.experiment_dir
            if folder is None:
                root = Path(__file__).resolve().parents[4]
                sys.path.insert(0, str(root))
                from scripts.lab.config import experiment_dir
                folder = root / experiment_dir(args.experiment)
            transcripts = {}
            for pair in args.transcript:
                sid, path = pair.split("=", 1)
                if sid in transcripts:
                    raise ValueError("같은 원본의 전사본 중복 지정")
                transcripts[sid] = path
            result = str(inspect_run(folder, args.label, args.source, transcripts, args.mode, args.deliver_dir))
        elif args.command == "preview":
            result = preview_run(args.manifest, args.source_id, args.start, args.end, args.step)
        elif args.command == "build":
            result = build_run(args.manifest)
        else:
            result = verify_run(args.manifest)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return int(args.command == "verify" and not result["complete"])
    except (ValueError, RuntimeError, FileExistsError, KeyError, OSError) as error:
        print(f"오류: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
