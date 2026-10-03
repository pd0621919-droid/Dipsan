import os
import uuid
import requests
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Beast Anime Studio V3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = Path("/tmp/beast_videos")
OUTPUT_DIR.mkdir(exist_ok=True)

REPLICATE_TOKEN = os.getenv("REPLICATE_API_TOKEN")
MODEL = os.getenv("REPLICATE_MODEL", "wan-video/wan-2.1-1.3b")


class VideoRequest(BaseModel):
    prompt: str
    seconds: int = 5
    aspect_ratio: str = "16:9"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "video_provider": "replicate",
        "configured": bool(REPLICATE_TOKEN),
        "model": MODEL,
    }


@app.post("/video/create")
def create_video(req: VideoRequest):
    if not REPLICATE_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="REPLICATE_API_TOKEN is not configured."
        )

    if req.seconds != 5:
        raise HTTPException(
            status_code=400,
            detail="First test supports exactly 5 seconds."
        )

    response = requests.post(
        f"https://api.replicate.com/v1/models/{MODEL}/predictions",
        headers={
            "Authorization": f"Bearer {REPLICATE_TOKEN}",
            "Content-Type": "application/json",
            "Prefer": "wait=60",
        },
        json={
            "input": {
                "prompt": req.prompt,
                "frame_num": 81,
                "resolution": "480p",
                "aspect_ratio": req.aspect_ratio,
                "sample_shift": 8,
                "sample_steps": 30,
                "sample_guide_scale": 6,
            }
        },
        timeout=75,
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text[:1000],
        )

    data = response.json()
    output = data.get("output")

    if not output:
        return {
            "ok": True,
            "status": data.get("status"),
            "prediction_id": data.get("id"),
            "message": "Generation is still processing.",
        }

    video_url = output if isinstance(output, str) else str(output)

    filename = f"{uuid.uuid4().hex}.mp4"
    destination = OUTPUT_DIR / filename

    download = requests.get(video_url, stream=True, timeout=120)
    download.raise_for_status()

    with open(destination, "wb") as file:
        for chunk in download.iter_content(1024 * 1024):
            if chunk:
                file.write(chunk)

    return {
        "ok": True,
        "status": "succeeded",
        "download": f"/video/{filename}",
    }


@app.get("/video/{filename}")
def get_video(filename: str):
    path = OUTPUT_DIR / Path(filename).name

    if not path.exists():
        raise HTTPException(404, "Video not found.")

    return FileResponse(
        path,
        media_type="video/mp4",
        filename=path.name,
)
