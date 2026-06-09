import { BookOpenCheck, Download, FileCode2, FolderGit2, Languages, PlayCircle, TestTube2 } from "lucide-react";
import DesignBasisBadge from "../common/DesignBasisBadge.jsx";
import { DESIGN_BASIS } from "../common/designBasis.js";

export default function RepoOverviewPanel({ repoUrl, analysis, overview, graph, workflow }) {
  const merged = overview || analysis || {};
  const files = merged.files || graph?.files || [];
  const repoName = merged.repo_name || repoNameFromUrl(repoUrl) || analysis?.repo_id || "未分析仓库";
  const languages = merged.languages_list || Object.keys(merged.languages || graph?.languages || {}) || topLanguages(files);
  const coreDirs = merged.core_directories || graph?.core_directories || topDirectories(files);
  const entrypoints = (merged.entrypoints || graph?.entrypoints || analysis?.entrypoints || []).map(entrypointLabel).filter(Boolean);
  const setupCommands = firstNonEmpty(
    merged.setup_commands,
    graph?.commands?.setup,
    commandValues(workflow?.development_commands?.filter((command) => command.command_type === "setup"))
  ).map(normalizeCommand);
  const startCommands = firstNonEmpty(
    merged.start_commands,
    merged.run_commands,
    commandValues(workflow?.development_commands),
    graph?.commands?.run,
    analysis?.run_commands
  ).map(normalizeCommand).filter((command) => !isEvaluationCommand(command));
  const evaluationCommands = firstNonEmpty(
    merged.evaluation_commands,
    commandValues(workflow?.quality_commands?.filter((command) => isEvaluationCommand(command?.command))),
    graph?.commands?.run?.filter(isEvaluationCommand),
    analysis?.run_commands?.filter(isEvaluationCommand)
  ).map(normalizeCommand);
  const testCommands = firstNonEmpty(
    merged.test_commands,
    commandValues(workflow?.test_commands),
    graph?.commands?.test,
    analysis?.test_commands
  ).map(normalizeCommand);
  const description = merged.description || buildDescription(files, graph?.symbols || [], repoName);

  return (
    <section className="panel userOverview">
      <header className="panelHeader">
        <BookOpenCheck size={17} />
        <h2>仓库概览</h2>
      </header>
      <DesignBasisBadge {...DESIGN_BASIS.repoOverview} />
      <p className="overviewIntro">{description}</p>
      <div className="overviewSummary">
        <Metric icon={Languages} label="主要语言" value={languages.length ? languages.join(", ") : "未检测到主要语言"} />
        <Metric icon={FolderGit2} label="核心目录" value={coreDirs.length ? coreDirs.join(", ") : "未检测到核心目录"} />
        <Metric icon={FileCode2} label="入口文件" value={entrypoints.length ? entrypoints.slice(0, 3).join("；") : "未检测到入口文件"} />
        <Metric icon={Download} label="安装命令" value={setupCommands.length ? setupCommands.slice(0, 2).join("；") : "未检测到安装命令"} />
        <Metric icon={PlayCircle} label="启动命令" value={startCommands.length ? startCommands.slice(0, 2).join("；") : "未检测到启动命令"} />
        <Metric icon={FileCode2} label="评估/高级命令" value={evaluationCommands.length ? evaluationCommands.slice(0, 2).join("；") : "未检测到评估命令"} />
        <Metric icon={TestTube2} label="测试命令" value={testCommands.length ? testCommands.slice(0, 2).join("；") : "未检测到测试命令"} />
      </div>
    </section>
  );
}

function Metric({ icon: Icon, label, value }) {
  return (
    <div className="overviewMetric">
      <span><Icon size={14} /> {label}</span>
      <strong title={value}>{value}</strong>
    </div>
  );
}

function repoNameFromUrl(url) {
  const match = url?.match(/github\.com\/([^/\s]+)\/([^/\s#?]+)/i);
  return match ? `${match[1]}/${match[2].replace(/\.git$/, "")}` : "";
}

function commandValues(commands = []) {
  return commands.map((item) => normalizeCommand(typeof item === "string" ? item : item?.command)).filter(Boolean);
}

function normalizeCommand(value) {
  return String(value || "").replaceAll("\\", "/").trim().split(/\s+/).join(" ");
}

function isEvaluationCommand(command) {
  return /run_(academic_)?eval|run_local_validation|run_stress_test|stress_test|benchmark/i.test(normalizeCommand(command));
}

function entrypointLabel(item) {
  if (typeof item === "string") return item;
  return item?.path || "";
}

function firstNonEmpty(...lists) {
  return lists.find((list) => Array.isArray(list) && list.length > 0) || [];
}

function topLanguages(files) {
  const counts = new Map();
  for (const file of files) {
    if (!file.language || file.language === "unknown") continue;
    counts.set(file.language, (counts.get(file.language) || 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3).map(([language]) => language);
}

function topDirectories(files) {
  const counts = new Map();
  for (const file of files) {
    const root = file.path?.split(/[\\/]/)[0];
    if (!root || root.includes(".")) continue;
    counts.set(root, (counts.get(root) || 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5).map(([directory]) => directory);
}

function buildDescription(files, symbols, repoName) {
  if (!files.length) return "输入 GitHub 仓库链接后，RepoMentor 会生成面向新贡献者的学习入口。";
  return `${repoName} 已解析 ${files.length} 个文件和 ${symbols.length} 个符号，可从代码地图、学习路径和开发流程开始。`;
}
