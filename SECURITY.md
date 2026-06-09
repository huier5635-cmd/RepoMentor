# Security Policy

RepoMentor is designed for public repository learning demos. Please avoid submitting private repositories or secrets to public deployments.

## Secrets

- Never commit `.env`, `backend/.env`, `frontend/.env`, API keys, GitHub tokens, private keys, or screenshots that reveal credentials.
- DeepSeek/OpenAI keys should be configured only in local environment variables or private hosting platform settings.
- Public demo deployments should default to `LLM_PROVIDER=mock`.

## Public Demo Guardrails

The backend supports:

- `MAX_REPO_FILES`
- `MAX_FILE_SIZE_KB`
- `ANALYZE_TIMEOUT_SECONDS`
- `ENABLE_PUBLIC_DEMO_GUARD`

Use these limits for online demos to avoid unexpectedly large repository analysis.
