# LangGraph 渐进迁移说明

## 目标

RepoMentor 当前保留 `LegacyOrchestrator` 作为默认稳定链路，并新增 LangGraph 薄包装层，用于逐步验证长任务编排、checkpoint、节点级 trace 和调试恢复能力。

本阶段不改后端业务 API，不删除已有 Worker，不改变用户页展示。LangGraph 信息只进入 Debug Console。

## 开关

默认关闭：

```env
LANGGRAPH_ENABLED=false
LANGGRAPH_CHECKPOINT_BACKEND=memory
LANGGRAPH_SQLITE_PATH=.repomentor_cache/langgraph_checkpoints.sqlite
LANGGRAPH_TRACE_ENABLED=true
LANGGRAPH_MAX_RETRIES=2
```

开启 LangGraph 需要重启后端：

```powershell
$env:LANGGRAPH_ENABLED="true"
uvicorn app.main:app --reload --port 8000
```

## 新增模块

- `backend/app/graphs/state.py`：定义 `RepoMentorState`。
- `backend/app/graphs/node_base.py`：统一节点执行、错误捕获和 trace。
- `backend/app/graphs/checkpoint.py`：memory/sqlite checkpoint。
- `backend/app/graphs/repo_analysis_graph.py`：仓库分析图，复用现有 Worker。
- `backend/app/graphs/qa_graph.py`：QA 图，复用现有检索、候选答案、SelfCheck 和 Optimizer。
- `backend/app/graphs/graph_orchestrator.py`：LangGraph/Legacy 切换与失败回退。
- `backend/app/graphs/graph_trace.py`：节点事件存储。
- `backend/app/graphs/graph_utils.py`：thread id 和状态摘要工具。

## Debug API

- `GET /api/graph/status`
- `GET /api/debug/graph/{thread_id}/state`
- `GET /api/debug/graph/{thread_id}/trace`
- `POST /api/debug/graph/{thread_id}/resume`

Thread ID 约定：

- 仓库分析：`analyze:{repo_id}`
- QA：`qa:{repo_id}:{session_id}`

## 前端

Debug Console 新增 `LangGraphDebugPanel`，展示：

- 是否启用 LangGraph
- 当前 active orchestrator
- checkpoint backend
- thread_id
- graph name
- current node
- 节点状态
- decision/retry/fallback 事件
- checkpoint 恢复按钮
- 原始 State/Trace JSON

用户页不展示 LangGraph、Agent Flow、Worker Outputs、Shared Memory、Trace 或 Final JSON。

## 回退策略

当 `LANGGRAPH_ENABLED=true` 且图执行失败时，`GraphOrchestrator` 会：

1. 写入 fallback trace event。
2. 回退到 `LegacyOrchestrator`。
3. 保持 `/api/repos/analyze` 与 `/api/repos/{repo_id}/qa` 返回结构不变。

## 压力测试

压力脚本支持记录请求的 orchestrator：

```powershell
python scripts\stress_test_repomentor.py --orchestrator legacy --provider mock --skip-large
python scripts\stress_test_repomentor.py --orchestrator langgraph --provider mock --skip-large
```

脚本会读取 `/api/graph/status` 并输出：

- `reports/stress_report.json`
- `reports/stress_report.md`
- `reports/stress_summary.md`
- `reports/evidence_coverage_breakdown.md`
- `reports/langgraph_comparison_report.md`

注意：脚本不会自动重启后端，也不会替你修改运行中的环境变量。切换 legacy/langgraph 需要重启后端。
