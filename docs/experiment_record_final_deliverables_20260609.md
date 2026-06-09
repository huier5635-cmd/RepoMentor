# 2026-06-09 最终展示材料整理实验记录

## 目标

按照任务书要求整理最终交付物，覆盖：

- 可运行 Demo
- 系统展示
- 完整交互轨迹

## 本次新增或更新

- 更新 `docs/presentation_outline.md`
- 更新 `docs/demo_script.md`
- 新增 `docs/interaction_trace.md`
- 新增 `docs/submission_checklist.md`
- 新增 `docs/testing_summary.md`
- 新增 `docs/upgrade_plan.md`
- 新增最终 PPT：`docs/RepoMentor_最终展示.pptx`
- 更新 README：
  - “如何运行 Demo”
  - “如何展示项目”

## 展示材料覆盖

- 项目定位：面向新贡献者的多智能体仓库学习助手。
- 任务目标：快速理解仓库、学习核心模块、理解开发流程、推荐入门任务、降低学习成本。
- 用户流程：输入 GitHub URL → 仓库解析 → 代码地图 → 学习路径 → 开发流程 → 推荐任务 → 证据问答。
- 系统架构：前端、后端、多 Worker、数据层、LLM、Evaluator。
- Agent 工作流：Orchestrator、Workers、Shared Memory、Evaluator、Optimizer。
- 用户页与调试页分离。
- Demo 录屏脚本。
- 压力测试与迭代记录。
- 开发路线：EvidenceBuilder、DeepSeek、LangGraph、部署展示。
- 提交材料清单。

## 验收说明

- PPT 页数控制在 10 页。
- 材料明确说明 evidence-grounded answer。
- 材料明确说明压力测试早期 FAIL 的原因是 evidence 覆盖不足，不是系统崩溃。
- 材料明确说明下一阶段为 EvidenceBuilder、DeepSeek、LangGraph 和部署展示。
- 交互轨迹位置记录为：
  - Codex：`~/.codex/sessions`
  - Claude Code：`~/.claude/projects/`
