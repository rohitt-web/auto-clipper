# Roadmap

## Milestone 1 — Mobile-first interface
- URL input for supported public Twitch/Kick VODs
- Analysis status and candidate-moment list
- Clip preview and download controls

## Milestone 2 — Processing worker
- Validate and fetch an authorized public VOD
- Extract audio with FFmpeg
- Transcribe Hindi/English speech
- Rank candidate moments using transcript cues and audio activity
- Render selected ranges as 9:16 MP4

## Milestone 3 — Captions and reliability
- Hindi/English caption tracks
- Caption timing and style controls
- Per-job limits, cleanup, and error reporting

## Technical reality
A mobile browser cannot reliably download and analyse multi-hour streams itself. The worker needs server CPU, memory, disk, and FFmpeg. Free hosting tiers may sleep, time out, or restrict media workloads. The app should expose these limits instead of promising unlimited free processing.
