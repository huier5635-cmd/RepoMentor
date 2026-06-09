import { useEffect, useMemo, useState } from "react";
import {
  analyzeRepo,
  askQuestion,
  getDebugAgentFlow,
  getDebugDataLayer,
  getDebugFinalAnswerJson,
  getDebugGraphState,
  getDebugGraphTrace,
  getDebugRepositoryGraph,
  getDebugRetrievalTrace,
  getDebugSelfCheck,
  getDebugSessionMemory,
  getDebugWorkerOutputs,
  getArchitectureTour,
  getBilingualDocs,
  getContributionFunnel,
  getDevelopmentWorkflow,
  getLearningAgentDebugBundle,
  getGraph,
  getGraphStatus,
  getLearningPath,
  getLearningPathV2,
  getMemory,
  getModuleStudyCards,
  getOnboardingDebt,
  getProjectGlossary,
  getRepoOverview,
  getTutorials,
  requestChangeImpact,
  recommendIssues,
  resumeDebugGraph,
  submitLearningCheck
} from "./api/client.js";
import { getModelStatus, testModelConnection, updateModelConfig } from "./api/model.js";
import {
  normalizeDevelopmentWorkflow,
  normalizeIssueRecommendations,
  normalizeLearningPath,
  normalizeQAAnswer,
  normalizeRepoOverview
} from "./api/normalizers.js";
import DebugConsole from "./pages/DebugConsole.jsx";
import UserDashboard from "./pages/UserDashboard.jsx";

const DEFAULT_REPO_URL = "https://github.com/pallets/flask";
const EMPTY_DEBUG = {
  agentFlow: null,
  workerOutputs: null,
  dataLayer: null,
  repositoryGraph: null,
  retrievalTrace: null,
  memory: null,
  selfCheck: null,
  finalAnswerJson: null,
  graphStatus: null,
  analysisGraphState: null,
  analysisGraphTrace: null,
  qaGraphState: null,
  qaGraphTrace: null,
  learningAgentBundle: null,
  duration: ""
};

export default function App() {
  const [route, setRoute] = useState(readRoute);
  const [repoUrl, setRepoUrl] = useState(DEFAULT_REPO_URL);
  const [analysis, setAnalysis] = useState(null);
  const [overview, setOverview] = useState(null);
  const [graph, setGraph] = useState(null);
  const [learningPath, setLearningPath] = useState(null);
  const [learningPathV2, setLearningPathV2] = useState(null);
  const [architectureTour, setArchitectureTour] = useState(null);
  const [moduleCards, setModuleCards] = useState([]);
  const [glossary, setGlossary] = useState(null);
  const [bilingualDocs, setBilingualDocs] = useState(null);
  const [tutorials, setTutorials] = useState([]);
  const [onboardingDebt, setOnboardingDebt] = useState(null);
  const [learningCheck, setLearningCheck] = useState(null);
  const [changeImpact, setChangeImpact] = useState(null);
  const [issueRanking, setIssueRanking] = useState(null);
  const [developmentWorkflow, setDevelopmentWorkflow] = useState(null);
  const [finalAnswer, setFinalAnswer] = useState(null);
  const [memoryTrace, setMemoryTrace] = useState(null);
  const [debugData, setDebugData] = useState(EMPTY_DEBUG);
  const [modelStatus, setModelStatus] = useState(null);
  const [modelBusy, setModelBusy] = useState(false);
  const [activeUserTab, setActiveUserTab] = useState("learning");
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState("idle");
  const [error, setError] = useState("");

  const effectiveRepoId = route.repoId || analysis?.repo_id || inferRepoId(memoryTrace?.current_task);
  const effectiveSessionId = route.sessionId || analysis?.session_id || memoryTrace?.session_id || "";

  useEffect(() => {
    function onPopState() {
      setRoute(readRoute());
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function hydrateRoute() {
      let hydratedFromCache = false;
      try {
        if (route.repoId) {
          hydratedFromCache = hydrateFromCache(route.repoId);
          await loadRepoArtifacts(route.repoId, { showBusy: true, cancelled: () => cancelled });
        }
        if (route.sessionId) {
          await loadSessionTrace(route.sessionId, { cancelled: () => cancelled });
        }
        if (route.page === "debug" && (route.repoId || route.sessionId)) {
          await loadDebugArtifacts(route.repoId, route.sessionId, { showBusy: true, cancelled: () => cancelled });
        }
      } catch (err) {
        if (!cancelled && hydratedFromCache) {
          setError("");
          setPhase("done");
          console.warn("Route hydrate used cached repo data after backend refresh failed.", err);
        } else if (!cancelled) {
          setError(err.message);
        }
      }
    }
    hydrateRoute();
    return () => {
      cancelled = true;
    };
  }, [route.page, route.repoId, route.sessionId]);

  useEffect(() => {
    refreshModelStatus();
  }, []);

  const headerActions = useMemo(() => {
    if (!effectiveRepoId) return null;
    return (
      <nav className="headerLinks" aria-label="页面路由">
        <button type="button" onClick={() => navigate(`/repos/${effectiveRepoId}`)}>
          用户页面
        </button>
        <button type="button" onClick={() => navigate(`/debug/${effectiveRepoId}${effectiveSessionId ? `?session_id=${effectiveSessionId}` : ""}`)}>
          调试控制台
        </button>
      </nav>
    );
  }, [effectiveRepoId, effectiveSessionId]);

  async function loadRepoArtifacts(repoId, options = {}) {
    const { showBusy = false, baseAnalysis = null, cancelled = () => false } = options;
    if (showBusy) {
      setBusy(true);
      setPhase("structure");
    }
    setError("");
    try {
      const [overviewResult, graphResult] = await Promise.allSettled([
        getRepoOverview(repoId),
        getGraph(repoId)
      ]);
      if (cancelled()) return;
      let nextGraph = null;
      if (graphResult.status === "fulfilled") {
        nextGraph = graphResult.value;
        setGraph(nextGraph);
      } else {
        throw graphResult.reason;
      }
      const apiOverview = overviewResult.status === "fulfilled" ? overviewResult.value : null;
      const existingAnalysis = analysis?.repo_id === repoId ? analysis : null;
      const nextAnalysis = normalizeRepoOverview(baseAnalysis || existingAnalysis || {
        repo_id: repoId,
        status: "loaded",
        graph_summary: {},
        worker_outputs: [],
        run_commands: [],
        test_commands: [],
        entrypoints: [],
        session_id: effectiveSessionId
      }, nextGraph);
      setAnalysis(nextAnalysis);
      const nextOverview = normalizeRepoOverview(apiOverview || nextAnalysis, nextGraph);
      setOverview(nextOverview);

      setPhase("learning");
      const [
        learning,
        learningV2,
        architecture,
        cards,
        glossaryResult,
        bilingualResult,
        tutorialsResult,
        debtResult,
        contribution,
        issues,
        workflow
      ] = await Promise.allSettled([
        getLearningPath(repoId),
        getLearningPathV2(repoId),
        getArchitectureTour(repoId),
        getModuleStudyCards(repoId),
        getProjectGlossary(repoId),
        getBilingualDocs(repoId),
        getTutorials(repoId),
        getOnboardingDebt(repoId),
        getContributionFunnel(repoId),
        recommendIssues(repoId),
        getDevelopmentWorkflow(repoId)
      ]);
      if (cancelled()) return;
      const nextLearningPath = learning.status === "fulfilled" ? normalizeLearningPath(learning.value) : null;
      const nextLearningPathV2 = learningV2.status === "fulfilled" ? learningV2.value : null;
      const nextArchitectureTour = architecture.status === "fulfilled" ? architecture.value : null;
      const nextModuleCards = cards.status === "fulfilled" && Array.isArray(cards.value) ? cards.value : [];
      const nextGlossary = glossaryResult.status === "fulfilled" ? glossaryResult.value : null;
      const nextBilingualDocs = bilingualResult.status === "fulfilled" ? bilingualResult.value : null;
      const nextTutorials = tutorialsResult.status === "fulfilled" && Array.isArray(tutorialsResult.value) ? tutorialsResult.value : [];
      const nextOnboardingDebt = debtResult.status === "fulfilled" ? debtResult.value : null;
      const contributionValue = contribution.status === "fulfilled" ? contribution.value : null;
      const legacyIssuesValue = issues.status === "fulfilled" ? issues.value : null;
      const nextIssueRanking = normalizeIssueRecommendations(contributionValue || legacyIssuesValue || {});
      const nextDevelopmentWorkflow = workflow.status === "fulfilled" ? normalizeDevelopmentWorkflow(workflow.value) : null;
      if (nextLearningPath) setLearningPath(nextLearningPath);
      if (nextLearningPathV2) setLearningPathV2(nextLearningPathV2);
      if (nextArchitectureTour) setArchitectureTour(nextArchitectureTour);
      setModuleCards(nextModuleCards);
      if (nextGlossary) setGlossary(nextGlossary);
      if (nextBilingualDocs) setBilingualDocs(nextBilingualDocs);
      setTutorials(nextTutorials);
      if (nextOnboardingDebt) setOnboardingDebt(nextOnboardingDebt);
      if (nextIssueRanking) setIssueRanking(nextIssueRanking);
      if (nextDevelopmentWorkflow) {
        setDevelopmentWorkflow(nextDevelopmentWorkflow);
        setOverview(normalizeRepoOverview(apiOverview || nextAnalysis, nextGraph, nextDevelopmentWorkflow));
      }
      setError("");
      writeRepoCache(repoId, {
        repoUrl,
        analysis: nextAnalysis,
        overview: nextOverview,
        graph: nextGraph,
        learningPath: nextLearningPath,
        learningPathV2: nextLearningPathV2,
        architectureTour: nextArchitectureTour,
        moduleCards: nextModuleCards,
        glossary: nextGlossary,
        bilingualDocs: nextBilingualDocs,
        tutorials: nextTutorials,
        onboardingDebt: nextOnboardingDebt,
        issueRanking: nextIssueRanking,
        developmentWorkflow: nextDevelopmentWorkflow
      });
      setPhase("done");
    } finally {
      if (showBusy && !cancelled()) setBusy(false);
    }
  }

  async function loadSessionTrace(sessionId, options = {}) {
    const { cancelled = () => false } = options;
    const debugMemory = await safeCall(() => getDebugSessionMemory(sessionId));
    const legacyMemory = debugMemory || await safeCall(() => getMemory(sessionId)) || readCachedMemory(route.repoId || analysis?.repo_id);
    if (!cancelled()) {
      setMemoryTrace(legacyMemory);
    }
    const repoIdFromMemory = inferRepoId(legacyMemory?.current_task);
    const cacheRepoId = repoIdFromMemory || route.repoId || analysis?.repo_id;
    if (cacheRepoId && legacyMemory) {
      writeRepoCache(cacheRepoId, { memoryTrace: legacyMemory });
    }
    if (repoIdFromMemory && !graph && !cancelled()) {
      await loadRepoArtifacts(repoIdFromMemory, { cancelled });
    }
  }

  async function loadDebugArtifacts(repoId, sessionId, options = {}) {
    const { showBusy = false, cancelled = () => false } = options;
    if (showBusy) setBusy(true);
    setError("");
    try {
      const analysisThreadId = repoId ? `analyze:${repoId}` : "";
      const qaThreadId = repoId && sessionId ? `qa:${repoId}:${sessionId}` : "";
      const [
        graphStatus,
        agentFlow,
        workerOutputs,
        dataLayer,
        repositoryGraph,
        retrievalTrace,
        selfCheck,
        finalAnswerJson,
        analysisGraphState,
        analysisGraphTrace,
        qaGraphState,
        qaGraphTrace,
        learningAgentBundle
      ] = await Promise.all([
        safeCall(() => getGraphStatus()),
        repoId ? safeCall(() => getDebugAgentFlow(repoId)) : Promise.resolve(null),
        repoId ? safeCall(() => getDebugWorkerOutputs(repoId)) : Promise.resolve(null),
        repoId ? safeCall(() => getDebugDataLayer(repoId)) : Promise.resolve(null),
        repoId ? safeCall(() => getDebugRepositoryGraph(repoId)) : Promise.resolve(null),
        sessionId ? safeCall(() => getDebugRetrievalTrace(sessionId)) : Promise.resolve(null),
        sessionId ? safeCall(() => getDebugSelfCheck(sessionId)) : Promise.resolve(null),
        sessionId ? safeCall(() => getDebugFinalAnswerJson(sessionId)) : Promise.resolve(null),
        analysisThreadId ? safeCall(() => getDebugGraphState(analysisThreadId)) : Promise.resolve(null),
        analysisThreadId ? safeCall(() => getDebugGraphTrace(analysisThreadId)) : Promise.resolve(null),
        qaThreadId ? safeCall(() => getDebugGraphState(qaThreadId)) : Promise.resolve(null),
        qaThreadId ? safeCall(() => getDebugGraphTrace(qaThreadId)) : Promise.resolve(null),
        repoId ? safeCall(() => getLearningAgentDebugBundle(repoId)) : Promise.resolve(null)
      ]);
      if (cancelled()) return;
      const latestQaThreadId = agentFlow?.latest_qa_thread_id || qaThreadId;
      let nextQaGraphState = qaGraphState;
      let nextQaGraphTrace = qaGraphTrace;
      if (latestQaThreadId && (!nextQaGraphState?.found || latestQaThreadId !== qaThreadId)) {
        nextQaGraphState = await safeCall(() => getDebugGraphState(latestQaThreadId));
        nextQaGraphTrace = await safeCall(() => getDebugGraphTrace(latestQaThreadId));
        if (cancelled()) return;
      }
      const nextDebugData = {
        agentFlow,
        workerOutputs: normalizeWorkerOutputs(workerOutputs),
        dataLayer,
        repositoryGraph,
        retrievalTrace,
        memory: null,
        selfCheck,
        finalAnswerJson,
        graphStatus,
        analysisGraphState,
        analysisGraphTrace,
        qaGraphState: nextQaGraphState,
        qaGraphTrace: nextQaGraphTrace,
        learningAgentBundle,
        duration: ""
      };
      setDebugData(nextDebugData);
      setError("");
      if (repoId) {
        writeRepoCache(repoId, { debugData: nextDebugData });
      }
      if (sessionId) await loadSessionTrace(sessionId, { cancelled });
    } finally {
      if (showBusy && !cancelled()) setBusy(false);
    }
  }

  async function handleAnalyze(nextUrl = repoUrl) {
    setBusy(true);
    setPhase("reading");
    setError("");
    setFinalAnswer(null);
    setMemoryTrace(null);
    setLearningCheck(null);
    setChangeImpact(null);
    setLearningPathV2(null);
    setArchitectureTour(null);
    setModuleCards([]);
    setGlossary(null);
    setBilingualDocs(null);
    setTutorials([]);
    setOnboardingDebt(null);
    setDebugData(EMPTY_DEBUG);
    try {
      const result = normalizeRepoOverview(await analyzeRepo(nextUrl));
      setAnalysis(result);
      writeRepoCache(result.repo_id, { repoUrl: nextUrl, analysis: result });
      setPhase("structure");
      await loadRepoArtifacts(result.repo_id, { baseAnalysis: result });
      await loadSessionTrace(result.session_id);
      setActiveUserTab("workflow");
      setPhase("done");
      navigate(`/repos/${result.repo_id}`);
    } catch (err) {
      setError(err.message);
      setPhase("idle");
    } finally {
      setBusy(false);
    }
  }

  async function handleAsk(question) {
    if (!effectiveRepoId) return;
    setBusy(true);
    setError("");
    try {
      const answer = normalizeQAAnswer(await askQuestion(effectiveRepoId, question));
      setFinalAnswer(answer);
      writeRepoCache(effectiveRepoId, { finalAnswer: answer });
      setActiveUserTab("qa");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleLearningCheck(payload) {
    if (!effectiveRepoId) return;
    setBusy(true);
    setError("");
    try {
      const result = await submitLearningCheck(effectiveRepoId, payload);
      setLearningCheck(result);
      writeRepoCache(effectiveRepoId, { learningCheck: result });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleChangeImpact(payload) {
    if (!effectiveRepoId) return;
    setBusy(true);
    setError("");
    try {
      const result = await requestChangeImpact(effectiveRepoId, payload);
      setChangeImpact(result);
      writeRepoCache(effectiveRepoId, { changeImpact: result });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function refreshModelStatus() {
    try {
      setError("");
      setModelStatus(await getModelStatus());
    } catch {
      setModelStatus(null);
    }
  }

  async function handleConfigureModel(payload) {
    setModelBusy(true);
    setError("");
    try {
      const status = await updateModelConfig(payload);
      setModelStatus(status);
      setError("");
      return status;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setModelBusy(false);
    }
  }

  async function handleSwitchModelProvider(provider) {
    return handleConfigureModel({
      provider,
      model: provider === "deepseek" ? modelStatus?.requested_model || "deepseek-chat" : "",
      base_url: provider === "deepseek" ? modelStatus?.base_url || "https://api.deepseek.com" : "",
      api_key: "",
      persist: false
    });
  }

  async function handleTestModelConnection() {
    setModelBusy(true);
    setError("");
    try {
      return await testModelConnection();
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setModelBusy(false);
    }
  }

  function navigate(path) {
    window.history.pushState({}, "", path);
    setRoute(readRoute());
  }

  function hydrateFromCache(repoId) {
    const cached = readRepoCache(repoId);
    if (!cached) return false;
    if (cached.repoUrl) setRepoUrl(cached.repoUrl);
    if (cached.analysis) setAnalysis(cached.analysis);
    if (cached.overview !== undefined) setOverview(cached.overview);
    if (cached.graph) setGraph(cached.graph);
    if (cached.learningPath) setLearningPath(cached.learningPath);
    if (cached.learningPathV2) setLearningPathV2(cached.learningPathV2);
    if (cached.architectureTour) setArchitectureTour(cached.architectureTour);
    if (cached.moduleCards) setModuleCards(cached.moduleCards);
    if (cached.glossary) setGlossary(cached.glossary);
    if (cached.bilingualDocs) setBilingualDocs(cached.bilingualDocs);
    if (cached.tutorials) setTutorials(cached.tutorials);
    if (cached.onboardingDebt) setOnboardingDebt(cached.onboardingDebt);
    if (cached.issueRanking) setIssueRanking(cached.issueRanking);
    if (cached.developmentWorkflow) setDevelopmentWorkflow(cached.developmentWorkflow);
    if (cached.finalAnswer) setFinalAnswer(cached.finalAnswer);
    if (cached.learningCheck) setLearningCheck(cached.learningCheck);
    if (cached.changeImpact) setChangeImpact(cached.changeImpact);
    if (cached.memoryTrace) setMemoryTrace(cached.memoryTrace);
    if (cached.debugData) setDebugData({ ...EMPTY_DEBUG, ...cached.debugData });
    setError("");
    setPhase("done");
    return true;
  }

  async function refreshDebug() {
    const repoId = route.repoId || effectiveRepoId;
    const sessionId = route.sessionId || effectiveSessionId;
    if (repoId && !graph) await loadRepoArtifacts(repoId, { showBusy: true });
    await loadDebugArtifacts(repoId, sessionId, { showBusy: true });
  }

  async function handleResumeGraph(threadId) {
    if (!threadId) return null;
    const result = await resumeDebugGraph(threadId);
    await loadDebugArtifacts(route.repoId || effectiveRepoId, route.sessionId || effectiveSessionId);
    return result;
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <h1>RepoMentor</h1>
          <p>GitHub 仓库学习、代码地图、议题推荐与调试控制台</p>
        </div>
        {headerActions}
      </header>

      {route.page === "debug" ? (
        <DebugConsole
          repoUrl={repoUrl}
          repoId={effectiveRepoId}
          sessionId={effectiveSessionId}
          debugTab={route.debugTab}
          analysis={analysis}
          overview={overview}
          graph={graph}
          finalAnswer={finalAnswer}
          memoryTrace={memoryTrace}
          debugData={debugData}
          modelStatus={modelStatus}
          modelBusy={modelBusy}
          busy={busy}
          error={error}
          onRefreshModel={refreshModelStatus}
          onConfigureModel={handleConfigureModel}
          onTestModel={handleTestModelConnection}
          onRefresh={refreshDebug}
          onResumeGraph={handleResumeGraph}
          onNavigate={navigate}
        />
      ) : (
        <UserDashboard
          repoUrl={repoUrl}
          setRepoUrl={setRepoUrl}
          onAnalyze={handleAnalyze}
          onReanalyze={() => handleAnalyze(repoUrl)}
          busy={busy}
          phase={phase}
          error={error}
          analysis={analysis}
          overview={overview}
          graph={graph}
          learningPath={learningPath}
          learningPathV2={learningPathV2}
          architectureTour={architectureTour}
          moduleCards={moduleCards}
          glossary={glossary}
          bilingualDocs={bilingualDocs}
          tutorials={tutorials}
          onboardingDebt={onboardingDebt}
          learningCheck={learningCheck}
          changeImpact={changeImpact}
          developmentWorkflow={developmentWorkflow}
          issueRanking={issueRanking}
          finalAnswer={finalAnswer}
          onAsk={handleAsk}
          onLearningCheck={handleLearningCheck}
          onChangeImpact={handleChangeImpact}
          modelStatus={modelStatus}
          modelBusy={modelBusy}
          onSwitchModelProvider={handleSwitchModelProvider}
          onOpenModelSettings={() => navigate(effectiveRepoId ? `/debug/${effectiveRepoId}?tab=model${effectiveSessionId ? `&session_id=${effectiveSessionId}` : ""}` : "/debug/model")}
          activeTab={activeUserTab}
          setActiveTab={setActiveUserTab}
        />
      )}
    </main>
  );
}

function readRoute() {
  const path = window.location.pathname.replace(/\/+$/, "");
  const parts = path.split("/").filter(Boolean).map(decodeURIComponent);
  const params = new URLSearchParams(window.location.search);
  if (parts[0] === "debug" && parts[1] === "session" && parts[2]) {
    return { page: "debug", repoId: "", sessionId: parts[2], debugTab: params.get("tab") || "" };
  }
  if (parts[0] === "debug" && parts[1] === "model") {
    return { page: "debug", repoId: "", sessionId: "", debugTab: "model" };
  }
  if (parts[0] === "debug" && parts[1]) {
    const cached = readRepoCache(parts[1]);
    return {
      page: "debug",
      repoId: parts[1],
      sessionId: params.get("session_id") || cached?.analysis?.session_id || cached?.memoryTrace?.session_id || "",
      debugTab: params.get("tab") || ""
    };
  }
  if (parts[0] === "repos" && parts[1]) {
    return { page: "user", repoId: parts[1], sessionId: "" };
  }
  return { page: "user", repoId: "", sessionId: "" };
}

async function safeCall(callback) {
  try {
    return await callback();
  } catch {
    return null;
  }
}

function normalizeWorkerOutputs(value) {
  if (Array.isArray(value)) return value;
  if (Array.isArray(value?.worker_outputs)) return value.worker_outputs;
  if (Array.isArray(value?.outputs)) return value.outputs;
  return null;
}

function inferRepoId(value) {
  if (!value) return "";
  const taskTypes = new Set([
    "repo_overview",
    "setup_run",
    "code_explanation",
    "learning_path",
    "issue_recommendation",
    "test_mapping",
    "development_workflow",
    "general_qa"
  ]);
  return taskTypes.has(value) ? "" : value;
}

function readRepoCache(repoId) {
  if (!repoId) return null;
  try {
    const raw = window.sessionStorage.getItem(cacheKey(repoId));
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeRepoCache(repoId, patch) {
  if (!repoId) return;
  try {
    const current = readRepoCache(repoId) || {};
    window.sessionStorage.setItem(cacheKey(repoId), JSON.stringify({ ...current, ...patch }));
  } catch {
    // Session storage is a convenience cache; rendering should not depend on it.
  }
}

function readCachedMemory(repoId) {
  return readRepoCache(repoId)?.memoryTrace || null;
}

function cacheKey(repoId) {
  return `repomentor:repo:${repoId}`;
}
