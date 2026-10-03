import os, uuid, subprocess, tempfile, shutil
from pathlib import Path
from typing import List

import replicate
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).resolve().parent
VIDEO_DIR = APP_DIR / "backend" / "generated_videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "https://dipsan.onrender.com").rstrip("/")
TOKEN = os.getenv("REPLICATE_API_TOKEN")
VIDEO_MODEL = os.getenv("REPLICATE_VIDEO_MODEL", "vidu/q3-turbo")
TTS_MODEL = os.getenv("REPLICATE_TTS_MODEL", "minimax/speech-02-turbo")

app = FastAPI(title="Beast Anime Studio Complete Pipeline", version="4.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

class VideoReq(BaseModel):
    prompt: str = Field(min_length=1, max_length=5000)
    duration: int = Field(default=8, ge=1, le=16)
    resolution: str = Field(default="720p", pattern=r"^(540p|720p|1080p)$")
    aspect_ratio: str = Field(default="16:9", pattern=r"^(16:9|9:16|3:4|4:3|1:1)$")
    audio: bool = True

class TTSReq(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    voice: str = "female"
    language: str = "Hindi"

class Scene(BaseModel):
    number: int
    type: str
    seconds: int = Field(ge=1, le=16)
    prompt: str
    dialogue: str = ""
    voice: str = "female"

class EpisodeReq(BaseModel):
    title: str
    scenes: List[Scene]
    resolution: str = Field(default="720p", pattern=r"^(540p|720p|1080p)$")
    aspect_ratio: str = Field(default="16:9", pattern=r"^(16:9|9:16|3:4|4:3|1:1)$")
    add_audio: bool = True

def require_token():
    if not TOKEN:
        raise HTTPException(500, "REPLICATE_API_TOKEN is missing in Render Environment Variables.")

def save_output(out, suffix):
    data = out.read() if hasattr(out, "read") else None
    if not data:
        raise ValueError("Model returned no file bytes.")
    name = f"beastbound_{uuid.uuid4().hex}{suffix}"
    (VIDEO_DIR / name).write_bytes(data)
    return name

def url(name): return f"{PUBLIC_URL}/video/{name}"

def run_video(scene, resolution, ratio, audio=False):
    out = replicate.run(VIDEO_MODEL, input={"prompt": scene.prompt, "duration": min(16, scene.seconds), "resolution": resolution, "aspect_ratio": ratio, "audio": audio})
    data = out.read() if hasattr(out, "read") else None
    if not data: raise RuntimeError(f"Scene {scene.number} returned no video.")
    return data

def ffmpeg(): return shutil.which("ffmpeg")

@app.get("/health")
def health():
    return {"ok": True, "service": "beast-anime-complete-pipeline", "replicate_configured": bool(TOKEN), "video_model": VIDEO_MODEL, "tts_model": TTS_MODEL, "ffmpeg": bool(ffmpeg())}

@app.post("/video/create")
def create_video(req: VideoReq):
    require_token()
    try:
        out = replicate.run(VIDEO_MODEL, input=req.model_dump())
        name = save_output(out, ".mp4")
        return {"success": True, "model": VIDEO_MODEL, "filename": name, "video_url": url(name)}
    except Exception as e:
        raise HTTPException(502, f"Video generation failed: {e}")

@app.post("/audio/tts")
def create_tts(req: TTSReq):
    require_token()
    try:
        out = replicate.run(TTS_MODEL, input={"text": req.text, "voice_id": req.voice, "language": req.language})
        name = save_output(out, ".mp3")
        return {"success": True, "model": TTS_MODEL, "filename": name, "audio_url": url(name)}
    except Exception as e:
        raise HTTPException(502, f"TTS generation failed: {e}")

@app.post("/episode/plan")
def episode_plan(req: EpisodeReq):
    if not req.scenes: raise HTTPException(400, "At least one scene is required.")
    return {"success": True, "title": req.title, "scene_count": len(req.scenes), "total_planned_seconds": sum(s.seconds for s in req.scenes), "scenes": [s.model_dump() for s in req.scenes]}

@app.post("/episode/render")
def render_episode(req: EpisodeReq):
    require_token()
    if not req.scenes: raise HTTPException(400, "At least one scene is required.")
    if not ffmpeg(): raise HTTPException(500, "FFmpeg is not installed on the Render server.")
    work = Path(tempfile.mkdtemp(prefix="beastbound_"))
    try:
        clips=[]; voices=[]
        for s in req.scenes:
            clip=work/f"scene_{s.number:03d}.mp4"
            clip.write_bytes(run_video(s, req.resolution, req.aspect_ratio, False))
            clips.append(clip)
            if req.add_audio and s.dialogue.strip():
                tts=replicate.run(TTS_MODEL, input={"text":s.dialogue,"voice_id":s.voice,"language":"Hindi"})
                data=tts.read() if hasattr(tts,"read") else None
                if data:
                    ap=work/f"voice_{s.number:03d}.mp3"; ap.write_bytes(data); voices.append(ap)
        concat=work/"concat.txt"; concat.write_text("\n".join(f"file '{p.as_posix()}'" for p in clips))
        joined=work/"joined.mp4"
        subprocess.run([ffmpeg(),"-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(joined)],check=True,capture_output=True)
        final=joined
        if voices:
            vlist=work/"voices.txt"; vlist.write_text("\n".join(f"file '{p.as_posix()}'" for p in voices))
            vjoined=work/"voices.mp3"
            subprocess.run([ffmpeg(),"-y","-f","concat","-safe","0","-i",str(vlist),"-c:a","libmp3lame",str(vjoined)],check=True,capture_output=True)
            mixed=work/"final.mp4"
            subprocess.run([ffmpeg(),"-y","-i",str(joined),"-i",str(vjoined),"-map","0:v:0","-map","1:a:0","-c:v","copy","-shortest",str(mixed)],check=True,capture_output=True)
            final=mixed
        name=f"beastbound_episode_{uuid.uuid4().hex}.mp4"; shutil.copyfile(final, VIDEO_DIR/name)
        return {"success":True,"title":req.title,"scene_count":len(req.scenes),"total_seconds":sum(s.seconds for s in req.scenes),"filename":name,"video_url":url(name)}
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, f"FFmpeg failed: {e.stderr.decode(errors='ignore')[-1200:]}")
    except Exception as e:
        raise HTTPException(502, f"Episode render failed: {e}")
    finally:
        shutil.rmtree(work, ignore_errors=True)

@app.get("/video/{filename}")
def get_video(filename: str):
    if Path(filename).name != filename or not filename.endswith((".mp4", ".mp3", ".wav")): raise HTTPException(400,"Invalid media filename.")
    p=VIDEO_DIR/filename
    if not p.is_file(): raise HTTPException(404,"Media not found.")
    media="video/mp4" if filename.endswith(".mp4") else ("audio/mpeg" if filename.endswith(".mp3") else "audio/wav")
    return FileResponse(p, media_type=media, filename=filename)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT","10000")))
