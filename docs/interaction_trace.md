# RepoMentor 完整交互轨迹说明

## 轨迹位置

- Codex 原始轨迹：`~/.codex/sessions`
- Claude Code 原始轨迹：`~/.claude/projects/`
- 项目侧整理文档：`docs/interaction_trace.md`

原始轨迹目录通常包含 prompt、工具调用、代码修改、运行日志和验证过程。提交前需要按要求脱敏，避免泄露 API Key、私人路径或个人信息。

## 项目关键阶段

### 阶段 1：MVP 可运行链路

- 建立 FastAPI 后端和 React 前端。
- 支持输入 GitHub 仓库 URL。
- 实现仓库抓取、本地缓存和 Repository Intelligence Graph。
- 初步实现仓库概览、学习路径、Issue 推荐和 QA。

### 阶段 2：用户页与调试页分离

- 将混合 Dashboard 拆为 User Dashboard 和 Debug Console。
- 用户页只展示仓库概览、代码地图、学习路径、开发流程、推荐任务、QA 和简化证据。
- 调试页展示 Agent Flow、Worker Outputs、Data Layer、Retrieval Trace、Shared Memory、SelfCheck、FinalAnswer JSON。

### 阶段 3：结构质量修复

- 修复入口文件识别，避免 `__init__.py` 被错误当作主流程入口。
- 增强 Test Worker，建立测试文件到源码的启发式映射。
- 增强 Docs Worker，建立 docs 到 code 的 documents/mentions 边。
- 对 quality commands 做规范化和去重。
- open issue 为 0 时生成 internal first tasks，并标记不是 GitHub Issue。

### 阶段 4：Evidence 与 SelfCheck

- 改进 setup_run 问答，让回答直接给出启动方式、demo 命令、测试命令、风险和证据来源。
- Shared Working Memory 合并 Worker evidence。
- SelfCheck 检查证据类型、命令来源和 missing_evidence。
- 修复 Development Workflow Worker 的规则分类。

### 阶段 5：模型模式与调试能力

- 增加 Mock / DeepSeek 模式切换。
- 用户页只显示当前模式与切换入口。
- 调试页显示 provider、model、base_url、连接测试和 fallback 原因。
- 增加 LangGraph 可选编排、checkpoint、trace 和 legacy fallback。

### 阶段 6：最终展示材料

- 整理 Demo 录屏脚本。
- 生成最终展示 PPT 和 PDF。
- 整理 speaker notes、submission checklist、testing summary 和 upgrade plan。

## 主要 Prompt 摘要

1. 将 Agent Flow、Data Layer、Worker Outputs 等内部信息从用户页移到调试页。
2. 前端文案统一中文，JSON 原始内容不翻译。
3. 修复入口文件、测试边、文档边、命令去重、Shared Memory evidence、Issue fallback 和文件类型识别。
4. 优化 setup_run 回答、SelfCheck、Development Workflow 分类和 Data Layer Summary。
5. 增加 DeepSeek/Mock 模型控制，并分离用户和调试视图。
6. 修复调试页面模型控制与智能体流程调试重叠。
7. 生成最终展示材料，满足可运行 Demo、系统展示和完整交互轨迹。

## 主要 Bug 与修复

| 问题 | 定位 | 修复 |
| --- | --- | --- |
| 用户页暴露内部 Agent Flow | 用户视图和调试视图混在一起 | 拆分 User Dashboard 和 Debug Console |
| 中文乱码 | 文案与终端编码混杂 | 前端显示文案统一中文，JSON 保留原始 |
| 入口文件错误 | `__init__.py` 优先级过高 | 优先 README/docs 运行命令、`__main__.py` 和常见入口 |
| 测试边不足 | 只依赖显式 import | 增加文件名、关键词、import 三类映射 |
| 文档边不足 | docs 未映射到 code | 增加路径、模块、函数、类名映射 |
| 命令重复 | Windows/Unix 路径未规范化 | normalized_command + command_type 去重 |
| Issue 为 0 时无任务 | 只依赖 GitHub issue | 生成 internal first tasks |
| SelfCheck 过宽松 | 只看 evidence 数量 | 增加证据类型约束和 missing_evidence |
| 调试按钮无反应 | 导出/复制未接完整 | 实现 JSON 导出和复制 |
| 调试布局重叠 | 面板密度过高 | 调整布局并验证重叠面积为 0 |

## 压力测试结果

本次最终展示采用的压力测试口径：

- QA 成功率：100%。
- evidence 覆盖率：50%，低于 85% 验收线。
- command hallucination：0。
- SelfCheck 通过率：25%。
- Issue fallback：3/3。
- 后端测试：20 passed。
- 前端 build：通过。

解释：

压力测试没有发现系统崩溃。失败点主要是 evidence 覆盖不足，说明回答链路可运行，但证据注入和 EvidenceBuilder 仍需加强。因此下一阶段的优先级不是继续堆功能，而是先补 EvidenceBuilder。

## 后续路线

1. P0：EvidenceBuilder 修复，提高 evidence coverage。
2. P1：DeepSeek 小仓库验收，对比 Mock 与真实模型输出。
3. P2：LangGraph 状态图升级，支持更完整 checkpoint、trace 和 resume。
4. P3：在线部署或 Docker 一键运行。
5. P4：多仓库评测与真实学习效果实验。
