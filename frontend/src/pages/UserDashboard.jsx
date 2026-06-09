import { AlertCircle, CheckCircle2, GitBranch, RefreshCw } from "lucide-react";
import ArchitectureTourPanel from "../components/user/ArchitectureTourPanel.jsx";
import BilingualGlossaryPanel from "../components/user/BilingualGlossaryPanel.jsx";
import ChangeImpactPanel from "../components/user/ChangeImpactPanel.jsx";
import CodeMapPanel from "../components/user/CodeMapPanel.jsx";
import DevelopmentWorkflowPanel from "../components/user/DevelopmentWorkflowPanel.jsx";
import IssueRecommendationPanel from "../components/user/IssueRecommendationPanel.jsx";
import LearningCheckPanel from "../components/user/LearningCheckPanel.jsx";
import LearningPathV2Panel from "../components/user/LearningPathV2Panel.jsx";
import ModuleStudyCardsPanel from "../components/user/ModuleStudyCardsPanel.jsx";
import OnboardingDebtPanel from "../components/user/OnboardingDebtPanel.jsx";
import QAPanel from "../components/user/QAPanel.jsx";
import RepoInput from "../components/user/RepoInput.jsx";
import RepoOverviewPanel from "../components/user/RepoOverviewPanel.jsx";
import UserModelSwitch from "../components/user/UserModelSwitch.jsx";

const MAIN_TABS = [
  { id: "learning", label: "学习路径" },
  { id: "architecture", label: "架构导览" },
  { id: "modules", label: "模块卡" },
  { id: "bilingual", label: "双语术语" },
  { id: "workflow", label: "开发流程" },
  { id: "issues", label: "推荐任务" },
  { id: "check", label: "学习检查" },
  { id: "impact", label: "改动演练" },
  { id: "debt", label: "新手友好度" },
  { id: "qa", label: "仓库问答" }
];

export default function UserDashboard({
  repoUrl,
  setRepoUrl,
  onAnalyze,
  onReanalyze,
  busy,
  phase,
  error,
  analysis,
  overview,
  graph,
  learningPath,
  learningPathV2,
  architectureTour,
  moduleCards,
  glossary,
  bilingualDocs,
  tutorials,
  onboardingDebt,
  learningCheck,
  changeImpact,
  developmentWorkflow,
  issueRanking,
  finalAnswer,
  onAsk,
  onLearningCheck,
  onChangeImpact,
  modelStatus,
  modelBusy,
  onSwitchModelProvider,
  onOpenModelSettings,
  activeTab,
  setActiveTab
}) {
  const repoReady = Boolean(analysis?.repo_id);

  return (
    <section className="pageStack userPage">
      <RepoInput value={repoUrl} onChange={setRepoUrl} onAnalyze={onAnalyze} busy={busy} phase={phase} />
      <UserModelSwitch
        status={modelStatus}
        busy={modelBusy}
        onSwitchProvider={onSwitchModelProvider}
        onOpenSettings={onOpenModelSettings}
      />

      {error && (
        <div className="errorBar">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <section className="statusLine">
        {repoReady ? <CheckCircle2 size={18} /> : <GitBranch size={18} />}
        <span>{busy ? "正在运行" : repoReady ? `仓库 ID ${analysis.repo_id}` : "等待仓库分析"}</span>
        {repoReady && (
          <button className="iconButton" title="重新分析" onClick={onReanalyze} disabled={busy}>
            <RefreshCw size={16} />
          </button>
        )}
      </section>

      <RepoOverviewPanel
        repoUrl={repoUrl}
        analysis={analysis}
        overview={overview}
        graph={graph}
        workflow={developmentWorkflow}
      />
      <CodeMapPanel graph={graph} />

      <nav className="tabBar userTabs" aria-label="主要功能标签">
        {MAIN_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={activeTab === tab.id ? "active" : ""}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {activeTab === "learning" && <LearningPathV2Panel learningPathV2={learningPathV2} fallbackLearningPath={learningPath} tutorials={tutorials} />}
      {activeTab === "architecture" && <ArchitectureTourPanel architectureTour={architectureTour} />}
      {activeTab === "modules" && <ModuleStudyCardsPanel moduleCards={moduleCards} />}
      {activeTab === "bilingual" && <BilingualGlossaryPanel glossary={glossary} bilingualDocs={bilingualDocs} />}
      {activeTab === "workflow" && <DevelopmentWorkflowPanel workflow={developmentWorkflow} />}
      {activeTab === "issues" && <IssueRecommendationPanel issueRanking={issueRanking} />}
      {activeTab === "check" && <LearningCheckPanel repoReady={repoReady} busy={busy} result={learningCheck} onSubmit={onLearningCheck} />}
      {activeTab === "impact" && <ChangeImpactPanel repoReady={repoReady} busy={busy} result={changeImpact} onSubmit={onChangeImpact} graph={graph} />}
      {activeTab === "debt" && <OnboardingDebtPanel onboardingDebt={onboardingDebt} />}
      {activeTab === "qa" && <QAPanel repoReady={repoReady} onAsk={onAsk} answer={finalAnswer} busy={busy} />}
    </section>
  );
}
