# 2026-06-09 学习 Agent 继续补强实验记录

## 实验目标

在不接真实 LLM 决策仓库事实、不大改架构的前提下，继续补齐学习 Agent 产品化链路：

- 修复 `/api/repos/{repo_id}/graph` 在 HTTP 响应阶段的 JSON 序列化错误。
- 将前端默认 API 改为同源 `/api`，由 Vite 代理到本地后端 `http://127.0.0.1:8000`。
- 补齐双语导读的 TranslationMemory 元数据。
- 在调试页增加学习 Agent 调试摘要，并保留原始 JSON 导出。
- 验证用户页与调试页继续分离，且调试页模型控制和智能体流程调试不重叠。

## 修改内容

- `backend/app/api/repos.py`
  - 对 `/api/repos/{repo_id}/graph` 使用 `jsonable_encoder` 和 `JSONResponse` 显式序列化。
  - 保持 RepositoryIntelligenceGraph 内部结构不变，只在 API 边界处理 JSON 输出。
- `frontend/src/api/client.js`
  - 默认 `API_BASE` 改为 `/api`。
- `frontend/vite.config.js`
  - 新增 `/api` 代理到 `http://127.0.0.1:8000`。
- `backend/app/core/schemas.py`
  - `TranslationChunkRecord` 增加 `source_file`、`source_chunk_hash`、`source_commit_hash`、`target_lang`、`translated_text`、`glossary_terms`、`stale_status`。
- `backend/app/services/learning_agent_service.py`
  - 双语导读生成 chunk hash、commit hash、目标语言、保留 token 和术语匹配。
  - 术语表补充符号术语与文档标题推导出的领域概念。
  - 架构导览和模块卡补充不同角色视角的学习提示。
- `frontend/src/components/user/BilingualGlossaryPanel.jsx`
  - 改为“原文 / 中文导读”左右对照。
  - 展示 chunk hash、commit、目标语言、术语和保留 token。
- `frontend/src/components/debug/LearningAgentDebugSummaryPanel.jsx`
  - 新增学习 Agent 调试摘要。
  - 展示 translation fidelity、internal first tasks trace、onboarding debt JSON 摘要和 hallucination guardrails。
- `frontend/src/components/debug/LearningAgentRawPanel.jsx`
  - 保留学习 Agent 原始 JSON 和导出按钮。

## 验证环境

- 后端：`http://127.0.0.1:8000`
- 前端：`http://127.0.0.1:5173`
- LangGraph 环境变量：
  - `LANGGRAPH_ENABLED=true`
  - `LANGGRAPH_CHECKPOINT_BACKEND=sqlite`
- 验证仓库：`repo_id=be338353cf5a`

## 自动化验证

```powershell
python -m pytest backend\tests -q
```

结果：`47 passed`

```powershell
& "C:\Users\Liaoke\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" node_modules/vite/bin/vite.js build
```

结果：Vite 构建通过，`1617 modules transformed`

```powershell
python scripts\run_learning_eval.py --repo-id be338353cf5a --output reports\learning_agent_eval_report.md
```

结果：已生成 `reports/learning_agent_eval_report.md`

## API 验证

- `http://127.0.0.1:8000/api/repos/be338353cf5a/graph`
  - 状态：`200`
  - 响应大小：`26455` bytes
- `http://127.0.0.1:5173/api/repos/be338353cf5a/graph`
  - 状态：`200`
  - 响应大小：`26455` bytes
- 学习 Agent debug bundle：
  - learning_path_v2 steps：`8`
  - module_study_cards：`2`
  - glossary terms：`11`
  - bilingual chunks：`1`
  - onboarding risks：`6`
  - internal first tasks：`5`

## 浏览器验证

用户页：`http://127.0.0.1:5173/repos/be338353cf5a?proxycheck=1`

- 显示 `学习路径 V2`。
- 显示 `双语术语`。
- 不显示 `Agent Flow`、`Worker Outputs`、`Data Layer`、`SelfCheck`、`原始 JSON`。
- 未发现错误条。
- 未发现乱码。

双语面板：

- 显示 `原文`。
- 显示 `中文导读`。
- 显示 `chunk hash`。
- 显示 `目标语言`。
- 显示保留 token。
- 不暴露 `learning_path_v2` 等调试 JSON。

调试页：`http://127.0.0.1:5173/debug/be338353cf5a?tab=model&verify=learning-agent`

- 显示 `模型控制`。
- 显示 `智能体流程调试`。
- 显示 `学习 Agent 调试摘要`。
- 显示 `translation fidelity`。
- 显示 `internal first tasks trace`。
- 显示 `学习 Agent 原始 JSON`。
- 原始 JSON 包含 `learning_path_v2`。
- 模型控制面板与智能体流程调试面板重叠面积：`0`。
- 学习 Agent 调试摘要与原始 JSON 面板重叠面积：`0`。
- 未发现错误条。
- 未发现乱码。

## 结论

本次继续补强后，RepoMentor 的学习 Agent 用户视图、调试视图、同源 API 代理、双语导读元数据和调试摘要均已跑通。仓库事实仍由确定性图谱和 GitHub/API 数据提供，LLM 后续只应作为解释、翻译润色和学习反馈层，不应决定文件、命令、测试、文档、Issue 或 CI 事实。
