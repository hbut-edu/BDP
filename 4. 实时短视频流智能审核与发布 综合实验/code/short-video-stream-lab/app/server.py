import threading
import time
from pathlib import Path
import re

import uvicorn
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .config import BASE_DIR, INCOMING_DIR, MEDIA_DIR, ensure_directories
from .demo_assets import ensure_demo_videos
from .model_registry import get_active_model, list_model_candidates, set_active_model
from .ollama_vlm import OllamaVLMClient, OllamaModelError
from .pipeline import ShortVideoPipeline
from .storage import add_event, clear_db, list_events, list_videos, stats


ensure_directories()
app = FastAPI(
    title="Short Video Stream Review Demo",
    description="Real-time short video understanding, moderation, tagging, and publishing demo.",
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
pipeline = ShortVideoPipeline()
processing_lock = threading.Lock()
ollama_client = OllamaVLMClient()


class ModelSelectionRequest(BaseModel):
    model_id: str


def _models_payload() -> dict:
    candidates = list_model_candidates()
    try:
        local_names = ollama_client.list_local_models()
        ollama_ready = True
    except OllamaModelError:
        local_names = set()
        ollama_ready = False
    for candidate in candidates:
        ollama_model = candidate.get("ollama_model")
        candidate["downloaded"] = True if not ollama_model else ollama_model in local_names
    active = get_active_model().to_dict()
    active["downloaded"] = True if not active.get("ollama_model") else active["ollama_model"] in local_names
    return {"active": active, "candidates": candidates, "ollama_ready": ollama_ready}


def _start_background_job(background_tasks: BackgroundTasks, target, *args, **kwargs) -> bool:
    if not processing_lock.acquire(blocking=False):
        return False

    def runner() -> None:
        try:
            target(*args, **kwargs)
        except Exception as exc:
            add_event(None, "system_failed", "后台处理任务失败", {"error": str(exc)})
        finally:
            processing_lock.release()

    background_tasks.add_task(runner)
    return True


def _process_demo(overwrite: bool = False) -> None:
    add_event(None, "system", "开始准备内置短视频样本", {"overwrite": overwrite})
    for descriptor in ensure_demo_videos(overwrite=overwrite):
        pipeline.process_video(
            Path(descriptor["path"]),
            title=descriptor["title"],
            source=descriptor["source"],
            simulate_stream=True,
        )
    add_event(None, "system", "内置样本处理完成", {})


def _process_uploaded(path: Path, title: str) -> None:
    pipeline.process_video(path, title=title, source="browser-upload", simulate_stream=True)


def _safe_upload_name(filename: str) -> str:
    name = Path(filename).name
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", Path(name).stem).strip("-") or "upload"
    suffix = Path(name).suffix.lower()
    return f"{stem}{suffix}"


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/media/{filename:path}")
def media(filename: str):
    path = MEDIA_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="media not found")
    return FileResponse(path)


@app.get("/api/health")
def health():
    models = _models_payload()
    return {
        "ok": True,
        "processing": processing_lock.locked(),
        "active_model": models["active"],
        "ollama_ready": models["ollama_ready"],
    }


@app.get("/api/models")
def api_models():
    return _models_payload()


@app.post("/api/models/select")
def api_select_model(selection: ModelSelectionRequest):
    if processing_lock.locked():
        raise HTTPException(status_code=409, detail="pipeline is running")
    try:
        active = set_active_model(selection.model_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    add_event(None, "model_config", f"后台模型已切换为 {active.name}", active.to_dict())
    return {"active": active.to_dict()}


@app.get("/api/videos")
def api_videos():
    return {"videos": list_videos(), "stats": stats()}


@app.get("/api/videos/{status}")
def api_videos_by_status(status: str):
    if status not in {"published", "review", "rejected"}:
        raise HTTPException(status_code=400, detail="invalid status")
    return {"videos": list_videos(status=status), "stats": stats()}


@app.get("/api/events")
def api_events():
    return {"events": list_events(limit=80)}


@app.post("/api/demo")
def api_demo(background_tasks: BackgroundTasks, overwrite: bool = False):
    started = _start_background_job(background_tasks, _process_demo, overwrite)
    if not started:
        raise HTTPException(status_code=409, detail="pipeline is already running")
    return {"started": True, "processing": True}


@app.post("/api/upload")
async def api_upload(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    title: str | None = Form(default=None),
):
    if not video.filename:
        raise HTTPException(status_code=400, detail="missing video file")

    original_name = _safe_upload_name(video.filename) or f"upload-{int(time.time())}.mp4"
    suffix = Path(original_name).suffix.lower()
    if suffix not in {".mp4", ".mov", ".m4v", ".webm"}:
        raise HTTPException(status_code=400, detail="only mp4/mov/m4v/webm video files are accepted")

    safe_name = f"{int(time.time())}-{original_name}"
    target = INCOMING_DIR / safe_name
    target.write_bytes(await video.read())

    started = _start_background_job(background_tasks, _process_uploaded, target, title or Path(original_name).stem)
    if not started:
        raise HTTPException(status_code=409, detail="pipeline is already running")
    return {"started": True, "path": str(target)}


@app.post("/api/reset")
def api_reset():
    if processing_lock.locked():
        raise HTTPException(status_code=409, detail="pipeline is running")
    clear_db()
    add_event(None, "system", "演示数据库已清空", {})
    return {"ok": True}


def main() -> None:
    uvicorn.run("app.server:app", host="127.0.0.1", port=5050, reload=False)


if __name__ == "__main__":
    main()
