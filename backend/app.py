import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl, Field

from store import DATA_DIR, create_job, get_job, init_db, update_job
from worker import analyse_job, render_clips

app = FastAPI(title="Auto Clipper AI", version="0.3.0")
init_db()
security = HTTPBasic()

def require_auth(credentials: HTTPBasicCredentials = Depends(security)):
    expected_user = os.getenv("APP_USERNAME", "")
    expected_password = os.getenv("APP_PASSWORD", "")
    if not expected_user or not expected_password:
        raise HTTPException(status_code=503, detail="Set APP_USERNAME and APP_PASSWORD before using the app.")
    user_ok = secrets.compare_digest(credentials.username, expected_user)
    password_ok = secrets.compare_digest(credentials.password, expected_password)
    if not (user_ok and password_ok):
        raise HTTPException(status_code=401, detail="Incorrect username or password.",
                            headers={"WWW-Authenticate": "Basic"})
    return credentials.username
WEB_DIR = Path(__file__).resolve().parent.parent / "web"

@app.get("/", include_in_schema=False)
def home(_: str = Depends(require_auth)):
    index = WEB_DIR / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=503, detail="Web client files are not installed in this deployment.")
    return FileResponse(index)

@app.get("/style.css", include_in_schema=False)
def stylesheet(_: str = Depends(require_auth)):
    return FileResponse(WEB_DIR / "style.css", media_type="text/css")

@app.get("/app.js", include_in_schema=False)
def javascript(_: str = Depends(require_auth)):
    return FileResponse(WEB_DIR / "app.js", media_type="application/javascript")

class AnalyseRequest(BaseModel):
    url: HttpUrl
    caption_language: str = Field(default="auto", pattern="^(auto|hi|en)$")

class RenderRequest(BaseModel):
    moment_indices: list[int] = Field(min_length=1, max_length=6)

def validate_source(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    allowed = host == "twitch.tv" or host.endswith(".twitch.tv") or host == "kick.com" or host.endswith(".kick.com")
    if parsed.scheme != "https" or not allowed:
        raise HTTPException(status_code=400, detail="Only HTTPS public Twitch and Kick VOD URLs are supported.")

@app.get("/api/health")
def health():
    return {"status": "ok", "worker_ready": True,
            "max_vod_seconds": int(os.getenv("MAX_VOD_SECONDS", "10800"))}

@app.post("/api/analyse", status_code=202)
def analyse(request: AnalyseRequest, background: BackgroundTasks, _: str = Depends(require_auth)):
    url = str(request.url)
    validate_source(url)
    job_id = uuid.uuid4().hex
    create_job(job_id, url, request.caption_language)
    background.add_task(analyse_job, job_id, url, request.caption_language)
    return {"job_id": job_id, "status": "queued", "message": "VOD queued for analysis."}

@app.get("/api/jobs/{job_id}")
def job_status(job_id: str, _: str = Depends(require_auth)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {k: job[k] for k in ("id", "status", "progress", "message", "duration", "moments", "clips", "error")}

@app.post("/api/jobs/{job_id}/clips", status_code=202)
def create_clips(job_id: str, request: RenderRequest, background: BackgroundTasks, _: str = Depends(require_auth)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job["status"] != "ready":
        raise HTTPException(status_code=409, detail="Wait until analysis is ready.")
    if any(i < 0 or i >= len(job["moments"]) for i in request.moment_indices):
        raise HTTPException(status_code=400, detail="One or more selected moment indices are invalid.")
    update_job(job_id, status="rendering", progress=0, message="Rendering selected clips")
    background.add_task(_render_task, job_id, request.moment_indices)
    return {"status": "rendering", "message": "Clip rendering started."}

def _render_task(job_id, indices):
    try:
        clips = render_clips(job_id, indices)
        update_job(job_id, status="complete", progress=100,
                   message=f"Rendered {len(clips)} clips.", clips_json=clips)
    except Exception as exc:
        update_job(job_id, status="failed", progress=100, message="Clip rendering failed",
                   error=str(exc)[:1500])

@app.get("/api/jobs/{job_id}/clips/{filename}")
def download_clip(job_id: str, filename: str, _: str = Depends(require_auth)):
    if not re.fullmatch(r"clip-\d+\.mp4", filename):
        raise HTTPException(status_code=400, detail="Invalid filename.")
    path = DATA_DIR / "jobs" / job_id / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Clip not found.")
    return FileResponse(path, media_type="video/mp4", filename=filename)
