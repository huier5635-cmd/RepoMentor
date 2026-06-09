# RepoMentor 压力测试报告

- 测试时间：2026-06-09T09:45:16.706967+00:00
- 测试环境：Windows-11-10.0.26200-SP0 / Python 3.13.5
- 模型模式：mock
- 整体结论：**PASS**

## 汇总指标

- 正常仓库 analyze 成功：3 / 3
- 异常仓库可读错误：4 / 4
- 平均 analyze 时间：8.617s
- 平均 QA 时间：0.044s
- p95 QA 延迟：0.102s
- QA 成功率：97.22%
- evidence 覆盖率：100.00%
- command hallucination 数量：0
- SelfCheck 通过率：80.56%
- SelfCheck 缺失率：0.00%
- Issue fallback 成功：3 / 3
- API Key 泄露：否

## 仓库列表与 Analyze 结果

### resilience-copilot-gemma4
- category：current-sample
- URL：https://github.com/huier5635-cmd/resilience-copilot-gemma4
- 状态：success
- repo_id：f89b095c9044
- 用时：3.661s
- files/symbols/imports：64 / 221 / 38
- docs files/chunks/edges：20 / 781 / 50
- tests files/edges：6 / 15
- quality/run/test commands：9 / 6 / 2
- open issues：0
- worker success/partial/failed：7 / 1 / 0
- warnings：无
- errors：无

### flask
- category：python-web-framework
- URL：https://github.com/pallets/flask
- 状态：success
- repo_id：654502453668
- 用时：22.079s
- files/symbols/imports：235 / 926 / 102
- docs files/chunks/edges：100 / 4313 / 731
- tests files/edges：68 / 154
- quality/run/test commands：22 / 1 / 2
- open issues：0
- worker success/partial/failed：7 / 1 / 0
- warnings：无
- errors：无

### academic-paper-workflow-skill
- category：cached-public-fallback
- URL：C:/Users/Liaoke/Desktop/RepoMentor 多智能体仓库学习助手/repomentor/backend/.repomentor_cache/repos/huier5635-cmd-academic-paper-workflow-skill-005ec74f4af7
- 状态：success
- repo_id：39947080d7b4
- 用时：0.112s
- files/symbols/imports：13 / 22 / 0
- docs files/chunks/edges：2 / 61 / 1
- tests files/edges：0 / 0
- quality/run/test commands：2 / 0 / 2
- open issues：0
- worker success/partial/failed：5 / 3 / 0
- warnings：无
- errors：无

## 异常仓库

- missing-repository：expected_error，git clone failed: Cloning into '.repomentor_cache\repos\not-exist-owner-not-exist-repo-7c5e8381a583'...
remote: Repository not found.
fatal: repository 'https://github.com/not-exist-owner/not-exist-repo/' not found
- empty-url：expected_error，repo_url must be a non-empty existing local path or a GitHub repository URL
- non-github-url：expected_error，repo_url must be an existing local path or a GitHub repository URL
- bad-format-url：expected_error，repo_url must be an existing local path or a GitHub repository URL

## QA 结果

- resilience-copilot-gemma4：QA 12 条，errors=0，warnings=0
- flask：QA 12 条，errors=0，warnings=0
- academic-paper-workflow-skill：QA 12 条，errors=1，warnings=0

## 并发轻压测

- total_requests：36
- success_count：36
- failure_count：0
- average_latency：0.077s
- p95_latency：0.188s
- max_latency：0.268s
- timeout_count：0
- 500_count：0

## 前端压力检查

- user_hides_agent_flow: True
- user_hides_worker_outputs: True
- user_hides_shared_memory: True
- user_model_has_no_password_input: True
- debug_has_agent_flow: True
- debug_has_worker_outputs: True
- debug_has_shared_memory: True
- debug_has_retrieval_trace: True
- debug_has_final_json: True
- debug_has_langgraph_panel: True
- debug_model_password_input: True
- debug_trace_export: True
- model_control_full_row: True
- raw_json_default_folded: True
- api_key_not_in_frontend_defaults: True

## 已发现 bug

- academic-paper-workflow-skill QA[入口文件在哪里？]: Response referenced nonexistent file paths: ['app.py', 'main.py']

## 已修复 bug

- 调试页模型控制和智能体流程调试布局重叠已修复
- 模型控制用户/调试视图已拆分
- 模型 API 状态返回不泄露 API Key

## 仍存在的限制

- DeepSeek 真模型调用依赖本地运行时 API Key；无 Key 时按设计回退 Mock。
- 压力测试不会并发 analyze 大仓库，只对已分析仓库做 QA 轻并发。
- 前端大数据分页/折叠目前主要通过静态源代码和浏览器抽样验证，未覆盖所有超大仓库场景。

## 下一阶段功能升级建议

### P0
- 修复压力测试发现的 bug
- 强化 evidence 和 SelfCheck
- 优化 setup_run 和 development workflow
- 完善 internal first tasks
### P1
- DeepSeek 深度接入 Code Explanation / LearningPath
- 多仓库评测集
- README 和 Demo 视频
- 评测报告
### P2
- LangGraph 迁移
- checkpoint
- long-running repo analysis
- MCP server
- 多用户任务队列
