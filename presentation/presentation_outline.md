# RepoMentor_Final_Demo PPT 结构提纲

## 设计原则

- 页数：9 页。
- 场景：比赛/课程最终展示，配合 3–5 分钟录屏 Demo。
- 风格：浅灰/白底工程科技风，深蓝、深紫、青色为主色。
- 结构：每页一个核心结论，每页 3–5 个要点，尽量用图示表达。
- 重点：系统架构、Agent 工作流、Evidence 机制、用户/调试页分离、设计依据、压力测试与迭代路线。

## 第 1 页：封面

核心结论：RepoMentor 是结构感知型 GitHub 仓库学习 Agent。

内容：

- Web Demo
- Repository Intelligence Graph
- Evidence-grounded Agent
- 作者 / 时间

视觉：

- 左侧标题与定位。
- 右侧简洁系统图：GitHub URL → Graph → Agent → User/Demo。

## 第 2 页：问题背景与任务目标

核心结论：新贡献者的难点不是没有信息，而是缺少可信阅读路径。

左右对照：

- 痛点：文件多、入口不清、命令分散、Issue 不适合新人、回答容易幻觉。
- RepoMentor 能力：目标/架构、核心模块、开发流程、入门任务、学习成本降低。

## 第 3 页：用户使用流程

核心结论：用户只需要输入一个 GitHub 仓库链接。

流程：

GitHub URL → 仓库解析 → 代码地图 → 学习路径 → 开发流程 → 推荐任务 → 证据问答。

视觉：

- 横向流程图，每一步一个统一风格图标和一句短说明。

## 第 4 页：系统整体架构

核心结论：系统采用前后端分离 + 多 Worker Agent 架构。

分层：

- Frontend：User Dashboard、Debug Console。
- Backend API：FastAPI、REST API、Debug API。
- Agent Layer：Orchestrator、Workers、Evaluator / Optimizer。
- Data Layer：Repository Intelligence Graph、Hybrid Retrieval Index、Shared Working Memory、Evidence Store。
- External：GitHub API、DeepSeek / Mock Provider。

架构依据：

- LangGraph 状态图编排 + Orchestrator-Workers。
- Repository Intelligence Graph 先恢复结构事实，再让 Agent 解释和重组。

## 第 5 页：核心设计亮点

核心结论：RepoMentor 不是普通 RAG 聊天框。

四张卡片：

- 结构优先：先恢复 files / symbols / docs / tests / commands。
- 学习模型：任务化学习路径、渐进式脚手架、teach-back、自我解释。
- 证据约束：回答绑定 README、代码、测试、Issue 或 graph evidence。
- 可观测调试：用户页负责学习，调试页负责验证。

## 第 6 页：Demo 页面展示

核心结论：用户页聚焦学习，调试页暴露真实执行轨迹。

左侧：

- 用户页标注截图。
- 仓库概览、学习路径、开发流程、推荐任务、QA。
- 标注“设计依据”：学习路径、Contribution Funnel、新手友好度、EvidenceBuilder。

右侧：

- 调试页标注截图。
- Agent Flow、Worker Outputs、Data Layer、SelfCheck、FinalAnswer JSON。
- 标注“数据证据与执行轨迹”：evidence、trace、raw JSON。

## 第 7 页：压力测试与问题定位

核心结论：压力测试发现的瓶颈是 evidence 覆盖，而不是系统崩溃。

指标：

- QA 成功率：100%。
- evidence 覆盖率：50%，低于 85% 验收线。
- command hallucination：0。
- SelfCheck 通过率：25%。
- Issue fallback：3/3。
- 后端测试：20 passed。
- 前端 build：通过。

结论：

- 系统链路稳定。
- 下一步不是继续堆功能，而是先补 EvidenceBuilder。

## 第 8 页：开发路线与迭代计划

核心结论：从可运行 Demo 到可信仓库学习 Agent。

时间线：

1. MVP：仓库解析 + 用户页 + 调试页。
2. 压力测试：发现 evidence 覆盖不足。
3. P0：EvidenceBuilder 修复。
4. P1：DeepSeek 小仓库验收。
5. P2：LangGraph 状态图升级。
6. P3：在线部署 + 多仓库评测。

## 第 9 页：提交材料与展示方式

核心结论：最终提交由 Demo、录屏讲解和完整交互轨迹组成。

内容：

- 可运行 Demo：在线部署或 Docker 一键运行；当前本地 Demo 使用 8000/5173。
- 系统展示：PPT 不超过 10 页，3–5 分钟录屏 Demo。
- 完整交互轨迹：Codex、Claude Code、docs/interaction_trace.md。
- 项目文档：README、testing_summary、upgrade_plan。
- 设计依据文档：docs/design_basis.md、presentation/design_basis.md。
