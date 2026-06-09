import { CheckSquare, GitPullRequest, ShieldCheck, TerminalSquare } from "lucide-react";
import { zhCommandType, zhStatus } from "../../utils/zh.js";
import DesignBasisBadge from "../common/DesignBasisBadge.jsx";
import { DESIGN_BASIS } from "../common/designBasis.js";

export default function DevelopmentWorkflowPanel({ workflow }) {
  if (!workflow) {
    return (
      <section className="panel">
        <header className="panelHeader">
          <GitPullRequest size={17} />
          <h2>开发流程</h2>
        </header>
        <DesignBasisBadge {...DESIGN_BASIS.developmentWorkflow} />
        <p className="muted">分析仓库后，这里会提取本地开发流程、质量命令、PR 流程和 CI 规则。</p>
      </section>
    );
  }

  return (
    <section className="panel workflowPanel">
      <header className="panelHeader">
        <GitPullRequest size={17} />
        <h2>开发流程</h2>
      </header>
      <DesignBasisBadge {...DESIGN_BASIS.developmentWorkflow} />
      <p className="workflowConclusion">{workflow.conclusion}</p>

      <div className="workflowGrid">
        <WorkflowSection title="本地开发流程" items={workflow.setup_steps} />
        <CommandSection title="安装 / 启动" commands={workflow.development_commands} />
        <CommandSection title="测试命令" commands={workflow.test_commands} />
        <CommandSection title="lint 命令" commands={workflow.lint_commands} />
        <CommandSection title="format 命令" commands={workflow.format_commands} />
        <CommandSection title="type check 命令" commands={workflow.type_check_commands} />
        <CommandSection title="build 命令" commands={workflow.build_commands} />
        <RuleSection title="分支规范" rules={workflow.branch_rules} />
        <RuleSection title="commit 规范" rules={workflow.commit_rules} />
        <RuleSection title="代码规范" rules={workflow.code_style_rules} />
        <PRSection workflows={workflow.pull_request_rules} />
        <CISection rules={workflow.ci_rules} />
        <WorkflowSection title="新贡献者 checklist" items={workflow.new_contributor_checklist} icon={CheckSquare} />
        <WorkflowSection title="风险和不确定点" items={[...(workflow.risks || []), ...(workflow.uncertainties || [])]} icon={ShieldCheck} />
      </div>
    </section>
  );
}

function WorkflowSection({ title, items, icon: Icon = TerminalSquare }) {
  return (
    <article className="workflowBlock">
      <h3><Icon size={15} />{title}</h3>
      {items?.length ? (
        <ul>
          {items.map((item, index) => <li key={`${title}-${index}-${item}`}>{item}</li>)}
        </ul>
      ) : (
        <p className="muted">仓库中未找到明确说明。</p>
      )}
    </article>
  );
}

function CommandSection({ title, commands }) {
  const visibleCommands = dedupeCommands(commands || []);
  return (
    <article className="workflowBlock">
      <h3><TerminalSquare size={15} />{title}</h3>
      {visibleCommands.length ? (
        <div className="workflowCommands">
          {visibleCommands.map((command) => (
            <div className="workflowCommand" key={`${command.command_type}-${command.command}`}>
              <code>{command.command}</code>
              <span>证据来源：{command.sources.join("、")} · 置信度：{zhStatus(command.confidence)}</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">仓库中未找到明确命令。</p>
      )}
    </article>
  );
}

function RuleSection({ title, rules }) {
  return (
    <article className="workflowBlock">
      <h3><ShieldCheck size={15} />{title}</h3>
      {rules?.length ? (
        <ul>
          {rules.slice(0, 8).map((rule) => (
            <li key={`${rule.source_file}-${rule.description}`}>
              {rule.description}
              <span className="ruleSource">{rule.source_file} · {zhStatus(rule.confidence)}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">仓库中未找到明确规范；系统不会编造。</p>
      )}
    </article>
  );
}

function PRSection({ workflows }) {
  return (
    <article className="workflowBlock wide">
      <h3><GitPullRequest size={15} />PR 流程</h3>
      {workflows?.length ? workflows.map((workflow) => (
        <div key={workflow.source_file}>
          <strong>{workflow.source_file}</strong>
          <ul>
            {[...workflow.steps, ...workflow.checklist].slice(0, 12).map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
      )) : <p className="muted">仓库中未找到明确 PR 模板。</p>}
    </article>
  );
}

function CISection({ rules }) {
  return (
    <article className="workflowBlock wide">
      <h3><ShieldCheck size={15} />CI 检查</h3>
      {rules?.length ? rules.map((rule) => (
        <div className="ciRule" key={rule.workflow_file}>
          <strong>{rule.workflow_name || rule.workflow_file}</strong>
          <span>{rule.workflow_file}</span>
          <p>触发条件：{(rule.triggers || []).join(", ") || "未检测到触发条件"}</p>
          <div className="workflowCommands">
            {dedupeCommands(rule.commands || []).slice(0, 8).map((command) => (
              <div className="workflowCommand" key={`${rule.workflow_file}-${command.command}`}>
                <code>{command.command}</code>
                <span>{zhCommandType(command.command_type)} · 证据来源：{command.sources.join("、")}</span>
              </div>
            ))}
          </div>
        </div>
      )) : <p className="muted">仓库中未找到 GitHub Actions workflow。</p>}
    </article>
  );
}

function dedupeCommands(commands) {
  const rank = { low: 1, medium: 2, high: 3 };
  const byCommand = new Map();
  for (const command of commands) {
    if (!command?.command) continue;
    const normalizedCommand = normalizeCommand(command.command);
    const key = `${command.command_type || "unknown"}::${normalizedCommand}`;
    const sources = new Set(command.evidence_sources || []);
    if (command.source_file) sources.add(command.source_file);
    const existing = byCommand.get(key);
    if (!existing) {
      byCommand.set(key, {
        ...command,
        command: normalizedCommand,
        sources: [...sources].filter(Boolean)
      });
      continue;
    }
    existing.sources = [...new Set([...existing.sources, ...sources].filter(Boolean))];
    if ((rank[command.confidence] || 0) > (rank[existing.confidence] || 0)) {
      existing.confidence = command.confidence;
    }
  }
  return [...byCommand.values()];
}

function normalizeCommand(value) {
  return String(value || "").replaceAll("\\", "/").trim().split(/\s+/).join(" ");
}
