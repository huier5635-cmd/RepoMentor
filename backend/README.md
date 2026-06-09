# RepoMentor Backend

FastAPI backend for the RepoMentor MVP.

## Run

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Endpoints

- `POST /api/repos/analyze`
- `GET /api/repos/{repo_id}/graph`
- `POST /api/repos/{repo_id}/qa`
- `GET /api/repos/{repo_id}/learning-path`
- `GET /api/repos/{repo_id}/issues/recommend`
- `GET /api/memory/{session_id}`
