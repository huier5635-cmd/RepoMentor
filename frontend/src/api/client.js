const configuredApiBaseUrl = String(import.meta.env.VITE_API_BASE_URL || "").trim();
const devApiBaseUrl = import.meta.env.DEV ? "http://127.0.0.1:8000" : "";
const API_ORIGIN = trimTrailingSlash(configuredApiBaseUrl || devApiBaseUrl);
const API_BASE = API_ORIGIN ? `${API_ORIGIN}/api` : "/api";

export function getApiBaseUrl() {
  return API_ORIGIN || `${window.location.origin}/api`;
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  });
  if (!response.ok) {
    const text = await response.text();
    const error = new Error(text || `HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

function trimTrailingSlash(value) {
  return String(value || "").replace(/\/+$/, "");
}

async function optionalRequest(path, options = {}) {
  try {
    return await request(path, options);
  } catch (error) {
    if (error.status === 404) return null;
    throw error;
  }
}

export function analyzeRepo(repoUrl) {
  return request("/repos/analyze", {
    method: "POST",
    body: JSON.stringify({ repo_url: repoUrl })
  });
}

export function getRepoOverview(repoId) {
  return optionalRequest(`/repos/${repoId}/overview`);
}

export function getGraph(repoId) {
  return request(`/repos/${repoId}/graph`);
}

export function askQuestion(repoId, question) {
  return request(`/repos/${repoId}/qa`, {
    method: "POST",
    body: JSON.stringify({ question })
  });
}

export function getLLMStatus() {
  return request("/llm/status");
}

export function configureLLM(payload) {
  return request("/llm/configure", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getLearningPath(repoId) {
  return request(`/repos/${repoId}/learning-path`);
}

export function getLearningPathV2(repoId) {
  return optionalRequest(`/repos/${repoId}/learning-path-v2`);
}

export function getArchitectureTour(repoId, audience = "newcomer") {
  return optionalRequest(`/repos/${repoId}/architecture-tour?audience=${encodeURIComponent(audience)}`);
}

export function getModuleStudyCards(repoId, audience = "newcomer") {
  return optionalRequest(`/repos/${repoId}/module-study-cards?audience=${encodeURIComponent(audience)}`);
}

export function getProjectGlossary(repoId) {
  return optionalRequest(`/repos/${repoId}/glossary`);
}

export function getBilingualDocs(repoId) {
  return optionalRequest(`/repos/${repoId}/bilingual-docs`);
}

export function submitLearningCheck(repoId, payload) {
  return request(`/repos/${repoId}/learning-check`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function requestChangeImpact(repoId, payload) {
  return request(`/repos/${repoId}/change-impact`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getContributionFunnel(repoId) {
  return optionalRequest(`/repos/${repoId}/contribution-funnel`);
}

export function getOnboardingDebt(repoId) {
  return optionalRequest(`/repos/${repoId}/onboarding-debt`);
}

export function getTutorials(repoId) {
  return optionalRequest(`/repos/${repoId}/tutorials`);
}

export function getLearningAgentDebugBundle(repoId) {
  return optionalRequest(`/repos/${repoId}/learning-agent/debug-bundle`);
}

export function recommendIssues(repoId) {
  return request(`/repos/${repoId}/issues/recommend`);
}

export function getDevelopmentWorkflow(repoId) {
  return request(`/repos/${repoId}/development-workflow`);
}

export function getMemory(sessionId) {
  return request(`/memory/${sessionId}`);
}

export function getDebugAgentFlow(repoId) {
  return optionalRequest(`/debug/repos/${repoId}/agent-flow`);
}

export function getDebugWorkerOutputs(repoId) {
  return optionalRequest(`/debug/repos/${repoId}/worker-outputs`);
}

export function getDebugDataLayer(repoId) {
  return optionalRequest(`/debug/repos/${repoId}/data-layer`);
}

export function getDebugRepositoryGraph(repoId) {
  return optionalRequest(`/debug/repos/${repoId}/repository-graph`);
}

export function getDebugSessionMemory(sessionId) {
  return optionalRequest(`/debug/session/${sessionId}/memory`);
}

export function getDebugRetrievalTrace(sessionId) {
  return optionalRequest(`/debug/session/${sessionId}/retrieval-trace`);
}

export function getDebugSelfCheck(sessionId) {
  return optionalRequest(`/debug/session/${sessionId}/self-check`);
}

export function getDebugFinalAnswerJson(sessionId) {
  return optionalRequest(`/debug/session/${sessionId}/final-answer-json`);
}

export function getGraphStatus() {
  return optionalRequest("/graph/status");
}

export function getDebugGraphState(threadId) {
  return optionalRequest(`/debug/graph/${encodeURIComponent(threadId)}/state`);
}

export function getDebugGraphTrace(threadId) {
  return optionalRequest(`/debug/graph/${encodeURIComponent(threadId)}/trace`);
}

export function resumeDebugGraph(threadId) {
  return optionalRequest(`/debug/graph/${encodeURIComponent(threadId)}/resume`, {
    method: "POST",
    body: JSON.stringify({})
  });
}
