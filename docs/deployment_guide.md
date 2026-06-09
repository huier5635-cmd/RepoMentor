# RepoMentor 部署指南

## 1. 为什么 127.0.0.1 不能作为在线地址

`127.0.0.1` 和 `localhost` 只指向访问者自己的电脑。你在本机打开 `http://127.0.0.1:5173` 能看到 Demo，是因为前端服务正在你的电脑上运行；评审在自己的电脑打开同一个地址，只会访问他们自己的电脑，不能访问你的项目。

在线提交需要填写公网可访问地址，例如：

- 前端：`https://your-frontend-domain.vercel.app`
- 后端健康检查：`https://your-backend-domain.onrender.com/api/health`

## 2. Vercel 前端部署步骤

1. 在 Vercel 新建项目，选择本仓库。
2. Root Directory 选择 `frontend`。
3. Framework 选择 Vite。
4. Build Command 使用 `npm run build`。
5. Output Directory 使用 `dist`。
6. 在 Environment Variables 中配置：

```env
VITE_API_BASE_URL=https://your-backend-domain.onrender.com
```

前端本地默认使用 `frontend/.env.example`：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

生产环境不要把 `VITE_API_BASE_URL` 配成 localhost 或 127.0.0.1。

## 3. Render 后端部署步骤

仓库根目录已提供 `render.yaml`。推荐流程：

1. 在 Render 创建 Blueprint 或 Web Service。
2. Root Directory 使用 `backend`。
3. Build Command：`pip install -r requirements.txt`。
4. Start Command：`uvicorn app.main:app --host 0.0.0.0 --port $PORT`。
5. 配置环境变量：

```env
LLM_PROVIDER=mock
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
BACKEND_CORS_ORIGINS=https://your-frontend-domain.vercel.app
MAX_REPO_FILES=1000
MAX_FILE_SIZE_KB=512
ANALYZE_TIMEOUT_SECONDS=120
ENABLE_PUBLIC_DEMO_GUARD=true
```

可选私密变量：

```env
GITHUB_TOKEN=your_read_only_token
DEEPSEEK_API_KEY=your_private_key
```

不要把 `GITHUB_TOKEN` 或 `DEEPSEEK_API_KEY` 写入代码、README、截图或提交材料。

## 4. Railway 后端 Docker 部署步骤

后端提供 `backend/Dockerfile`，可用于 Railway Dockerfile 部署：

```bash
cd backend
docker build -t repomentor-backend .
docker run -p 8000:8000 --env LLM_PROVIDER=mock repomentor-backend
```

Railway 会注入 `PORT` 环境变量，Dockerfile 使用：

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

## 5. CORS 配置

本地开发可使用：

```env
BACKEND_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

线上部署应使用真实前端域名：

```env
BACKEND_CORS_ORIGINS=https://your-frontend-domain.vercel.app
```

不要长期使用 `allow_origins=["*"]`。如果为了临时 Demo 开放所有来源，必须在 README 中说明风险，并在正式提交前改回明确域名。

## 6. DeepSeek API Key 安全

- 在线 Demo 默认 `LLM_PROVIDER=mock`，避免评审访问时产生模型费用。
- DeepSeek Key 只放在 Render/Railway 后台环境变量或本机 `backend/.env`。
- 不要把 Key 放入前端环境变量。
- 不要提交 `.env`。
- 如果截图中出现 Key，立即撤销旧 Key 并新建。

## 7. Docker 本地一键运行

```bash
docker compose up --build
```

启动后访问：

```text
http://127.0.0.1:5173
```

注意：这个地址只能在运行 Docker 的电脑上访问，不能作为在线 Demo 地址提交。

## 8. 部署检查脚本

```bash
python scripts/check_deployment.py \
  --frontend-url https://your-frontend-domain.vercel.app \
  --backend-url https://your-backend-domain.onrender.com
```

脚本会检查：

1. 后端 `/api/health`。
2. 后端 `/api/model/status` 是否可访问且不泄露 API Key。
3. 前端页面是否可访问。
4. CORS 是否允许前端访问后端。
5. 小仓库 `POST /api/repos/analyze` 是否返回结果。
6. 前端 bundle 是否仍写死 localhost 后端。
7. 是否处于 mock demo mode。

检查报告输出到：

```text
reports/deployment_check.md
```

## 9. 常见问题

| 问题 | 处理方式 |
| --- | --- |
| Vercel 页面能打开但分析失败 | 检查 `VITE_API_BASE_URL` 是否配置为公网后端域名。 |
| 浏览器报 CORS 错误 | 检查后端 `BACKEND_CORS_ORIGINS` 是否包含 Vercel 前端域名。 |
| Render 启动失败 | 确认 Start Command 使用 `$PORT`，不要写死 8000。 |
| DeepSeek 测试失败 | 确认平台环境变量里有 `DEEPSEEK_API_KEY`，且后端已安装 `openai`。 |
| analyze 超时 | 换小仓库，或调高 `ANALYZE_TIMEOUT_SECONDS`，并保持 `MAX_REPO_FILES` 限制。 |
