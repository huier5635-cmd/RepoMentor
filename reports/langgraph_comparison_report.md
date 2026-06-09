# LangGraph 迁移对比报告

- 生成时间：2026-06-09T09:45:16.706967+00:00
- 请求 Orchestrator：`legacy`
- 后端实际 Orchestrator：`legacy`
- LangGraph Enabled：`False`
- Checkpoint：`memory` / `available=True`
- Max Retries：`2`

## 验收指标

- analyze 成功：3 / 3
- QA 成功率：97.22%
- evidence 覆盖率：100.00%
- command hallucination：0
- SelfCheck 缺失率：0.00%
- Issue fallback：3 / 3

## Debug API 抽样

### resilience-copilot-gemma4
- agent_flow：200
- analysis_graph_state：200
- analysis_graph_trace：200
- qa_graph_state：200
- qa_graph_trace：200

### flask
- agent_flow：200
- analysis_graph_state：200
- analysis_graph_trace：200
- qa_graph_state：200
- qa_graph_trace：200

### academic-paper-workflow-skill
- agent_flow：200
- analysis_graph_state：200
- analysis_graph_trace：200
- qa_graph_state：200
- qa_graph_trace：200

## Pass / Fail

- at_least_3_analyze_success: `True`
- normal_files_gt_zero: `True`
- qa_success_rate_gte_90: `True`
- evidence_coverage_gte_85: `True`
- command_hallucination_zero: `True`
- self_check_missing_zero: `True`
- issue_fallback_success: `True`
- frontend_user_no_raw_debug: `True`
- debug_trace_available: `True`
- debug_langgraph_panel_available: `True`
- no_api_key_leak: `True`
- overall: `pass`
