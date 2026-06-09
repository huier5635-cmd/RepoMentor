import { FolderTree } from "lucide-react";
import { zhCommandType, zhEdgeType, zhField, zhSymbolType } from "../../utils/zh.js";

export default function RepositoryGraphDebugPanel({ graph }) {
  return (
    <section className="panel debugPanel">
      <header className="panelHeader">
        <FolderTree size={17} />
        <h2>仓库图谱调试</h2>
      </header>
      {!graph ? (
        <p className="muted">仓库图谱尚未加载。</p>
      ) : (
        <div className="graphDebugGrid">
          <GraphList title="files" items={(graph.files || []).map((item) => `${item.path} · file_type=${item.file_type}`)} />
          <GraphList title="entrypoints" items={(graph.entrypoints || graph.graph?.entrypoints || []).map(entrypointLabel)} />
          <GraphList title="symbols" items={(graph.symbols || []).map((item) => `${item.name} · ${zhSymbolType(item.symbol_type)} · ${item.file_path}:${item.line_start}`)} />
          <GraphList title="imports edges" items={(graph.imports || []).map(edgeLabel)} />
          <GraphList title="test edges" items={(graph.tests || []).map(edgeLabel)} />
          <GraphList title="doc edges" items={docEdges(graph).map(edgeLabel)} />
          <GraphList title="build commands" items={graph.commands?.build || []} />
          <GraphList title="quality commands" items={(graph.quality_commands || []).map((item) => `${zhCommandType(item.command_type)}：${item.command} · confidence=${item.confidence} · source=${item.source_file}`)} />
        </div>
      )}
    </section>
  );
}

function GraphList({ title, items }) {
  return (
    <article className="graphList">
      <h3>{zhField(title)}</h3>
      {items?.length ? (
        <ul>
          {items.slice(0, 20).map((item) => <li key={item}>{item}</li>)}
        </ul>
      ) : (
        <p className="muted">暂无</p>
      )}
    </article>
  );
}

function edgeLabel(edge) {
  const evidence = edge.evidence ? ` · evidence=${edge.evidence}` : "";
  return `${edge.source} -> ${edge.target} · ${zhEdgeType(edge.edge_type)} · confidence=${edge.confidence}${evidence}`;
}

function entrypointLabel(item) {
  if (typeof item === "string") return item;
  return `${item.path} · confidence=${item.confidence} · source=${item.source} · reason=${item.reason}`;
}

function docEdges(graph) {
  const edges = graph.edges || graph.graph?.edges || graph.raw_graph?.edges || [];
  return edges.filter((edge) => ["documents", "mentions"].includes(edge.edge_type));
}
