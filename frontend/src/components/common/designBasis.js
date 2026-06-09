export const DESIGN_BASIS = {
  repoOverview: {
    basis: "结构化仓库摘要 + 最小可运行入口",
    description: "先把项目目标、核心目录、入口、安装、启动和测试命令收敛到一屏，帮助新手建立第一张仓库心智地图。"
  },
  agentWorkflow: {
    basis: "LangGraph 状态图编排 + Orchestrator-Workers 模式",
    description: "将仓库分析、证据检索、回答生成、SelfCheck 和修正过程拆成可追踪节点，避免开放式多 Agent 群聊导致不可控。"
  },
  architectureGraph: {
    basis: "Repository Intelligence Graph 的结构优先路线",
    description: "先恢复文件、符号、导入、测试、文档和命令关系，再进行解释和问答，避免普通 RAG 只检索碎片文本。"
  },
  learningPath: {
    basis: "任务化重组模型 + 渐进式脚手架",
    description: "学习路径围绕目标、操作、观察和自检组织，不再只是让用户按顺序阅读文件清单。"
  },
  architectureTour: {
    basis: "explanation window 架构解释模型",
    description: "根据新手、贡献者、维护者三种角色调整解释窗口，同时覆盖问题域和技术域，帮助用户理解系统为什么这样设计。"
  },
  moduleStudyCard: {
    basis: "问题域 + 技术域双通道代码理解",
    description: "每张模块卡解释模块职责、存在原因、上游入口、下游依赖、相关测试、常见修改场景和修改风险。"
  },
  bilingualGlossary: {
    basis: "bilingual learning layer + 术语锚点",
    description: "为中文学习者提供中文解释，但保留英文术语、路径、命令、函数名和仓库原始标识符，避免脱离真实协作语境。"
  },
  bilingualDocs: {
    basis: "翻译保真检查 + canonical source 对齐",
    description: "保留英文原文作为 canonical source，中文解释用于降低理解门槛，同时检查代码块、链接、路径、命令和 Markdown 结构。"
  },
  developmentWorkflow: {
    basis: "贡献流程恢复 + 可验证命令分层",
    description: "把安装、启动、测试、PR、CI 和风险提示分开呈现，让新手能先跑通低风险路径，再进入贡献流程。"
  },
  learningCheck: {
    basis: "teach-back / 自我解释学习模型",
    description: "系统不是只给答案，而是要求学习者解释回去，并基于项目证据给反馈，从而检查是否真的理解。"
  },
  changeImpact: {
    basis: "Change Impact / Test Impact rehearsal",
    description: "在真实修改前，根据导入关系、测试映射和文档关系推演影响范围，帮助新手知道改哪里、看哪里、跑哪些测试。"
  },
  recommendation: {
    basis: "Contribution Funnel + First Issue 推荐研究",
    description: "如果有 open issue，则推荐适合新手的真实 issue；如果没有，则生成 internal first tasks，帮助用户先完成低风险入门任务。"
  },
  newcomerFriendliness: {
    basis: "Onboarding Readiness / Onboarding Debt 检查",
    description: "检查仓库是否提供贡献规范、模板、CI、测试入口、lint/format 说明、架构文档和双语支持，帮助维护者降低新人入门摩擦。"
  },
  qa: {
    basis: "EvidenceBuilder + SelfCheck 的证据约束问答",
    description: "回答必须能追溯到文档、代码、测试、Issue 或 Repository Graph；如果证据不足，系统必须明确说不确定。"
  },
  debugConsole: {
    basis: "observability / trace / replay 的 Agent 可观测性设计",
    description: "展示 Worker 输出、Data Layer、Shared Memory、SelfCheck、FinalAnswer JSON 和模型调用状态，用来证明系统不是静态展示。"
  }
};
