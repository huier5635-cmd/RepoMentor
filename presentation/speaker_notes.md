## 第 1 页：RepoMentor：基于结构感知的 GitHub 仓库学习 Agent

这一页先明确项目定位：RepoMentor 不是普通问答工具，而是面向开源仓库学习的结构感知型 Agent。它的核心不是把 README 摘一遍，而是先理解仓库的文件、符号、测试、文档、命令和证据关系，再生成学习路径和贡献任务。右侧流程图说明输入是 GitHub 仓库，中间由 RepoMentor 做结构化理解，输出面向学习和贡献。

## 第 2 页：基于新贡献者学习瓶颈的任务目标

这一页说明我们为什么做这个系统。新贡献者面对陌生开源仓库时，真正困难不是找不到文本，而是信息分散、架构边界不清、贡献入口不明确，而且 AI 容易回答得很顺但没有证据。RepoMentor 的目标就是把这些痛点转成能力：结构聚合、术语保真、架构导览、任务推荐和证据约束。

## 第 3 页：基于 Orchestrator-Workers 的结构化 Agent 架构

这一页是总体架构图。前端分成用户页和调试页，后端通过 FastAPI 暴露业务接口和调试接口。Agent 层采用 Orchestrator 加多个 Worker 的结构，把图谱、符号、文档、测试、Issue 和开发流程拆成可验证的工作单元。数据层用 Repository Intelligence Graph、Hybrid Retrieval 和 Shared Working Memory 来承接证据。模型层支持 Mock 与 DeepSeek Provider 切换，LangGraph 在这里被明确写成后续状态图升级方向，不把它包装成已经完成的主链路。

## 第 4 页：基于 Repository Intelligence Graph 的结构优先路线

这一页强调 RepoMentor 与普通 RAG 的区别。普通 RAG 往往从文本片段开始，检索到什么就围绕什么回答，容易碎片化。RepoMentor 的路线是先恢复仓库结构：文件、符号、依赖、测试、文档、命令和 Issue，再把这些结构转成 evidence，最后生成解释、学习路径和问答。这个顺序让系统更像工程工具，而不是聊天摘要。

## 第 5 页：基于任务化学习路径与渐进式脚手架

这一页讲学习路径设计依据。RepoMentor 不把学习路径做成简单的读 README、读源码，而是拆成目标、操作、观察、自检四步。目标说明这一步要学会什么，操作给出文件和命令，观察告诉用户应该看到什么结果，自检要求用户能解释回去。底部的小例子体现从运行 demo 到追踪入口、定位模块、对应测试的渐进式脚手架。

## 第 6 页：基于 Explanation Window 的架构讲解

这一页说明架构解释不是固定粒度。RepoMentor 使用 Explanation Window 的思路，根据角色调整解释窗口。新手需要知道项目解决什么问题、主流程怎么走；贡献者需要模块职责、入口文件和测试关系；维护者更关心边界、风险点和缺失文档。这样同一份仓库结构可以服务不同学习深度。

## 第 7 页：基于 Bilingual Learning Layer 与术语锚点

这一页说明中文学习支持的边界。系统可以用中文降低理解门槛，但不能粗暴全文翻译，因为路径、命令、函数名、英文术语和 Markdown 结构必须保真。因此这里采用双语学习层：英文术语保留，中文解释辅助理解，同时绑定 source file、命令和代码路径。重点不是翻译得好听，而是让用户能回到真实仓库继续验证。

## 第 8 页：基于 Contribution Funnel 与 First Issue 推荐

这一页讲贡献任务推荐。RepoMentor 不应该一上来就让用户挑 Issue，而是先经过贡献漏斗：理解项目、跑通项目、理解核心模块、识别影响范围，然后再选择适合的入门任务。任务来源有两种：如果仓库有 open issue，就推荐真实 Issue；如果没有，就生成 internal first tasks。这些不是伪造 Issue，而是低风险、可验证的学习任务。

## 第 9 页：基于 Evidence-grounded Answer 与 SelfCheck 的可信问答

这一页说明可信问答机制。系统回答必须绑定 docs、code、tests、issues 和 graph evidence，而不是只给流畅文本。SelfCheck 会检查命令幻觉、文件幻觉、Issue 幻觉、缺失证据和不确定性。这里的原则是宁可告诉用户不确定，也不编造。指标卡保留了 command hallucination 为 0，同时说明 evidence coverage 仍是需要继续提升的工程指标。

## 第 10 页：基于压力测试的工程迭代路线

我们没有把压力测试当成形式化通过，而是把它作为工程验收。系统链路没有崩溃，QA 成功率 100%，命令幻觉为 0，但 evidence 覆盖率只有 50%，低于 85% 验收线。因此下一阶段不是盲目堆功能，而是先修 EvidenceBuilder。这里的 FAIL 不是系统崩溃，而是工程验收发现的优先级信号。
