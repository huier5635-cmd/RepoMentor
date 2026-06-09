# RepoMentor Frontend

React + Vite workspace UI for the RepoMentor MVP.

## Run

```bash
cd frontend
npm install
npm run dev
```

The frontend reads the backend origin from `VITE_API_BASE_URL`.

```bash
cp .env.example .env
```

Local default:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

On Vercel, set `VITE_API_BASE_URL` to the deployed backend origin, for example `https://your-backend-domain.onrender.com`.
