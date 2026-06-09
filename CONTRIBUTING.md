# Contributing to RepoMentor

Thanks for checking out RepoMentor. This project is an educational multi-agent repository learning assistant, so contributions that improve evidence coverage, onboarding quality, deployment docs, and UI clarity are especially welcome.

## Good First Contribution Areas

- Improve EvidenceBuilder coverage for QA answers.
- Add repository fixtures and regression tests.
- Improve Docker/Vercel/Render deployment docs.
- Add more frontend empty/error states.
- Improve bilingual terminology and design-basis copy.

## Local Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

## Checks

```bash
cd backend
python -m pytest
```

```bash
cd frontend
npm run build
```

## Safety

Do not commit `.env`, API keys, tokens, cache folders, or generated package zips. Online demos should default to Mock mode unless a private model key is configured in the hosting platform.
