import { GitBranch, Play, RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";

export default function LangGraphDebugPanel({
  status,
  analysisState,
  analysisTrace,
  qaState,
  qaTrace,
  agentFlow,
  busy,
  onResume
}) {
  const [message, setMessage] = useState("");
  const selected = useMemo(() => selectThread({ analysisState, analysisTrace, qaState, qaTrace, agentFlow }), [
    analysisState,
    analysisTrace,
    qaState,
    qaTrace,
    agentFlow
  ]);
  const events = selected.trace?.events || [];
  const state = selected.state?.state || {};
  const nodes = selected.graphName === "repo_analysis_graph" && agentFlow?.nodes?.length
    ? agentFlow.nodes
    : nodesFromTrace(events, status, selected.graphName);
  const decisions = events.filter((event) => ["decision", "retry", "fallback"].includes(event.event_type));
  const checkpointCount = events.filter((event) => event.event_type === "checkpoint").length;
  const enabled = Boolean(status?.langgraph_enabled);
  const active = status?.active_orchestrator || (enabled ? "langgraph" : "legacy");

  async function resume() {
    if (!selected.threadId || !onResume) return;
    setMessage("正在恢复 checkpoint...");
    try {
      const result = await onResume(selected.threadId);
      setMessage(result?.resumed ? "checkpoint 已恢复并刷新。" : "没有找到可恢复的 checkpoint。");
    } catch {
      setMessage("恢复失败，请检查后端调试接口。");
    }
  }

  return (
    <section className="panel debugPanel langGraphPanel">
      <header className="panelHeader">
        <GitBranch size={17} />
        <h2>LangGraph 调试</h2>
        <button className="miniButton" type="button" onClick={resume} disabled={busy || !selected.threadId}>
          <RotateCcw size={14} />
          恢复 checkpoint
        </button>
      </header>

      <div className="metricGrid langGraphMetrics">
        <Metric label="启用状态" value={enabled ? "已启用" : "未启用"} />
        <Metric label="当前调度器" value={active} />
        <Metric label="Checkpoint" value={`${status?.checkpoint_backend || "memory"} / ${status?.checkpoint_available ? "可用" : "未知"}`} />
        <Metric label="Thread ID" value={selected.threadId || "暂无"} />
        <Metric label="Graph" value={selected.graphName || "暂无"} />
        <Metric label="当前节点" value={state.current_node || agentFlow?.current_node || "暂无"} />
      </div>

      {status?.warning && <p className="modelWarning">{status.warning}</p>}
      {message && <p className="actionStatus" role="status">{message}</p>}

      <div className="langGraphColumns">
        <div>
          <h3>节点状态</h3>
          <ol className="flowList debugFlow langGraphFlow">
            {nodes.map((node) => (
              <li className={node.status === "completed" ? "isDone" : ""} key={node.node_name || node.name}>
                <Play size={13} />
                <span>{node.node_name || node.name}</span>
                <small>{node.status || "pending"}{node.elapsed_ms != null ? ` · ${node.elapsed_ms}ms` : ""}</small>
              </li>
            ))}
          </ol>
        </div>
        <div>
          <h3>决策 / 重试 / 回退</h3>
          {decisions.length ? (
            <ul className="debugEventList">
              {decisions.slice(-8).map((event) => (
                <li key={event.event_id || `${event.node_name}-${event.timestamp}`}>
                  <strong>{event.event_type}</strong>
                  <span>{event.node_name}</span>
                  <small>{event.output_summary || event.error || "无摘要"}</small>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">暂无 LangGraph 决策事件。</p>
          )}
          <div className="dataRows compactRows">
            <span>Trace 事件数</span><strong>{events.length}</strong>
            <span>Checkpoint 数</span><strong>{checkpointCount}</strong>
            <span>Retry 次数</span><strong>{state.retry_count || agentFlow?.retry_count || 0}</strong>
          </div>
        </div>
      </div>

      <details>
        <summary>原始 LangGraph State JSON</summary>
        <pre>{JSON.stringify(state, null, 2)}</pre>
      </details>
      <details>
        <summary>原始 LangGraph Trace JSON</summary>
        <pre>{JSON.stringify(selected.trace || {}, null, 2)}</pre>
      </details>
    </section>
  );
}

function selectThread({ analysisState, analysisTrace, qaState, qaTrace, agentFlow }) {
  if (qaState?.found || qaTrace?.events?.length) {
    return {
      state: qaState,
      trace: qaTrace,
      threadId: qaState?.thread_id || qaTrace?.thread_id || "",
      graphName: "qa_graph"
    };
  }
  return {
    state: analysisState,
    trace: analysisTrace,
    threadId: analysisState?.thread_id || analysisTrace?.thread_id || agentFlow?.thread_id || "",
    graphName: agentFlow?.graph_name || "repo_analysis_graph"
  };
}

function nodesFromStatus(status, graphName) {
  const graph = (status?.graphs || []).find((item) => item.name === graphName) || status?.graphs?.[0];
  return (graph?.nodes || []).map((node) => ({ node_name: node, status: "registered" }));
}

function nodesFromTrace(events, status, graphName) {
  const nodes = nodesFromStatus(status, graphName);
  const byName = new Map(nodes.map((node) => [node.node_name, { ...node, events: 0, elapsed_ms: null, error: "" }]));
  for (const event of events || []) {
    const nodeName = event.node_name;
    if (!nodeName || nodeName === "checkpoint") continue;
    if (!byName.has(nodeName)) byName.set(nodeName, { node_name: nodeName, status: "pending", events: 0, elapsed_ms: null, error: "" });
    const node = byName.get(nodeName);
    node.events += 1;
    if (event.event_type === "start") node.status = "running";
    if (["success", "checkpoint", "decision"].includes(event.event_type)) node.status = "completed";
    if (event.event_type === "retry") node.status = "retry";
    if (event.event_type === "error") {
      node.status = "failed";
      node.error = event.error || "";
    }
    if (event.elapsed_ms != null) node.elapsed_ms = event.elapsed_ms;
  }
  return Array.from(byName.values());
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong title={String(value)}>{value}</strong>
    </div>
  );
}
