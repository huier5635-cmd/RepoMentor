import { Activity, Bug, Clock3, Database, GitBranch, Layers3 } from "lucide-react";
import { zhField, zhStatus, zhText } from "../../utils/zh.js";
import DesignBasisBadge from "../common/DesignBasisBadge.jsx";
import { DESIGN_BASIS } from "../common/designBasis.js";

export default function DebugHeader({ repoId, repoName, sessionId, currentTask, status, duration, workerCount, dataCount, outputCount, apiBaseUrl }) {
  return (
    <header className="debugConsoleHeader">
      <div>
        <h2><Bug size={18} /> 调试控制台</h2>
        <p>开发者专用视图，用于查看智能体流程、共享记忆、检索轨迹和原始输出。</p>
        <DesignBasisBadge {...DESIGN_BASIS.debugConsole} displayMode="inline" />
      </div>
      <div className="debugHeaderGrid">
        <Metric icon={GitBranch} label="repo_id" value={repoId || "not loaded"} />
        <Metric icon={Database} label="repo name" value={repoName || "后端未返回仓库名称"} />
        <Metric icon={Layers3} label="session_id" value={sessionId || "none"} />
        <Metric icon={Activity} label="current_task" value={currentTask || "not available"} />
        <Metric icon={Activity} label="status" value={status || "idle"} />
        <Metric icon={Clock3} label="duration" value={duration || "not measured"} />
        <Metric icon={Bug} label="workers" value={String(workerCount || 0)} />
        <Metric icon={Database} label="data" value={String(dataCount || 0)} />
        <Metric icon={Layers3} label="outputs" value={String(outputCount || 0)} />
        <Metric icon={Database} label="api_base" value={apiBaseUrl || "not configured"} />
      </div>
    </header>
  );
}

function Metric({ icon: Icon, label, value }) {
  return (
    <span className="debugMetric">
      <Icon size={14} />
      <em>{zhField(label)}</em>
      <strong title={value}>{zhStatus(zhText(value))}</strong>
    </span>
  );
}
