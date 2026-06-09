import { Braces, Download } from "lucide-react";

export default function LearningAgentRawPanel({ bundle }) {
  const payload = bundle || null;

  function exportJson() {
    if (!payload) return;
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `repomentor-learning-agent-${payload.repo_id || "current"}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <section className="panel debugPanel rawLearningAgentPanel">
      <header className="panelHeader">
        <Braces size={17} />
        <h2>学习 Agent 原始 JSON</h2>
        <button className="miniButton" type="button" onClick={exportJson} disabled={!payload}>
          <Download size={14} />
          导出 JSON
        </button>
      </header>
      {payload ? (
        <pre>{JSON.stringify(payload, null, 2)}</pre>
      ) : (
        <p className="muted">暂无学习 Agent 调试数据。请先分析仓库或点击刷新调试数据。</p>
      )}
    </section>
  );
}
