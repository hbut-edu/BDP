import json
import shutil
import subprocess
from pathlib import Path
from typing import Iterator

import numpy as np


class FFmpegError(RuntimeError):
    """Raised when ffmpeg or ffprobe cannot complete the requested operation."""


def require_ffmpeg() -> None:
    """Fail early with an actionable message when ffmpeg is missing."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise FFmpegError(
            "ffmpeg and ffprobe are required. Install ffmpeg before running this lab."
        )


def _parse_fraction(value: str | None) -> float:
    if not value or value == "0/0":
        return 0.0
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        try:
            denominator_value = float(denominator)
            return 0.0 if denominator_value == 0 else float(numerator) / denominator_value
        except ValueError:
            return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def probe_video(path: Path) -> dict:
    """Return basic video metadata from ffprobe as a plain dictionary."""
    require_ffmpeg()
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,avg_frame_rate,nb_frames,duration",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise FFmpegError(completed.stderr.strip() or f"ffprobe failed for {path}")

    payload = json.loads(completed.stdout or "{}")
    streams = payload.get("streams") or []
    if not streams:
        raise FFmpegError(f"no video stream found in {path}")

    stream = streams[0]
    duration = stream.get("duration") or (payload.get("format") or {}).get("duration")
    fps = _parse_fraction(stream.get("avg_frame_rate"))
    return {
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "fps": fps,
        "duration_sec": float(duration or 0.0),
        "frame_count": int(stream.get("nb_frames") or 0),
    }


def scaled_size(width: int, height: int, target_width: int) -> tuple[int, int]:
    """Compute an even ffmpeg-friendly scaled size while preserving aspect ratio."""
    if width <= 0 or height <= 0:
        return target_width, target_width
    scaled_height = max(2, int(round(height * target_width / width)))
    if scaled_height % 2:
        scaled_height += 1
    return target_width, scaled_height


def iter_sampled_frames(
    path: Path,
    *,
    sample_fps: int,
    max_frames: int,
    analysis_width: int,
) -> Iterator[np.ndarray]:
    """Yield RGB frames sampled from a video by streaming raw frames from ffmpeg."""
    metadata = probe_video(path)
    width, height = scaled_size(metadata["width"], metadata["height"], analysis_width)
    frame_size = width * height * 3
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(path),
        "-vf",
        f"fps={sample_fps},scale={width}:{height}",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "pipe:1",
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.stdout is not None
    yielded = 0
    try:
        while yielded < max_frames:
            chunk = process.stdout.read(frame_size)
            if len(chunk) < frame_size:
                break
            frame = np.frombuffer(chunk, dtype=np.uint8).reshape((height, width, 3))
            yielded += 1
            yield frame
    finally:
        if process.poll() is None:
            process.terminate()
        _, stderr = process.communicate(timeout=5)
        if yielded == 0 and process.returncode not in (0, None):
            raise FFmpegError(stderr.decode("utf-8", errors="ignore").strip())


def create_thumbnail(video_path: Path, thumbnail_path: Path) -> None:
    """Extract a middle-ish frame as a JPEG thumbnail for the website."""
    require_ffmpeg()
    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-ss",
        "00:00:01",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-q:v",
        "3",
        str(thumbnail_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise FFmpegError(completed.stderr.strip() or "thumbnail extraction failed")


def extract_audio_track(video_path: Path, audio_path: Path) -> bool:
    """Extract a mono 16 kHz wav track for ASR, returning False when no audio exists."""
    require_ffmpeg()
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        str(audio_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        message = completed.stderr.lower()
        if "output file #0 does not contain any stream" in message or "stream map" in message:
            return False
        return False
    return audio_path.exists() and audio_path.stat().st_size > 44
