from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.demo_assets import ensure_demo_videos  # noqa: E402


def main() -> None:
    videos = ensure_demo_videos(overwrite=True)
    for item in videos:
        print(f"created: {item['path']} ({item['title']})")


if __name__ == "__main__":
    main()

