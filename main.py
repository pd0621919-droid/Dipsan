import os
import uuid
from pathlib import Path
from typing import Optional

import replicate
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
VIDEO_DIR = APP_DIR / "generated_videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "https://dipsan.onrender.com").rstrip("/")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

# Fast first-pipeline model: text-to-video, 1–16 seconds, synchronized audio.
REPLICATE_MODEL = os.getenv("REPLICATE_VIDEO_MODEL", "vidu/q3-turbo")

DEFAULT_PROMPT = (
    "Original anime-inspired cinematic scene, a mysterious young hero stands in an "
    "ancient ruined forest at night. A gigantic dimensional portal opens behind him, "
    "glowing Beast energy surrounds his body, wind and debris swirl through the air, "
    "strange ancient symbols illuminate the ground, his eyes briefly glow with unknown "
    "power, and a huge mysterious shadow moves inside the portal. Dynamic camera "
    "movement, dramatic cinematic lighting, intense energy particles, powerful "
    "atmosphere, highly detailed original animation, mysterious cliffhanger feeling. "
    "Original characters and original world, no existing anime characters."
)

app = FastAPI(title="Beast Anime Studio Video API", version="3.0-fast")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class VideoCreateRequest(BaseModel):
    prompt: str = Field(default=DEFAULT_PROMPT, min_length=1, max_length=5000)
    duration: int = Field(default=5, ge=1, le=16)
    resolution: str = Field(default="720p", pattern=r"^(540p|720p|1080p)$")
    aspect_ratio: str = Field(default="16:9", pattern=r"^(16:9|9:16|3:4|4:3|1:1)$")
    audio: bool = True


def _public_video_url(filename: str) -> str:
    return f"{BACKEND_PUBLIC_URL}/video/{filename}"


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "beast-anime-studio-video",
        "replicate_configured": bool(REPLICATE_API_TOKEN),
        "model": REPLICATE_MODEL,
    }


@app.post("/video/create")
def create_video(request: VideoCreateRequest):
    if not REPLICATE_API_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="REPLICATE_API_TOKEN is missing. Add it only to Render Environment Variables.",
        )

    # Never accept or expose the token from the browser.
    try:
        output = replicate.run(
            REPLICATE_MODEL,
            input={
                "prompt": request.prompt,
                "duration": request.duration,
                "resolution": request.resolution,
                "aspect_ratio": request.aspect_ratio,
                "audio": request.audio,
            },
        )
    except Exception as exc:
        message = str(exc).strip() or "Unknown Replicate error."
        raise HTTPException(
            status_code=502,
            detail=f"Replicate video generation failed: {message}",
        ) from exc

    # Replicate's current video models return a file-like output with .read().
    try:
        video_bytes = output.read() if hasattr(output, "read") else None
        if not video_bytes:
            raise ValueError("Replicate returned no video bytes.")
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Replicate returned an unusable video output: {exc}",
        ) from exc

    filename = f"beastbound_{uuid.uuid4().hex}.mp4"
    destination = VIDEO_DIR / filename
    try:
        destination.write_bytes(video_bytes)
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not save generated MP4 on the server: {exc}",
        ) from exc

    return {
        "success": True,
        "model": REPLICATE_MODEL,
        "duration": request.duration,
        "filename": filename,
        "video_url": _public_video_url(filename),
    }


@app.get("/video/{filename}")
def get_video(filename: str):
    # Only serve generated .mp4 files from our own directory.
    if (
        Path(filename).name != filename
        or not filename.lower().endswith(".mp4")
        or "/" in filename
        or "\\" in filename
    ):
        raise HTTPException(status_code=400, detail="Invalid video filename.")

    video_path = VIDEO_DIR / filename
    if not video_path.is_file():
        raise HTTPException(status_code=404, detail="Video not found.")

    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=filename,
    )


# Render can run this file directly with: uvicorn main:app --host 0.0.0.0 --port $PORT
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        reload=False,
    )
