# RepoMentor 实验记录

## 2026-06-08 前端信息架构拆分：UserDashboard / DebugConsole

### 目标

将 RepoMentor 前端拆成两套界面：

- 用户界面：面向新贡献者，聚焦仓库概览、代码地图、学习路径、开发流程、推荐议题、问答和简化证据。
- 调试控制台：面向开发和演示，集中展示 Agent 编排、Worker 输出、Data Layer、Shared Memory、Retrieval Trace、Evaluator / Optimizer 和导出工具。

### 改动

- 新增路由级页面：
  - `/` 和 `/repos/:repoId` 渲染 `frontend/src/pages/UserDashboard.jsx`
  - `/debug/:repoId` 和 `/debug/session/:sessionId` 渲染 `frontend/src/pages/DebugConsole.jsx`
- 拆分组件目录：
  - `frontend/src/components/user/`
  - `frontend/src/components/debug/`
- 新增用户侧组件：
  - `RepoInput`
  - `RepoOverviewPanel`
  - `CodeMapPanel`
  - `LearningPathPanel`
  - `DevelopmentWorkflowPanel`
  - `IssueRecommendationPanel`
  - `QAPanel`
  - `UserEvidencePanel`
- 新增调试侧组件：
  - `DebugHeader`
  - `AgentFlowDebugPanel`
  - `WorkerOutputsDebugPanel`
  - `DataLayerDebugPanel`
  - `RepositoryGraphDebugPanel`
  - `RetrievalTracePanel`
  - `SharedMemoryPanel`
  - `EvaluatorOptimizerPanel`
  - `FinalAnswerJsonPanel`
  - `TraceExportPanel`
- 移除了旧的混合式 dashboard 组件文件。
- `frontend/src/api/client.js` 增加调试接口适配；未来调试接口暂缺时返回空状态，不让页面崩溃。
- 增加 `sessionStorage` 缓存，避免前端导航或刷新后 `/debug/:repoId` 丢失最近一次分析得到的 Worker 输出。
- 更新 `README.md`，补充用户页和调试控制台使用说明。

### 验证

前端构建命令：

```powershell
$nodeDir = 'C:\Users\Liaoke\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin'
$node = Join-Path $nodeDir 'node.exe'
$env:PATH = "$nodeDir;$env:PATH"
& $node node_modules\vite\bin\vite.js build
```

结果：

- Vite build 通过。
- 转换 1602 个模块。
- 产物生成在 `frontend/dist/`。

浏览器验证：

- 打开 `http://127.0.0.1:5173/`。
- 首页显示 `RepoInput`、分析状态、仓库概览、代码地图和用户主功能 tab。
- 首页不显示 `AgentFlowDebugPanel`、`WorkerOutputsDebugPanel`、`SharedMemoryPanel`、`RetrievalTracePanel`、`FinalAnswerJsonPanel` 等内部调试组件。
- 分析 `https://github.com/pallets/flask` 后跳转到 `/repos/654502453668`。
- 用户页展示仓库概览、代码地图、学习路径、开发流程、推荐议题和 Ask RepoMentor。
- QA 答案只显示结论、步骤、风险、可验证命令和简化证据。
- `/debug/654502453668` 显示调试控制台，包含 Agent Flow、8 个 Worker、Worker Outputs、Data Layer、Repository Graph、Shared Memory、Retrieval Trace、Evaluator / Optimizer、Final Answer JSON 和 Trace Export。

截图：

- `docs/routed-user-dashboard-viewport.png`
- `docs/routed-debug-console-viewport.png`
- `docs/routed-user-dashboard.png`
- `docs/routed-debug-console.png`

### 已知限制

- 当前后端尚未暴露所有规划中的 `/api/debug/...` 调试接口。
- 前端会复用已有的 `graph`、`memory`、analysis response 和 QA response 数据。
- 缺失的调试数据会显示明确空状态。
- 当时验证 Flask 仓库时后端 graph 返回 `files=0`，Code Map 正确显示为空，而不是编造文件或模块。

### 后续规则

每次实现改动都需要在本文件新增或更新一条记录，至少包含：

- 目标
- 修改的文件或模块
- 验证命令
- 浏览器或 API 检查
- 相关截图或产物
- 已知限制或回归风险

## 2026-06-08 前端中文展示本地化

### 目标

统一前端展示语言为中文。范围包括确定性 UI 标签、用户页和调试页中展示的后端/模型文本。翻译层不改变后端 API，也不改动导出的原始数据。

### 改动

- 新增 `frontend/src/utils/zh.js`，作为共享中文展示层，覆盖：
  - Worker 名称
  - 状态
  - 字段标签
  - 命令、文件、边、符号类型
  - 证据分组
  - 常见模型/后端句子
  - 基于正则的 Worker finding 翻译
  - 列表值和 JSON 展示标签
- 更新用户侧组件，展示中文标签和翻译后的模型文本：
  - `frontend/src/App.jsx`
  - `frontend/src/pages/UserDashboard.jsx`
  - `frontend/src/components/user/RepoInput.jsx`
  - `frontend/src/components/user/RepoOverviewPanel.jsx`
  - `frontend/src/components/user/CodeMapPanel.jsx`
  - `frontend/src/components/user/IssueRecommendationPanel.jsx`
  - `frontend/src/components/user/LearningPathPanel.jsx`
  - `frontend/src/components/user/DevelopmentWorkflowPanel.jsx`
  - `frontend/src/components/user/QAPanel.jsx`
  - `frontend/src/components/user/UserEvidencePanel.jsx`
- 更新调试侧组件，展示中文面板标题、Worker 轨迹、Shared Memory 字段、自检结果、检索证据和中文 JSON 预览：
  - `frontend/src/pages/DebugConsole.jsx`
  - `frontend/src/components/debug/DebugHeader.jsx`
  - `frontend/src/components/debug/AgentFlowDebugPanel.jsx`
  - `frontend/src/components/debug/WorkerOutputsDebugPanel.jsx`
  - `frontend/src/components/debug/DataLayerDebugPanel.jsx`
  - `frontend/src/components/debug/RepositoryGraphDebugPanel.jsx`
  - `frontend/src/components/debug/RetrievalTracePanel.jsx`
  - `frontend/src/components/debug/SharedMemoryPanel.jsx`
  - `frontend/src/components/debug/EvaluatorOptimizerPanel.jsx`
  - `frontend/src/components/debug/FinalAnswerJsonPanel.jsx`
  - `frontend/src/components/debug/TraceExportPanel.jsx`
- 保持 Trace Export 的原始数据行为不变，只本地化浏览器可见文本。
- 修复翻译链中 `PR issue`、`CI workflow` 等嵌入词仍漏出英文的问题。

### 验证

前端构建命令：

```powershell
$nodeDir = 'C:\Users\Liaoke\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin'
$node = Join-Path $nodeDir 'node.exe'
$env:PATH = "$nodeDir;$env:PATH"
& $node node_modules\vite\bin\vite.js build
```

结果：

- Vite build 通过。
- 转换 1603 个模块。
- 产物生成在 `frontend/dist/`。

浏览器验证：

- 打开 `http://127.0.0.1:5173/repos/654502453668`。
- 确认用户导航、仓库概览、学习路径、开发流程、议题推荐和 QA 标签均为中文。
- 确认用户视图不再显示 `User Dashboard`、`Learning Path`、`Development Workflow`、`Recommended Issues`、`Ask RepoMentor`、`Agent Flow`、`Worker Outputs`、`Data Layer`、`SelfCheck` 等内部英文词。
- 打开 `http://127.0.0.1:5173/debug/654502453668`。
- 确认调试页 header、Worker 名称、Worker 输出摘要、模型 finding、证据、自检和 JSON 预览显示为中文。
- 确认 `PR issue`、`CI workflow`、`workflow files`、`non-PR issues`、`fetch GitHub open issues` 无可见泄漏。
- 确认数字值 `0` 会保留为 `0`，不会被翻译成空状态。

截图：

- `docs/zh-user-dashboard-viewport.png`
- `docs/zh-debug-console-viewport.png`

### 已知限制

- 本次只本地化前端展示文本和常见后端/模型短句，不修改后端响应、schema、API 或导出的原始调试 JSON。
- 未来任意自由模型输出如果出现新的英文表达，可能仍需补充新的短语规则。

## 2026-06-08 调试 JSON 保持原始数据

### 目标

调试控制台里的 JSON 预览必须保持后端原始值。中文本地化只作用于 UI 标签、摘要、列表和阅读层文本，JSON 块不翻译、不改写。

### 改动

- 更新 `frontend/src/components/debug/WorkerOutputsDebugPanel.jsx`：
  - `原始输出 JSON` 使用 `JSON.stringify(output, null, 2)` 渲染，不再展示翻译后的 JSON。
- 更新 `frontend/src/components/debug/SharedMemoryPanel.jsx`：
  - `原始共享记忆 JSON` 的渲染和复制内容都使用同一份原始 shared-memory JSON。
- 更新 `frontend/src/components/debug/FinalAnswerJsonPanel.jsx`：
  - final-answer JSON 保留原始 payload。
- 更新 `frontend/src/utils/zh.js`：
  - 将标签从 `翻译后的输出 JSON` 改为 `原始输出 JSON`。
- 保留 JSON 上方的中文摘要，方便开发者快速扫描，同时仍可展开检查原始后端 JSON。

### 验证

前端构建命令：

```powershell
$nodeDir = 'C:\Users\Liaoke\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin'
$node = Join-Path $nodeDir 'node.exe'
$env:PATH = "$nodeDir;$env:PATH"
& $node node_modules\vite\bin\vite.js build
```

结果：

- Vite build 通过。
- 转换 1603 个模块。
- 产物生成在 `frontend/dist/`。

浏览器验证：

- 打开 `http://127.0.0.1:5173/debug/654502453668`。
- 展开第一个 `原始输出 JSON`。
- 确认 Worker JSON 保留原始键和值，例如 `worker_name`、`findings`、`Repo Graph Worker`、`scanned 0 files`。
- 确认 Shared Memory JSON 保留原始键和值，例如 `session_id`、`current_task`、`worker_outputs`、`Repo Graph Worker`。
- 确认不再显示翻译后的 JSON 标签。
- 确认 JSON 上方仍保留中文摘要，例如 `仓库图谱工作器`、`已扫描 0 个文件`。

截图：

- `docs/raw-json-debug-viewport.png`

### 已知限制

- 原始 JSON 中出现英文后端/模型文本是设计行为。
- JSON 上方的中文摘要仍是推荐阅读层。

## 2026-06-08 确定性仓库分析链路修复

### 目标

在接入真实 LLM 前修复确定性分析链路。公开 GitHub 仓库已有确定性证据时，用户页不应大量显示 `unknown` 状态；后端应基于 clone + 静态解析返回真实仓库事实，前端通过稳定 normalizer 读取这些字段。

### 根因

- `ParserService.list_files()` 用绝对路径 parts 过滤目录。克隆仓库位于 `.repomentor_cache` 下，导致每个文件路径都包含 `.repomentor_cache`，进而全部被过滤。
- `/api/repos/analyze` 因此返回 `files=0`，连带缺失 languages、key files、entrypoints、symbols、docs、workflow evidence 和前端状态。
- 前端 cache normalization 也可能保留 `sessionStorage` 中陈旧的空数组，遮蔽后端新返回的 graph 数据。

### 改动

- 修复仓库扫描：
  - `backend/app/services/parser_service.py`
  - 用相对仓库根目录的路径过滤 ignored dirs。
  - 跳过二进制/非文本 preview，避免图片被当成文档证据。
- 扩展确定性命令和图谱提取：
  - `backend/app/services/command_detector.py`
  - `backend/app/workers/repo_graph_worker.py`
  - `backend/app/data_layer/repository_intelligence_graph.py`
  - 新增 `setup_commands`、`lint_commands`、`format_commands`、`type_check_commands`、语言统计、核心目录、关键文件、README 检测和 Python package entrypoint 候选。
  - 拆分 setup/install 命令和 run/dev 命令。
  - 对 `pip install -e .`、`pytest`、`python -m flask` 等常见命令做优先排序。
- 收紧开发流程提取：
  - `backend/app/workers/development_workflow_worker.py`
  - 只扫描贡献、setup、development、testing、deployment 等相关文档，不再扫所有 docs asset。
- 扩展 API 响应和调试接口：
  - `backend/app/core/schemas.py`
  - `backend/app/core/orchestrator.py`
  - `backend/app/api/debug.py`
  - `backend/app/main.py`
  - `/api/repos/analyze` 增加 repo metadata、file tree、languages、core directories、key files、README status、setup/run/test/build/lint/format/type-check commands、worker outputs 和 `issues_count`。
  - 新增 `/api/debug/repos/{repo_id}/data-layer`、`/worker-outputs`、`/repository-graph` 以及 agent/session 调试辅助接口。
- 新增前端 normalizer 和更清晰的空状态：
  - `frontend/src/api/normalizers.js`
  - `frontend/src/App.jsx`
  - `frontend/src/components/user/RepoOverviewPanel.jsx`
  - `frontend/src/components/user/CodeMapPanel.jsx`
  - `frontend/src/components/user/DevelopmentWorkflowPanel.jsx`
  - `frontend/src/components/user/IssueRecommendationPanel.jsx`
  - `frontend/src/components/debug/DataLayerDebugPanel.jsx`
  - `frontend/src/components/debug/DebugHeader.jsx`
  - `frontend/src/utils/zh.js`
  - 将泛化的 “未知” 替换为明确状态，例如 “未检测到启动命令” 或 “未找到可推荐 open issues”。
- 新增本地 smoke test：
  - `scripts/smoke_test.py`
  - 生成 `scripts/smoke_test_report.md`。

### 验证

后端测试：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

结果：

- `6 passed`

前端构建：

```powershell
cd frontend
$nodeDir = 'C:\Users\Liaoke\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin'
$node = Join-Path $nodeDir 'node.exe'
$env:PATH = "$nodeDir;$env:PATH"
& $node node_modules\vite\bin\vite.js build
```

结果：

- Vite build 通过。
- 转换 1604 个模块。

后端 smoke test：

```powershell
backend\.venv\Scripts\python.exe scripts\smoke_test.py
```

结果：

- 报告写入 `scripts/smoke_test_report.md`。
- 必需确定性字段均存在，或以明确空状态返回。

`https://github.com/pallets/flask` 的关键 `/api/repos/analyze` 结果：

- `repo_id`: `654502453668`
- `owner/name`: `pallets/flask`
- `files`: 236
- `symbols`: 926
- `languages`: python, restructuredtext, html, text, yaml, markdown, toml, json, css, shell
- `key_files`: 14
- `readme_exists`: true
- `core_directories`: docs, tests, examples, src
- `entrypoints`: `src/flask/__init__.py`, `src/flask/app.py`, `src/flask/cli.py`, `src/flask/sansio/app.py`
- `setup_commands`: 以 `pip install -e .` 开头
- `run_commands`: `python -m flask`
- `test_commands`: `pytest`, `python -m pytest`
- `build_commands`: `python -m build --wheel`
- `lint_commands`: `ruff check .`
- `type_check_commands`: `mypy .`
- `worker_outputs`: 8
- `issues_count`: 0，前端明确显示 `未找到可推荐 open issues`

浏览器验证：

- 打开 `http://127.0.0.1:5173/repos/654502453668`。
- 清理旧 `sessionStorage` 并重新加载路由。
- 确认用户概览展示真实语言、目录、入口文件、安装/运行/测试命令。
- 确认用户概览不再显示 “未检测到主要语言”、“未检测到核心目录”、“未检测到测试命令”。
- 打开 Issue tab，确认空 issue 显示为 “未找到可推荐 open issues”，不是 “未知”。
- 打开 `http://127.0.0.1:5173/debug/654502453668`。
- 确认调试控制台显示 236 个数据项、Worker 输出、`RepoSnapshot` 和 `API raw response`。
- 确认新增 Worker finding 在调试摘要中本地化为中文，同时 raw JSON 不被改写。

截图：

- `docs/deterministic-user-dashboard-viewport.png`
- `docs/deterministic-debug-console-viewport.png`

### 已知限制

- 按设计没有接入真实 LLM provider。
- `pallets/flask` 经过 GitHub issue 过滤后返回 0 个非 PR open issue；UI 现在明确报告这个状态。
- 部分 setup 命令仍来自确定性文档证据；首个展示命令优先使用项目本地安装命令 `pip install -e .`。

## 2026-06-08 调试控制台按钮反馈

### 目标

让调试控制台的操作按钮点击后有明确反馈。用户反馈 `导出轨迹 JSON` 等按钮看起来没有反应，即使部分 handler 已存在。

### 改动

- 更新 `frontend/src/components/debug/TraceExportPanel.jsx`：
  - 下载链接点击前先 append 到 DOM，点击后再移除。
  - 延迟 `URL.revokeObjectURL`，给浏览器处理下载留出时间。
  - 导出后显示 action status，包括生成的文件名。
  - 当 `navigator.clipboard.writeText` 失败时，用临时 textarea 作为复制 fallback。
  - 为 `复制会话 ID` 显示明确成功/失败消息。
- 更新 `frontend/src/components/debug/SharedMemoryPanel.jsx`：
  - 为 `复制原始 JSON` 增加 clipboard fallback。
  - 显示明确复制成功/失败消息。
- 更新 `frontend/src/pages/DebugConsole.jsx`：
  - `刷新调试数据` 显示 “正在刷新/已刷新/刷新失败” 状态。
- 更新 `frontend/src/styles.css`：
  - 新增 `.actionStatus` 紧凑反馈样式。

### 验证

前端构建：

```powershell
cd frontend
$nodeDir = 'C:\Users\Liaoke\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin'
$node = Join-Path $nodeDir 'node.exe'
$env:PATH = "$nodeDir;$env:PATH"
& $node node_modules\vite\bin\vite.js build
```

结果：

- Vite build 通过。
- 转换 1604 个模块。

浏览器验证：

- 打开 `http://127.0.0.1:5173/debug/f89b095c9044?session_id=c2dd2bdc-9f02-450a-b7e1-1f0af1c1ae1c`。
- 点击 `刷新调试数据`，页面显示 `已刷新调试数据：...`。
- 点击 `复制原始 JSON`，按钮变为 `已复制`，状态显示 `原始 JSON 已复制。`。
- 点击 `导出轨迹 JSON`，状态显示 `已触发下载：repomentor-trace-c2dd2bdc-9f02-450a-b7e1-1f0af1c1ae1c.json`。
- 点击 `复制会话 ID`，按钮变为 `已复制`，状态显示 `会话 ID 已复制。`。

截图：

- `docs/debug-buttons-feedback-viewport.png`

### 已知限制

- 浏览器下载行为仍取决于宿主浏览器的下载设置，但 UI 现在会确认应用已经生成并触发下载动作。

## 2026-06-09 确定性结构质量修复

### 目标

在接入真实 LLM 前先修复确定性仓库结构质量。目标仓库为 `https://github.com/huier5635-cmd/resilience-copilot-gemma4`。

### 改动

- 更新入口文件识别：
  - README/docs 和已检测命令中的运行脚本优先于 `__init__.py`。
  - `entrypoints` 增加 `path`、`reason`、`source`、`confidence` 字段。
  - `__init__.py` 只作为低置信 package entry 保留。
- 改进 Test Worker：
  - 基于本地 import 创建高置信 `tests` 边。
  - 增加文件名精确匹配的中置信边。
  - 增加关键词启发式匹配的低置信边。
- 改进 Docs Worker：
  - 基于显式文件路径、模块名、符号名和文档文件名规则创建 docs -> code 的 `documents` / `mentions` 边。
  - 跳过 license/reference docs 的代码映射，减少噪声。
- 增加后端命令去重元数据：
  - 统一命令斜杠和空白。
  - 保留最高 confidence。
  - 合并 `evidence_sources`。
- 更新 Shared Working Memory：
  - `add_worker_output` 自动合并 `output.evidence`。
  - 按 `evidence_id` 去重。
- GitHub open issues 为 0 时生成内部入门任务：
  - `source = internal_suggestion`
  - 明确不是 GitHub Issue。
- 改进文件类型识别：
  - README 变体、LICENSE、HTML/CSS、JSON/JSONL、`.bib`、`.env.example`、`.gitignore`。
- 更新前端展示：
  - 用户页显示友好的中文文件类型。
  - 用户页减少 `unknown` 文件行。
  - Development Workflow 命令按 command 聚合，并显示 `证据来源：...`。
  - Issue fallback 任务显示为 `入门练习任务`，并展示无 open issue 的解释。
  - 调试页保留 raw `file_type`、entrypoint confidence/source/reason、edge evidence/confidence。
- 重写 `scripts/smoke_test.py`：
  - 新增 files、symbols、docs、entrypoints、test/doc edges、命令重复、Shared Memory evidence、issue fallback 等确定性结构检查。

### 验证

后端编译：

```powershell
python -m compileall backend/app scripts/smoke_test.py
```

结果：

- 编译通过。

前端构建：

```powershell
cd frontend
& "C:\Users\Liaoke\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" node_modules/vite/bin/vite.js build
```

结果：

- Vite build 通过。
- 转换 1604 个模块。

Smoke test：

```powershell
python scripts/smoke_test.py
```

结果：

- 报告写入 `scripts/smoke_test_report.md`。
- 所有确定性结构检查通过。

`f89b095c9044` 最终指标：

- `files`: 64
- `symbols`: 221
- `docs`: 20
- `entrypoints`: 14
- `test_edges`: 15
- `doc_edges`: 50
- `quality_commands`: 后端记录 14 条，用户可见命令组 9 个
- `shared_memory.retrieved_evidence`: 10
- Issue fallback tasks: 6 个，均为 `internal_suggestion`

修正后的高优先级入口：

- `scripts/run_academic_eval.py`
- `scripts/run_demo.py`
- `scripts/run_eval.py`
- `scripts/run_local_validation.py`
- `scripts/run_stress_test.py`
- `src/agent/__main__.py`
- `app.js`

浏览器验证：

- 恢复 Vite dev server：`http://127.0.0.1:5173/`。
- 用户页 `http://127.0.0.1:5173/repos/f89b095c9044`：
  - 显示脚本入口，不再显示 `[object Object]`。
  - 不显示 Agent Flow / Data Layer / Worker Outputs。
  - 显示友好中文文件类型，例如 `配置`、`许可证`、`文档`、`源码`、`数据`。
- Development Workflow tab：
  - 相同命令只显示一次。
  - 显示 `证据来源：README.md、RepositoryIntelligenceGraph`。
- Issues tab：
  - 显示 `当前仓库没有 open issue...` 说明。
  - 显示 6 个 `入门练习任务` 卡片。
- 调试页 `http://127.0.0.1:5173/debug/f89b095c9044`：
  - 显示 raw `file_type=docs_legal`、`file_type=data` 等。
  - 显示 entrypoint `confidence=high`。
  - 显示 edge `evidence=` 和 confidence。

### 已知限制

- 按设计没有连接真实 LLM。
- 后端仍保留按来源拆分的命令记录，方便调试；用户侧展示会按相同 command 聚合。

## 2026-06-09 实验记录中文化

### 目标

将 `docs/experiment_records.md` 的叙述内容统一改为中文，方便后续用中文追踪实验、验证和已知限制。

### 改动

- 重写 `docs/experiment_records.md`：
  - 一级标题改为 `RepoMentor 实验记录`。
  - 所有记录的通用标题统一为 `目标`、`改动`、`验证`、`已知限制`。
  - 将英文叙述翻译为中文。
  - 保留路径、命令、组件名、API 路由、指标名称和原始技术标识。
  - 增加本条中文化记录，延续“每次改动都留实验记录”的规则。

### 验证

文档检查：

```powershell
Get-Content docs/experiment_records.md -Encoding UTF8
```

结果：

- 文件可用 UTF-8 正常读取。
- 记录主体已统一为中文。

### 已知限制

- 技术名词、文件路径、命令、组件名和 API 路由按原样保留，不强行翻译。
## 2026-06-09 产品化修复：Data Layer、启动问答与推荐任务
### 目标

在不大改架构、不接入真实 LLM 的前提下，修复用户页与调试页之间的确定性质量问题。重点包括 Data Layer Summary 与详细图谱一致、启动问答更像用户答案、命令去重与分组、SelfCheck 变严格、Development Workflow 规则分类更准确，以及 open issue 为 0 时生成内部入门任务。

### 改动

- 修复 Data Layer Summary：
  - `/api/debug/repos/{repo_id}/data-layer` 改为使用 RepositoryGraph 的真实 summary。
  - `symbols`、`imports`、`tests`、`docs`、`quality_commands` 和 `development_workflow` 与详细图谱一致。
  - `docs` 统计文档关系边数量，另保留 `doc_files` 和 `doc_edges` 便于调试。
- 改进命令去重：
  - 后端按 `command_type + normalized_command` 合并质量命令。
  - 统一 Windows 反斜杠和 Unix 斜杠。
  - 合并 `evidence_sources`，保留最高 `confidence`。
  - 前端命令展示也按规范化 command 去重。
- 修复 `setup_run` 问答：
  - 修复乱码污染的 `IntentRouter`，让“这个项目怎么启动？”稳定路由到 `setup_run`。
  - 启动答案改为用户可执行分组：推荐启动方式、可选 demo 命令、评估/高级命令、测试命令、风险提示、证据来源。
  - 主启动优先 `pip install -r requirements.txt`、`python scripts/run_demo.py`、`python -m pytest tests`。
  - `run_academic_eval`、`run_eval`、`run_local_validation`、`run_stress_test` 进入评估/高级命令。
- 增强 SelfCheck：
  - 结论提到“配置文件”时要求 config/code/build evidence。
  - 结论提到“构建脚本”时要求 build/config evidence。
  - 只有 README/docs evidence 时，不允许声称配置文件或构建脚本直接支持结论。
  - `verifiable_commands` 中没有图谱证据或缺少 evidence source 的命令会标记 `missing_evidence`。
  - `evidence_code` 为空时，不声称代码或配置文件直接支持结论。
- 修正 Development Workflow 分类：
  - 新增并返回 `contribution_rules`、`setup_rules`、`test_rules`、`documentation_references`、`project_safety_policies`。
  - 安全策略、项目介绍和业务限制不再混入代码规范或贡献规则。
  - Development Workflow API 显式返回去重后的 `quality_commands`。
- 改进 Issue fallback：
  - open issue 为 0 时返回 6 个 `internal_suggestion` 入门练习任务。
  - 前端明确显示“不是 GitHub Issue · 内部建议”。
  - 任务包含 test/docs/setup/code-reading 标签和可执行第一步。
- 优化用户页展示：
  - 用户概览把“启动命令”和“评估/高级命令”分开。
  - `python scripts/run_demo.py` 留在启动命令。
  - `run_academic_eval`、`run_eval` 等不再与主启动命令混在一起。

### 验证

后端编译：

```powershell
python -m compileall backend/app scripts/smoke_test.py
```

结果：
- 编译通过。

前端构建：

```powershell
cd frontend
& "C:\Users\Liaoke\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" node_modules/vite/bin/vite.js build
```

结果：
- Vite build 通过。
- 转换 1604 个模块。

Smoke test：

```powershell
python scripts/smoke_test.py
```

结果：
- 报告写入 `scripts/smoke_test_report.md`。
- 所有确定性结构检查通过。

目标仓库 `https://github.com/huier5635-cmd/resilience-copilot-gemma4` 最新指标：

- `repo_id`: `f89b095c9044`
- `files`: 64
- `symbols`: 221
- `imports`: 38
- `test_edges`: 15
- `doc_edges`: 50
- `quality_commands`: 9
- `development_workflow`: `ready`
- `shared_memory.retrieved_evidence`: 10
- Issue fallback tasks: 6 个，均为 `internal_suggestion`

Data Layer Summary 与详细图谱核对：

- Summary `symbols=221`，详细图谱 `symbols=221`
- Summary `imports=38`，详细图谱 import edges `38`
- Summary `tests=15`，详细图谱 test edges `15`
- Summary `docs=50`，详细图谱 doc/mention edges `50`
- Summary `quality_commands=9`，详细质量命令 `9`
- Summary `development_workflow=ready`

启动问答验证：

- 结论：`这个项目推荐先安装依赖，再运行 demo 脚本。`
- 推荐启动方式：`pip install -r requirements.txt`；`python scripts/run_demo.py`
- 可选 demo 命令：`python scripts/run_demo.py --case-id ...`；`python scripts/run_demo.py --scenario ...`
- 评估/高级命令：`python scripts/run_academic_eval.py`；`python scripts/run_eval.py`；`python scripts/run_local_validation.py`；`python scripts/run_stress_test.py`
- 测试命令：`python -m pytest tests`
- SelfCheck：`passed=true`，无 `missing_evidence`，无 `hallucination_risks`

浏览器验证：

- 用户页 `http://127.0.0.1:5173/repos/f89b095c9044`：
  - 不显示 Agent Flow、Worker Outputs、Data Layer。
  - 推荐任务页显示“当前仓库没有 open issue，因此这是基于仓库结构生成的入门练习任务。”
  - fallback 任务显示“不是 GitHub Issue · 内部建议”。
  - 概览中“启动命令”只显示 demo 命令，“评估/高级命令”单独显示 eval 命令。
- 调试页 `http://127.0.0.1:5173/debug/f89b095c9044`：
  - Data Layer Summary 显示文件 64、符号 221、导入关系 38、测试 15、文档 50、质量命令 9、开发流程已就绪。
  - 保留 raw `file_type`、entrypoint confidence/source/reason、edge evidence/confidence。

### 已知限制

- 本轮仍未接入真实 LLM。
- Summary 中 `docs` 表示文档关系边数量；文档文件数量保留在 `doc_files`。
- 当前仓库没有 GitHub open issue，因此推荐任务是基于仓库结构生成的内部入门练习，不是远端 GitHub Issue。

## 2026-06-09 LLM Provider 接入：DeepSeekProvider 与 RepoQA 模型增强
### 目标

在不引入 LangGraph、不重写 Orchestrator、不让模型决定仓库事实的前提下，在现有 MockProvider 基础上新增 DeepSeekProvider，并先把模型增强接入 RepoQA。文件、命令、符号、Issue、测试边、文档边和依赖边仍全部来自确定性 Repository Intelligence Graph；LLM 只负责基于 evidence 做自然语言解释和润色。

### 改动

- 新增 LLM Provider 基础设施：
  - `BaseLLMProvider`
  - `MockProvider`
  - `DeepSeekProvider`
  - `OpenAIProvider` 预留
  - `LLMService`
- DeepSeek 使用 OpenAI-compatible 调用方式：
  - 默认 `DEEPSEEK_BASE_URL=https://api.deepseek.com`
  - 默认 `DEEPSEEK_MODEL=deepseek-chat`
  - 支持可选 `deepseek-reasoner`
  - 使用 `LLM_TEMPERATURE=0.2`
  - 使用 `LLM_MAX_TOKENS=1200`
- 保留 mock 默认模式：
  - `LLM_PROVIDER=mock`
  - 不调用外部 API
  - 适合无 key 开发和测试
- 增加 DeepSeek 无 key 回退：
  - `LLM_PROVIDER=deepseek` 且缺少 `DEEPSEEK_API_KEY` 时不崩溃。
  - 自动回退 MockProvider。
  - `model_info.fallback_to_mock=true`。
  - warning 不输出 API key。
- 新增配置与依赖：
  - 新建 `backend/.env.example`
  - `backend/requirements.txt` 增加 `openai` 和 `python-dotenv`
  - `.gitignore` 增加 `backend/.env` 和 `.env`
- RepoQA 接入模型增强：
  - Intent Router 仍先判定任务类型。
  - Hybrid Retrieval Index 先检索 evidence。
  - evidence 为空时不调用 LLM，并返回 evidence 不足。
  - evidence 足够时构造受限 system/user prompt。
  - LLM 输出只在 DeepSeek/OpenAI 真实调用成功时用于改写自然语言部分。
  - mock 或 fallback 时保留 deterministic answer。
  - 模型输出的可验证命令会按 RepositoryGraph 过滤。
  - 最终仍经过 Evaluator 和 Optimizer。
- FinalAnswer 和 Debug 数据增加 `model_info`：
  - `provider`
  - `model`
  - `prompt_type`
  - `evidence_count`
  - `elapsed_ms`
  - `success`
  - `used_llm`
  - `fallback_to_mock`
  - `error_message`
- Shared Working Memory 增加：
  - `model_calls`
  - `final_answer_json`
- Debug API 增加：
  - `/api/debug/session/{session_id}/self-check`
  - `/api/debug/session/{session_id}/final-answer-json`
- Evaluator 增强：
  - 检查模型输出中提到的文件是否存在于 RepositoryGraph。
  - 检查模型输出中提到的命令是否存在于 quality commands 或图谱命令。
  - 检查模型输出中提到的 Issue 编号是否有 Issue evidence。
  - 检查模型输出中提到的函数符号是否存在于 Symbol Graph。
  - evidence 为空但置信度不低时标记风险。
  - 继续检查“配置文件/构建脚本”是否有 config/build evidence。
- 前端更新：
  - 用户页 QA 底部显示轻量标签：`模型增强：Mock` / `模型增强：DeepSeek`。
  - 调试页 Evaluator/Optimizer 面板显示完整 LLM 调试信息。
  - FinalAnswer JSON 显示 `model_info`。
- README 更新：
  - 增加 Mock 模式说明。
  - 增加 DeepSeek 模式配置。
  - 增加 OpenAI-compatible 预留配置。
  - 增加 API key 安全提醒。
  - 增加“无 evidence 不调用模型”的使用建议。
- 测试更新：
  - LLM Provider 单元测试。
  - DeepSeek 无 key fallback 测试。
  - RepoQA evidence 为空不调用 LLM 测试。
  - RepoQA evidence 足够调用 LLMService 测试。
  - setup_run 具体命令测试。
  - FinalAnswer JSON `model_info` 测试。
  - smoke test 增加 `--provider mock|deepseek` 和 model_info 报告。

### 验证

后端编译：

```powershell
python -m compileall backend/app scripts/smoke_test.py
```

结果：
- 编译通过。

后端单元测试：

```powershell
python -m pytest backend/tests -q
```

结果：
- `14 passed`

前端构建：

```powershell
cd frontend
& "C:\Users\Liaoke\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" node_modules/vite/bin/vite.js build
```

结果：
- Vite build 通过。
- 转换 1604 个模块。

DeepSeek 无 key fallback 验证：

```powershell
$env:PYTHONPATH='backend'
$env:LLM_PROVIDER='deepseek'
Remove-Item Env:DEEPSEEK_API_KEY -ErrorAction SilentlyContinue
```

结果：

- `provider`: `deepseek`
- `model`: `mock-deterministic`
- `used_llm`: `false`
- `fallback_to_mock`: `true`
- `error_message`: `DEEPSEEK API key is not set; using MockProvider`
- 日志没有输出 API key。

Smoke test：

```powershell
python scripts/smoke_test.py --provider mock
```

结果：
- 报告写入 `scripts/smoke_test_report.md`。
- 所有确定性结构检查通过。
- `FinalAnswer JSON includes model_info` 通过。

RepoQA API 验证：

- 问题：`这个项目怎么启动？`
- 结论：`这个项目推荐先安装依赖，再运行 demo 脚本。`
- 命令包含：
  - `pip install -r requirements.txt`
  - `python scripts/run_demo.py`
  - `python -m pytest tests`
- `model_info`：
  - `provider=mock`
  - `model=mock-deterministic`
  - `prompt_type=setup_run`
  - `evidence_count=10`
  - `used_llm=false`
  - `fallback_to_mock=false`
- SelfCheck：
  - `passed=true`
  - 无 hallucination risks
  - 无 missing evidence

浏览器验证：

- 用户页 `http://127.0.0.1:5173/repos/f89b095c9044`：
  - QA 回答显示具体启动命令。
  - QA 底部显示 `模型增强：Mock`。
- 调试页 `http://127.0.0.1:5173/debug/f89b095c9044`：
  - 显示 `LLM 调试信息`。
  - 显示 `provider=mock`、`model=mock-deterministic`、`prompt_type=setup_run`、`evidence_count=10`、`fallback_to_mock=false`。
  - FinalAnswer JSON 包含 `model_info`。

### 已知限制

- 本轮按要求先接入 RepoQA，没有把真实 LLM 全系统铺开。
- Code Explanation Worker、LearningPath endpoint 和 DevelopmentWorkflow endpoint 仍以确定性结构化结果为主；后续可在 RepoQA 稳定后继续接入模型总结。
- 当前本地未配置真实 `DEEPSEEK_API_KEY`，因此浏览器和 smoke 验证使用 mock 默认模式。
- 使用 DeepSeek 前需要安装更新后的 `backend/requirements.txt` 并重启后端。

## 2026-06-09 前端模型启动：用户简版与调试详版拆分
### 目标

在用户已完成 DeepSeek 充值后，把“启动模型”做成前端可操作功能，同时继续保持用户页和调试页分离。用户页只展示当前模型模式和修改入口；API Key、模型选择、Base URL、启动/切回 Mock 等详细控制放到 Debug Console。

### 改动

- 后端新增运行时 LLM 配置能力：
  - `LLMService.configure(...)`
  - `LLMService.status()`
  - 不需要手动修改 `.env` 或重启后端即可在当前进程内切换 provider。
- 后端新增 LLM API：
  - `GET /api/llm/status`
  - `POST /api/llm/configure`
- 安全处理：
  - API key 只进入本地后端内存。
  - `status` 只返回 `has_api_key=true/false`。
  - 不回显 API key。
  - 错误信息会脱敏。
  - 重启后端后运行时 key 会清空，需要重新启动模型。
- 前端用户页：
  - `ModelControlPanel` 改为简版。
  - 只显示当前模式、模型、状态和“修改模式”按钮。
  - 不显示 API Key、Base URL、启动按钮等调试细节。
  - 如果路由加载时已有本地缓存数据，但后端运行态缺失导致补拉失败，不再把 `Failed to fetch` 直接展示给用户。
- 前端调试页：
  - 新增 `ModelDebugPanel`。
  - 显示完整模型控制：
    - 当前模式
    - 模型
    - API Key 是否已配置
    - 状态
    - DeepSeek API Key 输入框
    - `deepseek-chat` / `deepseek-reasoner` 选择
    - Base URL
    - 启动 DeepSeek
    - 切回 Mock
    - 最近一次模型调用 JSON
  - 已启动 DeepSeek 后，允许不重复输入 API Key，直接切换 `deepseek-chat` / `deepseek-reasoner` 并点击“重启 DeepSeek”生效。
  - 调试页仓库名称优先使用当前解析结果，避免旧输入框 URL 造成标题误导。
- 前端 API：
  - 新增 `getLLMStatus()`
  - 新增 `configureLLM(payload)`
  - 默认 API 地址改为 `http://127.0.0.1:8000/api`，减少本地 `localhost` 解析不稳定导致的 fetch 问题。
- README 更新：
  - 增加前端“模型启动”说明。

### 验证

后端编译：

```powershell
python -m compileall backend/app scripts/smoke_test.py
```

结果：
- 编译通过。

后端单元测试：

```powershell
python -m pytest backend/tests -q
```

结果：
- `15 passed`

前端构建：

```powershell
cd frontend
& "C:\Users\Liaoke\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" node_modules/vite/bin/vite.js build
```

结果：
- Vite build 通过。
- 转换 1606 个模块。

API 验证：

- `GET /api/llm/status` 返回：
  - `provider=mock`
  - `model=mock-deterministic`
  - `ready=true`
- 使用 fake key 调用 `POST /api/llm/configure` 返回：
  - `provider=deepseek`
  - `model=deepseek-chat`
  - `has_api_key=true`
  - `ready=true`
  - 返回 JSON 不包含 fake key。
- 随后切回 `mock`。

浏览器验证：

- 用户页 `http://127.0.0.1:5173/repos/f89b095c9044`：
  - 显示 `模型模式`。
  - 显示当前模式、模型和状态。
  - 显示 `修改模式` 按钮。
  - 不显示 `DeepSeek API Key`、`Base URL`、`启动 DeepSeek`。
- 点击 `修改模式` 后进入调试页：
  - 显示 `模型控制`。
  - 显示 `DeepSeek API Key`、模型选择、`Base URL`、`启动 DeepSeek`、`切回 Mock`。
  - 调试页仍保留 Agent Flow、Worker Outputs、Data Layer、FinalAnswer JSON 等内部信息。

### 已知限制

- 当前运行时配置存放在后端进程内存中；重启后端后需要重新在调试页启动 DeepSeek。
- API Key 不落盘，这是为了避免误提交或浏览器缓存泄露。
- 本次未用真实 key 触发 DeepSeek 请求，避免替用户消耗额度；启动真实模型后可通过 Debug Console 的 `model_info.used_llm=true` 验证。

## 2026-06-09 DeepSeek 启动与模型切换保留
### 目标

在前端调试页保留“启动 DeepSeek”入口，同时保留已有模型切换能力。用户页仍保持简版，只展示当前模式和“修改模式”入口。

### 改动

- 后端 `LLMService.configure(...)` 支持在已有 DeepSeek Key 的情况下，仅提交新模型名即可切换模型。
- 前端 `ModelDebugPanel`：
  - 保留 `deepseek-chat` / `deepseek-reasoner` 选择。
  - 保留 `启动 DeepSeek` / `切回 Mock`。
  - DeepSeek 已启动后，按钮显示为 `重启 DeepSeek`。
  - 已配置 Key 后，API Key 输入框可留空，直接切换模型并重启。
- 不把用户提供的 API Key 写入源码、缓存、README 或实验记录。

### 验证

- 后端测试：`16 passed`
- 后端编译：通过
- 前端构建：Vite build 通过，转换 1606 个模块
- 浏览器验证：
  - 调试页显示 `启动 DeepSeek` / `重启 DeepSeek`
  - 调试页显示 `切回 Mock`
  - 调试页显示 `deepseek-chat` 和 `deepseek-reasoner`
  - 调试页显示已配置 Key 后可留空切换模型的说明

## 2026-06-09 模型控制用户/调试二次拆分与 `/api/model` 接口
### 目标

按产品化要求把模型控制拆成用户页简化版和调试页完整版。用户页只允许查看当前模式并切换 Mock/DeepSeek，不出现 API Key、Base URL、fallback 细节或 LLM 调用日志。调试页集中管理 provider、模型、Base URL、Key 状态、fallback、最近调用、保存配置和测试连接。

### 改动

- 后端新增 `backend/app/services/model_config_service.py`：
  - 默认请求 provider 为 `deepseek`。
  - 默认模型为 `deepseek-chat`。
  - 默认 Base URL 为 `https://api.deepseek.com`。
  - 无 Key 时返回 `provider_requested=deepseek`、`provider_active=mock`、`fallback_to_mock=true`、`reason=missing_deepseek_api_key`。
  - API Key 只保存在后端运行时内存；只有用户显式选择 persist 时才写入 `backend/.env`。
  - `api_key_masked` 只返回掩码，不返回明文。
- 后端新增 API：
  - `GET /api/model/status`
  - `POST /api/model/config`
  - `POST /api/model/test`
- 前端新增 API 封装：
  - `frontend/src/api/model.js`
- 用户页新增：
  - `frontend/src/components/user/UserModelSwitch.jsx`
  - 只显示当前模式、当前模型、状态、Mock/DeepSeek 切换和“打开模型设置”。
- 调试页新增：
  - `frontend/src/components/debug/ModelControlDebugPanel.jsx`
  - 显示 provider_requested、provider_active、model、base_url、Key 掩码状态、fallback、reason、最近 LLM 调用信息。
  - API Key 输入框为 `type=password`，保存后清空，不回显旧 Key。
  - 支持仅本次后端运行时生效，或显式写入 `backend/.env`。
- 删除旧模型组件：
  - `frontend/src/components/user/ModelControlPanel.jsx`
  - `frontend/src/components/debug/ModelDebugPanel.jsx`
- 更新：
  - `backend/.env.example`
  - `.gitignore`
  - `README.md`

### 安全检查

- 未将真实 API Key 写入源码、README、实验记录或前端默认值。
- 搜索真实 Key 片段无命中。
- 前端模型配置不写入 localStorage、sessionStorage、IndexedDB 或浏览器缓存。
- sessionStorage 仍只用于仓库分析结果缓存，不保存模型配置或 Key。

### 验证

后端编译：

```powershell
python -m compileall backend/app scripts/smoke_test.py
```

结果：通过。

后端测试：

```powershell
python -m pytest backend/tests -q
```

结果：`18 passed`

前端构建：

```powershell
cd frontend
& "C:\Users\Liaoke\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" node_modules/vite/bin/vite.js build
```

结果：Vite build 通过，转换 1607 个模块。

API 验证：

- `GET /api/model/status`：
  - `provider_requested=deepseek`
  - `provider_active=mock`
  - `fallback_to_mock=true`
  - `reason=missing_deepseek_api_key`
- `POST /api/model/config` 使用测试 Key：
  - 返回 `provider_active=deepseek`
  - 返回 `api_key_masked`
  - 响应不包含测试 Key 明文
- 验证后已重启后端，清空测试 Key 运行时内存。

浏览器验证：

- 用户页：
  - 显示 `模型模式`
  - 显示 `免费 Mock 模式`、`DeepSeek 模式`、`打开模型设置`
  - 不显示 Base URL
  - 不显示 prompt_type
  - 模型区没有 password 输入框
- 调试页 `/debug/model`：
  - 显示 `模型控制`
  - 显示 provider_requested、provider_active、base_url、fallback_to_mock、reason
  - 显示 `保存配置`、`测试连接`
  - 显示 `deepseek-chat` 和 `deepseek-reasoner`
  - API Key 输入框数量为 1，类型为 password，值为空
- 用户页“打开模型设置”按钮跳转到 `/debug/f89b095c9044?tab=model`。

## 2026-06-09 调试页面模型控制与智能体流程布局修复
### 目标

修复调试页面中“模型控制”和“智能体流程调试”两个板块视觉重叠的问题。

### 改动

- `ModelControlDebugPanel` 增加专用类 `modelControlDebugPanel`。
- 调试页网格中模型控制面板固定占满整行：`grid-column: 1 / -1`。
- 模型控制内部状态区从固定 7 列改为自适应列：`repeat(auto-fit, minmax(150px, 1fr))`。
- 模型控制表单从固定 4 列改为自适应列：`repeat(auto-fit, minmax(220px, 1fr))`。
- 模型操作按钮允许换行，避免小宽度时横向挤压。

### 验证

- 前端构建：Vite build 通过。
- 后端测试：`18 passed`。
- 浏览器验证：
  - 当前窄宽度下，模型控制和智能体流程 `overlap=false`。
  - 1280x900 桌面视口下，模型控制占整行，智能体流程位于下一行，`overlap=false`。

## 2026-06-09 整体压力测试与稳定性验收
### 目标

进入产品化验收阶段，不新增 LangGraph、不重构整体架构，系统性测试多仓库分析、异常仓库处理、QA 证据链、模型状态、调试控制台和用户页/调试页展示稳定性。

### 新增测试资产

- 新增 `scripts/stress_test_repomentor.py`：
  - 支持 `--base-url`、`--provider`、`--concurrency`、`--output-dir`、`--skip-large`、`--repo-list`。
  - 启动前检查 `/api/health`、`/api/model/status`、`/api/model/config`、`/api/model/test`。
  - 覆盖 analyze、graph、data-layer、learning-path、development-workflow、issues、12 个固定 QA 问题、并发 QA、前端静态检查和敏感信息泄露检查。
  - 输出 `reports/stress_report.json`、`reports/stress_report.md`、`reports/stress_summary.md`、`docs/testing_plan.md`、`docs/known_limitations.md`、`docs/upgrade_recommendations.md`。
- 新增默认仓库清单 `tests/fixtures/stress_repos.json`：
  - `resilience-copilot-gemma4`
  - `pallets/flask`
  - `psf/requests`
  - `fastapi/typer`
  - `vitejs/vite-plugin-react`
  - 4 个异常仓库输入。
- 新增网络受限补充清单 `tests/fixtures/stress_repos_cached_fallback.json`：
  - 仍使用公开仓库样例和 Flask。
  - 使用已缓存的公开仓库 `academic-paper-workflow-skill` 补足当前 GitHub 443 连接不稳定时的 3 仓库复现测试。

### 测试中修复的问题

- 修复空 `repo_url` 被当成本地当前后端目录扫描的问题：
  - `GitService.prepare_repository` 现在会拒绝空 URL。
  - 异常信息为可读错误，不再误扫本地目录。
- 修复敏感文件扫描风险：
  - `ParserService.list_files` 跳过 `.env`、`.env.local`、私钥类文件和敏感后缀。
  - 保留 `.env.example` 作为配置示例文件。
- 修复压力测试脚本误判：
  - 文档边统计同时读取 Data Layer `edges` 和 RepositoryGraph `raw_graph.edges`。
  - QA 文件路径校验不再把“明确说明缺失的文件”误判为幻觉。
  - QA 命令校验不再把可验证命令里的路径误判为不存在文件。

### 执行命令

```powershell
python scripts\stress_test_repomentor.py --base-url http://127.0.0.1:8000 --provider mock --concurrency 3 --output-dir reports --skip-large
python scripts\stress_test_repomentor.py --base-url http://127.0.0.1:8000 --provider mock --concurrency 3 --output-dir reports --repo-list tests\fixtures\stress_repos_cached_fallback.json
python -m pytest backend\tests -q
cd frontend
& "C:\Users\Liaoke\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" node_modules/vite/bin/vite.js build
```

### 网络受限默认清单结果

- 默认公网清单执行时，GitHub 443 连接不稳定：
  - `resilience-copilot-gemma4` 成功。
  - `pallets/flask` 成功。
  - `fastapi/typer` 与 `vitejs/vite-plugin-react` 因 GitHub 连接失败未完成 clone。
  - `psf/requests` 按 `--skip-large` 跳过。
- 该轮报告已归档到 `reports/archive/stress_report_network_limited_20260609-150525.json`、`reports/archive/stress_report_network_limited_20260609-150525.md` 和 `reports/archive/stress_summary_network_limited_20260609-150525.md`。

### 缓存补充清单最终结果

- 整体结论：`FAIL`。
- 失败原因：`evidence_coverage_rate=50.00%`，低于验收阈值 `85.00%`。
- 正常仓库 analyze：`3 / 3` 成功。
- 异常仓库：`4 / 4` 返回可读错误。
- 平均 analyze 时间：`22.113s`。
- 平均 QA 时间：`0.044s`。
- p95 QA 延迟：`0.104s`。
- QA 成功率：`100.00%`。
- command hallucination：`0`。
- SelfCheck 通过率：`25.00%`。
- SelfCheck 缺失率：`0.00%`。
- Issue fallback：`3 / 3` 成功。
- API Key 泄露检查：未发现。

### 仓库结构结果

- `resilience-copilot-gemma4`：
  - files=`64`，symbols=`221`，imports=`38`，docs files=`20`，docs edges=`50`，test files=`6`，test edges=`15`，quality commands=`9`。
- `pallets/flask`：
  - files=`235`，symbols=`926`，imports=`102`，docs files=`100`，docs edges=`731`，test files=`68`，test edges=`154`，quality commands=`22`。
- `academic-paper-workflow-skill`：
  - files=`13`，symbols=`22`，imports=`0`，docs files=`2`，docs edges=`1`，test files=`0`，test edges=`0`，quality commands=`2`。

### 前端浏览器验证

- 用户页 `/repos/f89b095c9044`：
  - 不显示 `Agent Flow`、`Worker Outputs`、`Shared Memory raw JSON`、`Worker raw JSON`、`FinalAnswer JSON`。
  - 显示仓库概览、代码地图、学习路径、开发流程。
  - 模型区无 password 输入框。
- 调试页 `/debug/f89b095c9044?tab=model`：
  - 显示模型控制、智能体流程、工作器输出、数据层、仓库图谱、检索轨迹、共享记忆、评估器与优化器、最终答案 JSON。
  - API Key 输入框为 password，值为空。
  - 页面文本未发现 `sk-` 形式密钥。
  - 当前窄视口和 1280x900 桌面视口下，模型控制与智能体流程 `overlap=false`。

### 回归验证

- `python -m pytest backend\tests -q`：`20 passed`。
- Vite build：通过，转换 `1607` 个模块。
- 生成报告未发现 API Key 模式字符串。

### 仍存在的问题

- QA evidence 覆盖率只有 `50.00%`，仓库概览、核心模块、入口文件、文档推荐、新手任务等问题常返回 `evidence_count=0`。
- SelfCheck 通过率只有 `25.00%`，主要原因是无证据回答被严格评估拦下。
- 默认公网多仓库测试受 GitHub 443 连接影响，不能稳定完成全部 clone。

### 下一阶段建议

- P0：强化 QA evidence 注入，让仓库概览、核心模块、入口文件、文档推荐和 internal first tasks 都带上 evidence。
- P0：继续收紧 SelfCheck，对 `evidence_count=0` 的结论要求明确“不足证据”或补齐证据。
- P0：为 GitHub clone 失败增加更明确的网络错误提示和重试/缓存策略。
- P1：DeepSeek 真模型模式单独跑一轮小仓库验收，重点验证 `model_info.used_llm=true`、不泄露 Key、证据链不被模型改写。
- P2：在当前确定性链路稳定后，再考虑 LangGraph、checkpoint、长任务队列和 MCP server。

## 2026-06-09 P0 QA Evidence 注入与 SelfCheck 修复
### 目标

在不引入 LangGraph、不重构整体架构、不让 DeepSeek 替代 evidence builder 的前提下，修复 QA evidence 覆盖率不足问题。目标是将 evidence 覆盖率从 `50.00%` 提升到至少 `85.00%`，同时保持 command hallucination 为 `0`。

### 改动

- 新增 `backend/app/answer/evidence_builder.py`：
  - `build_repo_overview_evidence`
  - `build_core_modules_evidence`
  - `build_entrypoints_evidence`
  - `build_docs_recommendation_evidence`
  - `build_learning_path_evidence`
  - `build_issue_or_internal_task_evidence`
  - `build_development_workflow_evidence`
  - `build_setup_evidence`
- 扩展 `EvidenceItem`：
  - 增加 `source_path`、`title`、`snippet`、`reason`，保留原有字段兼容。
  - 新增 `SourceType.GRAPH` 和 `SourceType.COMMAND`。
- 扩展 `FinalAnswer`：
  - 增加 `evidence_graph`、`evidence_workflow`、`evidence_commands`、`evidence_internal_tasks` 和 `uncertainties`。
  - 保留 `evidence_docs`、`evidence_code`、`evidence_issues`。
- 修改 `CandidateAnswerGenerator`：
  - 对固定 QA 类型主动注入 RepositoryGraph、WorkerOutput 和命令证据，不再只依赖向量检索。
  - 针对 overview、core_modules、entrypoints、docs_recommendation、learning_path、beginner_tasks、development_workflow 生成结构化 evidence。
  - open issues 为 0 时，QA 的新手任务回答也会引用 internal first task evidence。
- 修改 `Evaluator`：
  - conclusion 非空但 evidence 为空时不通过。
  - 区分 `missing_evidence`、`missing_file_uncertainty`、`missing_command_uncertainty`、`hallucinated_file`、`hallucinated_command`、`hallucinated_issue`。
  - “未找到 CONTRIBUTING.md”归为缺失文件不确定性，不算文件幻觉。
  - “未找到 lint/format 命令”归为缺失命令不确定性，不算命令幻觉。
  - 修复 `package.json` 被误识别成 `package.js` 的路径正则问题。
  - 支持 `./scripts/x.py` 与 `scripts/x.py` 视为同一已知路径。
- 修改 Learning Path endpoint：
  - 每一步尽量绑定 README、命令、核心目录/文件、入口文件、测试、workflow、internal task evidence。
- 修改 `scripts/stress_test_repomentor.py`：
  - evidence 覆盖率统计扩展为 docs/code/issues/graph/workflow/commands/internal_tasks。
  - 按 QA 类型统计 overview、core_modules、entrypoints、docs_recommendation、learning_path、beginner_tasks、development_workflow 覆盖率。
  - 新增输出 `reports/evidence_coverage_breakdown.md`。
- 新增测试：
  - `backend/tests/test_evidence_builder.py`
  - `backend/tests/test_evaluator.py`
  - `backend/tests/test_stress_metrics.py`

### 验证

- 后端测试：

```powershell
python -m pytest backend\tests -q
```

结果：`38 passed`。

- 前端构建：

```powershell
cd frontend
& "C:\Users\Liaoke\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" node_modules/vite/bin/vite.js build
```

结果：Vite build 通过，转换 `1607` 个模块。

- Mock 压力测试：

```powershell
python scripts\stress_test_repomentor.py --base-url http://127.0.0.1:8000 --provider mock --concurrency 3 --output-dir reports --skip-large
```

最终结果：`PASS`。

### 最终指标

- 正常仓库 analyze 成功：`4 / 4`。
- 异常仓库可读错误：`4 / 4`。
- QA 成功率：`97.92%`。
- evidence 覆盖率：`100.00%`。
- command hallucination：`0`。
- SelfCheck 通过率：`79.17%`。
- SelfCheck 缺失率：`0.00%`。
- Issue fallback：`3 / 3`。
- API Key 泄露：未发现。

### Evidence 覆盖率分解

- overview：`100.00%`
- setup_run：`100.00%`
- core_modules：`100.00%`
- learning_path：`100.00%`
- development_workflow：`100.00%`
- beginner_tasks：`100.00%`
- entrypoints：`100.00%`
- docs_recommendation：`100.00%`

### 仍存在的问题

- SelfCheck 仍有部分 `passed=false`，但不再是 evidence 为空；主要集中在：
  - development workflow 中 lint/format 缺失时的风险降置信。
  - `vite-plugin-react` 中部分 npm 命令出现在文本里但没有进入 graph commands。
- 当前后端模型状态为 `provider_active=mock`，`api_key_configured=false`，因此未运行 DeepSeek 真模型验收。

### 下一步建议

- 可以进入 DeepSeek 小仓库验收，但应先在后端运行时显式配置 Key，并只选择 1-2 个小仓库，避免不必要消耗。
- 暂不建议进入 LangGraph 升级；当前确定性 evidence builder 和 SelfCheck 还可以继续产品化收尾。
## 2026-06-09 LangGraph 渐进迁移第一阶段

### 目标

在不删除 `LegacyOrchestrator`、不重写全部 Worker、不破坏现有 API 和用户页的前提下，新增可选 LangGraph 编排薄包装。默认仍使用 legacy；只有 `LANGGRAPH_ENABLED=true` 时才走 LangGraph。调试信息只进入 Debug Console，不出现在用户页。

### 改动

- 新增后端依赖声明：
  - `langgraph>=0.2.0`
  - `langchain-core>=0.2.0`
- 新增 LangGraph 配置项：
  - `LANGGRAPH_ENABLED=false`
  - `LANGGRAPH_CHECKPOINT_BACKEND=memory`
  - `LANGGRAPH_SQLITE_PATH=.repomentor_cache/langgraph_checkpoints.sqlite`
  - `LANGGRAPH_TRACE_ENABLED=true`
  - `LANGGRAPH_MAX_RETRIES=2`
- 新增 `backend/app/graphs/`：
  - `state.py`
  - `node_base.py`
  - `checkpoint.py`
  - `repo_analysis_graph.py`
  - `qa_graph.py`
  - `graph_orchestrator.py`
  - `graph_trace.py`
  - `graph_utils.py`
- 新增调度器 provider：
  - 默认返回 legacy。
  - flag 开启后返回 `GraphOrchestrator`。
  - 图执行失败时写入 fallback trace，并回退 legacy。
- 新增 API：
  - `GET /api/graph/status`
  - `GET /api/debug/graph/{thread_id}/state`
  - `GET /api/debug/graph/{thread_id}/trace`
  - `POST /api/debug/graph/{thread_id}/resume`
- 前端 Debug Console 新增：
  - `LangGraphDebugPanel.jsx`
  - graph status/state/trace/resume API client
  - 模型控制与 LangGraph 调试独立上方控制区
  - Agent Flow 支持 legacy/langgraph 两种模式
- 压力脚本新增：
  - `--orchestrator legacy|langgraph`
  - `/api/graph/status` preflight
  - graph debug state/trace endpoint 抽样
  - `reports/langgraph_comparison_report.md`
- 文档：
  - 新增 `docs/langgraph_migration.md`
  - README 增加 LangGraph Migration 小节
- 新增测试：
  - `test_langgraph_state.py`
  - `test_langgraph_repo_analysis.py`
  - `test_langgraph_qa.py`
  - `test_langgraph_fallback.py`
  - `test_langgraph_debug_api.py`

### 验证

```powershell
python -m compileall backend\app
python -m pytest backend\tests -q
& "C:\Users\Liaoke\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" node_modules/vite/bin/vite.js build
python -m py_compile scripts\stress_test_repomentor.py
python scripts\stress_test_repomentor.py --base-url http://127.0.0.1:8000 --provider mock --orchestrator legacy --concurrency 2 --output-dir reports --repo-list tests\fixtures\stress_repos_cached_fallback.json --skip-large
```

结果：

- 后端语法检查：通过。
- 后端测试：`44 passed`。
- 前端构建：通过，Vite 转换 `1608` 个模块。
- 压力脚本语法检查：通过。
- 轻量 stress：`PASS`。

### API 抽样

- `GET /api/health`：`{"status":"ok"}`
- `GET /api/graph/status`：
  - `langgraph_enabled=false`
  - `active_orchestrator=legacy`
  - `checkpoint_backend=memory`
  - `checkpoint_available=true`
  - `max_retries=2`
- `GET /api/debug/graph/analyze:missing/state`：
  - `found=false`
  - 返回结构正常。

### 浏览器验证

- 打开 `http://127.0.0.1:5173/debug/model`。
- Debug Console 显示：
  - 模型控制
  - LangGraph 调试
  - 启用状态
  - 当前调度器
  - checkpoint
  - thread id
  - 节点状态
  - 决策/重试/回退
  - 原始 State/Trace JSON
- 窄视口布局检查：
  - `modelGraphOverlap=false`
- 1280x900 桌面视口布局检查：
  - `modelGraphOverlap=false`
  - 模型控制与 LangGraph 调试并排显示。
- 用户页没有新增 LangGraph 信息。

### Stress 指标

- 后端实际 Orchestrator：`legacy`
- LangGraph Enabled：`false`
- analyze 成功：`3 / 3`
- QA 成功率：`97.22%`
- evidence 覆盖率：`100.00%`
- command hallucination：`0`
- SelfCheck 通过率：`80.56%`
- SelfCheck 缺失率：`0.00%`
- Issue fallback：`3 / 3`
- API Key 泄露检查：未发现真实 Key；唯一源码扫描命中是 `task-specific` 里的 `sk-specific` 字符串，不是密钥。

### 模型状态

- stress baseline 使用 mock 运行。
- stress 后已把本地运行时 provider 切回 DeepSeek。
- 切回时未写入 `.env`，未发送或回显明文 API Key。

### 仍需注意

- LangGraph 目前是渐进式薄包装，不是完整替换 legacy。
- 默认仍关闭 LangGraph。
- `POST /api/debug/graph/{thread_id}/resume` 当前用于恢复 checkpoint state 供调试查看，不负责继续执行长任务。
- 切换 legacy/langgraph 需要重启后端并设置 `LANGGRAPH_ENABLED`。

## 2026-06-09 LangGraph 8000/5173 实机验证与 QA Thread 修复

### 目标

按要求只使用本地标准端口：

- 后端：`http://127.0.0.1:8000`
- 前端：`http://127.0.0.1:5173`

继续验证 `LANGGRAPH_ENABLED=true` 下的真实 analyze、QA、checkpoint、trace 和前端 Debug Console 展示。

### 改动

- 停用临时验证端口 `8001`。
- 将 `8000` 后端以 LangGraph 模式启动：
  - `LANGGRAPH_ENABLED=true`
  - `LANGGRAPH_CHECKPOINT_BACKEND=sqlite`
- 修复 Debug Console 无法自动定位最新 QA graph thread 的问题：
  - `GraphOrchestrator.agent_flow_for_repo()` 新增 `latest_qa_thread_id`。
  - `App.jsx` 加载 debug artifacts 时优先用 `latest_qa_thread_id` 拉取 QA state/trace。
- 修复 `LangGraphDebugPanel` 在 QA graph 下误用 repo analysis 节点列表的问题：
  - QA thread 显示 `qa_graph` 节点。
  - repo analysis thread 才显示 analysis graph 节点。

### API 验证

- `GET /api/graph/status`：
  - `langgraph_enabled=true`
  - `checkpoint_backend=sqlite`
  - `checkpoint_available=true`
  - `active_orchestrator=langgraph`
- 使用 ASCII 临时小仓库 `C:\Temp\repomentor-lg-fixture` 验证：
  - `repo_id=ce55ab718308`
  - `status=done`
  - `files=6`
  - `worker_outputs=8`
  - `entrypoints=2`
- QA 验证：
  - `latest_qa_thread_id=qa:ce55ab718308:2ee33bf9-0727-45d1-a2d0-5837f6620662`
  - QA state found：`true`
  - 当前节点：`final_answer_node`
  - SelfCheck：`accept`
  - 命令：
    - `pip install -r requirements.txt`
    - `python scripts/run_demo.py`
    - `python -m pytest tests`

### 前端浏览器验证

- 打开 `http://127.0.0.1:5173/debug/ce55ab718308`。
- LangGraph 调试面板显示：
  - 启用状态：已启用
  - 当前调度器：langgraph
  - Checkpoint：sqlite / 可用
  - Thread ID：`qa:ce55ab718308:...`
  - Graph：`qa_graph`
  - 当前节点：`final_answer_node`
- QA 节点列表显示：
  - `init_qa_node`
  - `intent_router_node`
  - `retrieval_node`
  - `worker_context_node`
  - `answer_generator_node`
  - `evaluator_node`
  - `optimizer_node`
  - `final_answer_node`
- 验证结果：
  - `showsEnabled=true`
  - `showsQaThread=true`
  - `showsFinalNode=true`
  - `showsQaNodeList=true`
  - `stillShowsAnalysisNodesInQa=false`

### 回归验证

```powershell
python -m pytest backend\tests -q
& "C:\Users\Liaoke\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" node_modules/vite/bin/vite.js build
```

结果：

- 后端测试：`44 passed`
- 前端构建：通过，Vite 转换 `1608` 个模块。

### 当前运行状态

- `8000`：LangGraph 模式运行中。
- `5173`：前端 dev server 运行中。
- 代码默认值仍为 `LANGGRAPH_ENABLED=false`，当前只是本地运行时验证开启。

## 2026-06-09 在线部署交付准备

### 目标

- 准备可公网部署的交付版本。
- 前端支持 Vercel，后端支持 Render/Railway。
- 保留 Docker 本地一键运行。
- 不泄露 API Key，线上默认使用 Mock 模型。

### 改动

- 前端 API 地址统一为 `VITE_API_BASE_URL`，生产构建不写死本地后端。
- Debug Console 显示当前 `api_base`。
- 后端 CORS 改为读取 `BACKEND_CORS_ORIGINS`。
- 后端新增公开 Demo 基础保护：
  - `MAX_REPO_FILES`
  - `MAX_FILE_SIZE_KB`
  - `ANALYZE_TIMEOUT_SECONDS`
  - `ENABLE_PUBLIC_DEMO_GUARD`
- Parser 跳过敏感文件名、大文件，并限制扫描文件数。
- 新增部署配置：
  - `render.yaml`
  - `backend/Dockerfile`
  - `backend/start.sh`
  - `frontend/vercel.json`
  - `docker-compose.yml`
- 新增交付文档：
  - `docs/deployment_guide.md`
  - `docs/submission_urls.md`
  - `scripts/check_deployment.py`

### 验证

- 前端构建：

```powershell
& "C:\Users\Liaoke\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" node_modules/vite/bin/vite.js build
```

结果：通过，Vite 转换 `1619` 个模块。

- 后端测试：

```powershell
backend\.venv\Scripts\python.exe -m pytest
```

结果：`49 passed`。

- 生产 bundle 安全扫描：
  - 未发现 `localhost:8000`
  - 未发现 `127.0.0.1:8000`
  - 未发现旧变量 `VITE_API_BASE`
  - 未发现真实 API Key 形态
