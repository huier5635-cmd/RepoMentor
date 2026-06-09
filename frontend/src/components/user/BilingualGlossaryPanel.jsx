import { Languages, MessageSquareText, ShieldCheck } from "lucide-react";
import DesignBasisBadge from "../common/DesignBasisBadge.jsx";
import { DESIGN_BASIS } from "../common/designBasis.js";

export default function BilingualGlossaryPanel({ glossary, bilingualDocs }) {
  const terms = glossary?.terms || bilingualDocs?.glossary?.terms || [];
  const chunks = bilingualDocs?.chunks || [];
  const warnings = glossary?.fidelity_warnings || bilingualDocs?.fidelity_warnings || [];
  return (
    <section className="panel bilingualPanel">
      <header className="panelHeader">
        <Languages size={17} />
        <h2>双语术语 / 双语文档</h2>
      </header>
      <div className="designBasisStack">
        <DesignBasisBadge {...DESIGN_BASIS.bilingualGlossary} />
        <DesignBasisBadge {...DESIGN_BASIS.bilingualDocs} />
      </div>
      <div className="guardrailBox">
        <MessageSquareText size={16} />
        <div>
          <strong>翻译规则</strong>
          <p>{(glossary?.translation_policy || []).join("；") || "文件路径、命令、URL、代码块和符号保持原样。"}</p>
        </div>
      </div>
      {warnings.length > 0 && (
        <div className="warningList">
          {warnings.map((item) => <span key={item}>{item}</span>)}
        </div>
      )}
      <div className="glossaryGrid">
        {terms.slice(0, 24).map((term) => (
          <article className="glossaryTerm" key={`${term.category}-${term.term}`}>
            <strong>{term.term}</strong>
            <span>{term.zh_translation}</span>
            <p>{term.explanation}</p>
          </article>
        ))}
      </div>
      <div className="bilingualChunks">
        {chunks.slice(0, 4).map((chunk) => (
          <article className="bilingualChunk" key={chunk.chunk_id}>
            <div className="bilingualChunkHeader">
              <h3>{chunk.source_file || chunk.source_path}</h3>
              <span><ShieldCheck size={13} /> {fidelityLabel(chunk.fidelity_status)} · {staleLabel(chunk.stale_status)}</span>
            </div>
            <div className="bilingualCompare">
              <div>
                <strong>原文</strong>
                <pre>{chunk.source_text}</pre>
              </div>
              <div>
                <strong>中文导读</strong>
                <pre>{chunk.translated_text || chunk.zh_text}</pre>
              </div>
            </div>
            <div className="translationMeta">
              <small>chunk hash：{chunk.source_chunk_hash || "未生成"}</small>
              <small>commit：{chunk.source_commit_hash || "未知"}</small>
              <small>目标语言：{chunk.target_lang || "zh-CN"}</small>
            </div>
            {chunk.glossary_terms?.length > 0 && (
              <div className="plainChipList">
                {chunk.glossary_terms.map((term) => <span key={term}>{term}</span>)}
              </div>
            )}
            {chunk.preserved_tokens?.length > 0 && (
              <div className="codeChipList">
                {chunk.preserved_tokens.slice(0, 12).map((token) => <code key={token}>{token}</code>)}
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}

function fidelityLabel(value) {
  if (value === "deterministic_preserve_tokens") return "已做保真检查";
  return value || "未标注保真状态";
}

function staleLabel(value) {
  if (value === "fresh") return "当前版本";
  if (value === "unknown_commit") return "commit 未知";
  return value || "版本状态未知";
}
