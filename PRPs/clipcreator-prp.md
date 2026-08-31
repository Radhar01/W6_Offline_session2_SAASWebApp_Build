# PRP: ClipCreator

> Implementation blueprint for parallel agent execution

---

## METADATA

| Field | Value |
|-------|-------|
| **Product** | ClipCreator |
| **Type** | SaaS |
| **Version** | 1.0 |
| **Created** | 2026-08-30 |
| **Complexity** | Medium-High (video processing pipeline, background jobs, large file handling) |

---

## PRODUCT OVERVIEW

**Description:** ClipCreator takes long-form video — uploaded directly as a file or submitted via URL — and automatically converts it into short, shareable clips/reels by identifying logical, meaningful segments in the source video.

**Value Proposition:** YouTube and social media content creators save hours of manual editing by letting ClipCreator auto-generate short-form clips from long-form footage, ready to preview, retitle, and download.

**MVP Scope:**
- [ ] Upload video via file (chunked/resumable, large-file support)
- [ ] Submit video via URL
- [ ] Auto-generate logical short clips from source video (background job)
- [ ] View/preview generated clips in a library
- [ ] Download clips
- [ ] Update/change clip title and thumbnail
- [ ] Delete source videos (cascade-deletes their clips)
- [ ] Delete individual/unwanted clips
- [ ] Dashboard with processing history + stats (Analytics)

**Explicitly out of scope for MVP:** Authentication (open access / single-tenant), Payments, Admin Panel, Email notifications.

---

## TECH STACK

| Layer | Technology | Skill Reference |
|-------|------------|-----------------|
| Backend | FastAPI + Python 3.11+ | skills/BACKEND.md |
| Frontend | React + TypeScript + Vite | skills/FRONTEND.md |
| Database | PostgreSQL + SQLAlchemy | skills/DATABASE.md |
| Auth | None (MVP is open access — skip skills/BACKEND.md auth sections) | n/a |
| UI | Tailwind + shadcn/ui | skills/FRONTEND.md |
| Video Processing | ffmpeg (transcode/thumbnail) + segmentation service | skills/BACKEND.md |
| Testing | pytest + RTL | skills/TESTING.md |
| Deployment | Docker + GitHub Actions | skills/DEPLOYMENT.md |

---

## DATABASE MODELS

### Video Model
- id (PK)
- source_type: enum [upload, url]
- original_filename: str | null
- source_url: str | null
- file_path: str
- duration: float (seconds)
- size_bytes: int
- status: enum [pending, processing, completed, failed]
- created_at, updated_at

### Clip Model
- id (PK)
- video_id: FK -> Video (cascade delete)
- start_time: float (seconds)
- end_time: float (seconds)
- title: str
- thumbnail_url: str
- file_path: str
- aspect_ratio: enum [9:16, 1:1, 16:9]
- status: enum [pending, processing, completed, failed]
- created_at, updated_at

> No User model in MVP — no authentication layer.

---

## MODULES

### Module 1: Video Upload/Import
**Agents:** DATABASE-AGENT + BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/videos/upload | Upload a video file (chunked/resumable) |
| POST | /api/v1/videos/from-url | Submit a video URL for ingestion |
| GET | /api/v1/videos | List all videos |
| GET | /api/v1/videos/{id} | Get video details/status |
| DELETE | /api/v1/videos/{id} | Delete video (cascade-deletes clips + files) |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /upload | UploadPage | FileDropzone, ChunkedUploader, UrlInputForm, UploadProgressBar |

---

### Module 2: Clip Generation
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/videos/{id}/generate-clips | Trigger AI segmentation background job |
| GET | /api/v1/videos/{id}/clips | List clips for a video (with job status) |
| POST | /api/v1/clips/{id}/regenerate | Regenerate a specific clip |
| PUT | /api/v1/clips/{id}/boundaries | Adjust clip start/end time |
| DELETE | /api/v1/clips/{id} | Delete a specific clip |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /videos/:id/processing | ProcessingPage | JobStatusPoller, ProgressIndicator |

---

### Module 3: Clip Library
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/clips | List all clips (filter/sort by video, date, status) |
| GET | /api/v1/clips/{id} | Get clip detail (for preview) |
| PUT | /api/v1/clips/{id} | Update clip title/thumbnail |
| GET | /api/v1/clips/{id}/download | Download the clip file (streamed) |
| DELETE | /api/v1/clips/{id} | Delete clip |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /library | LibraryPage | ClipGrid, ClipCard, FilterSortBar, DeleteConfirm |
| /library/:clipId | ClipDetailPage | ClipPlayer, TitleEditForm, ThumbnailPicker, DownloadButton |

---

### Module 4: Dashboard
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/dashboard/stats | Aggregate stats: total videos, total clips, storage used |
| GET | /api/v1/dashboard/activity | Recent processing activity/history |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /dashboard | DashboardPage | StatsWidgetRow, ActivityFeed |

---

## PHASE EXECUTION PLAN

**Phase 1: Foundation (4 agents in parallel)**
- DATABASE-AGENT: `Video` and `Clip` models, Alembic migration, `database.py`
- BACKEND-AGENT: `main.py`, `config.py`, project structure, storage/ffmpeg config
- FRONTEND-AGENT: Vite setup, folder structure, Tailwind/shadcn base components, routing shell
- DEVOPS-AGENT: Docker (incl. ffmpeg in image), docker-compose, CI/CD, env files

**Validation Gate 1:** `pip install`, `alembic upgrade head`, `npm install`, `docker-compose config`

**Phase 2: Modules (backend + frontend parallel per module)**
- Video Upload/Import: chunked upload + URL ingestion endpoints + Upload page
- Clip Generation: background segmentation job + status endpoints + Processing page
- Clip Library: CRUD/download endpoints + Library/ClipDetail pages
- Dashboard: stats/activity endpoints + Dashboard page

**Validation Gate 2:** `ruff check backend/`, `npm run lint`, `npm run type-check`

**Phase 3: Quality (3 agents in parallel)**
- TEST-AGENT: pytest (upload validation, cascade delete, job status transitions) + RTL tests, 80%+ coverage
- REVIEW-AGENT: Security audit (file/URL validation, streaming downloads, no auth = no PII stored), performance review of video pipeline
- RESEARCH-AGENT: Validate ffmpeg segmentation approach and chunked upload best practices

**Final Validation:** Full test suite, `docker-compose up -d`, health check, manual upload → generate → download smoke test

---

## VALIDATION GATES

| Gate | Commands |
|------|----------|
| 1 | `alembic upgrade head`, `npm install`, `docker-compose config` |
| 2 | `ruff check backend/`, `npm run type-check` |
| 3 | `pytest --cov --cov-fail-under=80`, `npm test` |
| Final | `docker-compose up -d`, `curl localhost:8000/health` |

---

## ENVIRONMENT VARIABLES

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/clipcreator

# Storage
MEDIA_STORAGE_PATH=./storage
MAX_UPLOAD_SIZE_MB=2048

# Video processing
FFMPEG_PATH=/usr/bin/ffmpeg

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## NEXT STEP

Execute with parallel agents:
```bash
/execute-prp PRPs/clipcreator-prp.md
```
