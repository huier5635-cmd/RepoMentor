import { GitCompareArrows, Search } from "lucide-react";
import { useState } from "react";
import DesignBasisBadge from "../common/DesignBasisBadge.jsx";
import { DESIGN_BASIS } from "../common/designBasis.js";

export default function ChangeImpactPanel({ repoReady, busy, result, onSubmit, graph }) {
  const defaultTarget = firstTarget(graph);
  const [filePath, setFilePath] = useState(defaultTarget);

  async function submit(event) {
    event.preventDefault();
    await onSubmit({ file_path: filePath, symbol: "" });
  }

  return (
    <section className="panel changeImpactPanel">
      <header className="panelHeader">
        <GitCompareArrows size={17} />
        <h2>改动影响演练</h2>
      </header>
      <DesignBasisBadge {...DESIGN_BASIS.changeImpact} />
      <form className="inlineForm" onSubmit={submit}>
        <input
          value={filePath}
          onChange={(event) => setFilePath(event.target.value)}
          disabled={!repoReady || busy}
          placeholder="输入文件路径，例如 src/app.py"
        />
        <button className="miniButton" disabled={!repoReady || busy}>
          <Search size={14} />
          分析影响面
        </button>
      </form>
      {result ? (
        <div className="impactGrid">
          <ImpactBlock title="可能影响的模块" items={result.likely_affected_modules} code />
          <ImpactBlock title="可能影响的测试" items={result.likely_affected_tests} code />
          <ImpactBlock title="修改前必读" items={result.must_read_before_editing} code />
          <ImpactBlock title="必须运行的命令" items={result.must_run_commands} code />
          <ImpactBlock title="需要复查的文档" items={result.documentation_to_recheck} code />
          <ImpactBlock title="风险提示" items={result.risk_notes} />
        </div>
      ) : (
        <p className="muted">选择一个文件或符号，RepoMentor 会基于 import/test/docs edges 做低风险改动前演练。</p>
      )}
    </section>
  );
}

function ImpactBlock({ title, items, code = false }) {
  return (
    <article className="workflowBlock">
      <h3>{title}</h3>
      {items?.length ? (
        <div className={code ? "codeChipList" : "plainChipList"}>
          {items.map((item) => code ? <code key={item}>{item}</code> : <span key={item}>{item}</span>)}
        </div>
      ) : (
        <p className="muted">未发现明确关系。</p>
      )}
    </article>
  );
}

function firstTarget(graph) {
  const entry = graph?.entrypoints?.find((item) => item?.path && !item.path.endsWith("__init__.py"));
  if (entry?.path) return entry.path;
  const source = graph?.files?.find((file) => String(file.file_type || "").startsWith("source") && !file.path.endsWith("__init__.py"));
  return source?.path || "";
}
