# RepoMentor 录屏 Demo 脚本

建议时长：3–5 分钟。

本地演示地址：

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`

## 录屏流程

### 1. 打开首页

操作：

- 打开 `http://127.0.0.1:5173`

讲解：

> 这里是 RepoMentor 的用户入口。它面向第一次进入陌生仓库的新贡献者。

### 2. 输入 GitHub 仓库 URL

操作：

- 输入一个公开 GitHub 仓库链接。

讲解：

> 用户只需要提供仓库 URL，不需要手动告诉系统入口文件、测试命令或文档路径。

### 3. 点击 analyze

操作：

- 点击“分析”。
- 等待仓库解析完成。

讲解：

> 后端会启动多个 Worker，解析文件、符号、文档、测试、Issue、开发流程和命令，先建立 Repository Intelligence Graph。

### 4. 展示仓库概览

操作：

- 展示仓库概览区域。

讲解：

> 仓库概览回答“这个项目是什么、从哪里开始看、怎么安装、怎么启动、怎么测试”。

### 5. 展示学习路径

操作：

- 点击“学习路径”。

讲解：

> 学习路径把项目目标、入口文件、核心模块、测试边界和开发流程组织成可执行顺序。

### 6. 展示开发流程

操作：

- 点击“开发流程”。

讲解：

> 这里展示安装、运行、测试、PR、CI 和风险提示。缺失信息会作为不确定项显示，不会让模型编造。

### 7. 展示推荐任务

操作：

- 点击“推荐任务”。

讲解：

> 如果 GitHub open issue 为 0，系统会生成 internal first tasks，并明确标记它们不是 GitHub Issue。

### 8. 在 QA 输入问题

操作：

- 在 QA 输入：`这个项目怎么启动？`

讲解：

> 现在我们用自然语言问一个新贡献者最常问的问题：这个项目怎么启动？

### 9. 展示回答和 evidence

操作：

- 展示回答中的推荐启动方式、命令、风险提示和证据来源。

讲解：

> 回答不是凭空生成的。它会引用 README、命令解析、RepositoryGraph 或相关文件作为 evidence。

### 10. 切换到 Debug Console

操作：

- 点击“调试控制台”。

讲解：

> 用户页隐藏了内部细节。现在切到调试控制台，看完整执行轨迹。

### 11. 展示 Agent Flow

讲解：

> Agent Flow 展示 Orchestrator 如何调度不同 Worker，以及每个阶段是否有输出。

### 12. 展示 Data Layer

讲解：

> Data Layer 展示 Repository Intelligence Graph，包括 files、symbols、tests、docs、quality commands 和 development workflow。

### 13. 展示 SelfCheck

讲解：

> SelfCheck 会检查回答是否有足够证据，是否存在命令幻觉，是否需要补充检索。

### 14. 展示 FinalAnswer JSON

讲解：

> FinalAnswer JSON 是最终结构化输出，包含 conclusion、steps、risks、verifiable commands、evidence 和 self_check。

### 15. 回到 PPT 第 7 页说明压力测试结果

讲解：

> 压力测试不是为了隐藏问题。结果显示系统链路没有崩溃，QA 成功率 100%，但 evidence coverage 只有 50%，低于 85% 验收线。因此下一步重点是 EvidenceBuilder，而不是继续堆功能。
