import json
import os
import re
import subprocess
import threading
import wave

import numpy as np
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp
from faster_whisper import WhisperModel
from store import DATA_DIR, update_job

MAX_DURATION_SECONDS = int(os.getenv("MAX_VOD_SECONDS", "10800"))
MODEL_NAME = os.getenv("WHISPER_MODEL", "small")
OUTPUT_DIR = DATA_DIR / "jobs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
_model = None
_analysis_lock = threading.Lock()

def _whisper():
    global _model
    if _model is None:
        _model = WhisperModel(MODEL_NAME, device=os.getenv("WHISPER_DEVICE", "cpu"),
                              compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"))
    return _model

def _run(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout)[-2500:] or "Media command failed")
    return result.stdout

def _safe_source(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    allowed = host == "twitch.tv" or host.endswith(".twitch.tv") or host == "kick.com" or host.endswith(".kick.com")
    if parsed.scheme != "https" or not allowed:
        raise ValueError("Only HTTPS public Twitch and Kick VOD links are supported.")

def _download(url, folder):
    _safe_source(url)
    opts = {
        "outtmpl": str(folder / "source.%(ext)s"),
        "format": "best[height<=1080]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "max_filesize": int(os.getenv("MAX_DOWNLOAD_BYTES", str(6 * 1024**3))),
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        duration = float(info.get("duration") or 0)
        if duration <= 0:
            raise ValueError("Could not determine VOD duration.")
        if duration > MAX_DURATION_SECONDS:
            raise ValueError(f"VOD exceeds the {MAX_DURATION_SECONDS/3600:.0f}-hour limit.")
        ydl.download([url])
    files = [p for p in folder.glob("source.*") if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}]
    if not files:
        raise RuntimeError("No usable video file was downloaded.")
    return files[0], duration

def _audio_energy(audio_path):
    # Measure two-second RMS windows from the mono 16 kHz analysis track.
    values = []
    with wave.open(str(audio_path), "rb") as wav:
        rate = wav.getframerate()
        chunk_frames = rate * 2
        while True:
            raw = wav.readframes(chunk_frames)
            if not raw:
                break
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
            if samples.size:
                values.append(float(np.sqrt(np.mean(samples * samples))))
    if not values:
        return []
    baseline = max(float(np.median(values)), 1.0)
    return [value / baseline for value in values]

def _transcribe(video, language):
    audio = video.parent / "audio.wav"
    _run(["ffmpeg", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(audio)])
    lang = None if language == "auto" else language
    segments, info = _whisper().transcribe(str(audio), language=lang, vad_filter=True,
                                           word_timestamps=False, beam_size=3)
    rows = []
    for seg in segments:
        text = (seg.text or "").strip()
        if text:
            rows.append({"start": float(seg.start), "end": float(seg.end), "text": text})
    return rows, info.language or language, _audio_energy(audio)

def _score_window(rows, start, end, energy):
    text = " ".join(r["text"] for r in rows if r["start"] < end and r["end"] > start)
    lower = text.lower()
    cues = ["no way", "oh my god", "what", "bro", "lets go", "insane", "crazy",
            "holy", "wait", "help", "shit", "fuck", "damn", "wow",
            "अरे", "क्या", "भाई", "नहीं", "ओह", "चल", "पागल", "हंस"]
    cue_hits = sum(1 for cue in cues if cue in lower)
    punctuation = min(text.count("!") + text.count("?"), 5)
    words = len(re.findall(r"\w+", text, flags=re.UNICODE))
    first = max(0, int(start / 2))
    last = min(len(energy), max(first + 1, int(end / 2) + 1))
    activity = energy[first:last]
    mean_activity = float(np.mean(activity)) if activity else 1.0
    peak_activity = float(np.percentile(activity, 90)) if activity else 1.0
    audio_score = min(max(mean_activity - 1.0, 0.0), 2.0) * 0.7
    audio_score += min(max(peak_activity - 1.0, 0.0), 3.0) * 0.35
    score = cue_hits * 2.2 + punctuation * 0.55 + min(words / 42.0, 1.5) + audio_score
    return score, text[:260]

def _find_moments(rows, duration, energy):
    candidates = []
    start = 0.0
    while start < duration:
        end = min(duration, start + 36.0)
        score, excerpt = _score_window(rows, start, end, energy)
        if excerpt and score > 0:
            candidates.append({"start_seconds": round(start, 2), "end_seconds": round(end, 2),
                               "score": round(score, 2), "reason": "Transcript + audio activity score",
                               "excerpt": excerpt})
        start += 18.0
    candidates.sort(key=lambda x: x["score"], reverse=True)
    selected = []
    for item in candidates:
        if all(abs(item["start_seconds"] - old["start_seconds"]) >= 24 for old in selected):
            item["title"] = f"Highlight candidate {len(selected)+1}"
            selected.append(item)
        if len(selected) >= 12:
            break
    selected.sort(key=lambda x: x["start_seconds"])
    return selected

def analyse_job(job_id, url, language):
    # Keep one Whisper/download job active per container to avoid exhausting phone-sized/free-tier resources.
    with _analysis_lock:
        _analyse_job(job_id, url, language)

def _analyse_job(job_id, url, language):
    folder = OUTPUT_DIR / job_id
    folder.mkdir(parents=True, exist_ok=True)
    try:
        update_job(job_id, status="downloading", progress=5, message="Fetching public VOD")
        video, duration = _download(url, folder)
        update_job(job_id, status="transcribing", progress=35, message="Transcribing speech")
        rows, detected_language, energy = _transcribe(video, language)
        update_job(job_id, status="ranking", progress=75, message="Ranking candidate moments")
        moments = _find_moments(rows, duration, energy)
        (folder / "transcript.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        update_job(job_id, status="ready", progress=100,
                   message=f"Found {len(moments)} candidates. Detected language: {detected_language}.",
                   duration=duration, moments_json=moments)
    except Exception as exc:
        update_job(job_id, status="failed", progress=100, message="Analysis failed", error=str(exc)[:1500])

def _srt_time(seconds):
    ms = int(max(0, seconds) * 1000)
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def render_clips(job_id, selected_indices):
    from store import get_job
    job = get_job(job_id)
    if not job:
        raise ValueError("Job not found")
    folder = OUTPUT_DIR / job_id
    video_files = [p for p in folder.glob("source.*") if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}]
    if not video_files:
        raise ValueError("Original VOD is missing; submit it again.")
    video = video_files[0]
    rows_path = folder / "transcript.json"
    rows = json.loads(rows_path.read_text(encoding="utf-8")) if rows_path.exists() else []
    clips = []
    for idx in selected_indices:
        moment = job["moments"][idx]
        start, end = float(moment["start_seconds"]), float(moment["end_seconds"])
        subtitle = folder / f"clip-{idx+1}.srt"
        relevant = [r for r in rows if r["start"] < end and r["end"] > start]
        lines = []
        for cue_no, row in enumerate(relevant, start=1):
            cue_start = max(0.0, row["start"] - start)
            cue_end = max(cue_start + 0.25, min(end - start, row["end"] - start))
            lines.append(f"{cue_no}\n{_srt_time(cue_start)} --> {_srt_time(cue_end)}\n{row['text']}\n")
        subtitle.write_text("\n".join(lines), encoding="utf-8")
        output = folder / f"clip-{idx+1}.mp4"
        subtitle_path = subtitle.as_posix().replace(":", "\\:").replace("'", "\\'")
        vf = f"[0:v]split=2[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=18:8[bg];[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,subtitles='{subtitle_path}'"
        _run(["ffmpeg", "-y", "-ss", str(start), "-i", str(video), "-t", str(end-start),
              "-filter_complex", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
              "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output)])
        clips.append({"index": idx, "filename": output.name,
                      "url": f"/api/jobs/{job_id}/clips/{output.name}"})
    return clips
