import { Boxes, FileCode2, NotebookTabs, TestTube2 } from "lucide-react";
import DesignBasisBadge from "../common/DesignBasisBadge.jsx";
import { DESIGN_BASIS } from "../common/designBasis.js";

export default function ModuleStudyCardsPanel({ moduleCards }) {
  const cards = moduleCards || [];
  return (
    <section className="panel moduleCardsPanel">
      <header className="panelHeader">
        <Boxes size={17} />
        <h2>Module Study Card</h2>
        <span className="count">{cards.length}</span>
      </header>
      <DesignBasisBadge {...DESIGN_BASIS.moduleStudyCard} />
      {!cards.length ? (
        <p className="muted">分析仓库后，这里会按模块职责、依赖关系、测试边界和修改风险组织学习卡。</p>
      ) : (
        <div className="moduleCardGrid">
          {cards.map((card) => (
            <article className="moduleStudyCard" key={card.module_path}>
              <div className="moduleCardTitle">
                <span>{card.learning_order}</span>
                <strong>{card.module_path}</strong>
              </div>
              <p>{card.role_in_system}</p>
              <small>{card.why_it_exists}</small>
              <ChipBlock icon={FileCode2} title="关键符号" items={card.key_symbols} />
              <ChipBlock title="上游调用者" items={card.upstream_callers} code />
              <ChipBlock title="下游依赖" items={card.downstream_dependencies} code />
              <ChipBlock icon={TestTube2} title="相关测试" items={card.related_tests} code />
              <ChipBlock icon={NotebookTabs} title="相关文档" items={card.related_docs} code />
              <ChipBlock title="常见改动场景" items={card.common_change_scenarios} />
              <ChipBlock title="修改风险" items={card.risk_if_modified} />
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function ChipBlock({ icon: Icon, title, items, code = false }) {
  if (!items?.length) return null;
  return (
    <div className="factBlock">
      <strong>{Icon ? <Icon size={14} /> : null}{title}</strong>
      <div className={code ? "codeChipList" : "plainChipList"}>
        {items.slice(0, 8).map((item) => code ? <code key={item}>{item}</code> : <span key={item}>{item}</span>)}
      </div>
    </div>
  );
}
