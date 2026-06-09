import { Database } from "lucide-react";
import { zhField, zhStatus, zhText } from "../../utils/zh.js";

export default function DataLayerDebugPanel({ graph, summary, memory }) {
  const snapshot = graph?.snapshot || graph?.api_raw_response?.snapshot || null;
  const backendSummary = graph?.graph_summary || summary || {};
  const docEdges = (graph?.edges || graph?.raw_graph?.edges || graph?.graph?.edges || []).filter((edge) => ["documents", "mentions"].includes(edge.edge_type));
  const graphSummary = {
    files: backendSummary.files ?? graph?.files?.length ?? 0,
    symbols: backendSummary.symbols ?? graph?.symbols?.length ?? graph?.graph?.symbols?.length ?? 0,
    imports: backendSummary.imports ?? graph?.imports?.length ?? graph?.graph?.imports?.length ?? 0,
    tests: backendSummary.tests ?? graph?.tests?.length ?? graph?.graph?.tests?.length ?? 0,
    docs: backendSummary.docs ?? backendSummary.doc_edges ?? docEdges.length,
    buildScripts: backendSummary.build_scripts ?? graph?.build_scripts?.length ?? graph?.graph?.build_scripts?.length ?? 0,
    developmentWorkflow: backendSummary.development_workflow ?? workflowStatus(graph),
    ciRules: backendSummary.ci_rules ?? graph?.ci_rules?.length ?? graph?.graph?.ci_rules?.length ?? 0,
    qualityCommands: backendSummary.quality_commands ?? graph?.quality_commands?.length ?? graph?.graph?.quality_commands?.length ?? 0
  };
  const index = graph?.index || {};

  return (
    <section className="panel debugPanel">
      <header className="panelHeader">
        <Database size={17} />
        <h2>数据层调试</h2>
      </header>
      <h3>仓库智能图谱</h3>
      <div className="metricGrid">
        {Object.entries(graphSummary).map(([label, value]) => (
          <Metric key={label} label={label} value={value} />
        ))}
      </div>
      <h3>混合检索索引</h3>
      <div className="dataRows">
        <span>{zhField("keyword chunks")}</span><strong>{index.keyword_index_count ?? summary?.keyword_index_count ?? 0}</strong>
        <span>{zhField("vector index status")}</span><strong>{zhStatus(index.vector_index_status ?? summary?.vector_index_status ?? "not available")}</strong>
        <span>{zhField("metadata filters")}</span><strong>{zhStatus(index.metadata_filter_status ?? summary?.metadata_filter_status ?? "not available")}</strong>
      </div>
      <h3>共享工作记忆</h3>
      <div className="dataRows">
        <span>{zhField("current task")}</span><strong>{zhText(memory?.current_task || "not available")}</strong>
        <span>{zhField("evidence count")}</span><strong>{memory?.retrieved_evidence?.length ?? 0}</strong>
        <span>{zhField("intermediate conclusions")}</span><strong>{memory?.intermediate_conclusions?.length ?? 0}</strong>
        <span>{zhField("unresolved uncertainties")}</span><strong>{memory?.unresolved_uncertainties?.length ?? 0}</strong>
      </div>
      {snapshot && (
        <>
          <h3>RepoSnapshot</h3>
          <div className="dataRows">
            <span>{zhField("repo_id")}</span><strong>{snapshot.repo_id}</strong>
            <span>{zhField("repo name")}</span><strong>{snapshot.owner}/{snapshot.name}</strong>
            <span>默认分支</span><strong>{snapshot.default_branch || "后端未返回该字段"}</strong>
            <span>本地路径</span><strong>{snapshot.local_path || "后端未返回该字段"}</strong>
            <span>{zhField("files")}</span><strong>{snapshot.files?.length ?? 0}</strong>
            <span>Key Files</span><strong>{snapshot.key_files?.length ?? 0}</strong>
            <span>Open Issues</span><strong>{snapshot.issues?.length ?? 0}</strong>
          </div>
        </>
      )}
      {graph?.api_raw_response && (
        <details>
          <summary>API raw response</summary>
          <pre>{JSON.stringify(graph.api_raw_response, null, 2)}</pre>
        </details>
      )}
    </section>
  );
}

function workflowStatus(graph) {
  if (!graph?.development_workflow && !graph?.graph?.development_workflow) return "missing";
  const guide = graph.development_workflow || graph.graph.development_workflow;
  const hasCommands = [
    "development_commands",
    "test_commands",
    "lint_commands",
    "format_commands",
    "type_check_commands",
    "build_commands"
  ].some((key) => guide?.[key]?.length);
  return hasCommands ? "ready" : "partial";
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{zhField(label)}</span>
      <strong>{zhStatus(value)}</strong>
    </div>
  );
}
