import { FileCode2, FolderTree, Library, NotebookTabs, TestTube2 } from "lucide-react";
import { zhFileType } from "../../utils/zh.js";
import DesignBasisBadge from "../common/DesignBasisBadge.jsx";
import { DESIGN_BASIS } from "../common/designBasis.js";

export default function CodeMapPanel({ graph }) {
  const files = graph?.files || [];
  const symbols = graph?.symbols || [];
  const tests = graph?.tests || [];
  const docEdges = (graph?.raw_graph?.edges || graph?.edges || []).filter((edge) => ["documents", "mentions"].includes(edge.edge_type));
  const modules = summarizeModules(files, symbols, tests, docEdges);
  const displayFiles = visibleFiles(files);

  return (
    <section className="panel codeMapPanel">
      <header className="panelHeader">
        <FolderTree size={17} />
        <h2>架构导览</h2>
      </header>
      <DesignBasisBadge {...DESIGN_BASIS.architectureGraph} />
      {!files.length ? (
        <p className="muted">分析仓库后，这里会显示文件树、核心模块、测试关系和文档关系。</p>
      ) : (
        <div className="codeMapGrid">
          <article className="fileTreePreview">
            <h3><FileCode2 size={15} /> 文件树</h3>
            <div className="fileList">
              {displayFiles.map((file) => (
                <div className="fileRow" key={file.path}>
                  <FileCode2 size={14} />
                  <span title={file.path}>{file.path}</span>
                  <b>{zhFileType(file.file_type)}</b>
                </div>
              ))}
            </div>
          </article>
          <article className="moduleList">
            <h3><Library size={15} /> 核心模块</h3>
            {modules.map((module) => (
              <div className="moduleItem" key={module.name}>
                <strong>{module.name}</strong>
                <p>{module.role}</p>
                <span><TestTube2 size={13} /> 对应测试：{module.tests}</span>
                <span><NotebookTabs size={13} /> 对应文档：{module.docs}</span>
              </div>
            ))}
          </article>
        </div>
      )}
    </section>
  );
}

function summarizeModules(files, symbols, tests, docs) {
  const byDir = new Map();
  for (const file of files) {
    if (!isSourceFile(file)) continue;
    const directory = file.path?.split(/[\\/]/)[0] || "根目录";
    const current = byDir.get(directory) || { source: 0, languages: new Map(), symbols: 0 };
    current.source += 1;
    if (file.language && file.language !== "unknown") {
      current.languages.set(file.language, (current.languages.get(file.language) || 0) + 1);
    }
    byDir.set(directory, current);
  }
  for (const symbol of symbols) {
    const directory = symbol.file_path?.split(/[\\/]/)[0] || "根目录";
    const current = byDir.get(directory);
    if (current) current.symbols += 1;
  }
  return [...byDir.entries()]
    .sort((a, b) => b[1].source - a[1].source)
    .slice(0, 8)
    .map(([name, info]) => ({
      name,
      role: `${info.source} 个源码文件，${info.symbols} 个符号，主要语言 ${topLanguage(info.languages)}。`,
      tests: countEdgesForPrefix(tests, name, "测试关系"),
      docs: countEdgesForPrefix(docs, name, "文档关系")
    }));
}

function topLanguage(languages) {
  const [entry] = [...languages.entries()].sort((a, b) => b[1] - a[1]);
  return entry?.[0] || "未检测到主要语言";
}

function countEdgesForPrefix(edges, prefix, label) {
  const count = edges.filter((edge) => edge.source?.startsWith(prefix) || edge.target?.startsWith(prefix)).length;
  return count ? `${count} 条${label}` : `未检测到${label}`;
}

function isSourceFile(file) {
  return ["source", "source_frontend", "source_frontend_style"].includes(file.file_type);
}

function visibleFiles(files) {
  const recognized = files.filter((file) => file.file_type !== "unknown");
  const unknown = files.filter((file) => file.file_type === "unknown").slice(0, 8);
  return [...recognized, ...unknown].slice(0, 80);
}
