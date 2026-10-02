# Beast Anime Studio — Merged V1

A mobile-first website starter that combines the two uploaded Beast Anime projects.

## What is included

- Mobile-friendly dashboard
- Original anime universe/story-bible editor
- Childhood → growing-up → teen → adult chapter progression
- 4 Shorts + 2 long-video daily planner
- SEO draft generator in the browser
- GitHub Pages-ready frontend
- FastAPI cloud backend
- Google Cloud Storage temporary MP4 workflow
- Safe cleanup guardrail after a YouTube video ID is supplied
- PWA/offline shell

## Important V1 limitation

This package is a working architecture/starter, not a magic one-click AI studio. The actual paid/credentialed services still need to be connected:

1. AI story generation API
2. Hindi TTS
3. AI image/video generation provider
4. FFmpeg rendering worker
5. Google Cloud Storage credentials
6. YouTube OAuth + upload
7. YouTube Analytics
8. A real job queue/worker for scheduled production

Do not put API keys or Google OAuth secrets in the frontend.

## Free/mobile setup

### Website
Upload the root frontend files to a GitHub repository and enable GitHub Pages. The website can run from a phone browser.

### Cloud backend
Deploy `backend/` to a Python-compatible cloud service. Set:

- `FRONTEND_ORIGIN`
- `GCS_BUCKET`
- `GCS_TEMP_PREFIX`
- Google Application Credentials for the storage service account

Then open the website's Settings tab and enter the backend URL.

## Local backend test

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `/docs` on the backend URL.

## Production workflow

Phone website
→ cloud API
→ story generation
→ Hindi narration
→ scene generation
→ FFmpeg render
→ temporary GCS MP4
→ YouTube upload
→ verify upload
→ schedule next day
→ delete only the verified old temporary file

Keep the project original and age-appropriate. YouTube growth and monetization are not guaranteed.
