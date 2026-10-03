import os
import secrets
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from google.cloud import storage
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

app = FastAPI(title="Beast Anime Studio Cloud API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "https://dipsan.onrender.com/youtube/callback",
)
TOKEN_FILE = Path(os.getenv("YOUTUBE_TOKEN_FILE", "/tmp/youtube_token.json"))

def oauth_config():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in Render.",
        )
    return {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }

@app.get("/health")
def health():
    return {"status": "ok", "service": "beast-anime-cloud-api"}

@app.get("/workflow")
def workflow():
    return {
        "steps": ["story", "scene_plan", "voice", "video_render", "youtube_upload", "analytics"],
        "youtube_oauth": True,
    }

@app.get("/youtube/auth")
def youtube_auth():
    flow = Flow.from_client_config(
        oauth_config(), scopes=YOUTUBE_SCOPES, redirect_uri=REDIRECT_URI
    )
    state = secrets.token_urlsafe(32)
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return RedirectResponse(authorization_url)

@app.get("/youtube/callback")
def youtube_callback(code: str, state: Optional[str] = None):
    flow = Flow.from_client_config(
        oauth_config(), scopes=YOUTUBE_SCOPES, redirect_uri=REDIRECT_URI
    )
    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"YouTube OAuth failed: {exc}")
    TOKEN_FILE.write_text(flow.credentials.to_json(), encoding="utf-8")
    return HTMLResponse(
        "<html><body style='font-family:Arial;padding:30px'>"
        "<h2>YouTube connected successfully.</h2>"
        "<p>You can close this window and return to Beast Anime Studio.</p>"
        "</body></html>"
    )

@app.get("/youtube/status")
def youtube_status():
    if not TOKEN_FILE.exists():
        return {"connected": False}
    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), YOUTUBE_SCOPES)
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        youtube = build("youtube", "v3", credentials=creds)
        response = youtube.channels().list(part="snippet", mine=True).execute()
        items = response.get("items", [])
        if not items:
            return {"connected": False, "reason": "No YouTube channel was returned."}
        channel = items[0]
        return {
            "connected": True,
            "channel_id": channel.get("id"),
            "channel_title": channel.get("snippet", {}).get("title"),
        }
    except Exception as exc:
        return {"connected": False, "reason": str(exc)}

@app.post("/storage/upload")
async def storage_upload(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    bucket_name = os.getenv("GCS_BUCKET")
    if not bucket_name:
        raise HTTPException(status_code=500, detail="GCS_BUCKET is not configured.")
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        object_name = f"temp/{file.filename}"
        blob = bucket.blob(object_name)
        blob.upload_from_file(file.file, content_type=file.content_type or "video/mp4")
        return {"ok": True, "object_name": object_name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/storage/list")
def storage_list():
    bucket_name = os.getenv("GCS_BUCKET")
    if not bucket_name:
        raise HTTPException(status_code=500, detail="GCS_BUCKET is not configured.")
    try:
        client = storage.Client()
        blobs = client.list_blobs(bucket_name, prefix="temp/")
        return {"objects": [b.name for b in blobs]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.delete("/storage/{object_name:path}")
def storage_delete(object_name: str):
    bucket_name = os.getenv("GCS_BUCKET")
    if not bucket_name:
        raise HTTPException(status_code=500, detail="GCS_BUCKET is not configured.")
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        bucket.blob(object_name).delete()
        return {"ok": True, "deleted": object_name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/workflow/verify-and-clean")
def verify_and_clean(object_name: str, youtube_video_id: str):
    if not youtube_video_id.strip():
        raise HTTPException(status_code=400, detail="A non-empty YouTube video ID is required.")
    bucket_name = os.getenv("GCS_BUCKET")
    if not bucket_name:
        raise HTTPException(status_code=500, detail="GCS_BUCKET is not configured.")
    try:
        client = storage.Client()
        client.bucket(bucket_name).blob(object_name).delete()
        return {"ok": True, "deleted": object_name, "youtube_video_id": youtube_video_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
