# CLAUDE.md - ClipCreator Project Rules

> Project-specific rules for Claude Code. This file is read automatically.

---

## Project Overview

**Project Name:** ClipCreator
**Description:** Upload a long-duration or large video (via file upload or URL) and automatically convert it into meaningful, logically-segmented short clips/reels. Target users: YouTube and social media content creators.

**Tech Stack:**
- Backend: FastAPI + Python 3.11+
- Frontend: React + Vite + TypeScript
- Database: PostgreSQL + SQLAlchemy
- Auth: None (no authentication in MVP — single-tenant/open access)
- UI: Tailwind + shadcn/ui
- Payments: None

---

## Project Structure

```
clipcreator/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── video.py
│   │   │   └── clip.py
│   │   ├── schemas/
│   │   │   ├── video.py
│   │   │   └── clip.py
│   │   ├── routers/
│   │   │   ├── videos.py
│   │   │   ├── clips.py
│   │   │   └── dashboard.py
│   │   ├── services/
│   │   │   ├── upload_service.py      # chunked/resumable file upload
│   │   │   ├── url_ingest_service.py  # video-from-URL fetching
│   │   │   ├── segmentation_service.py # AI clip generation
│   │   │   └── storage_service.py     # video/clip file storage
│   │   └── workers/
│   │       └── clip_generation_worker.py  # background/async processing job
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   │   ├── Upload.tsx
│   │   │   ├── Processing.tsx
│   │   │   ├── Library.tsx
│   │   │   ├── ClipDetail.tsx
│   │   │   └── Dashboard.tsx
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── context/
│   │   └── types/
│   └── package.json
├── .claude/
│   └── commands/
├── skills/
├── agents/
└── PRPs/
```

---

## Code Standards

### Python (Backend)
```python
# ALWAYS use type hints
def get_video(db: Session, video_id: int) -> Video:
    pass

# ALWAYS add docstrings for public functions
def create_clip(db: Session, data: ClipCreate) -> Clip:
    """
    Create a new clip.

    Args:
        db: Database session
        data: Clip creation data

    Returns:
        Created Clip object
    """
    pass
```

### TypeScript (Frontend)
```typescript
// ALWAYS define interfaces for props and data
interface ClipProps {
  id: number;
  videoId: number;
  title: string;
  thumbnailUrl: string;
  startTime: number;
  endTime: number;
  status: "pending" | "processing" | "completed" | "failed";
}

// NO any types allowed
const fetchClip = async (id: number): Promise<ClipProps> => {
  // ...
};
```

---

## Forbidden Patterns

### Backend
- Never use `print()` - use `logging` module
- Never hardcode secrets - use environment variables
- Never use `SELECT *` - specify columns
- Never skip input validation (especially file type/size and URL validation on upload endpoints)
- Never load an entire large video file into memory - stream/chunk file I/O

### Frontend
- Never use `any` type
- Never leave console.log in production
- Never skip error handling in async operations (uploads and clip generation are long-running and failure-prone)
- Never use inline styles - use Tailwind/shadcn

---

## Module-Specific Rules

### Video Upload/Import Module
- All uploads must be validated for file type (video formats only) and size limit before processing starts
- Large file uploads must use chunked/resumable upload — do not require the full file in a single request
- URL ingestion must validate the URL scheme/host before fetching
- `Video.status` must be one of: `pending`, `processing`, `completed`, `failed`

### Clip Generation Module
- Clip generation must run as a background job (not blocking the request/response cycle)
- `Clip.status` must be one of: `pending`, `processing`, `completed`, `failed`
- Deleting a `Video` must cascade-delete its associated `Clip` records and files

### Clip Library Module
- Clip title/thumbnail updates must not alter the underlying clip video file
- Clip download endpoint must stream the file, not load it fully into memory

### Dashboard Module
- Stats must be computed from `Video`/`Clip` tables directly — do not introduce a separate stats/cache model for MVP

---

## API Conventions

- All endpoints prefixed with `/api/v1/`
- Use plural nouns for resources: `/videos`, `/clips`
- Return appropriate HTTP status codes:
  - 200: Success
  - 201: Created
  - 400: Bad Request
  - 404: Not Found
  - 409: Conflict
  - 422: Unprocessable Entity (validation errors)

---

## Authentication

No authentication in this MVP — the app is single-tenant/open access. Do not add login/register flows, JWT handling, or protected routes unless the scope changes. If auth is added later, revisit `INITIAL.md` first.

---

## Environment Variables

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

## Development Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Docker
docker-compose up -d

# Tests
pytest backend/tests -v
cd frontend && npm test

# Linting
ruff check backend/
cd frontend && npm run lint
```

---

## Commit Message Format

```
feat([module]): add [feature]
fix([module]): fix [bug]
refactor([module]): refactor [component]
test([module]): add tests for [feature]
docs: update [documentation]
```

---

## Skills Reference

| Task | Skill to Read |
|------|---------------|
| Database models | skills/DATABASE.md |
| API + Auth | skills/BACKEND.md |
| React + UI | skills/FRONTEND.md |
| Testing | skills/TESTING.md |
| Deployment | skills/DEPLOYMENT.md |

---

## Agent Coordination

For complex tasks, the ORCHESTRATOR coordinates:
- DATABASE-AGENT → Backend models (Video, Clip)
- BACKEND-AGENT → API development (upload, URL ingestion, clip generation, library, dashboard)
- FRONTEND-AGENT → UI components (upload, processing status, library, dashboard pages)
- TEST-AGENT → Testing
- REVIEW-AGENT → Code review
- DEVOPS-AGENT → Deployment (incl. video processing worker/container)

Read agent definitions in `/agents/` folder.
