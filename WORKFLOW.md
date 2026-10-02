# Cloud workflow notes

## Intended sequence
1. Generate script/storyboard and render episode on a cloud worker.
2. Store rendered MP4 in a **private** Google Cloud Storage bucket (`episodes/temporary/...`).
3. Upload it to YouTube using server-side OAuth credentials.
4. Verify YouTube returned a video ID and the upload is complete.
5. Enqueue next day's episode generation.
6. Wait until the next episode has rendered and is safely stored.
7. Delete the previous temporary GCS object. Keep the YouTube copy untouched.

Use a durable database queue (e.g. PostgreSQL + a task queue) with idempotency keys. Do not rely on a browser tab or phone staying open. Retry failed uploads; never delete the only copy before successful verification.

## Google Cloud setup
- Create a Google Cloud project and enable Cloud Storage.
- Create a private bucket; avoid public access.
- Create a server service account with only required bucket permissions (object create/list/delete as needed).
- Set `GCS_BUCKET` and provide credentials using your hosting provider's secret manager.
- Configure lifecycle deletion only as a fallback, with a suitably long age threshold. Lifecycle rules are not a replacement for the verified workflow.

Cloud Storage and cloud compute may incur charges. Free quotas/credits and regional availability can change. Set billing budgets/alerts before enabling automation.

## Important
This folder is a reference integration, not a complete hosted production service. The browser front end is a demo queue. Real YouTube OAuth, generation worker, database job queue, and confirmation callback must be connected on a deployed backend. Never put Google service-account JSON or OAuth client secrets in frontend JavaScript.
