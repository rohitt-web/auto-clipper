from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from urllib.parse import urlparse

app = FastAPI(title="Auto Clipper AI", version="0.1.0")

class AnalyseRequest(BaseModel):
    url: HttpUrl
    caption_language: str = "auto"

@app.get("/api/health")
def health():
    return {"status": "ok", "worker_ready": False}

@app.post("/api/analyse")
def analyse(request: AnalyseRequest):
    host = (urlparse(str(request.url)).hostname or "").lower()
    if not (host == "twitch.tv" or host.endswith(".twitch.tv") or host == "kick.com" or host.endswith(".kick.com")):
        raise HTTPException(status_code=400, detail="Only Twitch and Kick URLs are accepted in this build.")
    # Deliberately fail clearly until the media worker is implemented and deployed.
    raise HTTPException(
        status_code=503,
        detail="The web interface is online, but the video-processing worker is not installed yet. No video has been downloaded or analysed."
    )
