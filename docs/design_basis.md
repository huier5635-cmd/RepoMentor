# RepoMentor 展示 PPT 设计依据

## 定位

本 PPT 面向项目评审，目标不是演示点击路径，而是说明 RepoMentor 的系统设计依据、架构亮点和工程迭代过程。

## 叙事主线

1. 从新贡献者真实学习瓶颈出发。
2. 说明为什么选择 Repository Intelligence Graph 与 evidence-grounded workflow。
3. 展示前端、后端、Agent、数据层和模型层如何协同。
4. 解释 LearningPathV2、Explanation Window、Bilingual Learning Layer、Contribution Funnel、SelfCheck 的方法论依据。
5. 用压力测试说明当前工程边界和下一阶段 EvidenceBuilder 优先级。

## 视觉系统

- 背景：白底 / 浅灰底。
- 主色：深蓝、青蓝。
- 风险与 FAIL：低饱和橙色。
- 通过指标：绿色。
- 字体：中文优先 Microsoft YaHei / DengXian，英文优先 Aptos / Calibri。
- 版式：每页一个核心观点，一个主视觉对象，最多 3-5 个重点。

## 真实性约束

- 不把 LangGraph 写成当前已完整完成。
- 不把 DeepSeek 写成所有回答来源，只写支持 Mock / DeepSeek Provider 切换。
- 不隐藏压力测试暴露的 evidence 覆盖率不足。
- 不加入 demo 操作流程页。
