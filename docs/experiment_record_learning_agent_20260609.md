# 2026-06-09 学习 Agent 产品化修复实验记录

## 目标

在不大改现有架构、不接真实 LLM 决策仓库事实的前提下，把 RepoMentor 从“仓库扫描 + QA”增强为“证据约束的仓库学习 Agent”。用户页展示学习者需要的产品化视图，调试页保留 raw JSON 和内部链路。

## 改动

- 新增后端确定性学习服务：`backend/app/services/learning_agent_service.py`。
- 新增 API：`backend/app/api/learning_agent.py`。
- 新增 LearningPathV2、ArchitectureTour、ModuleStudyCard、ProjectGlossary、BilingualDocView、LearningCheck、ChangeImpact、OnboardingDebt、TutorialDraft 等 schema。
- 将 `/api/repos/{repo_id}/issues/recommend` 切换为 Contribution Funnel 输出，open issue 为 0 时生成 internal first tasks，并明确标记“不是 GitHub Issue”。
- 新增用户页组件：
  - `LearningPathV2Panel.jsx`
  - `ArchitectureTourPanel.jsx`
  - `ModuleStudyCardsPanel.jsx`
  - `BilingualGlossaryPanel.jsx`
  - `LearningCheckPanel.jsx`
  - `ChangeImpactPanel.jsx`
  - `OnboardingDebtPanel.jsx`
  - `TutorialDraftPanel.jsx`
- 新增调试页组件：`LearningAgentRawPanel.jsx`，用于查看和导出学习 Agent 原始 JSON。
- 重写用户页高频面板中文文案：仓库概览、代码地图、开发流程、推荐任务、QA。
- 新增评估计划与脚本：
  - `docs/learning_agent_evaluation_plan.md`
  - `scripts/run_learning_eval.py`
  - `reports/learning_agent_eval_report.md`
- 新增测试：`backend/tests/test_learning_agent_service.py`。

## 事实约束

- 文件、命令、测试关系、文档关系、Issue、CI、CONTRIBUTING 状态均来自 RepositoryIntelligenceGraph 或 GitHub API。
- LLM 只能用于解释、翻译、润色和学习反馈，不决定仓库事实。
- 缺少 CONTRIBUTING、CI、Issue/PR 模板、中文文档时，显示缺失和维护者建议，不编造。
- 双语导读保留命令、路径、URL、代码块和符号；当前为确定性中文导读，不等同人工全文翻译。

## API 验证

- 后端端口：`http://127.0.0.1:8000`
- 前端端口：`http://127.0.0.1:5173`
- LangGraph 状态：
  - `langgraph_enabled=true`
  - `checkpoint_backend=sqlite`
  - `checkpoint_available=true`
  - `active_orchestrator=langgraph`
- 新本地 fixture：`C:\Temp\repomentor-learning-agent-fixture`
- 新 repo_id：`be338353cf5a`
- 分析结果：
  - files = 7
  - quality_commands = 3
  - test edges = 2
  - doc edges = 3
  - entrypoints 包含 `scripts/run_demo.py`
- 学习 Agent bundle：
  - LearningPathV2 steps = 8
  - ModuleStudyCard = 2
  - Contribution Funnel internal tasks = 5
  - OnboardingDebt risks = 7
  - Glossary terms = 8

## 回归验证

```powershell
python -m pytest backend\tests -q
& "C:\Users\Liaoke\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe" node_modules/vite/bin/vite.js build
python scripts\run_learning_eval.py --repo-id be338353cf5a --output reports\learning_agent_eval_report.md
```

结果：
- 后端测试：`47 passed`
- 前端构建：通过，Vite 转换 `1616` 个模块
- 学习评估报告：已生成 `reports/learning_agent_eval_report.md`

## 浏览器验证

- 用户页：`http://127.0.0.1:5173/repos/be338353cf5a`
  - 显示 `学习路径 V2`
  - 显示 8 个学习步骤
  - 显示架构导览、模块卡、双语术语、推荐任务、学习检查、改动演练、新手友好度、QA 标签
  - 不显示乱码标记
  - 不显示 Agent Flow、Worker Outputs、Data Layer、SelfCheck raw JSON
- 推荐任务：
  - open issue 为 0 时生成 internal first tasks
  - 明确显示“不是 GitHub Issue”
  - 显示 `source = internal_suggestion`
- 学习检查：
  - 提交学习者解释后返回“掌握度：高”
  - 返回证据来源：`README.md`、`scripts/run_demo.py`、`tests/test_demo_app.py`
- 改动演练：
  - 返回相关测试：`tests/test_demo_app.py`
  - 返回必须运行命令：`python -m pytest tests`
  - 返回必读文件和风险提示
- 调试页：`http://127.0.0.1:5173/debug/be338353cf5a?tab=model`
  - 显示模型控制、LangGraph 调试、智能体流程调试
  - 显示 `学习 Agent 原始 JSON`
  - raw JSON 包含 `learning_path_v2` 和 `onboarding_debt`
  - 布局重叠检查：`overlaps=[]`
  - 不显示乱码标记

## 当前结论

本次已经完成 P0 学习 Agent 产品化结构：学习路径 V2、架构导览、模块卡、internal first tasks、新手友好度、术语/双语导读、学习检查和改动演练。自动评估只能证明结构覆盖与证据约束已经增强，不能单独证明真实学习效果提升；真实效果仍需要后续 A/B/C 真人评测。
