# RepoMentor 后端

RepoMentor 后端使用 FastAPI 构建，负责仓库解析、Worker 编排、Repository Intelligence Graph、证据检索、问答生成和调试 API。

## 本地启动

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

## 主要接口

- `POST /api/repos/analyze`：分析公开 GitHub 仓库。
- `GET /api/repos/{repo_id}/graph`：读取仓库图谱。
- `GET /api/repos/{repo_id}/learning-path`：读取学习路径。
- `GET /api/repos/{repo_id}/development-workflow`：读取开发流程。
- `GET /api/repos/{repo_id}/issues/recommend`：读取推荐任务。
- `POST /api/repos/{repo_id}/qa`：进行证据约束问答。
- `GET /api/model/status`：读取模型状态。
- `POST /api/model/test`：测试模型连接。
- `GET /api/memory/{session_id}`：读取共享工作记忆。

## 模型配置

默认可以请求 DeepSeek：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=
```

如果没有配置 API Key，后端会回退到 Mock Provider，确定性仓库解析仍可运行。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

当前仓库暂不包含公网发布配置，公开提交中只保留本地开发运行说明。
