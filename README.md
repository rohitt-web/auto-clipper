# Auto Clipper AI

A mobile-first browser app and containerized worker for analysing creator-approved public Twitch and Kick VODs, suggesting highlight timestamps, and rendering selected clips as vertical MP4s.

## Current implementation

- Mobile web interface for VOD submission, progress polling, moment selection, and clip downloads.
- FastAPI backend with SQLite job records.
- yt-dlp ingestion for eligible public Twitch/Kick VODs.
- faster-whisper speech transcription with automatic, Hindi, or English language selection.
- Baseline candidate ranking using transcript cue words, punctuation, speech density, and two-second audio RMS activity.
- FFmpeg rendering to 1080x1920 with the full landscape frame preserved over a blurred background and burned-in subtitles.
- Docker Compose deployment.

## Important: what this detector does and does not do

This first version is a transcript-based highlight suggester. It does not yet understand on-screen GTA events, facecam reactions, streamer facial expressions, or Twitch/Kick chat spikes. The scoring is a transparent heuristic, not a trained highlight model. Hindi-English code-switching transcription quality depends on the VOD audio and Whisper model.

## Requirements

- Docker Engine and Docker Compose plugin.
- Recommended server: at least 4 vCPU, 8 GB RAM, and 20 GB free disk for the small Whisper model and temporary media. More is better.
- FFmpeg is installed inside the container.

## Run

From the repository root, copy .env.example to .env, set a strong private username and password, then run: docker compose up --build

Open http://localhost:8000. Your browser will ask for the username and password. Never commit the .env file or share its password. The first transcription may take longer because the Whisper model must be downloaded. Persistent job data is stored in the clipper-data Docker volume.

## Configuration

| Variable | Default | Meaning |
|---|---:|---|
| DATA_DIR | /data | Persistent jobs and SQLite database |
| MAX_VOD_SECONDS | 10800 | Maximum VOD duration (3 hours) |
| MAX_DOWNLOAD_BYTES | 6442450944 | Approximate download size limit (6 GiB) |
| WHISPER_MODEL | small | faster-whisper model |
| WHISPER_DEVICE | cpu | CPU or CUDA |
| WHISPER_COMPUTE_TYPE | int8 | Quantization for CPU inference |

## API

- GET /api/health
- POST /api/analyse with a VOD URL and caption_language auto, hi, or en
- GET /api/jobs/{job_id}
- POST /api/jobs/{job_id}/clips with selected moment_indices
- GET /api/jobs/{job_id}/clips/{filename}

## Current limitations

- Only public Twitch and Kick VOD URLs are accepted. YouTube is not implemented.
- Maximum VOD duration is 3 hours; default download cap is 6 GiB.
- One analysis runs at a time per container. Rendering is CPU-intensive.
- This is a single-instance MVP. It needs a proper queue, per-user accounts, quotas, job expiry/cleanup, and persistent object storage before public multi-user deployment.
- The app uses shared HTTP Basic authentication. Set APP_USERNAME and APP_PASSWORD before use; the service refuses requests if they are missing. There is not yet per-user accounts or rate limiting.
- Free cloud hosts generally cannot promise the CPU, RAM, disk, execution time, and persistent storage needed for multi-hour video analysis.

## Content and platform rules

Only process content you have permission to download, edit, and republish. Public availability does not automatically grant reuse rights. Respect each creator's clipping policy, platform terms, and takedown requests. The app does not attempt to bypass private, subscriber-only, DRM-protected, or access-controlled streams.
