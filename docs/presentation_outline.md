# RepoMentor 最终展示 PPT 提纲

本提纲对应最终 PPT《RepoMentor_最终展示.pptx》，总页数控制在 10 页以内。

## 1. 项目标题与一句话定位

**RepoMentor：面向新贡献者的多智能体仓库学习助手**

一句话定位：输入一个 GitHub 仓库链接，RepoMentor 自动解析代码、文档、测试、开发流程和 Issue，生成有证据来源的学习路径、入门任务和问答结果。

## 2. 任务目标

RepoMentor 解决新贡献者进入陌生仓库时的五个问题：

- 快速理解仓库：文件、模块、入口、命令和依赖关系。
- 学习核心模块：把主流程、关键符号、测试和文档关联到一起。
- 理解开发流程：恢复安装、运行、测试、PR、CI、代码风格和不确定项。
- 推荐入门任务：GitHub open issue 为 0 时生成 internal first tasks。
- 降低学习成本：用 evidence-grounded answer 减少臆测和上下文切换。

## 3. 用户使用流程

输入 GitHub URL → 仓库解析 → 代码地图 → 学习路径 → 开发流程 → 推荐任务 → 证据问答。

展示重点：

- 用户只看到面向学习和贡献的产品化界面。
- 所有答案带证据来源。
- 可切换 Mock / DeepSeek 模型模式，但仓库事实仍由确定性图谱提供。

## 4. 系统整体架构

系统由五层组成：

- 前端：React 用户页与调试页。
- 后端：FastAPI API、Orchestrator、QA pipeline。
- 多 Worker：RepoGraph、Symbol、Dependency、Docs、Test、Issue、Development Workflow、Code Explanation。
- 数据层：Repository Intelligence Graph、Shared Working Memory、Hybrid Index。
- LLM 与 Evaluator：模型只做解释/润色，Evaluator 和 SelfCheck 检查证据覆盖。

## 5. Agent 工作流

工作流：

1. Orchestrator 接收仓库或问题。
2. Workers 并行/顺序产出结构化结果。
3. Shared Memory 合并 worker output 和 evidence。
4. Candidate Answer Generator 生成候选答案。
5. Evaluator 检查证据覆盖、命令幻觉和风险。
6. Optimizer 修正答案。
7. 返回 FinalAnswer JSON，并在用户页显示简化结果。

## 6. 用户页与调试页分离设计

用户页保留：

- 仓库概览
- 代码地图
- 学习路径
- 开发流程
- 推荐任务
- QA
- 简化证据

调试页保留：

- Agent Flow
- Worker Outputs
- Data Layer
- Retrieval Trace
- Shared Memory
- Evaluator / Optimizer
- FinalAnswer JSON
- 学习 Agent 原始 JSON
- 模型控制与 LangGraph 调试

## 7. Demo 录屏脚本

3–5 分钟脚本：

1. 输入 GitHub 仓库链接。
2. 展示仓库概览。
3. 展示代码地图。
4. 展示学习路径。
5. 展示开发流程。
6. 展示推荐任务。
7. 提问“这个项目怎么启动”。
8. 展示证据来源。
9. 切换调试控制台展示 Agent Flow、Data Layer、SelfCheck、FinalAnswer JSON。

## 8. 压力测试与迭代记录

关键验证结果：

- Smoke test：64 个文件、221 个符号、20 个文档、8 个 Worker。
- Test Worker：15 条测试边。
- Docs Worker：50 条文档边。
- Open issue 为 0 时生成 6 个 internal first tasks。
- Shared Memory evidence 覆盖 worker evidence。
- 压力测试曾暴露的 FAIL 主要来自 evidence 覆盖不足和结构映射不足，不是系统崩溃；后续通过 EvidenceBuilder、Docs/Test edge、SelfCheck 和命令去重修复。

## 9. 开发路线

已经完成：

- Evidence 修复：入口文件、测试边、文档边、命令去重、Shared Memory evidence。
- DeepSeek 接入：模型控制面板、Mock/DeepSeek 模式切换、Key 不回显。
- LangGraph：可选编排层、checkpoint、trace、fallback。
- 用户/调试视图分离。

下一阶段：

- EvidenceBuilder 覆盖更多 QA 类型。
- DeepSeek 真实回答效果评估。
- LangGraph 默认路径与可恢复执行。
- 部署展示：后端服务、前端静态站点、演示仓库缓存。

## 10. 提交材料清单

- 可运行 Demo：本地 8000 + 5173。
- PPT：`docs/RepoMentor_最终展示.pptx`。
- Demo 录屏脚本：`docs/demo_script.md`。
- PPT 提纲：`docs/presentation_outline.md`。
- 完整交互轨迹：`docs/interaction_trace.md`。
- 测试总结：`docs/testing_summary.md`。
- 升级计划：`docs/upgrade_plan.md`。
- 提交清单：`docs/submission_checklist.md`。
- README 的“如何运行 Demo”和“如何展示项目”。
