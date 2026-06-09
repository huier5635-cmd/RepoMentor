# 实验记录：用户页设计依据文案产品化

## 时间

2026-06-09

## 目标

将 RepoMentor 用户页和展示材料中的模块说明从“数据来源说明”升级为“设计依据 / 理论依据 / 架构依据”，让用户和评审能看到每个模块背后的方法论。

## 改动

- 新增 `frontend/src/components/common/DesignBasisBadge.jsx`。
- 新增 `frontend/src/components/common/designBasis.js` 统一维护设计依据文案。
- 在仓库概览、架构导览、学习路径、模块卡、双语术语/文档、开发流程、推荐任务、学习检查、改动演练、新手友好度、仓库问答中加入设计依据说明。
- 在调试控制台和 Agent 工作流中加入可观测性与 LangGraph/Orchestrator-Workers 架构依据。
- 将用户可见的旧称调整为“新手友好度”。
- 新增 `docs/design_basis.md` 与 `presentation/design_basis.md`。

## 验证计划

- 运行前端构建，确认新增组件和引用不会破坏 Vite build。
- 浏览器检查用户页是否显示“设计依据”，且用户页不再把 raw evidence 放在模块依据位置。
- 搜索确认当前用户可见文案统一使用“新手友好度”。
