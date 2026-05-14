import subprocess
from pathlib import Path

import numpy as np

from .config import INCOMING_DIR, ensure_directories
from .ffmpeg_tools import FFmpegError, require_ffmpeg


def _draw_circle(frame: np.ndarray, cx: int, cy: int, radius: int, color: tuple[int, int, int]) -> None:
    yy, xx = np.ogrid[: frame.shape[0], : frame.shape[1]]
    mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius**2
    frame[mask] = color


def _draw_rect(
    frame: np.ndarray,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: tuple[int, int, int],
) -> None:
    frame[max(0, y0) : min(frame.shape[0], y1), max(0, x0) : min(frame.shape[1], x1)] = color


def _campus_sports_frame(index: int, total: int, width: int, height: int) -> np.ndarray:
    y = np.linspace(0, 1, height, dtype=np.float32)[:, None]
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, :, 0] = (65 + 35 * (1 - y)).astype(np.uint8)
    frame[:, :, 1] = (150 + 55 * y).astype(np.uint8)
    frame[:, :, 2] = (210 - 75 * y).astype(np.uint8)
    _draw_rect(frame, 0, int(height * 0.66), width, height, (38, 150, 76))
    for lane in range(4):
        y0 = int(height * (0.72 + lane * 0.055))
        _draw_rect(frame, 20, y0, width - 20, y0 + 5, (240, 245, 230))
    progress = index / max(1, total - 1)
    cx = 45 + int((width - 90) * progress)
    cy = int(height * 0.72 + 30 * np.sin(progress * np.pi * 4))
    _draw_circle(frame, cx, cy, 24, (245, 205, 64))
    _draw_circle(frame, width - cx // 2, int(height * 0.42), 18, (255, 255, 255))
    return frame


def _night_scene_frame(index: int, total: int, width: int, height: int) -> np.ndarray:
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, :, :] = (8, 12, 24)
    progress = index / max(1, total - 1)
    for lamp in range(6):
        cx = int((lamp + 0.5) * width / 6)
        cy = int(height * (0.28 + 0.08 * np.sin(progress * np.pi * 2 + lamp)))
        _draw_circle(frame, cx, cy, 8, (45, 70, 130))
    _draw_rect(frame, 0, int(height * 0.72), width, height, (5, 8, 14))
    _draw_circle(frame, int(40 + progress * (width - 80)), int(height * 0.78), 16, (65, 95, 145))
    return frame


def _flashy_frame(index: int, total: int, width: int, height: int) -> np.ndarray:
    palette = [
        (245, 245, 245),
        (12, 16, 32),
        (245, 212, 64),
        (18, 42, 190),
    ]
    color = palette[(index // 5) % len(palette)]
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, :, :] = color
    progress = index / max(1, total - 1)
    cx = int(width * (0.2 + 0.6 * progress))
    _draw_circle(frame, cx, int(height * 0.48), 32, (240, 90, 80))
    return frame


FRAME_BUILDERS = {
    "campus_sports": _campus_sports_frame,
    "night_scene_review": _night_scene_frame,
    "flashy_clip_review": _flashy_frame,
}

DEMO_TITLES = {
    "campus_sports": "校园运动短视频",
    "night_scene_review": "夜间低照度街景",
    "flashy_clip_review": "强闪烁舞台片段",
}


def create_demo_video(
    output_path: Path,
    *,
    kind: str,
    seconds: int = 6,
    width: int = 360,
    height: int = 640,
    fps: int = 24,
    overwrite: bool = False,
) -> Path:
    """Create a small vertical MP4 using generated RGB frames."""
    require_ffmpeg()
    if output_path.exists() and not overwrite:
        return output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    builder = FRAME_BUILDERS[kind]
    total_frames = seconds * fps
    command = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{height}",
        "-r",
        str(fps),
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.stdin is not None
    try:
        for index in range(total_frames):
            frame = builder(index, total_frames, width, height)
            process.stdin.write(frame.tobytes())
    finally:
        process.stdin.close()
    stderr = process.stderr.read().decode("utf-8", errors="ignore") if process.stderr else ""
    return_code = process.wait()
    if return_code != 0:
        raise FFmpegError(stderr.strip() or f"failed to create {output_path}")
    return output_path


def ensure_demo_videos(overwrite: bool = False) -> list[dict]:
    """Create the three local demo videos and return ingestion descriptors."""
    ensure_directories()
    videos = []
    for kind, title in DEMO_TITLES.items():
        path = INCOMING_DIR / f"{kind}.mp4"
        create_demo_video(path, kind=kind, overwrite=overwrite)
        videos.append({"path": path, "title": title, "source": "generated-demo"})
    return videos

