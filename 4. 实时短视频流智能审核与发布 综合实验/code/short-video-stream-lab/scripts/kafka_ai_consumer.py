import json
import os
from pathlib import Path
import sys

from kafka import KafkaConsumer, KafkaProducer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.pipeline import ShortVideoPipeline  # noqa: E402


BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
INGEST_TOPIC = os.getenv("SHORT_VIDEO_INGEST_TOPIC", "short_video_ingest")
RESULT_TOPIC = os.getenv("SHORT_VIDEO_RESULT_TOPIC", "short_video_result")


def main() -> None:
    pipeline = ShortVideoPipeline()
    consumer = KafkaConsumer(
        INGEST_TOPIC,
        bootstrap_servers=BOOTSTRAP,
        auto_offset_reset="earliest",
        group_id="short-video-ai-reviewer",
        value_deserializer=lambda raw: json.loads(raw.decode("utf-8")),
    )
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode("utf-8"),
    )
    print(f"listening on {INGEST_TOPIC}, publishing decisions to {RESULT_TOPIC}")
    for message in consumer:
        payload = message.value
        record = pipeline.process_video(
            Path(payload["path"]),
            title=payload.get("title"),
            source=payload.get("source", "kafka"),
            simulate_stream=True,
        )
        result = {
            "id": record["id"],
            "title": record["title"],
            "status": record["status"],
            "risk_score": record["risk_score"],
            "tags": record["tags"],
        }
        producer.send(RESULT_TOPIC, value=result)
        producer.flush()
        print(f"processed: {result}")


if __name__ == "__main__":
    main()

