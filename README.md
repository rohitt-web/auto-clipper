# Auto Clipper AI

A browser-first tool for finding highlight moments in creator-approved Twitch/Kick VODs and turning selected moments into vertical clips.

## Current status

Project scaffold is being built. The first milestone is a working web interface and API contract. Full-video AI processing requires a backend worker with FFmpeg and speech transcription; it cannot run reliably inside a mobile browser alone.

## Planned workflow

1. Paste a Twitch or Kick VOD URL.
2. Submit it for analysis.
3. Review candidate moments and timestamps.
4. Select moments and render 9:16 clips.
5. Add Hindi/English captions and download MP4 files.

## Important limits

- Start with public Twitch/Kick VODs; YouTube ingestion may be added only where platform access permits.
- The project will not bypass private, subscriber-only, age-gated, DRM-protected, or access-controlled streams.
- Clip only content you have permission to reuse; follow each platform's terms and the creator's clipping policy.
- Free hosting and unlimited video processing are not realistic. Expect per-job limits and external hosting/compute constraints.

## Development

The initial scaffold will document the web client and processing API. See `docs/ROADMAP.md` for milestones.
