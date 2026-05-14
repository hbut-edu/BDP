from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
INCOMING_DIR = DATA_DIR / "incoming"
MEDIA_DIR = DATA_DIR / "media"
FRAME_DIR = MEDIA_DIR / "frames"
AUDIO_DIR = MEDIA_DIR / "audio"
MODEL_DIR = DATA_DIR / "models"
STATE_DIR = DATA_DIR / "state"
DB_PATH = STATE_DIR / "short_video_demo.sqlite3"

SAMPLE_FPS = 2
MAX_SAMPLED_FRAMES = 80
ANALYSIS_WIDTH = 160
VLM_FRAME_WIDTH = 448
MAX_VLM_KEYFRAMES = 12
LOCAL_VLM_MAX_IMAGES = int(os.getenv("LOCAL_VLM_MAX_IMAGES", "4"))
SCENE_CHANGE_THRESHOLD = 42.0
MOTION_PEAK_THRESHOLD = 18.0

DEFAULT_MODEL_ID = "qwen3-vl-4b-ollama"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
LOCAL_VLM_TIMEOUT_SEC = int(os.getenv("LOCAL_VLM_TIMEOUT_SEC", "180"))
LOCAL_VLM_MAX_TOKENS = int(os.getenv("LOCAL_VLM_MAX_TOKENS", "3500"))
ALLOW_LOCAL_MODEL_FALLBACK = os.getenv("ALLOW_LOCAL_MODEL_FALLBACK", "1") != "0"

BANNED_TITLE_WORDS = {
    "adult",
    "bloody",
    "gambling",
    "violent",
    "violence",
    "成人",
    "博彩",
    "赌博",
    "暴力",
    "血腥",
}


def ensure_directories() -> None:
    """Create the directories used by the local demo runtime."""
    for directory in (DATA_DIR, INCOMING_DIR, MEDIA_DIR, FRAME_DIR, AUDIO_DIR, MODEL_DIR, STATE_DIR):
        directory.mkdir(parents=True, exist_ok=True)
