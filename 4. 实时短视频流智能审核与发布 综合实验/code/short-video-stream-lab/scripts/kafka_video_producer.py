import json
import os
from pathlib import Path
import sys
import time

from kafka import KafkaProducer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.demo_assets import ensure_demo_videos  # noqa: E402


BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("SHORT_VIDEO_INGEST_TOPIC", "short_video_ingest")


def main() -> None:
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode("utf-8"),
    )
    for item in ensure_demo_videos(overwrite=False):
        event = {
            "title": item["title"],
            "path": str(Path(item["path"]).resolve()),
            "source": item["source"],
            "event_time": int(time.time() * 1000),
        }
        producer.send(TOPIC, value=event)
        print(f"sent to {TOPIC}: {event}")
    producer.flush()
    producer.close()


if __name__ == "__main__":
    main()

