# RepoMentor 后续升级路线

## 近期优先级

1. 修复 EvidenceBuilder，提高 docs、code、tests、graph、workflow evidence 覆盖率。
2. 使用 DeepSeek 小仓库做低成本验收，检查回答质量与证据绑定。
3. 强化 SelfCheck 对命令、文件、Issue 和不确定性的分类。

## 中期方向

1. 将 Orchestrator-Workers 迁移到 LangGraph 状态图，但不在当前展示中声称已经完全完成。
2. 将 LearningPathV2、ArchitectureTour、Contribution Funnel 做成可复用学习层。
3. 增强多仓库缓存、批量评测和贡献任务推荐稳定性。

## 约束

所有仓库事实必须来自确定性图谱和证据层，模型只负责解释、翻译、润色和学习反馈。
