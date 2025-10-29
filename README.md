**DBackup Server**
- Purpose: FastAPI service to collect and download users' Google Takeout folders for authenticated users, plus a scheduler to process queued requests and basic uploads (ChatGPT exports, audio).

**Architecture**
- **API**: `main.py` exposes auth, folder management, download, and utility endpoints.
- **Core**: `x.py` handles Google OAuth/Drive, SQLite persistence, and CSV exports.
- **Scheduler**: `schedular.py` polls queued requests, downloads folders, unzips, refreshes history counts, and logs runs.
- **Utilities**: `convert_zip.py`, `unzip_takeout.py`, `count_db.py`, `bot.py` (Telegram notifications).

**Quick Start (Docker Compose)**
- Build and start:
  - `docker-compose up -d`
- Update/redeploy (repo has `start.sh`):
  - `./start.sh`
- Services:
  - `fastapi-server` at port `8040` (mapped to container `80`).
  - `scheduler` runs `schedular.py` in a separate container.

**Volumes (host → container)**
- `credentials.db` → `/dbackup-server/credentials.db` (SQLite DB)
- `saved_data` → `/dbackup-server/saved_data` (downloaded content + zips)
- `formResponse` → `/dbackup-server/formResponse` (survey JSON files)
- `chatgpt_uploads` → `/dbackup-server/chatgpt_uploads` (ChatGPT uploads)
- `logs` → `/dbackup-server/logs` (scheduler log file)

**Environment Variables**
- `CLIENT_ORIGIN`: Client app origin (used for redirects and cookies).
- `PROXY_SERVER`: Public base URL for this API (used as OAuth redirect base).
- `INTERVAL_TIME` (scheduler): Polling interval in seconds. Default `600`. Example `1200`.
- `REGISTRATION_CUTOFF_DATE` (scheduler): Optional ISO-8601 date/time; only users registered at/after this will be processed. Examples:
  - `2024-07-01`
  - `2024-07-01T00:00:00Z`
  - `2024-07-01T00:00:00+00:00`

Notes:
- OAuth client secrets file must exist at `credentials.json` in the working directory.
- `OAUTHLIB_INSECURE_TRANSPORT=1` is set in code to allow non-HTTPS during development; ensure HTTPS in production.
- Telegram bot token is currently hardcoded in `bot.py`. Change it before deploying publicly.

**Local Run (without Docker)**
- Install Python 3.11 and dependencies: `pip install -r requirements.txt`.
- Run API: `uvicorn main:app --host 0.0.0.0 --port 8040`.
- Run scheduler: `python3 -u schedular.py`.

**Auth & Data Flow**
- Connect (signup):
  - `GET /connect?auth-request=datareq` → Google OAuth consent → `/oauth2_connect_callback`
  - On success, user credentials are saved; a `registered_at` timestamp is stored.
- Login (existing users):
  - `GET /login` → Google OAuth → `/oauth2_login_callback` → redirects to client with `token` (access token).

**Core Endpoints**
- `POST /addfolder` (body: `access_token`, `folder_name`, `scheduling_type`):
  - If folder exists: download immediately; else if `scheduling_type != "0"`, queue a request.
- `POST /getfolderlist` (body: `access_token`): returns saved and requested folders for the user.
- `POST /deletefolder` (body: `access_token`, `folder_name`): remove saved folder record.
- `POST /deleterequest` (body: `access_token`, `folder_name`): remove queued request.
- `POST /downloadfolder` (body: `access_token`, `folder_name`): returns the ZIP file response for the folder.
- CSV/exports:
  - `GET /vdata` → CSV of folders table.
  - `GET /get_drive_access_info` → CSV of Drive access per user.
  - `GET /hcdata` → CSV of combined history counts + last backup.
  - `GET /requests_csv/` → CSV of `requests` table.
- Survey and uploads:
  - `POST /survey` (JSON with `cid`, `email`) → stores under `formResponse/{cid}.json`.
  - `POST /upload-chatgpt-data/` (multipart form: `email`, file `.html`/`.json`) → saves under `chatgpt_uploads/<email>/`.
  - `POST /upload-audio/` (file `.mp3`/`.wav`) → saves under `audio/`.
  - `GET /list-audio/` → lists audio files.

**Scheduler Behavior**
- Cycle: read all `requests` → for each request with available folder and valid creds, download → unzip Takeout zips → refresh history counts → log results.
- Cutoff filter: if `REGISTRATION_CUTOFF_DATE` is set, only process users with `registered_at >= cutoff`. Users missing `registered_at` are skipped.
- Logging: appends a line to `/dbackup-server/logs/scheduler_log.txt` each cycle.

**Database Notes (SQLite)**
- Main DB: `credentials.db` with tables:
  - `access_credentials` (stores Google OAuth tokens; auto-migrated to include `registered_at`).
  - `folders` (user_id, folder_name, last_backup).
  - `requests` (queue of pending downloads).
  - `history_counts` (YouTube watched count, browser history count per user).
- Migrations: `x.py` auto-creates/migrates required columns at runtime; no separate migration tool.

**Operational Tips**
- Ensure the mounted volumes/directories exist and are writable on the host.
- Drive API quotas: downloads are serial per scheduler cycle to reduce pressure.
- If many requests accumulate, consider increasing `INTERVAL_TIME` or splitting workloads.

**License / Security**
- This repository contains credentials and tokens handling logic. Keep `credentials.json`, database files, and any tokens out of public repos.
