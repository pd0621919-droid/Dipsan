import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage

app = FastAPI(title="Beast Anime Studio Cloud API", version="1.0.0")

origins = [x.strip() for x in os.getenv("FRONTEND_ORIGIN", "*").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BUCKET = os.getenv("GCS_BUCKET", "")
PREFIX = os.getenv("GCS_TEMP_PREFIX", "beast-anime/temp")
TMP = Path(os.getenv("LOCAL_TMP_DIR", "/tmp/beast-anime"))
TMP.mkdir(parents=True, exist_ok=True)

def client():
    if not BUCKET:
        raise HTTPException(500, "GCS_BUCKET is not configured")
    return storage.Client()

@app.get("/health")
def health():
    return {"status":"ok","service":"beast-anime-studio","time":datetime.now(timezone.utc).isoformat()}

@app.get("/workflow")
def workflow():
    return {
        "steps":[
            "generate_story",
            "generate_hindi_voice",
            "render_ffmpeg",
            "upload_temp_gcs",
            "upload_youtube",
            "verify_youtube",
            "prepare_next_day",
            "delete_verified_temp"
        ]
    }

@app.post("/storage/upload")
async def upload_video(file: UploadFile = File(...), name: Optional[str] = None):
    if not file.filename.lower().endswith(".mp4"):
        raise HTTPException(400, "Only MP4 files are accepted in this V1 endpoint")
    target = name or file.filename
    object_name = f"{PREFIX}/{target}"
    data = await file.read()
    bucket = client().bucket(BUCKET)
    blob = bucket.blob(object_name)
    blob.upload_from_string(data, content_type="video/mp4")
    return {"status":"uploaded","bucket":BUCKET,"object":object_name,"bytes":len(data)}

@app.get("/storage/list")
def list_temp():
    blobs = client().list_blobs(BUCKET, prefix=f"{PREFIX}/")
    return {"objects":[b.name for b in blobs]}

@app.delete("/storage/{object_name:path}")
def delete_temp(object_name: str):
    if not object_name.startswith(PREFIX + "/"):
        raise HTTPException(400, "Object is outside the temporary prefix")
    client().bucket(BUCKET).blob(object_name).delete()
    return {"status":"deleted","object":object_name}

@app.post("/workflow/verify-and-clean")
def verify_and_clean(object_name: str, youtube_video_id: str):
    # V1 guardrail: cleanup is only allowed after a non-empty YouTube ID is supplied.
    # A production version should call YouTube to verify the video exists before deleting.
    if not youtube_video_id.strip():
        raise HTTPException(400, "YouTube video ID is required before cleanup")
    if not object_name.startswith(PREFIX + "/"):
        raise HTTPException(400, "Object is outside the temporary prefix")
    client().bucket(BUCKET).blob(object_name).delete()
    return {"status":"verified_cleanup_requested","youtube_video_id":youtube_video_id,"object":object_name}
