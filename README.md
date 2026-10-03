# Beast Anime Studio Complete Production Pipeline v4

This package keeps the existing frontend and adds a production backend.

### Added
- Existing `/video/create` compatibility
- Hindi TTS endpoint `/audio/tts`
- Episode planning endpoint `/episode/plan`
- Multi-scene rendering endpoint `/episode/render`
- FFmpeg scene stitching
- Hindi dialogue mixing
- Render-ready environment variables

### Environment variables
- `REPLICATE_API_TOKEN` (required, Render only)
- `BACKEND_PUBLIC_URL` = `https://dipsan.onrender.com`
- `REPLICATE_VIDEO_MODEL` = `vidu/q3-turbo`
- `REPLICATE_TTS_MODEL` = `minimax/speech-02-turbo`

### Important
Long episodes are assembled from short AI-generated clips. The current video model is not asked to generate a 15–20 minute clip in one request.

The backend provides the audio/TTS and episode-render building blocks. Music/SFX/VFX asset libraries are not bundled because they require actual licensed/original assets; the frontend can describe those layers for the production plan.
