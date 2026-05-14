from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.demo_assets import ensure_demo_videos  # noqa: E402
from app.model_registry import set_active_model  # noqa: E402
from app.pipeline import ShortVideoPipeline  # noqa: E402
from app.storage import clear_db, list_events, list_videos, stats  # noqa: E402


def main() -> None:
    clear_db()
    set_active_model("qwen3-vl-4b-ollama")
    pipeline = ShortVideoPipeline()
    for item in ensure_demo_videos(overwrite=True):
        pipeline.process_video(
            Path(item["path"]),
            title=item["title"],
            source=item["source"],
            simulate_stream=False,
        )

    videos = list_videos()
    current_stats = stats()
    assert len(videos) == 3, f"expected 3 videos, got {len(videos)}"
    assert current_stats["published"] >= 1, current_stats
    assert current_stats["review"] >= 1, current_stats
    assert len(list_events()) >= 12, "expected pipeline events"
    for video in videos:
        assert video["tags"], f"missing tags for {video['id']}"
        assert video["caption"], f"missing caption for {video['id']}"
        assert video["metrics"]["sampled_frames"] > 0, f"missing frame samples for {video['id']}"
        assert video["metrics"]["model"]["selected_id"] == "qwen3-vl-4b-ollama"
        assert video["metrics"]["model"]["backend"] == "local_ollama_vlm", video["metrics"]["model"]
        assert video["metrics"]["preprocess"]["keyframes"] > 0
    print("verification passed")
    print(current_stats)


if __name__ == "__main__":
    main()
