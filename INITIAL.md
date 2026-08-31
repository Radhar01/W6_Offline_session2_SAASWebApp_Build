# INITIAL.md - ClipCreator Product Definition

> Upload a long-duration or large video (via file upload or URL) and automatically convert it into meaningful, logically-segmented short clips/reels.

---

## PRODUCT

### Name
ClipCreator

### Description
ClipCreator takes long-form video — uploaded directly as a file or submitted via URL — and automatically converts it into short, shareable clips/reels by identifying logical, meaningful segments in the source video. It targets YouTube and social media content creators who need to repurpose long content into short-form clips quickly.

### Target User
YouTube and social media content creators repurposing long-form video into short-form clips/reels.

### Type
- [x] SaaS (Software as a Service)

---

## TECH STACK

### Backend
- [x] FastAPI + Python

### Frontend
- [x] React + Vite + TypeScript

### Database
- [x] PostgreSQL (recommended for all stacks)

### Authentication
- [x] None (no authentication for MVP — single-tenant / open access)

### UI Framework
- [x] Tailwind + shadcn/ui

### Payments
- [ ] None (no payments for MVP)

---

## MODULES

> No Authentication module for this MVP — the app is single-tenant / open access. Revisit auth if multi-user support is needed later.

### Module 1: Video Upload/Import

**Description:** Ingests long-duration or large source videos, either via direct file upload or by URL (e.g., YouTube or direct video link).

**Models:**
```
Video:
  - id
  - source_type: enum [upload, url]
  - original_filename: str | null
  - source_url: str | null
  - file_path: str
  - duration: float (seconds)
  - size_bytes: int
  - status: enum [pending, processing, completed, failed]
  - created_at, updated_at
```

**API Endpoints:**
```
POST   /api/v1/videos/upload      - Upload a video file
POST   /api/v1/videos/from-url    - Submit a video URL for ingestion
GET    /api/v1/videos             - List all videos
GET    /api/v1/videos/{id}        - Get video details/status
DELETE /api/v1/videos/{id}        - Delete video (and its source file + associated clips)
```

**Frontend Pages:**
- `/upload` - Upload form with file picker (drag-drop, chunked upload for large files) + URL input field, upload progress indicator

---

### Module 2: Clip Generation

**Description:** Automatically segments an ingested video into logical, meaningful short clips (AI-driven scene/topic detection), producing reel/short-ready output.

**Models:**
```
Clip:
  - id
  - video_id (FK -> Video)
  - start_time: float (seconds)
  - end_time: float (seconds)
  - title: str
  - thumbnail_url: str
  - file_path: str
  - aspect_ratio: enum [9:16, 1:1, 16:9]
  - status: enum [pending, processing, completed, failed]
  - created_at, updated_at
```

**API Endpoints:**
```
POST   /api/v1/videos/{id}/generate-clips  - Trigger AI segmentation job
GET    /api/v1/videos/{id}/clips           - List clips for a video (with job status)
POST   /api/v1/clips/{id}/regenerate       - Regenerate a specific clip
PUT    /api/v1/clips/{id}/boundaries       - Adjust clip start/end time
DELETE /api/v1/clips/{id}                  - Delete a specific clip
```

**Frontend Pages:**
- `/videos/{id}/processing` - Live status of the segmentation job (polling or websocket-driven progress)

---

### Module 3: Clip Library

**Description:** Browse, preview, edit metadata, download, and manage all generated clips across all source videos.

**Models:**
_(Reuses `Clip` from Module 2 — no additional models)_

**API Endpoints:**
```
GET    /api/v1/clips               - List all clips (filter/sort by video, date, status)
GET    /api/v1/clips/{id}          - Get clip detail (for preview)
PUT    /api/v1/clips/{id}          - Update clip title/thumbnail
GET    /api/v1/clips/{id}/download - Download the clip file
DELETE /api/v1/clips/{id}          - Delete clip
```

**Frontend Pages:**
- `/library` - Grid view of all clips with filter/sort controls, delete action
- `/library/{clip_id}` - Detail/preview page with inline title edit, thumbnail change, and download button

---

### Module 4: Dashboard

**Description:** Overview of processing history and usage statistics across videos and clips.

**Models:** none (aggregates `Video` and `Clip` data)

**API Endpoints:**
```
GET    /api/v1/dashboard/stats    - Aggregate stats: total videos, total clips generated, storage used
GET    /api/v1/dashboard/activity - Recent processing activity/history
```

**Frontend Pages:**
- `/dashboard` - Overview with recent activity feed and stats widgets (also serves as the Analytics Dashboard)

---

## MVP SCOPE

### Must Have (MVP)
- [x] Upload video via file
- [x] Submit video via URL
- [x] Auto-generate logical short clips from source video
- [x] View/preview generated clips in a library
- [x] Download clips
- [x] Update/change clip title and thumbnail
- [x] Delete source videos (and their clips)
- [x] Delete individual/unwanted clips
- [x] Large file upload support (chunked/resumable upload)

### Nice to Have (Post-MVP)
- [ ] Authentication / multi-user support
- [ ] Payments / subscription plans
- [ ] Admin panel
- [ ] Email notifications on job completion
- [ ] Manual clip boundary re-cutting UI (drag handles on a timeline)

---

## ACCEPTANCE CRITERIA

### Video Upload/Import
- [ ] User can upload a large video file via chunked/resumable upload without timing out
- [ ] User can submit a video URL and the system fetches/ingests it
- [ ] Upload progress is visible in real time
- [ ] Invalid URLs / unsupported file types are rejected with a clear error

### Clip Generation
- [ ] Submitting a video for clip generation produces one or more logically segmented clips
- [ ] Processing status is visible and updates without a full page reload
- [ ] Failed generation jobs surface a clear error and allow retry

### Clip Library
- [ ] User can view all generated clips in a grid with thumbnails
- [ ] User can preview a clip inline before downloading
- [ ] User can download a clip
- [ ] User can edit a clip's title and thumbnail
- [ ] User can delete a clip or a source video (cascade-deletes its clips)

### Dashboard
- [ ] Dashboard shows total videos, total clips, and storage used
- [ ] Dashboard shows recent processing activity

### Quality
- [ ] All API endpoints documented in OpenAPI
- [ ] Backend test coverage 80%+
- [ ] Frontend TypeScript strict mode passes
- [ ] Docker builds and runs successfully

---

## SPECIAL REQUIREMENTS

### Security
- [x] Input validation on all endpoints (file type/size limits, URL validation)
- [x] SQL injection prevention
- [x] XSS prevention
- [x] Rate limiting on upload/generation endpoints (to prevent abuse given compute-heavy processing)

> No auth/rate-limiting-per-user in MVP since there is no authentication layer.

### Integrations
- [x] Video processing pipeline (e.g., ffmpeg for transcoding/thumbnailing, AI model for scene/topic segmentation)
- [x] File storage for large video/clip assets (local disk or object storage, chunked upload support)
- [ ] Email service (not needed for MVP)
- [ ] Stripe/payments (not needed for MVP)

---

## AGENTS

> These agents will build your product in parallel:

| Agent | Role | Works On |
|-------|------|----------|
| DATABASE-AGENT | Creates all models and migrations | Video, Clip models |
| BACKEND-AGENT | Builds API endpoints and services | Upload, URL ingestion, clip generation, library, dashboard |
| FRONTEND-AGENT | Creates UI pages and components | Upload, processing status, library, dashboard pages |
| DEVOPS-AGENT | Sets up Docker, CI/CD, environments | Infrastructure, video processing worker setup |
| TEST-AGENT | Writes unit and integration tests | All code |
| REVIEW-AGENT | Security and code quality audit | All code |

---

# READY?

```bash
/generate-prp INITIAL.md
```

Then:

```bash
/execute-prp PRPs/clipcreator-prp.md
```
