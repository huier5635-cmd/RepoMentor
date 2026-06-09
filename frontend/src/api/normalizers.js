export function normalizeRepoOverview(apiResponse = {}, graph = {}, workflow = null) {
  const response = apiResponse || {};
  const files = firstNonEmpty(response.files, response.file_tree, graph?.files, graph?.snapshot?.files);
  const languages = firstNonEmptyObject(response.languages, graph?.languages) || countLanguages(files);
  const languageList = Object.keys(languages || {});
  const coreDirectories = firstNonEmpty(response.core_directories, graph?.core_directories, topDirectories(files));
  const commands = graph?.commands || {};
  const developmentCommands = commandValues(workflow?.development_commands);
  const rawRunCommands = commandValues(firstNonEmpty(response.run_commands, commands.run, developmentCommands));
  const runCommands = rawRunCommands.filter((command) => !isEvaluationCommand(command));
  const evaluationCommands = rawRunCommands.filter(isEvaluationCommand);

  return {
    ...response,
    repo_name: response.repo_name || fullRepoName(response) || fullRepoName(graph?.snapshot),
    files,
    file_tree: response.file_tree || files,
    languages,
    languages_list: languageList,
    primary_language: response.primary_language || languageList[0] || "",
    core_directories: coreDirectories,
    key_files: firstNonEmpty(response.key_files, graph?.key_files, graph?.snapshot?.key_files),
    readme_exists: response.readme_exists ?? hasFile(files, "README.md"),
    entrypoints: firstNonEmpty(response.entrypoints, graph?.entrypoints).map(entrypointLabel).filter(Boolean),
    setup_commands: firstNonEmpty(response.setup_commands, commands.setup, commandValues(workflow?.development_commands?.filter((item) => item.command_type === "setup"))),
    run_commands: runCommands,
    evaluation_commands: evaluationCommands,
    test_commands: firstNonEmpty(response.test_commands, commands.test, commandValues(workflow?.test_commands)),
    build_commands: firstNonEmpty(response.build_commands, commands.build, commandValues(workflow?.build_commands)),
    lint_commands: firstNonEmpty(response.lint_commands, commands.lint, commandValues(workflow?.lint_commands)),
    format_commands: firstNonEmpty(response.format_commands, commands.format, commandValues(workflow?.format_commands)),
    type_check_commands: firstNonEmpty(response.type_check_commands, commands.type_check, commandValues(workflow?.type_check_commands)),
    issues_count: response.issues_count ?? graph?.issues_count ?? graph?.snapshot?.issues?.length ?? 0
  };
}

export function normalizeLearningPath(apiResponse = {}) {
  const response = apiResponse || {};
  return {
    conclusion: response.conclusion || "后端未返回学习路径结论。",
    steps: response.steps || [],
    risks: response.risks || [],
    verifiable_commands: response.verifiable_commands || [],
    self_check: response.self_check || null
  };
}

export function normalizeDevelopmentWorkflow(apiResponse = {}) {
  const response = apiResponse || {};
  return {
    conclusion: response.conclusion || "后端未返回开发流程结论。",
    quality_commands: response.quality_commands || [],
    setup_steps: response.setup_steps || [],
    development_commands: response.development_commands || [],
    test_commands: response.test_commands || [],
    lint_commands: response.lint_commands || [],
    format_commands: response.format_commands || [],
    type_check_commands: response.type_check_commands || [],
    build_commands: response.build_commands || [],
    branch_rules: response.branch_rules || [],
    commit_rules: response.commit_rules || [],
    pull_request_rules: response.pull_request_rules || [],
    ci_rules: response.ci_rules || [],
    code_style_rules: response.code_style_rules || [],
    new_contributor_checklist: response.new_contributor_checklist || [],
    evidence_docs: response.evidence_docs || [],
    evidence_code: response.evidence_code || [],
    evidence_issues: response.evidence_issues || [],
    risks: response.risks || [],
    uncertainties: response.uncertainties || [],
    verifiable_commands: response.verifiable_commands || [],
    self_check: response.self_check || null
  };
}

export function normalizeIssueRecommendations(apiResponse = {}) {
  const response = apiResponse || {};
  return {
    issues: response.issues || [],
    message: response.message || (response.issues?.length ? "" : "未找到可推荐 open issues"),
    self_check: response.self_check || null
  };
}

export function normalizeQAAnswer(apiResponse = {}) {
  const response = apiResponse || {};
  return {
    conclusion: response.conclusion || "后端未返回回答结论。",
    evidence_docs: response.evidence_docs || [],
    evidence_code: response.evidence_code || [],
    evidence_issues: response.evidence_issues || [],
    steps: response.steps || [],
    risks: response.risks || [],
    verifiable_commands: response.verifiable_commands || [],
    self_check: response.self_check || null,
    trace_summary: response.trace_summary || [],
    model_info: response.model_info || null
  };
}

function firstNonEmpty(...lists) {
  return lists.find((list) => Array.isArray(list) && list.length > 0) || [];
}

function firstNonEmptyObject(...objects) {
  return objects.find((item) => item && typeof item === "object" && !Array.isArray(item) && Object.keys(item).length > 0) || null;
}

function commandValues(commands = []) {
  return commands.map((item) => normalizeCommand(typeof item === "string" ? item : item?.command)).filter(Boolean);
}

function entrypointLabel(item) {
  if (typeof item === "string") return item;
  return item?.path || "";
}

function normalizeCommand(value) {
  return String(value || "").replaceAll("\\", "/").trim().split(/\s+/).join(" ");
}

function isEvaluationCommand(command) {
  return /run_(academic_)?eval|run_local_validation|run_stress_test|stress_test|benchmark/i.test(normalizeCommand(command));
}

function fullRepoName(value = {}) {
  return value?.owner && value?.name ? `${value.owner}/${value.name}` : "";
}

function hasFile(files, name) {
  return files.some((file) => file.name?.toLowerCase() === name.toLowerCase());
}

function countLanguages(files) {
  const counts = {};
  for (const file of files) {
    if (!file.language || file.language === "unknown") continue;
    counts[file.language] = (counts[file.language] || 0) + 1;
  }
  return Object.fromEntries(Object.entries(counts).sort((a, b) => b[1] - a[1]));
}

function topDirectories(files) {
  const counts = {};
  for (const file of files) {
    const root = file.path?.split(/[\\/]/)[0];
    if (!root || root.includes(".")) continue;
    counts[root] = (counts[root] || 0) + 1;
  }
  return Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 8).map(([name]) => name);
}
