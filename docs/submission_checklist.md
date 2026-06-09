# RepoMentor 提交材料清单

## 必交材料

- [x] 可运行 Demo
  - 后端：`http://127.0.0.1:8000`
  - 前端：`http://127.0.0.1:5173`
  - 用户页：`/repos/{repo_id}`
  - 调试页：`/debug/{repo_id}?tab=model`
- [x] PPT 展示材料
  - `docs/RepoMentor_最终展示.pptx`
  - 页数不超过 10 页。
- [x] Demo 录屏脚本
  - `docs/demo_script.md`
- [x] 完整交互轨迹说明
  - `docs/interaction_trace.md`
  - Codex：`~/.codex/sessions`
  - Claude Code：`~/.claude/projects/`
- [x] PPT 提纲
  - `docs/presentation_outline.md`
- [x] 测试总结
  - `docs/testing_summary.md`
- [x] 升级路线
  - `docs/upgrade_plan.md`
- [x] README 运行与展示说明
  - “如何运行 Demo”
  - “如何展示项目”

## 展示时必须讲清楚

- [x] RepoMentor 是结构优先的仓库学习助手，不是纯聊天机器人。
- [x] 用户页和调试页分离。
- [x] Agent Flow、Data Layer、SelfCheck、FinalAnswer JSON 只在调试页展示。
- [x] 用户问答是 evidence-grounded answer，每条关键结论都尽量绑定证据。
- [x] LLM 只做解释、翻译润色和学习反馈，不决定仓库事实。
- [x] Mock 模式可免费运行；DeepSeek 模式可选。
- [x] 压力测试早期 FAIL 的原因是 evidence 覆盖不足，不是系统崩溃。
- [x] 下一阶段重点是 EvidenceBuilder、DeepSeek、LangGraph 和部署展示。

## Demo 推荐顺序

1. 打开用户页。
2. 输入 GitHub 仓库 URL。
3. 展示仓库概览。
4. 展示代码地图。
5. 展示学习路径。
6. 展示开发流程。
7. 展示推荐任务。
8. QA 提问“这个项目怎么启动”。
9. 展示证据来源。
10. 切到调试控制台展示 Agent Flow、Data Layer、SelfCheck、FinalAnswer JSON。

## 风险与说明

- 公开 GitHub API 可能受网络或 rate limit 影响；建议提前分析好演示仓库并使用本地缓存。
- DeepSeek 需要有效 API Key；没有 Key 时应切换 Mock 模式。
- `.env`、API Key、私人 session 目录不应提交到公开仓库。
- 完整交互轨迹来自本机会话目录，提交前需按学校或任务书要求脱敏。
