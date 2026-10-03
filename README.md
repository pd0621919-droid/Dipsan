# Beast Anime Studio — Fast Video Backend

This backend adds a small, real MP4 text-to-video pipeline to Beast Anime Studio.

## Current model

The package uses `vidu/q3-turbo` by default. It is a current Replicate video model designed for faster iteration and supports text-to-video clips up to 16 seconds, with optional synchronized audio.

The first test should stay small (the frontend defaults to 5 seconds). Do not try to generate a 15–20 minute episode in one request.

## Environment variables

Required on Render:

- `REPLICATE_API_TOKEN` — your existing private Render environment variable.

Optional:

- `BACKEND_PUBLIC_URL=https://dipsan.onrender.com`
- `REPLICATE_VIDEO_MODEL=vidu/q3-turbo`

Never put the real Replicate token in `.env.example`, GitHub, `index.html`, or JavaScript.

## Routes

- `GET /health`
- `POST /video/create`
- `GET /video/{filename}`

FastAPI Swagger docs are available at `/docs`.

## Render start command

Use:

```text
uvicorn main:app --host 0.0.0.0 --port $PORT
```

If your Render service already has an equivalent FastAPI start command, keep it.

## YouTube OAuth

This package is intentionally focused on the video-generation pipeline. It does not contain or expose YouTube OAuth credentials.

Because the existing repository's current OAuth implementation was not available inside this ZIP-generation environment, do not delete unrelated OAuth routes/configuration from your existing application when integrating this backend. If your production `main.py` contains OAuth routes that are not present in this package, preserve those routes when applying the video routes.

## Storage note

Generated MP4s are saved under `backend/generated_videos/` and served immediately through `/video/{filename}`. Render filesystems can be ephemeral, so this is intended as the first working test pipeline rather than permanent media storage.
