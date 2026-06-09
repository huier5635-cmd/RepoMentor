import { ArrowLeft, AlertCircle, RefreshCw } from "lucide-react";
import { useRef, useState } from "react";
import AgentFlowDebugPanel from "../components/debug/AgentFlowDebugPanel.jsx";
import DataLayerDebugPanel from "../components/debug/DataLayerDebugPanel.jsx";
import DebugHeader from "../components/debug/DebugHeader.jsx";
import EvaluatorOptimizerPanel from "../components/debug/EvaluatorOptimizerPanel.jsx";
import FinalAnswerJsonPanel from "../components/debug/FinalAnswerJsonPanel.jsx";
import LangGraphDebugPanel from "../components/debug/LangGraphDebugPanel.jsx";
import LearningAgentDebugSummaryPanel from "../components/debug/LearningAgentDebugSummaryPanel.jsx";
import LearningAgentRawPanel from "../components/debug/LearningAgentRawPanel.jsx";
import ModelControlDebugPanel from "../components/debug/ModelControlDebugPanel.jsx";
import RepositoryGraphDebugPanel from "../components/debug/RepositoryGraphDebugPanel.jsx";
import RetrievalTracePanel from "../components/debug/RetrievalTracePanel.jsx";
import SharedMemoryPanel from "../components/debug/SharedMemoryPanel.jsx";
import TraceExportPanel from "../components/debug/TraceExportPanel.jsx";
import WorkerOutputsDebugPanel from "../components/debug/WorkerOutputsDebugPanel.jsx";
import { getApiBaseUrl } from "../api/client.js";

export default function DebugConsole({
  repoUrl,
  repoId,
  sessionId,
  debugTab,
  analysis,
  overview,
  graph,
  finalAnswer,
  memoryTrace,
  debugData,
  modelStatus,
  modelBusy,
  busy,
  error,
  onRefreshModel,
  onConfigureModel,
  onTestModel,
  onRefresh,
  onResumeGraph,
  onNavigate
}) {
  const [refreshMessage, setRefreshMessage] = useState("");
  const refreshTimer = useRef(null);
  const workerOutputs = debugData.workerOutputs || memoryTrace?.worker_outputs || analysis?.worker_outputs || [];
  const repoName = debugData.repoName || overview?.repo_name || analysis?.repo_name || graph?.repo_name || repoNameFromUrl(repoUrl);
  const dataCount = graph?.files?.length || analysis?.graph_summary?.files || 0;
  const tracePayload = {
    repo_id: repoId,
    session_id: sessionId,
    memory: memoryTrace,
    final_answer: debugData.finalAnswerJson || finalAnswer,
    retrieval_trace: debugData.retrievalTrace,
    learning_agent: debugData.learningAgentBundle
  };

  async function handleRefresh() {
    showRefreshMessage("正在刷新调试数据...");
    try {
      await onRefresh();
      showRefreshMessage(`已刷新调试数据：${new Date().toLocaleTimeString()}`);
    } catch {
      showRefreshMessage("刷新失败，请查看页面错误提示或后端服务状态。");
    }
  }

  function showRefreshMessage(message) {
    setRefreshMessage(message);
    window.clearTimeout(refreshTimer.current);
    refreshTimer.current = window.setTimeout(() => setRefreshMessage(""), 3200);
  }

  return (
    <section className="pageStack debugConsole">
      <div className="debugNav">
        <button className="miniButton" type="button" onClick={() => onNavigate(repoId ? `/repos/${repoId}` : "/")}>
          <ArrowLeft size={14} />
          返回用户页面
        </button>
        <button className="miniButton" type="button" onClick={handleRefresh} disabled={busy}>
          <RefreshCw size={14} />
          刷新调试数据
        </button>
      </div>
      {refreshMessage && <p className="actionStatus" role="status">{refreshMessage}</p>}

      {error && (
        <div className="errorBar">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <DebugHeader
        repoId={repoId}
        repoName={repoName}
        sessionId={sessionId}
        currentTask={memoryTrace?.current_task}
        status={busy ? "loading" : analysis?.status || (repoId ? "loaded" : "idle")}
        duration={debugData.duration}
        workerCount={workerOutputs.length}
        dataCount={dataCount}
        outputCount={finalAnswer || debugData.finalAnswerJson ? 1 : 0}
        apiBaseUrl={getApiBaseUrl()}
      />

      <div className="debugConsoleGrid">
        <div className="debugTopControls">
          <ModelControlDebugPanel
            status={modelStatus}
            busy={modelBusy}
            onRefresh={onRefreshModel}
            onConfigure={onConfigureModel}
            onTest={onTestModel}
          />
          <LangGraphDebugPanel
            status={debugData.graphStatus}
            analysisState={debugData.analysisGraphState}
            analysisTrace={debugData.analysisGraphTrace}
            qaState={debugData.qaGraphState}
            qaTrace={debugData.qaGraphTrace}
            agentFlow={debugData.agentFlow}
            busy={busy}
            onResume={onResumeGraph}
          />
        </div>
        {debugTab === "model" && !repoId ? null : (
          <>
        <AgentFlowDebugPanel
          userQuestion={memoryTrace?.user_question}
          agentFlow={debugData.agentFlow}
          workerOutputs={workerOutputs}
          busy={busy}
        />
        <WorkerOutputsDebugPanel outputs={workerOutputs} />
        <DataLayerDebugPanel graph={debugData.dataLayer || graph} summary={analysis?.graph_summary} memory={memoryTrace} />
        <RepositoryGraphDebugPanel graph={debugData.repositoryGraph || graph} />
        <LearningAgentDebugSummaryPanel bundle={debugData.learningAgentBundle} />
        <LearningAgentRawPanel bundle={debugData.learningAgentBundle} />
        <RetrievalTracePanel trace={debugData.retrievalTrace} memory={memoryTrace} />
        <SharedMemoryPanel memory={debugData.memory || memoryTrace} />
        <EvaluatorOptimizerPanel answer={finalAnswer} selfCheck={debugData.selfCheck} trace={memoryTrace?.final_decision_trace} />
        <FinalAnswerJsonPanel answer={finalAnswer} finalAnswerJson={debugData.finalAnswerJson} />
        <TraceExportPanel sessionId={sessionId} tracePayload={tracePayload} />
          </>
        )}
      </div>
    </section>
  );
}

function repoNameFromUrl(url) {
  const match = url?.match(/github\.com\/([^/\s]+)\/([^/\s#?]+)/i);
  return match ? `${match[1]}/${match[2].replace(/\.git$/, "")}` : "";
}
