import { Bot, CheckCircle2, Circle, Loader2 } from "lucide-react";
import { zhText, zhWorkerName } from "../../utils/zh.js";
import DesignBasisBadge from "../common/DesignBasisBadge.jsx";
import { DESIGN_BASIS } from "../common/designBasis.js";

const WORKERS = [
  "Repo Graph Worker",
  "Symbol Worker",
  "Dependency Worker",
  "Docs Worker",
  "Issue Worker",
  "Test Worker",
  "Code Explanation Worker",
  "Development Workflow Worker"
];

export default function AgentFlowDebugPanel({ userQuestion, agentFlow, workerOutputs, busy }) {
  const outputs = workerOutputs || [];
  const outputByName = new Map(outputs.map((item) => [item.worker_name, item]));
  const graphNodes = agentFlow?.mode === "langgraph" ? agentFlow.nodes || [] : [];
  const generated = outputs.length > 0 || graphNodes.length > 0;

  return (
    <section className="panel debugPanel">
      <header className="panelHeader">
        <Bot size={17} />
        <h2>Agent 工作流</h2>
      </header>
      <DesignBasisBadge {...DESIGN_BASIS.agentWorkflow} />
      <div className="debugField">
        <span>用户问题</span>
        <strong>{zhText(userQuestion || "No question in current session")}</strong>
      </div>
      <div className="debugField">
        <span>编排模式</span>
        <strong>{agentFlow?.mode === "langgraph" ? `LangGraph · ${agentFlow.thread_id || ""}` : "Legacy Orchestrator"}</strong>
      </div>
      <ol className="flowList debugFlow">
        {graphNodes.length ? (
          graphNodes.map((node) => (
            <FlowStep
              key={node.node_name}
              name={node.node_name}
              active={node.status === "completed"}
              busy={busy && node.status === "running"}
              detail={`${node.status || "pending"}${node.events ? ` · ${node.events} events` : ""}`}
            />
          ))
        ) : (
          <>
            <FlowStep name="Intent Router" active={generated} busy={busy && !generated} detail={generated ? "classified or initialized" : "waiting"} />
            <FlowStep name="Orchestrator" active={generated} busy={busy && !generated} detail={generated ? "worker plan executed" : "waiting"} />
            {WORKERS.map((name) => {
              const output = outputByName.get(name);
              return (
                <FlowStep
                  key={name}
                  name={name}
                  active={Boolean(output)}
                  busy={busy && !output}
                  detail={output ? `${output.status} · ${output.findings?.length || 0} findings` : "no output yet"}
                />
              );
            })}
            <FlowStep name="Candidate Answer Generator" active={generated} detail={generated ? "candidate output available" : "waiting"} />
            <FlowStep name="Evaluator" active={generated} detail={generated ? "self-check available when QA/workflow returns" : "waiting"} />
            <FlowStep name="Optimizer" active={generated} detail={generated ? "final answer optimization path available when QA returns" : "waiting"} />
            <FlowStep name="Final Answer" active={generated} detail={generated ? "ready for output layer" : "waiting"} />
          </>
        )}
      </ol>
    </section>
  );
}

function FlowStep({ name, active, busy, detail }) {
  return (
    <li className={active ? "isDone" : ""}>
      {busy ? <Loader2 className="spin" size={14} /> : active ? <CheckCircle2 size={14} /> : <Circle size={14} />}
      <span>{zhWorkerName(name)}</span>
      <small>{zhText(detail)}</small>
    </li>
  );
}
