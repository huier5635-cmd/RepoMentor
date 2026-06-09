# RepoMentor 测试计划

## 范围

- 公开 GitHub 仓库 analyze
- Repository Intelligence Graph 和 Data Layer 一致性
- Learning Path
- Development Workflow
- Issue Recommendation / internal first tasks
- 固定仓库级 QA
- Mock / DeepSeek 模型状态与 fallback
- Debug Console 与用户页展示隔离
- QA 轻并发

## 命令

```powershell
python scripts/stress_test_repomentor.py --base-url http://127.0.0.1:8000 --provider mock --concurrency 3 --output-dir reports --skip-large
```

## 通过标准

- 至少 3 个正常公开仓库 analyze 成功。
- QA 成功率 >= 90%。
- evidence 覆盖率 >= 85%。
- command hallucination = 0。
- SelfCheck 缺失率 = 0。
- 无 open issues 仓库能生成 internal first tasks。
- 用户页不展示 raw debug 信息。
- 调试页能展示完整 trace。
- 不出现 API Key 泄露。
