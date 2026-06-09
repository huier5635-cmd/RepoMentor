const WORKER_NAMES = {
  "Intent Router": "意图路由器",
  Orchestrator: "编排器",
  "Repo Graph Worker": "仓库图谱工作器",
  "Symbol Worker": "符号分析工作器",
  "Dependency Worker": "依赖分析工作器",
  "Docs Worker": "文档分析工作器",
  "Issue Worker": "议题分析工作器",
  "Test Worker": "测试分析工作器",
  "Code Explanation Worker": "代码解释工作器",
  "Development Workflow Worker": "开发流程工作器",
  "Candidate Answer Generator": "候选答案生成器",
  Evaluator: "评估器",
  Optimizer: "优化器",
  "Final Answer": "最终答案"
};

const STATUS = {
  success: "成功",
  partial: "部分完成",
  failed: "失败",
  loaded: "已加载",
  loading: "加载中",
  idle: "待命",
  done: "完成",
  ready: "已就绪",
  pending: "待生成",
  enabled: "已启用",
  "not available": "暂无数据",
  "not loaded": "未加载",
  missing: "缺失",
  none: "无",
  unknown: "未明确识别",
  "not measured": "未计时",
  "simple_similarity_fallback": "简单相似度回退",
  easy: "简单",
  medium: "中等",
  high: "高",
  low: "低",
  hard: "困难",
  beginner: "新手友好",
  repo_overview: "仓库概览",
  setup_run: "启动与运行",
  code_explanation: "代码解释",
  learning_path: "学习路径",
  issue_recommendation: "Issue 推荐",
  test_mapping: "测试映射",
  development_workflow: "开发流程",
  general_qa: "通用问答"
};

const FIELD_LABELS = {
  repo_id: "仓库 ID",
  "repo name": "仓库名称",
  session_id: "会话 ID",
  current_task: "当前任务",
  status: "状态",
  duration: "耗时",
  workers: "工作器",
  data: "数据",
  outputs: "输出",
  files: "文件",
  entrypoints: "入口文件",
  symbols: "符号",
  imports: "导入关系",
  "imports edges": "导入关系",
  "test edges": "测试关系",
  "doc edges": "文档关系",
  "build commands": "构建命令",
  "quality commands": "质量命令",
  tests: "测试",
  docs: "文档",
  buildScripts: "构建脚本",
  developmentWorkflow: "开发流程",
  ciRules: "CI 规则",
  qualityCommands: "质量命令",
  "keyword chunks": "关键词切片",
  "vector index status": "向量索引状态",
  "metadata filters": "元数据过滤器",
  "current task": "当前任务",
  "evidence count": "证据数量",
  "intermediate conclusions": "中间结论",
  "unresolved uncertainties": "未解决不确定点",
  intermediate_conclusions: "中间结论",
  unresolved_uncertainties: "未解决不确定点",
  query: "查询",
  route: "路由",
  "keyword results": "关键词结果",
  "vector results": "向量结果",
  "final evidence": "最终证据",
  task: "任务",
  findings: "发现",
  evidence: "证据",
  uncertainties: "不确定点",
  next_actions: "下一步动作",
  "raw output": "原始输出 JSON",
  "hallucination risks": "幻觉风险",
  "missing evidence": "缺失证据",
  conflicts: "冲突",
  "optimizer changes / decision trace": "优化器调整 / 决策轨迹",
  "SelfCheckReport.passed": "自检是否通过",
  "evidence coverage": "证据覆盖率",
  suggested_action: "建议动作",
  currentTask: "当前任务",
  user_question: "用户问题",
  retrieved_evidence: "检索证据",
  worker_outputs: "工作器输出",
  final_decision_trace: "最终决策轨迹"
};

const FILE_TYPES = {
  source: "源码",
  source_frontend: "前端页面",
  source_frontend_style: "样式",
  test: "测试",
  docs: "文档",
  docs_legal: "许可证",
  docs_reference: "参考文献",
  docs_static: "文档静态页",
  config: "配置",
  data: "数据",
  build: "构建",
  issue: "议题",
  unknown: "未明确识别"
};

const COMMAND_TYPES = {
  setup: "安装",
  dev: "开发启动",
  test: "测试",
  lint: "代码检查",
  format: "格式化",
  type_check: "类型检查",
  build: "构建",
  ci: "CI",
  unknown: "未明确识别"
};

const EDGE_TYPES = {
  imports: "导入",
  calls: "调用",
  tests: "测试",
  documents: "文档说明",
  mentions: "提及",
  builds: "构建",
  defines: "定义",
  configures: "配置"
};

const SYMBOL_TYPES = {
  function: "函数",
  class: "类",
  method: "方法",
  variable: "变量",
  constant: "常量",
  interface: "接口",
  unknown: "未明确识别"
};

const ACTIONS = {
  accept: "接受",
  retrieve_more: "继续检索",
  revise: "修订",
  lower_confidence: "降低置信度",
  refuse: "拒答"
};

const EXACT_TEXT = {
  analyze_repo: "仓库分析",
  waiting: "等待中",
  "classified or initialized": "已分类或已初始化",
  "worker plan executed": "工作器计划已执行",
  "no output yet": "暂无输出",
  "candidate output available": "候选输出可用",
  "self-check available when QA/workflow returns": "QA 或流程返回后可查看自检",
  "final answer optimization path available when QA returns": "QA 返回后可查看最终答案优化路径",
  "ready for output layer": "输出层已就绪",
  "No question in current session": "当前会话没有问题",
  "No worker outputs are available from the current repo/session yet.": "当前仓库或会话暂无工作器输出。",
  "Repository graph is not loaded yet.": "仓库图谱尚未加载。",
  "Dedicated retrieval-trace API is not available; showing evidence from current shared memory when present.": "后端暂未提供专用检索轨迹接口；这里会优先展示当前共享记忆中的证据。",
  "No shared memory loaded. Open /debug/session/:sessionId or run an analysis in this browser session.": "尚未加载共享记忆。请打开 /debug/session/:sessionId，或在当前浏览器会话中先运行一次分析。",
  "No SelfCheckReport is available yet.": "暂无自检报告。",
  "No final answer JSON is available yet. Ask a RepoMentor question or open a debug session that provides final-answer-json.": "暂无最终答案 JSON。请先提出一个 RepoMentor 问题，或打开包含最终答案的调试会话。",
  "Debug Console is for development and demos of technical internals. It exposes agent orchestration, worker outputs, shared memory and evaluator decisions; it is not intended for ordinary user onboarding.": "调试控制台用于开发调试和技术展示，会展示智能体编排、工作器输出、共享记忆和评估决策；它不面向普通新贡献者。",
  "answer has no EvidenceItem": "回答没有证据项",
  "conclusion is not evidence-backed": "结论缺少证据支撑",
  "format is mentioned but no format command evidence was found": "提到了格式化，但没有找到格式化命令证据",
  "Development Workflow Guide has no evidence": "开发流程指南缺少证据",
  "recommendation references a real GitHub issue": "推荐依据来自真实 GitHub 议题",
  "repository contains no readable files or clone failed": "仓库没有可读文件，或克隆失败",
  "no symbols found; repository may be non-code or parser coverage is limited": "未找到符号；仓库可能不是代码仓库，或解析器覆盖不足",
  "no documentation files found": "未找到文档文件",
  "no open issues fetched; repository may have no issues or GitHub API was unavailable": "未拉取到开放 issue；仓库可能没有 issue，或 GitHub API 暂不可用",
  "test-to-source mapping is heuristic until explicit coverage data is available": "在没有明确覆盖率数据前，测试到源码的映射是启发式结果",
  "code target is ambiguous or absent from parsed symbols/files": "代码目标不明确，或不存在于已解析的符号/文件中",
  "current graph did not contain a direct match for the requested code target": "当前图谱没有找到请求代码目标的直接匹配",
  "retrieve more docs/code chunks if evidence coverage is low": "如果证据覆盖不足，继续检索更多文档/代码切片",
  "run Symbol Worker": "运行符号分析工作器",
  "run Dependency Worker": "运行依赖分析工作器",
  "run Docs Worker": "运行文档分析工作器",
  "run Test Worker": "运行测试分析工作器",
  "use symbols for code explanation": "将符号用于代码解释",
  "use import graph for module explanation": "将导入图用于模块解释",
  "use docs chunks for setup and learning path answers": "将文档切片用于启动说明和学习路径回答",
  "combine labels, activity, scope, tests, docs and skill tags for recommendations": "结合标签、活跃度、范围、测试、文档和技能标签生成推荐",
  "use test edges for changed-file test mapping": "使用测试边生成变更文件的测试映射",
  "surface workflow guide in Development Workflow Panel": "在开发流程面板展示流程指南",
  "use guide for contribution-related QA": "将指南用于贡献相关问答",
  "scan files, classify file types, detect key files and commands": "扫描文件、分类文件类型、检测关键文件和命令",
  "extract deterministic symbols and defines edges": "提取确定性符号和定义边",
  "extract import edges and unresolved imports": "提取导入边和未解析导入",
  "parse README/docs/examples/contributing/changelog": "解析 README、文档、示例、贡献说明和变更日志",
  "fetch GitHub open issues and produce recommendation candidates": "拉取 GitHub 开放 issue 并生成推荐候选",
  "identify test files, test edges and test command candidates": "识别测试文件、测试边和测试命令候选",
  "explain module/function using graph, symbols, imports, docs and tests evidence": "基于图谱、符号、导入、文档和测试证据解释模块/函数",
  "extract development workflow, contribution rules, quality commands, PR rules and CI checks": "提取开发流程、贡献规则、质量命令、PR 规则和 CI 检查"
};

const KEY_LABELS = {
  worker_name: "工作器名称",
  task: "任务",
  status: "状态",
  findings: "发现",
  evidence: "证据",
  uncertainties: "不确定点",
  next_actions: "下一步动作",
  source_type: "来源类型",
  source_ref: "来源",
  file_path: "文件路径",
  issue_number: "议题编号",
  line_start: "起始行",
  line_end: "结束行",
  quote: "引用",
  supports_claim: "支持结论",
  confidence: "置信度",
  session_id: "会话 ID",
  current_task: "当前任务",
  user_question: "用户问题",
  retrieved_evidence: "检索证据",
  intermediate_conclusions: "中间结论",
  unresolved_uncertainties: "未解决不确定点",
  worker_outputs: "工作器输出",
  final_decision_trace: "最终决策轨迹",
  development_workflow_findings: "开发流程发现",
  quality_commands: "质量命令",
  contributing_rules: "贡献规则",
  ci_findings: "CI 发现",
  workflow_uncertainties: "流程不确定点",
  conclusion: "结论",
  evidence_docs: "文档证据",
  evidence_code: "代码证据",
  evidence_issues: "议题证据",
  steps: "步骤",
  risks: "风险",
  verifiable_commands: "可验证命令",
  self_check: "自检",
  trace_summary: "轨迹摘要",
  passed: "通过",
  evidence_coverage: "证据覆盖率",
  hallucination_risks: "幻觉风险",
  missing_evidence: "缺失证据",
  conflicts: "冲突",
  suggested_action: "建议动作"
};

export function zhWorkerName(value) {
  return WORKER_NAMES[value] || value || "未明确识别的工作器";
}

export function zhStatus(value) {
  if (value === 0) return "0";
  if (value === "" || value === null || value === undefined) return "暂无数据";
  if (typeof value === "boolean") return value ? "是" : "否";
  return STATUS[value] || ACTIONS[value] || value || "暂无数据";
}

export function zhField(value) {
  return FIELD_LABELS[value] || value;
}

export function zhFileType(value) {
  return FILE_TYPES[value] || zhStatus(value);
}

export function zhCommandType(value) {
  return COMMAND_TYPES[value] || zhStatus(value);
}

export function zhEdgeType(value) {
  return EDGE_TYPES[value] || zhStatus(value);
}

export function zhSymbolType(value) {
  return SYMBOL_TYPES[value] || zhStatus(value);
}

export function zhEvidenceGroup(value) {
  return { docs: "文档", code: "代码", issues: "议题" }[value] || value;
}

export function zhText(value) {
  if (value === null || value === undefined) return "";
  if (typeof value !== "string") return String(value);
  if (WORKER_NAMES[value]) return WORKER_NAMES[value];
  if (EXACT_TEXT[value]) return replaceEmbeddedTerms(EXACT_TEXT[value]);
  if (STATUS[value] || ACTIONS[value]) return zhStatus(value);

  const regexRules = [
    [/^(\w+) · (\d+) findings$/, (_, status, count) => `${zhStatus(status)} · ${count} 条发现`],
    [/^(\w+) · (\d+) 个 findings$/, (_, status, count) => `${zhStatus(status)} · ${count} 条发现`],
    [/^scanned (\d+) files$/, (_, count) => `已扫描 ${count} 个文件`],
    [/^detected (\d+) key files$/, (_, count) => `检测到 ${count} 个关键文件`],
    [/^detected (\d+) setup commands, (\d+) run commands and (\d+) test commands$/, (_, setup, run, test) => `检测到 ${setup} 条安装命令、${run} 条启动命令和 ${test} 条测试命令`],
    [/^detected (\d+) run commands and (\d+) test commands$/, (_, run, test) => `检测到 ${run} 条启动命令和 ${test} 条测试命令`],
    [/^detected (\d+) lint commands and (\d+) format commands$/, (_, lint, format) => `检测到 ${lint} 条代码检查命令和 ${format} 条格式化命令`],
    [/^extracted (\d+) symbols from (\d+) source files$/, (_, symbols, files) => `从 ${files} 个源码文件中提取 ${symbols} 个符号`],
    [/^resolved (\d+) local imports$/, (_, count) => `解析出 ${count} 条本地导入`],
    [/^marked (\d+) unresolved imports$/, (_, count) => `标记 ${count} 条未解析导入`],
    [/^found (\d+) docs files$/, (_, count) => `发现 ${count} 个文档文件`],
    [/^created (\d+) docs chunks$/, (_, count) => `创建 ${count} 个文档切片`],
    [/^fetched (\d+) open non-PR issues$/, (_, count) => `拉取到 ${count} 个开放的非 PR issue`],
    [/^found (\d+) test files$/, (_, count) => `发现 ${count} 个测试文件`],
    [/^created (\d+) test edges$/, (_, count) => `创建 ${count} 条测试边`],
    [/^found (\d+) workflow-related files$/, (_, count) => `发现 ${count} 个流程相关文件`],
    [/^extracted (\d+) quality commands$/, (_, count) => `提取 ${count} 条质量命令`],
    [/^extracted (\d+) contribution\/code-style rules$/, (_, count) => `提取 ${count} 条贡献/代码风格规则`],
    [/^found (\d+) CI workflow files$/, (_, count) => `发现 ${count} 个 CI workflow 文件`],
    [/^session started for repo (.+)$/, (_, repoId) => `会话已为仓库 ${repoId} 启动`],
    [/^intent router classified task as (.+)$/, (_, task) => `意图路由器将任务分类为 ${zhStatus(task)}`],
    [/^evaluator suggested (.+)$/, (_, action) => `评估器建议：${zhStatus(action)}`],
    [/^optimizer produced final answer$/, () => "优化器生成了最终答案"],
    [/^(.+): (success|partial|failed)$/, (_, worker, status) => `${zhWorkerName(worker)}：${zhStatus(status)}`],
    [/^labels=(.*); comments=(\d+); type=(.*); skills=(.*)$/, (_, labels, comments, type, skills) => `标签：${zhStatus(labels) || "无"}；评论数：${comments}；类型：${zhStatus(type)}；技能：${zhStatus(skills)}`]
  ];

  for (const [pattern, replacer] of regexRules) {
    if (pattern.test(value)) return replaceEmbeddedTerms(value.replace(pattern, replacer));
  }

  return replaceEmbeddedTerms(value);
}

export function zhList(items = []) {
  return items.map((item) => zhText(item));
}

export function localizeJson(value) {
  if (Array.isArray(value)) return value.map((item) => localizeJson(item));
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [KEY_LABELS[key] || key, localizeJson(item)])
    );
  }
  return typeof value === "string" ? zhText(value) : value;
}

function replaceEmbeddedTerms(value) {
  return value
    .replace(/\bdocs\b/g, "文档")
    .replace(/\bentrypoints\b/g, "入口文件")
    .replace(/\bsymbols\b/g, "符号")
    .replace(/\btests\b/g, "测试")
    .replace(/CONTRIBUTING \/ README/g, "贡献说明与 README 文档")
    .replace(/\blint \/ format\b/g, "代码检查和格式化")
    .replace(/\blint\b/g, "代码检查")
    .replace(/\bformat\b/g, "格式化")
    .replace(/\bCI workflow\b/g, "持续集成工作流")
    .replace(/\bworkflow\b/g, "工作流")
    .replace(/\bchecklist\b/g, "清单")
    .replace(/\bQA\b/g, "问答")
    .replace(/\bCI\b/g, "持续集成")
    .replace(/\bPR\b/g, "合并请求")
    .replace(/\bIssue\b/g, "议题")
    .replace(/\bissue\b/g, "议题")
    .replace(/\bissues\b/g, "议题");
}
