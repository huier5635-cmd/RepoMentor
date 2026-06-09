# RepoMentor 学习 Agent 评估计划

## 目标

评估 RepoMentor 从“仓库扫描 + QA”升级为“证据约束的仓库学习 Agent”后，是否降低新贡献者理解仓库、跑通项目、选择第一项任务的成本。

## 对照组

- A 组：只使用 GitHub 页面、README 和原始文档。
- B 组：使用当前 RepoMentor 基础版，即仓库概览、代码地图、学习路径、开发流程、推荐任务和 QA。
- C 组：使用增强版 RepoMentor，即 LearningPathV2、ArchitectureTour、ModuleStudyCard、BilingualDocView/Glossary、Contribution Funnel、LearningCheck、Change Impact Rehearsal 和 OnboardingDebtReport。

## 固定任务

1. 找到项目目标，并用证据说明来源。
2. 跑通最小启动命令。
3. 解释主流程入口和关键模块。
4. 找到一个核心模块对应的测试。
5. 选择一个适合新贡献者的第一项任务。
6. 做一次改动前影响面演练。
7. 用中文解释一个 README 或架构文档片段，同时保留命令、路径、URL 和代码 token。

## 指标

- `time_to_first_successful_run`
- `time_to_correct_project_goal`
- `architecture_explanation_score`
- `module_test_mapping_accuracy`
- `first_task_selection_quality`
- `evidence_coverage`
- `hallucination_rate`
- `translation_fidelity_pass_rate`
- `self_reported_cognitive_load`
- `self_reported_confidence`
- `retention_followup_placeholder`

## 事实约束

- 文件、命令、测试关系、文档关系、Issue、CI 和 CONTRIBUTING 只能来自 RepositoryIntelligenceGraph 或 GitHub API。
- LLM 只能做解释、翻译、润色和学习反馈，不能决定仓库事实。
- 没有证据时必须显示缺失或不确定性，不能生成假文件、假命令、假 Issue 或假 CI。

## 评估方式

第一阶段使用脚本生成代理指标，检查 C 组是否提供更多可验证学习支架。第二阶段需要真人 A/B/C 测试，记录用时、正确率、认知负荷和信心变化。当前报告只能证明结构覆盖和证据覆盖，不单独证明真实学习效果提升。
