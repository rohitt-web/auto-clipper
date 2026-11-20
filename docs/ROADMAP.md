# Roadmap

## Implemented in MVP
- Mobile-first VOD submission interface.
- Async job status polling.
- Public Twitch/Kick VOD download with duration and size limits.
- faster-whisper transcription with auto/hi/en selection.
- Transcript heuristic candidate ranking.
- User selection of up to six moments.
- FFmpeg vertical export with blurred background, full gameplay frame, and burned-in subtitles.
- SQLite job records and Docker Compose packaging.

## Next engineering milestones
1. Add audio energy / loudness analysis and Twitch/Kick chat activity signals.
2. Add a visual highlight model for gameplay events and facecam reactions.
3. Improve bilingual caption segmentation, punctuation, and editable subtitle timing.
4. Add authenticated users, quotas, queue management, job expiry, and object storage.
5. Add safe YouTube ingestion only through an explicitly permitted integration.
6. Add deployment and smoke-test instructions for a persistent container host.

## Known quality boundary
The current moment ranker is a transparent transcript heuristic. It is not a visual AI model and cannot reliably identify silent gameplay events or expressions visible only in the video.
