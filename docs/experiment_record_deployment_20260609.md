# 实验记录：在线部署交付准备

## 时间

2026-06-09

## 目标

准备 RepoMentor 在线部署交付版本：前端可部署到 Vercel，后端可部署到 Render/Railway，同时保留 Docker 本地一键运行方案，并避免泄露 API Key。

## 改动

- 前端 API 地址统一改为 `VITE_API_BASE_URL`。
- Debug Console 显示当前后端 API 地址。
- 后端 CORS 改为通过 `BACKEND_CORS_ORIGINS` 配置。
- 后端新增 `MAX_REPO_FILES`、`MAX_FILE_SIZE_KB`、`ANALYZE_TIMEOUT_SECONDS`、`ENABLE_PUBLIC_DEMO_GUARD` 配置。
- Parser 跳过敏感文件名、大文件，并限制最多扫描文件数。
- `POST /api/repos/analyze` 增加超时错误。
- 新增 `render.yaml`、`backend/Dockerfile`、`backend/start.sh`、`frontend/vercel.json`、前后端 `.dockerignore`。
- 重写 `docker-compose.yml` 为本地一键运行方案。
- 新增 `scripts/check_deployment.py`、`docs/deployment_guide.md`、`docs/submission_urls.md`。

## 验证计划

- 前端构建：`node node_modules/vite/bin/vite.js build`。
- 后端测试：`python -m pytest backend/tests`。
- 部署后运行：`python scripts/check_deployment.py --frontend-url ... --backend-url ...`。
